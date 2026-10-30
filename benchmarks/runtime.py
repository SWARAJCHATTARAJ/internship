"""Runtime controls shared by offline and real benchmark modes."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
import os
import sys
from typing import Iterator
from unittest.mock import patch


@contextmanager
def benchmark_runtime(mode: str, timeout_seconds: float = 30.0) -> Iterator[None]:
    """Disable external/model downloads for mock mode, retaining local fallbacks."""
    if mode == "real":
        import tools.llm_client as llm_client

        missing = object()
        env_keys = ("HF_HUB_ETAG_TIMEOUT", "HF_HUB_DOWNLOAD_TIMEOUT")
        previous = {key: os.environ.get(key, missing) for key in env_keys}
        for key in env_keys:
            os.environ[key] = str(max(1, int(timeout_seconds)))

        original_json_call = llm_client.call_gemini_json
        original_transcribe = llm_client.transcribe_clinical_image

        def call_json(prompt: str, model: str = "gemini-3.1-flash-lite", timeout: int | None = None):
            effective_timeout = min(timeout, timeout_seconds) if timeout is not None else timeout_seconds
            return original_json_call(prompt, model=model, timeout=max(1, int(effective_timeout)))

        def transcribe(
            image_bytes: bytes,
            mime_type: str = "image/jpeg",
            model: str = "gemini-3.1-flash-lite",
            timeout: int | None = None,
        ):
            effective_timeout = min(timeout, timeout_seconds) if timeout is not None else timeout_seconds
            return original_transcribe(
                image_bytes, mime_type=mime_type, model=model,
                timeout=max(1, int(effective_timeout)),
            )

        try:
            with ExitStack() as stack:
                stack.enter_context(patch.object(llm_client, "call_gemini_json", call_json))
                stack.enter_context(patch.object(llm_client, "transcribe_clinical_image", transcribe))
                yield
        finally:
            for key, value in previous.items():
                if value is missing:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return

    missing = object()
    previous_spacy = sys.modules.get("spacy", missing)
    sys.modules["spacy"] = None
    try:
        with ExitStack() as stack:
            import agents.ner as ner
            import agents.relation as relation
            import tools.llm_client as llm_client
            import agents.grounding as grounding

            stack.enter_context(patch.object(ner, "nlp", None))
            stack.enter_context(patch.object(ner, "find_huggingface_entities", return_value=[]))
            stack.enter_context(patch.object(relation, "_huggingface_relations", return_value=[]))
            stack.enter_context(patch.object(llm_client, "get_api_key", return_value=None))
            stack.enter_context(patch.object(llm_client, "call_gemini_json", return_value=None))
            stack.enter_context(patch.object(llm_client, "transcribe_clinical_image", return_value=None))
            stack.enter_context(patch.object(
                grounding,
                "retrieve_best_matches",
                side_effect=lambda texts: [(None, "fallback", 0.0) for _ in texts],
            ))
            yield
    finally:
        if previous_spacy is missing:
            sys.modules.pop("spacy", None)
        else:
            sys.modules["spacy"] = previous_spacy


def model_inventory() -> dict[str, str]:
    """Names configured in source; this does not assert that a model was loaded."""
    return {
        "ner": "d4data/biomedical-ner-all; optional custom_medical_ner or en_core_sci_sm",
        "relation": "wesin/pubmedbert-relation-extraction",
        "grounding": "NeuML/biomedbert-base-embeddings; Chroma index may use all-MiniLM-L6-v2",
        "vision_ocr": "Gemini gemini-3.1-flash-lite, gemini-2.5-flash, gemini-2.0-flash",
        "local_ocr": "winocr on Windows or Tesseract",
    }
