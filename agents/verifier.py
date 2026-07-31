import uuid
from schemas.core import ReportState, VerifierFlag, AuditEvent

def verifier_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    flags = list(state.verifier_flags)
    
    medications = [e.text.lower() for e in state.extracted_entities if e.label == "MEDICATION"]
    
    # Mock Ruleset
    # Rule 1: Aspirin + Ibuprofen contradiction
    if "aspirin" in medications and "ibuprofen" in medications:
        # Check if already flagged to avoid duplicates if replanning
        already_flagged = any(f.check_type == "DRUG_PLAUSIBILITY" for f in flags)
        if not already_flagged:
            flags.append(VerifierFlag(
                id=f"V_FLAG_{uuid.uuid4().hex[:8]}",
                check_type="DRUG_PLAUSIBILITY",
                status="NEEDS_REVIEW",
                justification="Concurrent use of Aspirin and Ibuprofen detected. May increase bleeding risk and decrease cardioprotective effect of Aspirin.",
                confidence_score=0.9
            ))
        
    # Log to audit trail
    audit_trail.append(AuditEvent(
        agent_name="verifier_agent",
        action_type="VERIFICATION_CHECK",
        details={"message": f"Performed safety checks. Raised {len(flags) - len(state.verifier_flags)} new flags."}
    ))
    
    return {
        "verifier_flags": flags,
        "audit_trail": audit_trail
    }
