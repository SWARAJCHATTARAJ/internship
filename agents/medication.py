"""Evidence-preserving medication attribute extraction for research/demo documents."""
from __future__ import annotations

import re

from schemas.core import AuditEvent, MedicationRecord, ReportState


DOSE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|mL|units?)\b", re.I)
FREQUENCY = re.compile(r"\b(?:once|twice|three times) daily|\b(?:OD|BD|BID|TID|QID)\b|every\s+\d+[- ]?(?:hours?|h)\b|at night\b", re.I)
DURATION = re.compile(r"\b(?:for|x)\s*\d+\s*(?:days?|weeks?|months?)\b|\b\d+\s*(?:days?|weeks?|months?)\b", re.I)
ROUTE = re.compile(r"\b(?:oral|by mouth|IV|intravenous|topical|inhaled|sublingual)\b", re.I)


def medication_agent(state: ReportState) -> dict:
    medications: list[MedicationRecord] = []
    text = state.original_text
    for entity in state.extracted_entities:
        if entity.label != "MEDICATION":
            continue
        # Keep extraction local to a line so attributes are not borrowed from another drug.
        line_start = text.rfind("\n", 0, entity.start_char) + 1
        line_end = text.find("\n", entity.end_char)
        line = text[line_start:] if line_end == -1 else text[line_start:line_end]
        dose = DOSE.search(line)
        frequency = FREQUENCY.search(line)
        duration = DURATION.search(line)
        route = ROUTE.search(line)
        base_confidence = entity.confidence
        if entity.provenance and entity.provenance.ocr_confidence is not None:
            base_confidence = min(base_confidence, entity.provenance.ocr_confidence)
        drug = DOSE.split(entity.text, maxsplit=1)[0].strip() or entity.text
        medications.append(MedicationRecord(
            drug=drug, dose=dose.group(0) if dose else None,
            frequency=frequency.group(0) if frequency else None,
            duration=duration.group(0) if duration else None,
            route=route.group(0) if route else None,
            evidence_entity_id=entity.id, confidence=base_confidence, provenance=entity.provenance,
        ))
    audit = state.audit_trail.copy()
    audit.append(AuditEvent(agent_name="medication_agent", action_type="MEDICATION_EXTRACTION", details={
        "count": len(medications), "evidence_only": True,
    }))
    return {"medications": medications, "audit_trail": audit}
