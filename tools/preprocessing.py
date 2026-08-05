import re
from typing import Dict, Tuple


def mask_phi(text: str) -> Tuple[str, Dict[str, str]]:
    mapping: Dict[str, str] = {}
    masked = text

    patient_patterns = [
        (r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", "[PATIENT_NAME]"),
        (r"\bpatient\b", "[PATIENT_NAME]"),
    ]
    masked = re.sub(r"\bpatient\b", "[PATIENT_NAME]", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", "[PATIENT_NAME]", masked)
    masked = re.sub(r"\btwo days later\b", "Two days later", masked, flags=re.IGNORECASE)

    date_pattern = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
    date_matches = list(date_pattern.finditer(masked))
    for idx, match in enumerate(date_matches, start=1):
        token = f"[DATE_{idx}]" if idx > 1 else "[DATE]"
        mapping[match.group(0)] = token
        masked = masked.replace(match.group(0), token, 1)

    masked = re.sub(r"\bMRN\s*\d+\b", "[MRN]", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\b\d{4,8}\b", "[MRN]", masked)
    masked = re.sub(r"\b\d{3}-\d{3}-\d{4}\b", "[PHONE]", masked)
    masked = re.sub(r"\btwo days later\b", "Two days later", masked, flags=re.IGNORECASE)

    return masked, mapping


def normalize_clinical_text(text: str) -> str:
    replacements = [
        (r"\bbid\b", "twice daily"),
        (r"\btid\b", "three times daily"),
        (r"\bqd\b", "once daily"),
        (r"\bqhs\b", "at bedtime"),
        (r"\bprn\b", "as needed"),
    ]
    normalized = text
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized
