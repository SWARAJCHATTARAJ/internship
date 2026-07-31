import uuid
from typing import List
from schemas.core import ReportState, Relation, AuditEvent

def mock_relation_extraction(entities: list) -> List[Relation]:
    """
    Simulates relation extraction between clinical entities.
    For this mocked phase, we assume any MEDICATION extracted
    TREATS any DIAGNOSIS or SYMPTOM found in the same report.
    """
    relations = []
    
    medications = [e for e in entities if e.label == "MEDICATION"]
    conditions = [e for e in entities if e.label in ["DIAGNOSIS", "SYMPTOM"]]
    
    for med in medications:
        for cond in conditions:
            # We assume a TREATS relationship for demonstration
            rel = Relation(
                id=f"R_MOCK_{uuid.uuid4().hex[:8]}",
                source_entity_id=med.id,
                target_entity_id=cond.id,
                relation_type="TREATS"
            )
            relations.append(rel)
            
    return relations

def relation_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    extracted_entities = state.extracted_entities
    existing_relations = list(state.relations)
    
    # 1. Extract relationships using mocked logic
    new_relations = mock_relation_extraction(extracted_entities)
    existing_relations.extend(new_relations)
    
    # 2. Log to audit trail
    audit_trail.append(AuditEvent(
        agent_name="relation_agent",
        action_type="RELATION_EXTRACTION",
        details={"message": f"Extracted {len(new_relations)} relations between entities."}
    ))
    
    return {
        "relations": existing_relations,
        "audit_trail": audit_trail
    }
