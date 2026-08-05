import os
import re
from typing import List
from schemas.core import ReportState, ExtractedEntity, AuditEvent

try:
    # pyrefly: ignore [missing-import]
    import spacy
    MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'custom_medical_ner')
    if os.path.exists(MODEL_PATH):
        print(f"Loading custom NLP model from {MODEL_PATH}")
        nlp = spacy.load(MODEL_PATH)
    else:
        nlp = spacy.load("en_core_sci_sm")
except (OSError, ImportError, ModuleNotFoundError):
    nlp = None

def mock_llm_fallback(text: str) -> List[ExtractedEntity]:
    """
    Mocked Anthropic API call for NER extraction.
    We just do some naive extraction to simulate an LLM.
    """
    entities = []
    text_lower = text.lower()
    if "metformin" in text_lower:
        entities.append(ExtractedEntity(
            id="E_LLM_1", text="Metformin", label="MEDICATION", 
            start_char=text_lower.find("metformin"), 
            end_char=text_lower.find("metformin")+9,
            extraction_source="LLM_fallback"
        ))
    if "amlodipine" in text_lower:
        entities.append(ExtractedEntity(
            id="E_LLM_2", text="Amlodipine", label="MEDICATION", 
            start_char=text_lower.find("amlodipine"), 
            end_char=text_lower.find("amlodipine")+10,
            extraction_source="LLM_fallback"
        ))
    if "aspirin" in text_lower:
        entities.append(ExtractedEntity(
            id="E_LLM_3", text="Aspirin", label="MEDICATION", 
            start_char=text_lower.find("aspirin"), 
            end_char=text_lower.find("aspirin")+7,
            extraction_source="LLM_fallback"
        ))
    if "diabetes" in text_lower:
        entities.append(ExtractedEntity(
            id="E_LLM_4", text="Diabetes Mellitus", label="DIAGNOSIS", 
            start_char=text_lower.find("diabetes"), 
            end_char=text_lower.find("diabetes")+8,
            extraction_source="LLM_fallback"
        ))
    if "abdominal pain" in text_lower:
        entities.append(ExtractedEntity(
            id="E_LLM_5", text="abdominal pain", label="SYMPTOM", 
            start_char=text_lower.find("abdominal pain"), 
            end_char=text_lower.find("abdominal pain") + 14,
            extraction_source="LLM_fallback"
        ))
        
    return entities


def find_regex_entities(text: str) -> List[ExtractedEntity]:
    entities: List[ExtractedEntity] = []
    medication_names = [
        "metformin", "lisinopril", "amlodipine", "aspirin", "azithromycin",
        "clopidogrel", "ibuprofen", "furosemide", "amoxicillin", "apixaban",
        "loratadine"
    ]
    med_pattern = re.compile(
        rf"\b(?P<name>{'|'.join(map(re.escape, medication_names))})\b"
        r"(?:\s+(?P<dose>\d+(?:\.\d+)?\s*(?:mg|mcg|g|units|tablet|tablets|capsule|capsules)))?"
        r"(?:\s*(?:once daily|daily|bid|tid|q\d?h|qod|qhs))?\b",
        re.I
    )
    for m in med_pattern.finditer(text):
        entities.append(ExtractedEntity(
            text=m.group(0).strip(),
            label="MEDICATION",
            start_char=m.start(),
            end_char=m.end(),
            extraction_source="REGEX"
        ))

    lab_pattern = re.compile(
        r"\b(?P<name>creatinine|potassium|sodium|glucose|hemoglobin|cholesterol|bicarbonate)\b"
        r"[\s:=]*"
        r"(?P<value>\d+(?:\.\d+)?\s*(?:mg/dL|mmol/L|mmol|g/dL|mg/dl|mEq/L)?)\b",
        re.I
    )
    for m in lab_pattern.finditer(text):
        entities.append(ExtractedEntity(
            text=m.group(0).strip(),
            label="LAB_RESULT",
            start_char=m.start(),
            end_char=m.end(),
            extraction_source="REGEX"
        ))

    return entities


def normalize_entities(text: str, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
    normalized: List[ExtractedEntity] = []
    entities_sorted = sorted(entities, key=lambda e: (e.start_char, -(e.end_char - e.start_char)))
    seen_spans = set()

    for entity in entities_sorted:
        span = (entity.start_char, entity.end_char, entity.label)
        if span in seen_spans:
            continue

        if normalized:
            prev = normalized[-1]
            if prev.label == "MEDICATION" and entity.label == "MEDICATION":
                if entity.start_char <= prev.end_char + 8:
                    merged_text = text[prev.start_char:entity.end_char].strip()
                    merged_entity = ExtractedEntity(
                        id=prev.id,
                        text=merged_text,
                        label="MEDICATION",
                        start_char=prev.start_char,
                        end_char=entity.end_char,
                        confidence=max(prev.confidence, entity.confidence),
                        extraction_source=prev.extraction_source,
                        grounding=prev.grounding,
                    )
                    normalized[-1] = merged_entity
                    seen_spans.add(span)
                    continue

        normalized.append(entity)
        seen_spans.add(span)

    return normalized


def normalize_label(label: str) -> str:
    label_upper = (label or "").upper()
    if label_upper in {"MEDICATION", "DRUG", "MEDICINE"}:
        return "MEDICATION"
    if label_upper in {"DIAGNOSIS", "DISEASE", "DISORDER", "CONDITION"}:
        return "DIAGNOSIS"
    if label_upper in {"PROCEDURE", "TREATMENT"}:
        return "PROCEDURE"
    if label_upper in {"LAB_RESULT", "TEST", "LAB"}:
        return "LAB_RESULT"
    if label_upper in {"SYMPTOM", "SIGN"}:
        return "SYMPTOM"
    if label_upper in {"ANATOMY", "BODY_PART"}:
        return "ANATOMY"
    return "SYMPTOM"


def ner_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    execution_plan = state.execution_plan.copy()
    extracted = list(state.extracted_entities)
    
    # 1. ScispaCy extraction
    spacy_entities = []
    if nlp is not None:
        doc = nlp(state.original_text)
        for i, ent in enumerate(doc.ents):
            spacy_entities.append(ExtractedEntity(
                id=f"E_SPACY_{i}",
                text=ent.text,
                label=normalize_label(ent.label_),
                start_char=ent.start_char,
                end_char=ent.end_char,
                extraction_source="custom_spacy_model"
            ))
            
    # 2. LLM Fallback Logic
    text_lower = state.original_text.lower()
    keywords = ["diagnosed", "treated", "prescribed", "medication", "pain"]
    has_keywords = any(kw in text_lower for kw in keywords)
    
    used_fallback = False
    
    if len(spacy_entities) == 0 and has_keywords:
        used_fallback = True
        llm_entities = mock_llm_fallback(state.original_text)
        extracted.extend(llm_entities)
        audit_trail.append(AuditEvent(
            agent_name="ner_agent",
            action_type="LLM_FALLBACK_EXTRACTION",
            details={"message": f"ScispaCy missed entities. LLM extracted {len(llm_entities)} entities."}
        ))
    else:
        extracted.extend(spacy_entities)
        audit_trail.append(AuditEvent(
            agent_name="ner_agent",
            action_type="SCISPACY_EXTRACTION",
            details={"message": f"ScispaCy extracted {len(spacy_entities)} entities."}
        ))

    regex_entities = find_regex_entities(state.original_text)
    if regex_entities:
        extracted.extend(regex_entities)
        audit_trail.append(AuditEvent(
            agent_name="ner_agent",
            action_type="REGEX_POSTPROCESSING",
            details={"message": f"Added {len(regex_entities)} normalized entities from regex patterns."}
        ))

    extracted = normalize_entities(state.original_text, extracted)

    # 3. Dynamic Routing: check if multiple drugs are present
    drug_count = sum(1 for e in extracted if e.label == "MEDICATION")
    
    drug_names = ["metformin", "amlodipine", "aspirin", "azithromycin", "clopidogrel", "ibuprofen"]
    drug_count += sum(1 for e in extracted if e.text.lower() in drug_names and e.label != "MEDICATION")

    if drug_count >= 1 and "drug_agent" not in execution_plan:
        execution_plan.insert(execution_plan.index("ner_agent") + 1, "drug_agent")
        audit_trail.append(AuditEvent(
            agent_name="ner_agent",
            action_type="PLAN_UPDATE",
            details={"message": "Detected drug entities. Added drug_agent to execution plan."}
        ))
    
    trained_model_used = bool(spacy_entities) and not used_fallback
    return {
        "extracted_entities": extracted,
        "audit_trail": audit_trail,
        "execution_plan": execution_plan,
        "trained_model_used": trained_model_used
    }
