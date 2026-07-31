import pytest
from schemas.core import ReportState, ExtractedEntity
from agents.grounding import grounding_agent

def test_grounding_mapping():
    """
    Test that the grounding agent correctly maps entities to specific ontologies.
    """
    initial_state = ReportState(
        document_id="TEST_GRND_1",
        original_text="Patient admitted with abdominal pain. Diagnosed with Diabetes Mellitus. Treated with Metformin.",
        extracted_entities=[
            ExtractedEntity(id="E1", text="abdominal pain", label="SYMPTOM", start_char=22, end_char=36),
            ExtractedEntity(id="E2", text="Diabetes Mellitus", label="DIAGNOSIS", start_char=53, end_char=70),
            ExtractedEntity(id="E3", text="Metformin", label="MEDICATION", start_char=85, end_char=94)
        ]
    )
    
    result = grounding_agent(initial_state)
    
    assert "extracted_entities" in result
    entities = result["extracted_entities"]
    
    # Check that all entities have been grounded
    assert all(e.grounding is not None for e in entities)
    
    # Check specific mocked mappings
    pain = next(e for e in entities if e.text == "abdominal pain")
    assert pain.grounding.ontology == "SNOMED"
    assert pain.grounding.code == "21522001"
    
    diabetes = next(e for e in entities if e.text == "Diabetes Mellitus")
    assert diabetes.grounding.ontology == "SNOMED"
    assert diabetes.grounding.code == "73211009"
    
    metformin = next(e for e in entities if e.text == "Metformin")
    assert metformin.grounding.ontology == "RxNorm"
    assert metformin.grounding.code == "860975"
    
    # Check audit trail
    audit = result["audit_trail"][-1]
    assert audit.agent_name == "grounding_agent"
    assert audit.action_type == "GROUNDING_MAPPING"
    assert "Successfully mapped 3 entities" in audit.details["message"]
