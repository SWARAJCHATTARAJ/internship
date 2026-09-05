"""Builds an evidence-oriented final response; it does not add medical facts."""
from schemas.core import AuditEvent, ReportState


def finalizer_agent(state: ReportState) -> dict:
    entities = state.extracted_entities
    flags = state.verifier_flags
    unresolved = [flag for flag in flags if not flag.resolved]
    provenance = {
        entity.id: {"text": entity.text, "label": entity.label, "evidence": entity.provenance.model_dump() if entity.provenance else None}
        for entity in entities
    }
    grounded = [entity.model_dump() for entity in entities if entity.grounding]
    agent_outputs = {
        "document": state.document_analysis.model_dump() if state.document_analysis else {},
        "ocr": state.ocr_result.model_dump() if state.ocr_result else None,
        "ner": [entity.model_dump() for entity in entities],
        "medication": [record.model_dump() for record in state.medications],
        "clinical_context": state.clinical_context,
        "relation": [relation.model_dump() for relation in state.relations],
        "timeline": [event.model_dump() for event in state.timeline],
        "grounding": grounded,
        "summary": state.summary,
        "verifier": {"status": "HITL_REQUIRED" if unresolved else "PASS", "flags": [flag.model_dump() for flag in flags]},
    }
    trace_order = ["document", "ocr", "orchestrator", "ner", "medication", "clinical_context", "relation", "timeline", "grounding", "summary", "verifier"]
    plan_names = {name.replace("_agent", "") for name in state.execution_plan}
    if state.ocr_result:
        plan_names.add("ocr")
    trace = []
    for step, agent in enumerate(trace_order, start=1):
        if agent == "document":
            status, reason = "completed", "Document characterization completed before orchestration."
        elif agent == "orchestrator":
            status, reason = "completed", "Selected the minimum evidence-based agent plan."
        elif agent in plan_names:
            status, reason = "completed", "Dispatched by the orchestrator."
        elif agent == "ocr" and state.document_analysis:
            status, reason = "not_dispatched", "Native text detected; OCR was not required."
        else:
            status, reason = "not_dispatched", "Not required for this document."
        trace.append({"step": step, "agent": agent, "status": status, "reason": reason, "output": agent_outputs.get(agent)})
    replans = [event.details for event in state.audit_trail if event.action_type == "REPLANNING"]
    final_result = {
        "research_demo_only": True,
        "disclaimer": "Document understanding output only; it is not a diagnosis, prescription, or clinical decision.",
        "document": state.document_analysis.model_dump() if state.document_analysis else {},
        "ocr": {"used": state.ocr_result is not None, "confidence": state.ocr_result.overall_confidence if state.ocr_result else None},
        "diagnoses": [entity.model_dump() for entity in entities if entity.label == "DIAGNOSIS"],
        "symptoms": [entity.model_dump() for entity in entities if entity.label == "SYMPTOM"],
        "medications": [record.model_dump() for record in state.medications],
        "relations": [relation.model_dump() for relation in state.relations],
        "grounded_concepts": grounded,
        "external_medical_knowledge": [], "inferences": [],
        "uncertainties": [flag.model_dump() for flag in unresolved if flag.check_type == "OCR_UNCERTAINTY"],
        "contradictions": [flag.model_dump() for flag in unresolved if flag.check_type == "DOSAGE_CONTRADICTION"],
        "verification": {"status": "HITL_REQUIRED" if unresolved else "PASS", "flags": [flag.model_dump() for flag in flags]},
        "hitl_flags": [flag.model_dump() for flag in unresolved],
        "provenance": provenance,
        "audit_reference": {"document_id": state.document_id, "event_count": len(state.audit_trail) + 1},
    }
    audit = state.audit_trail.copy()
    audit.append(AuditEvent(agent_name="finalizer_agent", action_type="FINAL_OUTPUT", details={
        "verification_status": final_result["verification"]["status"], "claim_count": len(provenance),
    }))
    return {"final_result": final_result, "agent_outputs": agent_outputs, "execution_trace": trace, "replans": replans, "audit_trail": audit}
