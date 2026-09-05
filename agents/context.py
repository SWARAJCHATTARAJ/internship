"""Classifies document evidence as explicit diagnosis, symptom, or unknown; it does not diagnose."""
from schemas.core import AuditEvent, ReportState


def clinical_context_agent(state: ReportState) -> dict:
    contexts = []
    text = state.original_text.lower()
    for entity in state.extracted_entities:
        if entity.label not in {"DIAGNOSIS", "SYMPTOM"}:
            continue
        before = text[max(0, entity.start_char - 40):entity.start_char]
        classification = "explicit_diagnosis" if entity.label == "DIAGNOSIS" and any(k in before for k in ("diagnosis", "diagnosed", "assessment")) else ("symptom" if entity.label == "SYMPTOM" else "document_mention")
        contexts.append({"entity_id": entity.id, "classification": classification, "source": "document", "confidence": entity.confidence})
    audit = state.audit_trail.copy()
    audit.append(AuditEvent(agent_name="clinical_context_agent", action_type="CONTEXT_CLASSIFICATION", details={"count": len(contexts), "no_inference": True}))
    return {"clinical_context": contexts, "audit_trail": audit}
