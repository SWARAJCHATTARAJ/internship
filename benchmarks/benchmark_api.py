"""Concurrent API measurements over an in-process FastAPI app with no persistence."""

from __future__ import annotations

import asyncio
import mimetypes
import time

from benchmarks.common import documents_for
from benchmarks.config import BenchmarkConfig, BenchmarkResult
from benchmarks.metrics import latency_summary, throughput
from benchmarks.resource_monitor import ResourceMonitor
from benchmarks.runtime import benchmark_runtime


async def _request_batch(config: BenchmarkConfig, documents: list, result: BenchmarkResult) -> tuple[list[float], list[int], int]:
    import httpx
    import api.main as api_main
    from unittest.mock import patch

    latencies: list[float] = []
    statuses: list[int] = []
    timeouts = 0
    semaphore = asyncio.Semaphore(config.workers)
    transport = httpx.ASGITransport(app=api_main.app)

    async def request_one(client: httpx.AsyncClient, document: object, index: int) -> None:
        nonlocal timeouts
        document_id = f"BENCH-{config.seed}-{index:06d}"
        started = time.perf_counter()
        async with semaphore:
            try:
                source_path = document.source_path
                if source_path is not None and source_path.suffix.lower() in {
                    ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
                }:
                    mime_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
                    response_call = client.post(
                        "/process/upload",
                        data={"document_id": document_id},
                        files={"file": (source_path.name, source_path.read_bytes(), mime_type)},
                    )
                else:
                    text = document.text
                    if not text and source_path is not None:
                        text = source_path.read_text(encoding="utf-8")
                    response_call = client.post(
                        "/process", json={"document_id": document_id, "text": text}
                    )
                response = await asyncio.wait_for(
                    response_call,
                    timeout=config.timeout,
                )
                statuses.append(response.status_code)
            except (asyncio.TimeoutError, httpx.TimeoutException):
                timeouts += 1
                statuses.append(0)
            except Exception as exc:
                result.errors.append({"document_id": document_id, "error": str(exc)})
                statuses.append(0)
            finally:
                latencies.append(time.perf_counter() - started)

    with patch.object(api_main, "save_report", lambda *_args, **_kwargs: None), \
         patch.object(api_main, "save_upload", lambda *_args, **_kwargs: None), \
         patch.object(api_main, "init_db", lambda *_args, **_kwargs: None):
        async with httpx.AsyncClient(transport=transport, base_url="http://benchmark.local") as client:
            await asyncio.gather(*(request_one(client, document, index) for index, document in enumerate(documents)))
    return latencies, statuses, timeouts


def run(config: BenchmarkConfig) -> BenchmarkResult:
    documents, source = documents_for(config)
    result = BenchmarkResult("api")
    if not documents:
        result.warnings.append("No API input documents found.")
        return result
    documents = [documents[index % len(documents)] for index in range(config.documents)]

    with benchmark_runtime(config.mode, config.timeout), ResourceMonitor() as monitor:
        started = time.perf_counter()
        latencies, statuses, timeouts = asyncio.run(_request_batch(config, documents, result))
        total_time = time.perf_counter() - started

    requests = len(statuses)
    successes = sum(200 <= status < 300 for status in statuses)
    errors_4xx = sum(400 <= status < 500 for status in statuses)
    errors_5xx = sum(500 <= status < 600 for status in statuses)
    result.resource_metrics.append({"suite": "api", **monitor.snapshot().as_dict()})
    result.metrics = {
        "endpoints": ["POST /process", "POST /process/upload"],
        "execution_scope": "in-process FastAPI ASGI transport; persistence methods disabled",
        "requests": requests,
        "concurrency": config.workers,
        "requests_per_second": throughput(requests, total_time),
        **latency_summary(latencies),
        "http_4xx_errors": errors_4xx,
        "http_5xx_errors": errors_5xx,
        "request_error_count": sum(status == 0 for status in statuses) - timeouts,
        "timeout_count": timeouts,
        "timeout_rate": timeouts / requests if requests else None,
        "success_count": successes,
        "success_rate": successes / requests if requests else None,
        "dataset_source": source,
        "elapsed_seconds": total_time,
    }
    if config.mode == "mock":
        result.warnings.append("Mock mode disables pretrained/external inference; API persistence is stubbed to protect application data.")
    result.warnings.append(
        "FastAPI's /process handler executes the agent graph synchronously; concurrent clients may be serialized by the event loop."
    )
    return result
