import re
from typing import List
from schemas.core import ReportState, TimelineEvent, AuditEvent


def _extract_temporal_events(text: str) -> List[TimelineEvent]:
    events: List[TimelineEvent] = []
    lowered = text.lower()

    if "day 1" in lowered:
        events.append(TimelineEvent(event="day 1", normalized_time_or_offset="day 1", confidence=0.9))
    if "day 2" in lowered:
        events.append(TimelineEvent(event="day 2", normalized_time_or_offset="day 2", confidence=0.9))
    if "two days later" in lowered:
        events.append(TimelineEvent(event="two days later", normalized_time_or_offset="+2 days", confidence=0.85))
    if "on discharge" in lowered:
        events.append(TimelineEvent(event="on discharge", normalized_time_or_offset="discharge", confidence=0.8))

    date_matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if date_matches:
        for idx, date in enumerate(date_matches):
            events.append(TimelineEvent(event=date, normalized_time_or_offset=f"date_{idx + 1}", confidence=0.9))

    if not events:
        events.append(TimelineEvent(event="timeline inferred", normalized_time_or_offset="unspecified", confidence=0.2))

    return events


def timeline_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    timeline = _extract_temporal_events(state.original_text)

    audit_trail.append(AuditEvent(
        agent_name="timeline_agent",
        action_type="TIMELINE_EXTRACTION",
        details={"message": f"Extracted {len(timeline)} timeline events.", "events": [e.event for e in timeline]},
    ))

    return {
        "timeline": timeline,
        "audit_trail": audit_trail,
    }
