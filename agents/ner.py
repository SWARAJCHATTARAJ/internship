import os
import re
from typing import List
from schemas.core import ReportState, ExtractedEntity, AuditEvent, EntityLabel, SourceEvidence

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
        "loratadine", "paracetamol", "acetaminophen", "cetirizine", "vitamin c", "ors"
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

    symptom_pattern = re.compile(r"\b(?:fever|cough|headache|body ache|nausea|vomiting|pain|fatigue|dizziness)\b", re.I)
    for m in symptom_pattern.finditer(text):
        entities.append(ExtractedEntity(text=m.group(0), label="SYMPTOM", start_char=m.start(), end_char=m.end(), extraction_source="REGEX"))

    diagnosis_pattern = re.compile(r"\b(?:diabetes(?: mellitus)?|hypertension|pneumonia|asthma|viral upper respiratory tract infection|common cold)\b", re.I)
    for m in diagnosis_pattern.finditer(text):
        entities.append(ExtractedEntity(text=m.group(0), label="DIAGNOSIS", start_char=m.start(), end_char=m.end(), extraction_source="REGEX"))

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


def normalize_label(label: str) -> EntityLabel:
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
            
    # 2. Gemini LLM Clinical Extraction (Zero-shot across all scenarios)
    llm_used = False
    try:
        from tools.llm_client import call_gemini_json
        prompt = (
            "You are a clinical NER specialist. Extract all clinical entities from the clinical text below.\n"
            "Classify each entity with one of these labels:\n"
            "- MEDICATION (drug names, e.g. Metformin, Lisinopril, Aspirin, Azithromycin, Ibuprofen)\n"
            "- DIAGNOSIS (conditions, diseases, e.g. Type 2 Diabetes Mellitus, Hypertension, Pneumonia, Osteoarthritis)\n"
            "- SYMPTOM (clinical signs, e.g. fever, cough, pain, fatigue)\n"
            "- LAB_RESULT (tests and lab values, e.g. Glucose 145 mg/dL, Creatinine 1.8 mg/dL)\n\n"
            f"Clinical Text:\n\"\"\"{state.original_text}\"\"\"\n\n"
            "Return JSON with key 'entities': list of {text: string, label: string}."
        )
        llm_data = call_gemini_json(prompt)
        if llm_data and "entities" in llm_data and isinstance(llm_data["entities"], list):
            llm_entities = []
            for item in llm_data["entities"]:
                ent_text = item.get("text", "").strip()
                ent_label = normalize_label(item.get("label", ""))
                if ent_text:
                    pos = state.original_text.lower().find(ent_text.lower())
                    start = pos if pos != -1 else 0
                    end = start + len(ent_text)
                    llm_entities.append(ExtractedEntity(
                        text=ent_text,
                        label=ent_label,
                        start_char=start,
                        end_char=end,
                        confidence=0.98,
                        extraction_source="LLM_fallback",
                    ))
            if llm_entities:
                extracted.extend(llm_entities)
                llm_used = True
                audit_trail.append(AuditEvent(
                    agent_name="ner_agent",
                    action_type="GEMINI_LLM_EXTRACTION",
                    details={"extracted_count": len(llm_entities), "model": "gemini-3.1-flash-lite"}
                ))
    except Exception:
        pass

    if not llm_used:
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
                details={"message": f"ScispaCy missed entities. Fallback extracted {len(llm_entities)} entities."}
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

    extracted = normalize_entities(state.original_text, extracted)

    # Attach observable source evidence with multi-word bounding box aggregation
    source_kind = "ocr" if state.ocr_result else ("native_text" if state.source_type == "pdf" else "user_text")
    for entity in extracted:
        evidence = SourceEvidence(source_kind=source_kind, text_span=[entity.start_char, entity.end_char])
        if state.ocr_result:
            evidence.ocr_confidence = state.ocr_result.overall_confidence
            for page in state.ocr_result.pages:
                entity_words = set(re.findall(r"\w+", entity.text.lower()))
                matching_boxes = []
                conf_list = []
                for region in page.regions:
                    reg_word = region.text.lower()
                    if reg_word in entity_words:
                        if region.bbox:
                            matching_boxes.append(region.bbox)
                        if region.confidence is not None:
                            conf_list.append(region.confidence)
                if matching_boxes:
                    evidence.page_number = page.page_number
                    min_x = min(b[0] for b in matching_boxes)
                    min_y = min(b[1] for b in matching_boxes)
                    max_x = max(b[2] for b in matching_boxes)
                    max_y = max(b[3] for b in matching_boxes)
                    evidence.bbox = [min_x, min_y, max_x, max_y]
                    evidence.ocr_confidence = (sum(conf_list) / len(conf_list)) if conf_list else page.confidence
                    break
        entity.provenance = evidence

    # 3. Dynamic Routing: ask the orchestrator's medication specialist when needed.
    drug_count = sum(1 for e in extracted if e.label == "MEDICATION")
    drug_names = ["metformin", "amlodipine", "aspirin", "azithromycin", "clopidogrel", "ibuprofen", "lisinopril"]
    drug_count += sum(1 for e in extracted if e.text.lower() in drug_names and e.label != "MEDICATION")

    if drug_count >= 1 and "drug_agent" not in execution_plan and "medication_agent" not in execution_plan:
        if "ner_agent" in execution_plan:
            execution_plan.insert(execution_plan.index("ner_agent") + 1, "medication_agent")
        else:
            execution_plan.append("medication_agent")
        audit_trail.append(AuditEvent(
            agent_name="ner_agent",
            action_type="PLAN_UPDATE",
            details={"message": "Detected drug entities. Added medication specialist to execution plan."}
        ))
    
    trained_model_used = bool(spacy_entities) and not llm_used
    return {
        "extracted_entities": extracted,
        "audit_trail": audit_trail,
        "execution_plan": execution_plan,
        "trained_model_used": trained_model_used
    }
