from schemas.core import ReportState, AuditEvent

def summary_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    
    # Generate summary text
    lines = ["## Clinical Summary"]
    
    # Group entities by label
    medications = [e for e in state.extracted_entities if e.label == "MEDICATION"]
    diagnoses = [e for e in state.extracted_entities if e.label == "DIAGNOSIS"]
    symptoms = [e for e in state.extracted_entities if e.label == "SYMPTOM"]
    
    if diagnoses or symptoms:
        lines.append("\n### Diagnoses & Symptoms")
        for e in diagnoses + symptoms:
            code_str = f" [{e.grounding.ontology}: {e.grounding.code}]" if e.grounding else ""
            lines.append(f"- **{e.text}** ({e.label}){code_str}")
            
    if medications:
        lines.append("\n### Medications")
        for e in medications:
            code_str = f" [{e.grounding.ontology}: {e.grounding.code}]" if e.grounding else ""
            lines.append(f"- **{e.text}**{code_str}")
            
    if state.relations:
        lines.append("\n### Relationships")
        # map ID to text for readability
        id_to_text = {e.id: e.text for e in state.extracted_entities}
        for r in state.relations:
            source = id_to_text.get(r.source_entity_id, r.source_entity_id)
            target = id_to_text.get(r.target_entity_id, r.target_entity_id)
            lines.append(f"- {source} **{r.relation_type}** {target}")
            
    summary_text = "\n".join(lines)
    
    # Log to audit trail
    audit_trail.append(AuditEvent(
        agent_name="summary_agent",
        action_type="SUMMARY_GENERATION",
        details={"message": "Generated formatted clinical summary.", "length": len(summary_text)}
    ))
    
    return {
        "summary": summary_text,
        "audit_trail": audit_trail
    }
