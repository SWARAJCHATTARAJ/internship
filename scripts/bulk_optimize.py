import os
import sys
import concurrent.futures
from typing import List, Dict, Any
from time import time

# Add root directory to python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.data_loader import DataLoader
from schemas.core import ReportState
from agents.orchestrator import graph
from data.db import save_report

DATASET_PATH = os.path.join(os.path.dirname(__file__), '..', 'dataset', 'clinical_dataset_100k.xlsx')

def process_single_report(report_data: Dict[str, Any]) -> dict:
    """
    Process a single report through the LangGraph pipeline.
    """
    initial_state = ReportState(
        document_id=report_data["document_id"],
        original_text=report_data["text"]
    )
    
    try:
        # invoke returns a dict in LangGraph when state is a Pydantic object wrapped/converted
        final_state = graph.invoke(initial_state)
        state_obj = ReportState(**final_state)
        save_report(state_obj)
        return {
            "document_id": report_data["document_id"],
            "status": "success",
            "audit_trail_length": len(final_state.get("audit_trail", [])),
            "execution_plan": final_state.get("execution_plan", []),
            "replan_count": final_state.get("replan_count", 0)
        }
    except Exception as e:
        return {
            "document_id": report_data["document_id"],
            "status": "error",
            "error_msg": str(e)
        }

def run_bulk_optimization(max_records: int = 10, max_workers: int = 4):
    """
    Runs the pipeline across the dataset concurrently.
    """
    print(f"Starting bulk optimization on max {max_records} records with {max_workers} workers...")
    start_time = time()
    
    loader = DataLoader(DATASET_PATH)
    
    results = []
    # Using ThreadPoolExecutor for concurrent I/O-bound tasks (like LLM calls in the future)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_single_report, report): report["document_id"]
            for report in loader.stream_reports(chunk_size=50, max_records=max_records)
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(futures):
            doc_id = futures[future]
            try:
                res = future.result()
                results.append(res)
                if res["status"] == "error":
                    print(f"[{doc_id}] ERROR: {res.get('error_msg')}")
                else:
                    print(f"[{doc_id}] SUCCESS | Plan: {res['execution_plan']} | Audit steps: {res['audit_trail_length']}")
            except Exception as exc:
                print(f"[{doc_id}] generated an exception: {exc}")
                
    elapsed = time() - start_time
    print(f"\nCompleted {len(results)} reports in {elapsed:.2f} seconds.")
    
    # In Phase 8, we will persist this to SQLite. For now, we just print the summary.
    successes = sum(1 for r in results if r.get("status") == "success")
    print(f"Success Rate: {successes}/{len(results)}")

if __name__ == "__main__":
    # For testing, we only process 10 records. We will scale this up in later phases.
    run_bulk_optimization(max_records=10, max_workers=2)
