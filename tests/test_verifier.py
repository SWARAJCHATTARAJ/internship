import pytest
from schemas.core import ReportState, ExtractedEntity
from agents.verifier import verifier_agent

def test_verifier_plausibility_flag():
    """
    Test that the verifier agent correctly flags the mock Aspirin+Ibuprofen contradiction.
    """
    initial_state = ReportState(
        document_id="TEST_VER_1",
        original_text="Patient takes Aspirin and Ibuprofen.",
        extracted_entities=[
            ExtractedEntity(id="E1", text="Aspirin", label="MEDICATION", start_char=14, end_char=21),
            ExtractedEntity(id="E2", text="Ibuprofen", label="MEDICATION", start_char=26, end_char=35)
        ]
    )
    
    result = verifier_agent(initial_state)
    
    assert "verifier_flags" in result
    flags = result["verifier_flags"]
    
    assert len(flags) == 1
    flag = flags[0]
    
    assert flag.check_type == "DRUG_PLAUSIBILITY"
    assert flag.status == "NEEDS_REVIEW"
    assert "Aspirin and Ibuprofen" in flag.justification
    
    # Check audit trail
    audit = result["audit_trail"][-1]
    assert audit.agent_name == "verifier_agent"
    assert audit.action_type == "VERIFICATION_CHECK"
    assert "Raised 1 new flags" in audit.details["message"]

def test_verifier_no_flags():
    """
    Test that the verifier agent does not raise flags for safe states.
    """
    initial_state = ReportState(
        document_id="TEST_VER_2",
        original_text="Patient takes Metformin.",
        extracted_entities=[
            ExtractedEntity(id="E1", text="Metformin", label="MEDICATION", start_char=14, end_char=23)
        ]
    )
    
    result = verifier_agent(initial_state)
    
    assert len(result["verifier_flags"]) == 0
