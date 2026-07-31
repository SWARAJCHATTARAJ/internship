from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AuditEvent:
    """
    Represents a single action or thought within our system.
    This is the core of our "Agentic Observability". Instead of a black box,
    we log exactly what the agent thought and did.
    """
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_name: str = ""       # e.g., "Orchestrator", "Verifier", "ExtractionAgent"
    action_type: str = ""      # e.g., "THOUGHT", "TOOL_CALL", "ROUTING", "ERROR"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ClinicalDocumentState:
    """
    Holds the state of a clinical document as it moves through our multi-agent system.
    """
    document_id: str
    original_text: str
    document_type: str = "UNKNOWN"  # e.g., "Short Clinic Letter", "Discharge Summary"
    
    # The dynamically generated plan by the Orchestrator
    execution_plan: List[str] = field(default_factory=list) 
    
    # Extracted data and summaries added by worker agents
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    
    # The queryable trace of everything that happened
    audit_trail: List[AuditEvent] = field(default_factory=list)

    def add_audit_event(self, agent_name: str, action_type: str, details: Dict[str, Any]):
        """Helper method to append a new event to our audit trail."""
        event = AuditEvent(
            agent_name=agent_name,
            action_type=action_type,
            details=details
        )
        self.audit_trail.append(event)


class OrchestratorAgent:
    """
    The Orchestrator reads the document and dynamically decides the execution plan.
    Instead of hardcoding a pipeline, it 'thinks' and 'routes'.
    """
    def __init__(self):
        self.agent_name = "Orchestrator"

    def process(self, doc_state: ClinicalDocumentState) -> ClinicalDocumentState:
        # 1. THOUGHT PHASE: Analyze the document
        text_length = len(doc_state.original_text.split())
        
        # We simulate LLM reasoning (in a real system, we'd prompt an LLM here)
        if text_length < 20:
            doc_type = "Short Clinic Letter"
            reasoning = "Document is very short. Likely a quick update or prescription note. Needs extraction and medication check."
            plan = ["ExtractionAgent", "MedicationVerifier"]
        else:
            doc_type = "Complex Discharge Summary"
            reasoning = "Document is long and complex. Needs full extraction, summarization, medication check, and cross-reference verification."
            plan = ["ExtractionAgent", "SummarizationAgent", "MedicationVerifier", "CrossReferenceVerifier"]

        # Log the thought process (Agentic Observability!)
        doc_state.add_audit_event(
            agent_name=self.agent_name,
            action_type="THOUGHT",
            details={"reasoning": reasoning, "detected_type": doc_type}
        )

        # 2. ROUTING PHASE: Update the state and log the routing
        doc_state.document_type = doc_type
        doc_state.execution_plan = plan
        
        doc_state.add_audit_event(
            agent_name=self.agent_name,
            action_type="ROUTING",
            details={"assigned_agents": plan}
        )
        
        return doc_state

# Quick test to show how it works
if __name__ == "__main__":
    orchestrator = OrchestratorAgent()

    print("--- Processing Short Document ---")
    short_doc = ClinicalDocumentState(
        document_id="DOC_SHORT",
        original_text="Patient presents with mild hypertension. Prescribed Lisinopril 10mg."
    )
    orchestrator.process(short_doc)
    
    for event in short_doc.audit_trail:
        print(f"[{event.timestamp}] {event.agent_name} -> {event.action_type}: {event.details}")

    print("\n--- Processing Long Document ---")
    # Multiplying a string to make it artificially long for our heuristic
    long_text = "Patient was admitted on 10/12 for shortness of breath and chest pain. " * 5 
    long_doc = ClinicalDocumentState(
        document_id="DOC_LONG",
        original_text=long_text
    )
    orchestrator.process(long_doc)
    
    for event in long_doc.audit_trail:
        print(f"[{event.timestamp}] {event.agent_name} -> {event.action_type}: {event.details}")
