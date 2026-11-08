"""Run the UDA-Hub agentic app.

Interactive chat:   python 03_agentic_app.py --user-id f556c0 --ticket-id t-001
Scripted demo:      python 03_agentic_app.py --demo
Tests:              pytest -q            (LLM scenario tests need OPENAI_API_KEY)
"""
import argparse
import uuid
from langchain_core.messages import HumanMessage

from utils import chat_interface
from agentic.workflow import orchestrator
from agentic.logging_utils import search_logs

DEMO = [  # (user_id, message)
    ("f556c0", "Hi!"),
    ("f556c0", "How do I reserve a spot for an event?"),
    ("f556c0", "Can you show me my current reservations?"),
    ("a4ab87", "Please reserve Samba Night at Lapa for me."),
    ("f556c0", "I was charged twice, I want a refund now!"),
    ("f556c0", "What's the best pizza place in Lisbon?"),
]


def run_demo():
    for user, text in DEMO:
        tid = f"demo-{uuid.uuid4().hex[:6]}"
        cfg = {"configurable": {"thread_id": tid}}
        out = orchestrator.invoke({"messages": [HumanMessage(content=text)], "external_user_id": user,
                                   "channel": "chat", "account_id": "cultpass"}, cfg)
        print(f"\n[{user}] {text}\n  route={out['route']} resolution={out['resolution']} "
              f"confidence={out.get('confidence')} reason={out.get('escalation_reason') or '-'}"
              f"\n  tools={[t['tool'] for t in out.get('tool_usage', [])]}"
              f"\n  Assistant: {out['messages'][-1].content}")
        print("  logged events:", [e["event"] for e in search_logs(ticket_id=tid)])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--user-id", default=None, help="CultPass user id of the logged-in customer")
    p.add_argument("--ticket-id", default=f"t-{uuid.uuid4().hex[:6]}")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()
    run_demo() if a.demo else chat_interface(orchestrator, a.ticket_id, external_user_id=a.user_id)
