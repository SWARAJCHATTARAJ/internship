from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

EntityLabel = Literal["MEDICATION", "DIAGNOSIS", "PROCEDURE", "LAB_RESULT", "SYMPTOM", "ANATOMY", "DOSAGE", "FREQUENCY", "ROUTE", "DURATION"]

class GroundedConcept(BaseModel):
    ontology: Literal["SNOMED", "ICD-10", "RxNorm", "UNKNOWN"] = "UNKNOWN"
    code: str
    name: str


class SourceEvidence(BaseModel):
    """Evidence pointer for a claim; never a hidden reasoning trace."""
    source_kind: Literal["native_text", "ocr", "user_text"] = "user_text"
    page_number: Optional[int] = None
    text_span: Optional[List[int]] = None
    bbox: Optional[List[int]] = None
    ocr_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class DocumentAnalysis(BaseModel):
    document_type: Literal["prescription", "clinical_report", "unknown"] = "unknown"
    format: Literal["text", "pdf", "image", "unknown"] = "text"
    pages: int = 1
    requires_ocr: bool = False
    machine_readable_pages: List[int] = Field(default_factory=list)
    scanned_pages: List[int] = Field(default_factory=list)
    has_tables: bool = False
    has_handwriting: bool = False
    source_text_kind: Literal["user_text", "native_text", "ocr", "mixed"] = "user_text"


class MedicationRecord(BaseModel):
    drug: str
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    evidence_entity_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: Optional[SourceEvidence] = None

class ExtractedEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    label: EntityLabel
    start_char: int
    end_char: int
    confidence: float = 1.0
    extraction_source: Literal["scispaCy", "LLM_fallback", "custom_spacy_model", "REGEX"] = "scispaCy"
    grounding: Optional[GroundedConcept] = None
    provenance: Optional[SourceEvidence] = None

class Relation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str
    target_entity_id: str
    relation_type: Literal["CAUSES", "TREATS", "INDICATES", "TEMPORAL_BEFORE", "TEMPORAL_AFTER", "HAS_DOSE", "HAS_FREQUENCY", "HAS_ROUTE", "HAS_DURATION"]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: Optional[SourceEvidence] = None

class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event: str
    entity_refs: List[str] = Field(default_factory=list)
    normalized_time_or_offset: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)

class VerifierFlag(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_or_relation_id: Optional[str] = None
    check_type: Literal["DRUG_PLAUSIBILITY", "LAB_RANGE", "DIAGNOSIS_ENTAILMENT", "FHIR_SCHEMA", "OCR_UNCERTAINTY", "DOSAGE_CONTRADICTION", "UNSUPPORTED_CLAIM"]
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

class OCRRegion(BaseModel):
    text: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bbox: Optional[List[int]] = None

class OCRPage(BaseModel):
    page_number: int
    text: str = ""
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    regions: List[OCRRegion] = Field(default_factory=list)
    error: Optional[str] = None

class OCRResult(BaseModel):
    success: bool
    text: str = ""
    pages: List[OCRPage] = Field(default_factory=list)
    overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source_type: Optional[str] = None
    pages_processed: int = 0
    pages_failed: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class ReportState(BaseModel):
    document_id: str
    original_text: str
    source_text: Optional[str] = None
    source_type: Optional[str] = None
    source_file: Optional[str] = None
    ocr_result: Optional[OCRResult] = None
    document_analysis: Optional[DocumentAnalysis] = None
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
    medications: List[MedicationRecord] = Field(default_factory=list)
    clinical_context: List[Dict[str, Any]] = Field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list)
    replans: List[Dict[str, Any]] = Field(default_factory=list)
