"""End-to-end scenario tests through the LangGraph orchestrator (real LLM + embeddings).
Run:  OPENAI_API_KEY=... pytest tests/test_scenarios.py -q"""
import os
import uuid
import pytest
from langchain_core.messages import HumanMessage

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")

from agentic.workflow import orchestrator
from agentic.logging_utils import search_logs
from agentic.tools.memory_store import recall

BOB, ALICE = "f556c0", "a4ab87"


def run(text, user=BOB, thread=None):
    thread = thread or f"test-{uuid.uuid4().hex[:8]}"
    out = orchestrator.invoke({"messages": [HumanMessage(content=text)], "external_user_id": user,
                               "channel": "chat", "account_id": "cultpass"},
                              {"configurable": {"thread_id": thread}})
    return thread, out


def test_kb_resolution_with_rag():
    tid, out = run("How can I reserve a spot for an event?")
    assert out["route"] == "knowledge" and out["resolution"] == "resolved"
    assert any("Reserve" in h["title"] for h in out["retrieved"][:2])
    assert search_logs(ticket_id=tid, event="kb_answer")


def test_account_tool_usage():
    tid, out = run("Please show me my current reservations")
    assert out["route"] == "account_ops" and out["resolution"] == "resolved"
    assert "list_reservations" in [t["tool"] for t in out["tool_usage"]]


def test_blocked_user_is_escalated():
    tid, out = run("Please reserve Samba Night at Lapa for me", user=ALICE)
    assert out["resolution"] == "escalated" and out["escalation_reason"] == "user_blocked"


def test_refund_is_escalated():
    tid, out = run("I was charged twice! I want a refund right now.")
    assert out["resolution"] == "escalated"


def test_unknown_topic_is_escalated():
    tid, out = run("What is the best pizza place in Lisbon?")
    assert out["resolution"] == "escalated"
    assert out["escalation_reason"] in {"no_relevant_knowledge", "low_confidence_kb_answer", "low_classifier_confidence"}

def test_short_term_memory_same_thread():
    tid, _ = run("Hi, my name is Bob and I love museums.")
    _, out = run("What did I just say I love?", thread=tid)
    assert len(out["messages"]) >= 4            # history restored by checkpointer


def test_long_term_memory_across_threads():
    run("I prefer to be contacted by email. How do I cancel my subscription?")
    assert recall(BOB, "contact preference", k=3)   # persisted across sessions
