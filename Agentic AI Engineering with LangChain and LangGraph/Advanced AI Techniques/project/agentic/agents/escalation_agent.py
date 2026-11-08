"""Escalation agent: summarises the ticket for a human, marks it escalated, informs the customer."""
from langchain_core.messages import AIMessage, SystemMessage

from agentic.config import get_llm
from agentic.logging_utils import log_event
from agentic.tools import ticket_tools

CUSTOMER_MESSAGES = {
    "user_blocked": "Your account is currently restricted, so I can't make changes to it myself. I've passed your request "
                    "to our support team, who will review it and get back to you.",
    "refund_or_dispute_requires_human": "I'm sorry about the trouble. Refunds and payment disputes need a review by our "
                    "support team, so I've escalated your ticket and a specialist will follow up with you.",
    "urgent_and_angry_customer": "I'm really sorry for the experience. I've marked this as urgent and handed it to a "
                    "human support specialist who will contact you shortly.",
    "identity_unverified": "I couldn't verify your account, so I've passed this to our support team to help you securely.",
}
DEFAULT = ("I wasn't able to fully resolve this myself, so I've escalated your ticket to our human support team. "
           "They'll follow up with you soon.")


def escalation_node(state):
    tid = state["ticket_id"]
    reason = state.get("escalation_reason") or "unspecified"
    convo = "\n".join(f"{m.type}: {m.content}" for m in state["messages"][-8:])
    try:
        summary = get_llm().invoke([SystemMessage(content=(
            "Write a 3-bullet handoff summary for a human support agent: issue, what was tried, suggested next step. "
            f"Escalation reason: {reason}. Classification: {state.get('classification')}. "
            f"Tools used: {state.get('tool_usage')}.")), SystemMessage(content=convo)]).content
    except Exception as exc:  # noqa: BLE001
        summary = f"Auto-summary unavailable ({exc}). Reason: {reason}.\n{convo}"

    ticket_tools.add_message(tid, "agent", f"[ESCALATION SUMMARY] {summary}")
    ticket_tools.set_ticket_status(tid, "escalated", issue_type=(state.get("classification") or {}).get("issue_type"))
    log_event(tid, "escalation", "escalated", reason=reason, summary=summary[:500])
    return {"messages": [AIMessage(content=CUSTOMER_MESSAGES.get(reason, DEFAULT))], "resolution": "escalated"}
