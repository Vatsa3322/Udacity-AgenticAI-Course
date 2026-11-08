"""LangGraph orchestration (built from scratch). See agentic/design/architecture.md.

START -> intake -> classifier -> supervisor -> {knowledge | account_ops | escalation | smalltalk}
knowledge/account_ops -> (resolved -> finalize | needs_escalation -> escalation)
escalation/smalltalk -> finalize -> END
"""
import sqlite3
from langgraph.graph import StateGraph, START, END

from agentic.config import CHECKPOINT_DB
from agentic.state import TicketState
from agentic.agents.intake import intake_node
from agentic.agents.classifier import classifier_node
from agentic.agents.supervisor import supervisor_node, route_from_supervisor, smalltalk_node
from agentic.agents.knowledge_agent import knowledge_node
from agentic.agents.account_agent import account_ops_node
from agentic.agents.escalation_agent import escalation_node
from agentic.agents.memory_agent import finalize_node


def route_after_resolver(state) -> str:
    return "escalation" if state.get("resolution") == "needs_escalation" else "finalize"


def build_graph() -> StateGraph:
    g = StateGraph(TicketState)
    g.add_node("intake", intake_node)
    g.add_node("classifier", classifier_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("knowledge", knowledge_node)
    g.add_node("account_ops", account_ops_node)
    g.add_node("escalation", escalation_node)
    g.add_node("smalltalk", smalltalk_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "intake")
    g.add_edge("intake", "classifier")
    g.add_edge("classifier", "supervisor")
    g.add_conditional_edges("supervisor", route_from_supervisor, {
        "knowledge": "knowledge", "account_ops": "account_ops",
        "escalation": "escalation", "smalltalk": "smalltalk"})
    g.add_conditional_edges("knowledge", route_after_resolver, {"escalation": "escalation", "finalize": "finalize"})
    g.add_conditional_edges("account_ops", route_after_resolver, {"escalation": "escalation", "finalize": "finalize"})
    g.add_edge("escalation", "finalize")
    g.add_edge("smalltalk", "finalize")
    g.add_edge("finalize", END)
    return g


def _checkpointer():
    """Short-term memory: persistent per-thread_id checkpoints (falls back to in-memory)."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver(sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False))
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


orchestrator = build_graph().compile(checkpointer=_checkpointer())
