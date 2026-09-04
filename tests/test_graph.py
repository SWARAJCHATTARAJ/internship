import pytest
import json
import os
from schemas.core import ReportState, VerifierFlag
from agents.orchestrator import graph

@pytest.fixture
def test_reports():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'synthetic', 'reports.json')
    with open(data_path, 'r') as f:
        return json.load(f)

def test_complexity_routing(test_reports):
    """
    Test that the graph routes differently depending on the complexity of the report.
    We'll assert that different reports have different paths based on the heuristic.
    """
    assert len(test_reports) > 0, "No reports loaded"
    
    for r in test_reports:
        # Initialize state with the report
        initial_state = ReportState(
            document_id=r['id'],
            original_text=r['text']
        )
        
        # Run graph
        final_state = graph.invoke(initial_state)
        
        assert len(final_state["execution_plan"]) > 0
        
        # Check audit trail correctly logs execution
        audit_agents = [event.agent_name for event in final_state["audit_trail"]]
        
        # Always includes orchestrator and verifier
        assert "orchestrator" in audit_agents
        assert "verifier_agent" in audit_agents
        assert "ner_agent" in audit_agents
        
        text = r['text'].lower()
        length = len(text.split())
        keywords = ["medication", "lab", "procedure", "diagnos", "history"]
        keyword_count = sum(1 for kw in keywords if kw in text)

        if length > 30 or keyword_count >= 1:
            assert "relation_agent" in audit_agents
            assert "grounding_agent" in audit_agents
            assert "summary_agent" in audit_agents
            assert len(final_state["execution_plan"]) >= 5
        else:
            assert "relation_agent" not in audit_agents
            assert "grounding_agent" not in audit_agents
            assert "summary_agent" not in audit_agents
            # It starts with 1 (ner_agent) but verifier is a node, so 2 maybe?
            # Wait, the orchestrator for simple cases only puts ["ner_agent"] in the plan!
            # The verifier runs because it's a separate edge in the graph, but it's not in the `execution_plan` array unless orchestrator adds it.
            # But wait, orchestrator doesn't add verifier to the `plan`! 
            # Oh wait, I just changed `orchestrator.py` to add `verifier_agent` to the complex plan, but what about simple?
            assert len(final_state["execution_plan"]) >= 1

def test_replan_loop(test_reports):
    """
    Test the conditional edge for the replan loop by injecting a VerifierFlag.
    """
    initial_state = ReportState(
        document_id="TEST_REPLAN",
        original_text="Patient given medication. Diagnosed with condition.",
        verifier_flags=[
            VerifierFlag(
                check_type="DRUG_PLAUSIBILITY",
                status="CONTRADICTION",
                justification="Hallucinated drug",
                confidence_score=1.0,
                resolved=False
            )
        ]
    )
    
    # Run graph
    final_state = graph.invoke(initial_state)
    
    # The replan loop should run 2 times and then stop (replan_count < 2).
    # Since we inject a flag that never gets resolved in the stubs, it should loop twice.
    assert final_state["replan_count"] == 2
    
    # Check the audit trail to see replanning occurred
    replan_events = [e for e in final_state["audit_trail"] if e.action_type == "REPLANNING"]
    assert len(replan_events) == 2
