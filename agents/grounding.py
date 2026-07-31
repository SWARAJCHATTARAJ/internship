from schemas.core import ReportState, GroundedConcept, AuditEvent

def mock_ontology_mapping(text: str, label: str) -> GroundedConcept:
    """
    Mocked lookup for ontology mapping.
    Maps MEDICATION to RxNorm and DIAGNOSIS/SYMPTOM to SNOMED.
    """
    text_lower = text.lower()
    
    # Mock RxNorm
    if label == "MEDICATION":
        if "metformin" in text_lower:
            return GroundedConcept(ontology="RxNorm", code="860975", name="Metformin")
        if "amlodipine" in text_lower:
            return GroundedConcept(ontology="RxNorm", code="17767", name="Amlodipine")
        if "aspirin" in text_lower:
            return GroundedConcept(ontology="RxNorm", code="1191", name="Aspirin")
        return GroundedConcept(ontology="RxNorm", code="00000", name=text)
        
    # Mock SNOMED
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
    extracted_entities = list(state.extracted_entities)
    
    mapped_count = 0
    
    # Map each extracted entity to a grounded concept
    for entity in extracted_entities:
        if entity.grounding is None:
            concept = mock_ontology_mapping(entity.text, entity.label)
            entity.grounding = concept
            mapped_count += 1
            
    # Log to audit trail
    audit_trail.append(AuditEvent(
        agent_name="grounding_agent",
        action_type="GROUNDING_MAPPING",
        details={"message": f"Successfully mapped {mapped_count} entities to standard ontologies."}
    ))
    
    return {
        "extracted_entities": extracted_entities,
        "audit_trail": audit_trail
    }
