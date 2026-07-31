# Multi-Agent Clinical Report Understanding System

## Project Overview
An orchestrator agent receives a raw clinical report (e.g., discharge summary) and dynamically decomposes it based on complexity. Simple reports are processed by a 2-agent path, while complex ones trigger up to 4 specialist sub-agents (NER, Relation, Grounding, Summary). A Verifier agent reviews the output and flags any contradictions, routing them back to the orchestrator for replanning.

## Architecture & Stack
- **Python 3.11**
- **LangGraph**: Agent orchestration
- **FastAPI**: Backend REST API
- **Pydantic v2**: Strict schema definitions
- **ChromaDB**: Vector storage (Semantic Memory)
- **scispaCy**: Baseline NER
- **Anthropic API (Claude)**: LLM calls
- **pytest**: Testing framework

## Project Structure
- `/agents`: Agent logic and LangGraph state machine.
- `/api`: FastAPI backend endpoints.
- `/data/synthetic`: Synthetic clinical reports for testing.
- `/memory`: Components for working, episodic, semantic, and procedural memory.
- `/schemas`: Core Pydantic models.
- `/tests`: Pytest tests.
- `/tools`: Utility functions and tools for the agents.

## Phase 0 completed features
- Initial scaffolding and `schemas/core.py` definitions.
- FastAPI stub.
- Synthetic dataset generation.
