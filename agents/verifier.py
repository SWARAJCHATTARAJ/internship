import uuid
from schemas.core import ReportState, VerifierFlag, AuditEvent
from tools.fhir_validator import validate_fhir_draft


def verifier_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    flags = list(state.verifier_flags)

    medications = [e.text.lower() for e in state.extracted_entities if e.label == "MEDICATION"]

    if "aspirin" in medications and "ibuprofen" in medications:
        already_flagged = any(f.check_type == "DRUG_PLAUSIBILITY" for f in flags)
        if not already_flagged:
            flags.append(VerifierFlag(
                id=f"V_FLAG_{uuid.uuid4().hex[:8]}",
                check_type="DRUG_PLAUSIBILITY",
                status="NEEDS_REVIEW",
                justification="Concurrent use of Aspirin and Ibuprofen detected. May increase bleeding risk and decrease cardioprotective effect of Aspirin.",
                confidence_score=0.9
            ))

    if state.fhir_draft:
        validation_errors = validate_fhir_draft(state.fhir_draft)
        if validation_errors:
            already_flagged = any(f.check_type == "FHIR_SCHEMA" for f in flags)
            if not already_flagged:
                flags.append(VerifierFlag(
                    id=f"V_FLAG_{uuid.uuid4().hex[:8]}",
                    check_type="FHIR_SCHEMA",
                    status="NEEDS_REVIEW",
                    justification="FHIR draft validation failed: " + "; ".join(validation_errors),
                    confidence_score=0.8,
                ))

    if state.ocr_result and (state.ocr_result.overall_confidence is None or state.ocr_result.overall_confidence < 0.75):
        if not any(f.check_type == "OCR_UNCERTAINTY" for f in flags):
            flags.append(VerifierFlag(
                id=f"V_FLAG_{uuid.uuid4().hex[:8]}", check_type="OCR_UNCERTAINTY", status="NEEDS_REVIEW",
                justification="OCR confidence is too low for reliable clinical interpretation; review the source document.",
                confidence_score=0.9,
            ))

    doses_by_drug = {}
    for medication in state.medications:
        if medication.dose:
            doses_by_drug.setdefault(medication.drug.lower(), set()).add(medication.dose.lower())
    for drug, doses in doses_by_drug.items():
        if len(doses) > 1 and not any(f.check_type == "DOSAGE_CONTRADICTION" for f in flags):
            flags.append(VerifierFlag(
                id=f"V_FLAG_{uuid.uuid4().hex[:8]}", check_type="DOSAGE_CONTRADICTION", status="CONTRADICTION",
                justification=f"Conflicting documented doses for {drug}: {', '.join(sorted(doses))}. Human review is required.",
                confidence_score=0.95,
            ))

    audit_trail.append(AuditEvent(
        agent_name="verifier_agent",
        action_type="VERIFICATION_CHECK",
        details={"message": f"Performed safety checks. Raised {len(flags) - len(state.verifier_flags)} new flags."}
    ))

    return {
        "verifier_flags": flags,
        "audit_trail": audit_trail,
    }
