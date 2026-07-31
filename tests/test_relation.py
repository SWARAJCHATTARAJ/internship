import pytest
from schemas.core import ReportState, ExtractedEntity
from agents.relation import relation_agent

def test_relation_extraction():
    """
    Test that the relation agent successfully links MEDICATION to DIAGNOSIS/SYMPTOM.
    """
    initial_state = ReportState(
        document_id="TEST_REL_1",
        original_text="Patient admitted with abdominal pain. Diagnosed with Diabetes Mellitus. Treated with Metformin.",
        extracted_entities=[
            ExtractedEntity(id="E1", text="abdominal pain", label="SYMPTOM", start_char=22, end_char=36, extraction_source="LLM_fallback"),
            ExtractedEntity(id="E2", text="Diabetes Mellitus", label="DIAGNOSIS", start_char=53, end_char=70, extraction_source="LLM_fallback"),
            ExtractedEntity(id="E3", text="Metformin", label="MEDICATION", start_char=85, end_char=94, extraction_source="LLM_fallback")
        ]
    )
    
    result = relation_agent(initial_state)
    
    assert "relations" in result
    relations = result["relations"]
    
    # Metformin should TREAT both abdominal pain and Diabetes Mellitus according to our mocked logic
    assert len(relations) == 2
    
    for r in relations:
        assert r.source_entity_id == "E3" # Metformin
        assert r.target_entity_id in ["E1", "E2"]
        assert r.relation_type == "TREATS"
        
    audit = result["audit_trail"][-1]
    assert audit.agent_name == "relation_agent"
    assert audit.action_type == "RELATION_EXTRACTION"
