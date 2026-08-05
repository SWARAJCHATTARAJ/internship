from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class GroundedConcept(BaseModel):
    ontology: Literal["SNOMED", "ICD-10", "RxNorm", "UNKNOWN"] = "UNKNOWN"
    code: str
    name: str

class ExtractedEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    label: Literal["MEDICATION", "DIAGNOSIS", "PROCEDURE", "LAB_RESULT", "SYMPTOM", "ANATOMY"]
    start_char: int
    end_char: int
    confidence: float = 1.0
    extraction_source: Literal["scispaCy", "LLM_fallback", "custom_spacy_model", "REGEX"] = "scispaCy"
    grounding: Optional[GroundedConcept] = None

class Relation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str
    target_entity_id: str
    relation_type: Literal["CAUSES", "TREATS", "INDICATES", "TEMPORAL_BEFORE", "TEMPORAL_AFTER"]

class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: str
    entity_refs: List[str] = Field(default_factory=list)
    normalized_time_or_offset: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)

class VerifierFlag(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_or_relation_id: Optional[str] = None
    check_type: Literal["DRUG_PLAUSIBILITY", "LAB_RANGE", "DIAGNOSIS_ENTAILMENT", "FHIR_SCHEMA"]
    status: Literal["NEEDS_REVIEW", "CONTRADICTION", "INSUFFICIENT_EVIDENCE"]
    justification: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    resolved: bool = False
    resolution_note: Optional[str] = None

class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_name: str
    action_type: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ReportState(BaseModel):
    document_id: str
    original_text: str
    source_text: Optional[str] = None
    execution_plan: List[str] = Field(default_factory=list)
    extracted_entities: List[ExtractedEntity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    verifier_flags: List[VerifierFlag] = Field(default_factory=list)
    audit_trail: List[AuditEvent] = Field(default_factory=list)
    summary: Optional[str] = None
    fhir_draft: Optional[Dict[str, Any]] = None
    trained_model_used: bool = False
    replan_count: int = 0
