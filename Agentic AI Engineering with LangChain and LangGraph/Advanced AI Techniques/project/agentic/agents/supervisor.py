"""Supervisor agent: deterministic, auditable routing based on classification + metadata.
Also contains the small-talk responder."""
from langchain_core.messages import AIMessage, SystemMessage

from agentic.config import CLASSIFIER_MIN_CONFIDENCE, get_llm
from agentic.logging_utils import log_event
from agentic.state import last_user_text


def supervisor_node(state):
    c = state["classification"]
    text = last_user_text(state)
    if c["issue_type"] == "smalltalk" and ("?" in text or len(text.split()) > 6):
        c = {**c, "issue_type": "other"}   # guard: real questions are never small talk
    profile = state.get("user_profile", {})
    reason = ""
    if c["issue_type"] == "smalltalk":
        route = "smalltalk"
    elif c["confidence"] < CLASSIFIER_MIN_CONFIDENCE:
        route, reason = "escalation", "low_classifier_confidence"
    elif c["wants_refund_or_dispute"]:
        route, reason = "escalation", "refund_or_dispute_requires_human"      # KB policy: refunds need support lead
    elif c["urgency"] == "high" and c["sentiment"] == "angry":
        route, reason = "escalation", "urgent_and_angry_customer"
    elif c["needs_account_action"] and not state.get("external_user_id"):
        route, reason = "escalation", "identity_unverified"
    elif c["needs_account_action"] and profile.get("is_blocked"):
        route, reason = "escalation", "user_blocked"
    elif c["needs_account_action"]:
        route = "account_ops"
    else:
        route = "knowledge"
    log_event(state["ticket_id"], "supervisor", "routing_decision", route=route, reason=reason,
              issue_type=c["issue_type"], urgency=c["urgency"], complexity=c["complexity"],
              sentiment=c["sentiment"], classifier_confidence=c["confidence"])
    return {"route": route, "escalation_reason": reason, "classification": c}


def route_from_supervisor(state) -> str:
    return state["route"]


def smalltalk_node(state):
    llm = get_llm(0.3)
    name = (state.get("user_profile") or {}).get("name") or "there"
    reply = llm.invoke([SystemMessage(content=f"You are CultPass support. Reply in one short friendly sentence to the "
                                              f"customer ({name}) and offer help with reservations, subscriptions or login."),
                        *state["messages"][-4:]])
    log_event(state["ticket_id"], "smalltalk", "reply")
    return {"messages": [AIMessage(content=reply.content)], "resolution": "resolved", "confidence": 1.0}
