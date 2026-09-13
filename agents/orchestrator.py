"""Adaptive, observable coordinator for the clinical document demo."""
from __future__ import annotations

from schemas.core import AuditEvent, ReportState
from agents.ner import ner_agent
from agents.medication import medication_agent
from agents.context import clinical_context_agent
from agents.relation import relation_agent
from agents.timeline import timeline_agent
from agents.grounding import grounding_agent
from agents.summary import summary_agent
from agents.verifier import verifier_agent
from agents.finalizer import finalizer_agent


def orchestrator_node(state: ReportState) -> dict:
    analysis = state.document_analysis
    text = state.original_text.lower()
    complex_document = bool(
        (analysis and (analysis.requires_ocr or analysis.document_type == "prescription"))
        or len(text.split()) > 30
        or any(k in text for k in ("prescription", "diagnos", "history", "medication", "lab", "procedure"))
    )
    has_medication_signal = any(k in text for k in (
        "mg", "tablet", "capsule", "medicine", "metformin", "paracetamol", "cetirizine", "amoxicillin",
    ))
    if complex_document:
        plan = ["ner_agent"]
        if has_medication_signal:
            plan.append("medication_agent")
        plan.extend(["clinical_context_agent", "relation_agent", "grounding_agent", "summary_agent", "verifier_agent"])
    else:
        plan = ["ner_agent", "verifier_agent"]

    audit = state.audit_trail.copy()
    audit.append(AuditEvent(agent_name="orchestrator", action_type="ROUTING_DECISION", details={
        "document_analysis": analysis.model_dump() if analysis else None,
        "complex_document": complex_document,
        "plan": plan,
        "reason": "conditional document-aware specialist selection",
    }))
    return {"execution_plan": plan, "audit_trail": audit}


class SimpleGraph:
    """State runner with bounded, explicit re-planning and no hidden reasoning trace."""
    node_map = {
        "ner_agent": ner_agent,
        "drug_agent": medication_agent,  # legacy alias retained for saved execution plans
        "medication_agent": medication_agent,
        "clinical_context_agent": clinical_context_agent,
        "relation_agent": relation_agent,
        "timeline_agent": timeline_agent,
        "grounding_agent": grounding_agent,
        "summary_agent": summary_agent,
        "verifier_agent": verifier_agent,
    }

    @staticmethod
    def _apply_update(state: ReportState, update: dict) -> ReportState:
        payload = state.model_dump()
        payload.update(update)
        return ReportState(**payload)

    def invoke(self, state_input):
        state = state_input if isinstance(state_input, ReportState) else ReportState(**state_input)
        state = self._apply_update(state, orchestrator_node(state))
        plan_index = 0
        # Agents may add a narrowly scoped specialist after observing evidence.
        while plan_index < len(state.execution_plan):
            agent_name = state.execution_plan[plan_index]
            state = self._apply_update(state, self.node_map[agent_name](state))
            plan_index += 1

        unresolved = [flag for flag in state.verifier_flags if not flag.resolved]
        while state.replan_count < 2 and unresolved:
            audit = state.audit_trail.copy()
            audit.append(AuditEvent(agent_name="orchestrator", action_type="REPLANNING", details={
                "replan_count": state.replan_count + 1,
                "strategy": "repeat deterministic evidence extraction; escalate unresolved items to HITL",
                "flags": [flag.check_type for flag in unresolved],
            }))
            state = self._apply_update(state, {"replan_count": state.replan_count + 1, "audit_trail": audit})
            for agent_name in ("ner_agent", "medication_agent", "clinical_context_agent", "relation_agent", "verifier_agent"):
                if agent_name in state.execution_plan:
                    state = self._apply_update(state, self.node_map[agent_name](state))
            unresolved = [flag for flag in state.verifier_flags if not flag.resolved]

        state = self._apply_update(state, finalizer_agent(state))
        # Keep model objects in the runner result for the established in-process
        # API/tests; FastAPI serializes them through ReportState at the boundary.
        return {name: getattr(state, name) for name in ReportState.model_fields}


graph = SimpleGraph()
