from langgraph.graph import StateGraph, END
from schemas.core import ReportState, AuditEvent
from agents.ner import ner_agent
from agents.relation import relation_agent
from agents.grounding import grounding_agent
from agents.summary import summary_agent
from agents.verifier import verifier_agent

def orchestrator_node(state: ReportState) -> dict:
    text = state.original_text.lower()
    length = len(text.split())
    
    keywords = ["medication", "lab", "procedure", "diagnos", "history"]
    keyword_count = sum(1 for kw in keywords if kw in text)
    
    # Deterministic complexity heuristic
    if length > 50 or keyword_count >= 2:
        plan = ["ner_agent", "relation_agent", "grounding_agent", "summary_agent", "verifier_agent"]
        reasoning = f"Complex report detected (length={length}, keywords={keyword_count}). Routing to full specialist suite."
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
    # If we arrived here and there are unresolved flags, we are replanning
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
    if "drug_agent" in state.execution_plan: return "drug_agent"
    if "relation_agent" in state.execution_plan: return "relation_agent"
    if "grounding_agent" in state.execution_plan: return "grounding_agent"
    if "summary_agent" in state.execution_plan: return "summary_agent"
    return "verifier_agent"

def route_after_drug(state: ReportState) -> str:
    if "relation_agent" in state.execution_plan: return "relation_agent"
    if "grounding_agent" in state.execution_plan: return "grounding_agent"
    if "summary_agent" in state.execution_plan: return "summary_agent"
    return "verifier_agent"

def route_after_relation(state: ReportState) -> str:
    if "grounding_agent" in state.execution_plan: return "grounding_agent"
    if "summary_agent" in state.execution_plan: return "summary_agent"
    return "verifier_agent"

def route_after_grounding(state: ReportState) -> str:
    if "summary_agent" in state.execution_plan: return "summary_agent"
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
workflow.add_node("grounding_agent", grounding_agent)
workflow.add_node("summary_agent", summary_agent)
workflow.add_node("verifier_agent", verifier_agent)

workflow.set_entry_point("orchestrator")

workflow.add_edge("orchestrator", "ner_agent")
workflow.add_conditional_edges("ner_agent", route_after_ner)
workflow.add_conditional_edges("drug_agent", route_after_drug)
workflow.add_conditional_edges("relation_agent", route_after_relation)
workflow.add_conditional_edges("grounding_agent", route_after_grounding)
workflow.add_edge("summary_agent", "verifier_agent")
workflow.add_conditional_edges("verifier_agent", verify_and_replan)

graph = workflow.compile()
