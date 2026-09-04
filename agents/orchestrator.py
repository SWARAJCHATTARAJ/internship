from langgraph.graph import StateGraph, END
from schemas.core import ReportState, AuditEvent
from agents.ner import ner_agent
from agents.relation import relation_agent
from agents.timeline import timeline_agent
from agents.grounding import grounding_agent
from agents.summary import summary_agent
from agents.verifier import verifier_agent


def orchestrator_node(state: ReportState) -> dict:
    text = state.original_text.lower()
    length = len(text.split())

    keywords = ["medication", "lab", "procedure", "diagnos", "history"]
    keyword_count = sum(1 for kw in keywords if kw in text)

    if length > 30 or keyword_count >= 1 or state.ocr_result is not None:
        plan = ["ner_agent", "relation_agent", "timeline_agent", "grounding_agent", "summary_agent", "verifier_agent"]
        reasoning = f"Complex / Intake report detected (length={length}, keywords={keyword_count}, ocr={state.ocr_result is not None}). Routing to full specialist suite."
    else:
        plan = ["ner_agent"]
        reasoning = f"Simple report detected (length={length}, keywords={keyword_count}). Routing to NER only."

    new_audit = AuditEvent(
        agent_name="orchestrator",
        action_type="ROUTING_DECISION",
        details={"reasoning": reasoning, "plan": plan}
    )

    audit_trail = state.audit_trail.copy()
    audit_trail.append(new_audit)

    replan_count = state.replan_count
    unresolved = [f for f in state.verifier_flags if not f.resolved]
    if len(unresolved) > 0:
        replan_count += 1
        audit_trail.append(AuditEvent(
            agent_name="orchestrator",
            action_type="REPLANNING",
            details={"replan_count": replan_count, "unresolved_flags": len(unresolved)}
        ))

    return {"execution_plan": plan, "audit_trail": audit_trail, "replan_count": replan_count}


def drug_agent(state: ReportState) -> dict:
    audit_trail = state.audit_trail.copy()
    audit_trail.append(AuditEvent(
        agent_name="drug_agent",
        action_type="STUB_EXECUTION",
        details={"message": "Drug agent validated complex medication regimen."}
    ))
    return {"audit_trail": audit_trail}


# --- Routing Logic ---
def route_after_ner(state: ReportState) -> str:
    if "drug_agent" in state.execution_plan:
        return "drug_agent"
    if "relation_agent" in state.execution_plan:
        return "relation_agent"
    if "timeline_agent" in state.execution_plan:
        return "timeline_agent"
    if "grounding_agent" in state.execution_plan:
        return "grounding_agent"
    if "summary_agent" in state.execution_plan:
        return "summary_agent"
    return "verifier_agent"


def route_after_drug(state: ReportState) -> str:
    if "relation_agent" in state.execution_plan:
        return "relation_agent"
    if "timeline_agent" in state.execution_plan:
        return "timeline_agent"
    if "grounding_agent" in state.execution_plan:
        return "grounding_agent"
    if "summary_agent" in state.execution_plan:
        return "summary_agent"
    return "verifier_agent"


def route_after_relation(state: ReportState) -> str:
    if "timeline_agent" in state.execution_plan:
        return "timeline_agent"
    if "grounding_agent" in state.execution_plan:
        return "grounding_agent"
    if "summary_agent" in state.execution_plan:
        return "summary_agent"
    return "verifier_agent"


def route_after_timeline(state: ReportState) -> str:
    if "grounding_agent" in state.execution_plan:
        return "grounding_agent"
    if "summary_agent" in state.execution_plan:
        return "summary_agent"
    return "verifier_agent"


def route_after_grounding(state: ReportState) -> str:
    if "summary_agent" in state.execution_plan:
        return "summary_agent"
    return "verifier_agent"


def verify_and_replan(state: ReportState) -> str:
    unresolved = [f for f in state.verifier_flags if not f.resolved]
    if len(unresolved) > 0 and state.replan_count < 2:
        return "orchestrator"
    return END


# --- Build the Graph ---
workflow = StateGraph(ReportState)

workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("ner_agent", ner_agent)
workflow.add_node("drug_agent", drug_agent)
workflow.add_node("relation_agent", relation_agent)
workflow.add_node("timeline_agent", timeline_agent)
workflow.add_node("grounding_agent", grounding_agent)
workflow.add_node("summary_agent", summary_agent)
workflow.add_node("verifier_agent", verifier_agent)

workflow.set_entry_point("orchestrator")

workflow.add_edge("orchestrator", "ner_agent")
workflow.add_conditional_edges("ner_agent", route_after_ner)
workflow.add_conditional_edges("drug_agent", route_after_drug)
workflow.add_conditional_edges("relation_agent", route_after_relation)
workflow.add_conditional_edges("timeline_agent", route_after_timeline)
workflow.add_conditional_edges("grounding_agent", route_after_grounding)
workflow.add_edge("summary_agent", "verifier_agent")
workflow.add_conditional_edges("verifier_agent", verify_and_replan)

graph = workflow.compile()


class SimpleGraph:
    def __init__(self):
        self.node_map = {
            "orchestrator": orchestrator_node,
            "ner_agent": ner_agent,
            "drug_agent": drug_agent,
            "relation_agent": relation_agent,
            "timeline_agent": timeline_agent,
            "grounding_agent": grounding_agent,
            "summary_agent": summary_agent,
            "verifier_agent": verifier_agent,
        }

    def _apply_update(self, state, update: dict):
        base = state.model_dump()
        for k, v in update.items():
            base[k] = v
        return ReportState(**base)

    def invoke(self, state_input):
        if isinstance(state_input, dict):
            state = ReportState(**state_input)
        elif isinstance(state_input, ReportState):
            state = state_input
        else:
            state = ReportState(**state_input)

        if not state.execution_plan:
            res = orchestrator_node(state)
            state = self._apply_update(state, res)

        max_replans = 2
        while True:
            for agent_name in list(state.execution_plan):
                fn = self.node_map.get(agent_name)
                if not fn:
                    continue
                try:
                    res = fn(state)
                    state = self._apply_update(state, res)
                except Exception:
                    continue

            if "verifier_agent" not in state.execution_plan:
                try:
                    res = verifier_agent(state)
                    state = self._apply_update(state, res)
                except Exception:
                    pass

            nxt = verify_and_replan(state)
            if nxt == "orchestrator" and state.replan_count < max_replans:
                res = orchestrator_node(state)
                state = self._apply_update(state, res)
                continue
            break

        return {
            "document_id": state.document_id,
            "original_text": state.original_text,
            "source_text": state.source_text,
            "source_type": state.source_type,
            "source_file": state.source_file,
            "ocr_result": state.ocr_result,
            "execution_plan": state.execution_plan,
            "extracted_entities": state.extracted_entities,
            "relations": state.relations,
            "timeline": state.timeline,
            "verifier_flags": state.verifier_flags,
            "audit_trail": state.audit_trail,
            "summary": state.summary,
            "fhir_draft": state.fhir_draft,
            "trained_model_used": state.trained_model_used,
            "replan_count": state.replan_count,
        }


graph = SimpleGraph()
