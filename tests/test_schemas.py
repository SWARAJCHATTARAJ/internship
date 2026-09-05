import pytest
from schemas.core import ReportState, ExtractedEntity, GroundedConcept

def test_report_state_initialization():
    state = ReportState(
        document_id="test_001",
        original_text="Patient has a headache."
    )
    assert state.document_id == "test_001"
    assert state.original_text == "Patient has a headache."
    assert len(state.execution_plan) == 0

def test_extracted_entity_validation():
    entity = ExtractedEntity(
        text="headache",
        label="SYMPTOM",
        start_char=14,
        end_char=22,
        grounding=GroundedConcept(
            ontology="SNOMED",
            code="25064002",
            name="Headache"
        )
    )
    assert entity.label == "SYMPTOM"
    assert entity.grounding is not None
    assert entity.grounding.ontology == "SNOMED"

def test_invalid_entity_label_raises_error():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ExtractedEntity(
            text="headache",
            label="NOT_A_VALID_LABEL",  # pyright: ignore[reportArgumentType]
            start_char=0,
            end_char=8
        )
