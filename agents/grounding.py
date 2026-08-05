from schemas.core import ReportState, GroundedConcept, AuditEvent
from tools.ontology_index import retrieve_best_match


def mock_ontology_mapping(text: str, label: str) -> GroundedConcept:
    """Simple fallback ontology mapping used when the RAG index is unavailable."""
    text_lower = text.lower()

    if label == "MEDICATION":
        if "metformin" in text_lower:
            return GroundedConcept(ontology="RxNorm", code="860975", name="Metformin")
        if "amlodipine" in text_lower:
            return GroundedConcept(ontology="RxNorm", code="17767", name="Amlodipine")
        if "aspirin" in text_lower:
            return GroundedConcept(ontology="RxNorm", code="1191", name="Aspirin")
        return GroundedConcept(ontology="RxNorm", code="00000", name=text)

    if label in ["DIAGNOSIS", "SYMPTOM"]:
        if "diabetes" in text_lower:
            return GroundedConcept(ontology="SNOMED", code="73211009", name="Diabetes mellitus")
        if "abdominal pain" in text_lower:
            return GroundedConcept(ontology="SNOMED", code="21522001", name="Abdominal pain")
        if "hypertension" in text_lower:
            return GroundedConcept(ontology="SNOMED", code="38341003", name="Hypertensive disorder")
        if "myocardial infarction" in text_lower or "heart attack" in text_lower:
            return GroundedConcept(ontology="SNOMED", code="22298006", name="Myocardial infarction")
        return GroundedConcept(ontology="SNOMED", code="00000", name=text)

    return GroundedConcept(ontology="UNKNOWN", code="00000", name=text)


def grounding_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    extracted_entities = [entity.model_copy(deep=True) for entity in state.extracted_entities]

    mapped_count = 0
    ungrounded_count = 0
    mode_used = "rag"

    for entity in extracted_entities:
        if entity.grounding is None:
            concept, mode, similarity = retrieve_best_match(entity.text, entity.label)
            mode_used = mode if mode == "fallback" else mode_used
            if concept is not None and similarity >= 0.35:
                entity.grounding = concept
                mapped_count += 1
            else:
                fallback_concept = mock_ontology_mapping(entity.text, entity.label)
                if fallback_concept.code != "00000" and mode == "fallback":
                    entity.grounding = fallback_concept
                    mapped_count += 1
                else:
                    entity.grounding = None
                    ungrounded_count += 1

    audit_trail.append(AuditEvent(
        agent_name="grounding_agent",
        action_type="GROUNDING_MAPPING",
        details={
            "message": f"Successfully mapped {mapped_count} entities to standard ontologies.",
            "mode": mode_used,
            "ungrounded": ungrounded_count,
        }
    ))

    return {
        "extracted_entities": extracted_entities,
        "audit_trail": audit_trail,
    }
