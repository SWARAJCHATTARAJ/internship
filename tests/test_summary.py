import pytest
from schemas.core import ReportState, ExtractedEntity, Relation, GroundedConcept
from agents.summary import summary_agent

def test_summary_generation():
    """
    Test that the summary agent correctly generates a markdown string.
    """
    pain_entity = ExtractedEntity(id="E1", text="abdominal pain", label="SYMPTOM", start_char=22, end_char=36)
    pain_entity.grounding = GroundedConcept(ontology="SNOMED", code="21522001", name="Abdominal pain")
    
    met_entity = ExtractedEntity(id="E2", text="Metformin", label="MEDICATION", start_char=85, end_char=94)
    met_entity.grounding = GroundedConcept(ontology="RxNorm", code="860975", name="Metformin")
    
    rel = Relation(id="R1", source_entity_id="E2", target_entity_id="E1", relation_type="TREATS")
    
    initial_state = ReportState(
        document_id="TEST_SUM_1",
        original_text="Patient admitted with abdominal pain. Treated with Metformin.",
        extracted_entities=[pain_entity, met_entity],
        relations=[rel]
    )
    
    result = summary_agent(initial_state)
    
    assert "summary" in result
    summary = result["summary"]
    
    assert "## Clinical Summary" in summary
    assert "abdominal pain" in summary
    assert "SNOMED: 21522001" in summary
    assert "Metformin" in summary
    assert "RxNorm: 860975" in summary
    assert "Metformin **TREATS** abdominal pain" in summary
    
    # Check audit trail
    audit = result["audit_trail"][-1]
    assert audit.agent_name == "summary_agent"
    assert audit.action_type == "SUMMARY_GENERATION"
