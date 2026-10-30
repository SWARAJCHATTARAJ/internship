import uuid
from typing import List
import torch
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


def _marked_pair_text(text: str, source, target) -> str:
    first, second = sorted((source, target), key=lambda entity: entity.start_char)
    chunks = [
        (second.end_char, second.end_char, "[/E2]" if second is target else "[/E1]"),
        (second.start_char, second.start_char, "[E2]" if second is target else "[E1]"),
        (first.end_char, first.end_char, "[/E2]" if first is target else "[/E1]"),
        (first.start_char, first.start_char, "[E2]" if first is target else "[E1]"),
    ]
    marked = text
    for start, end, token in sorted(chunks, reverse=True):
        marked = marked[:start] + token + marked[end:]
    return marked


def _huggingface_relations(text: str, entities: list) -> List[Relation]:
    from tools.hf_models import get_relation_model

    tokenizer, model = get_relation_model()
    relations = []
    labels = {int(key): str(value).lower() for key, value in model.config.id2label.items()}
    relation_map = {
        "treats": "TREATS",
        "causes": "CAUSES",
        "associated_with": "INDICATES",
        "interacts_with": "CAUSES",
    }
    candidates = [
        (source, target)
        for index, source in enumerate(entities)
        for target in entities[index + 1:]
        if source.label == "MEDICATION" and target.label in {"DIAGNOSIS", "SYMPTOM"}
        or target.label == "MEDICATION" and source.label in {"DIAGNOSIS", "SYMPTOM"}
    ]
    for first, second in candidates[:100]:
        source, target = (first, second) if first.label == "MEDICATION" else (second, first)
        encoded = tokenizer(_marked_pair_text(text, source, target), return_tensors="pt", truncation=True, max_length=256)
        encoded = {key: value.to(model.device) for key, value in encoded.items()}
        with torch.no_grad():
            probabilities = torch.softmax(model(**encoded).logits, dim=-1)[0]
        class_id = int(torch.argmax(probabilities).item())
        relation_type = relation_map.get(labels.get(class_id, ""))
        confidence = float(probabilities[class_id].item())
        if relation_type and confidence >= 0.5:
            relations.append(Relation(
                id=f"R_HF_{uuid.uuid4().hex[:8]}",
                source_entity_id=source.id,
                target_entity_id=target.id,
                relation_type=relation_type,
                confidence=confidence,
            ))
    return relations

def relation_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    extracted_entities = state.extracted_entities
    existing_relations = list(state.relations)
    new_relations: List[Relation] = []
    model_used = False

    try:
        new_relations = _huggingface_relations(state.original_text, extracted_entities)
        if new_relations:
            model_used = True
            audit_trail.append(AuditEvent(
                agent_name="relation_agent",
                action_type="RELATION_EXTRACTION",
                details={"extracted_count": len(new_relations), "model": "wesin/pubmedbert-relation-extraction"},
            ))
    except Exception as exc:
        audit_trail.append(AuditEvent(
            agent_name="relation_agent",
            action_type="HUGGINGFACE_RELATION_UNAVAILABLE",
            details={"model": "wesin/pubmedbert-relation-extraction", "error": str(exc)},
        ))

    if not model_used:
        try:
            from tools.llm_client import call_gemini_json

            entity_summary = [{"id": e.id, "text": e.text, "label": e.label} for e in extracted_entities]
            prompt = (
                "You are a clinical relationship extraction specialist.\n"
                "Given these clinical entities from a medical report, identify semantic relationships between them:\n"
                f"Entities: {entity_summary}\n"
                f"Original Text: \"\"\"{state.original_text}\"\"\"\n\n"
                "Allowed relation types:\n"
                "- TREATS (medication treats disease or symptom)\n"
                "- CAUSES (disease or medication causes symptom or adverse effect)\n"
                "- INDICATES (symptom or lab result indicates condition)\n"
                "- TEMPORAL_BEFORE / TEMPORAL_AFTER\n\n"
                "Return JSON with key 'relations': list of {source_id: string, target_id: string, relation_type: string}."
            )
            data = call_gemini_json(prompt)
            if data and "relations" in data and isinstance(data["relations"], list):
                valid_types = {"CAUSES", "TREATS", "INDICATES", "TEMPORAL_BEFORE", "TEMPORAL_AFTER", "HAS_DOSE", "HAS_FREQUENCY", "HAS_ROUTE", "HAS_DURATION"}
                ent_ids = {e.id for e in extracted_entities}
                for item in data["relations"]:
                    src = item.get("source_id")
                    tgt = item.get("target_id")
                    rel_type = (item.get("relation_type") or "").upper()
                    if src in ent_ids and tgt in ent_ids and rel_type in valid_types:
                        new_relations.append(Relation(
                            id=f"R_LLM_{uuid.uuid4().hex[:8]}",
                            source_entity_id=src,
                            target_entity_id=tgt,
                            relation_type=rel_type,
                            confidence=0.95,
                        ))
                if new_relations:
                    model_used = True
                    audit_trail.append(AuditEvent(
                        agent_name="relation_agent",
                        action_type="GEMINI_RELATION_EXTRACTION",
                        details={"extracted_count": len(new_relations), "model": "gemini-3.1-flash-lite"},
                    ))
        except Exception as exc:
            audit_trail.append(AuditEvent(
                agent_name="relation_agent",
                action_type="GEMINI_RELATION_UNAVAILABLE",
                details={"error": str(exc)},
            ))

    if not model_used:
        new_relations = mock_relation_extraction(extracted_entities)
        audit_trail.append(AuditEvent(
            agent_name="relation_agent",
            action_type="RELATION_EXTRACTION",
            details={"message": f"Extracted {len(new_relations)} relations using fallback rules."},
        ))

    existing_relations.extend(new_relations)
    return {"relations": existing_relations, "audit_trail": audit_trail}
