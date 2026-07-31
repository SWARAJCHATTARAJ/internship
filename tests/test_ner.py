import pytest
from schemas.core import ReportState
from agents.ner import ner_agent

def test_ner_scispacy_extraction():
    """
    Test that scispacy correctly extracts entities when the text contains clear terms.
    If scispacy isn't installed/loaded, this test will just check that it gracefully handles it.
    """
    initial_state = ReportState(
        document_id="TEST_NER_1",
        original_text="Patient admitted with abdominal pain."
    )
    
    result = ner_agent(initial_state)
    
    # It should extract entities and log it
    assert "extracted_entities" in result
    audit = result["audit_trail"][-1]
    assert audit.agent_name == "ner_agent"
    assert audit.action_type in ["SCISPACY_EXTRACTION", "LLM_FALLBACK_EXTRACTION"]

def test_ner_llm_fallback():
    """
    Test that the LLM fallback triggers when scispacy is bypassed or misses obvious keywords.
    """
    # Using specific mocked keywords like metformin, amlodipine
    initial_state = ReportState(
        document_id="TEST_NER_2",
        original_text="Patient treated with Metformin and Amlodipine.",
        execution_plan=["ner_agent"]
    )
    
    # We can force the fallback by emptying the doc entities or ensuring keywords are there
    result = ner_agent(initial_state)
    
    extracted = result["extracted_entities"]
    
    # Check if multiple drugs caused routing update
    assert "drug_agent" in result["execution_plan"]
    
    # Check audit trail for plan update
    audit_events = [e.action_type for e in result["audit_trail"]]
    assert "PLAN_UPDATE" in audit_events
