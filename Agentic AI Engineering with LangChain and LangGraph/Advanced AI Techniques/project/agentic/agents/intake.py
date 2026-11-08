"""Intake agent: identifies the customer, creates/loads the ticket, recalls long-term memory."""
from langchain_core.runnables import RunnableConfig

from agentic.config import ACCOUNT_ID
from agentic.logging_utils import log_event
from agentic.state import last_user_text
from agentic.tools.account_tools import lookup_user
from agentic.tools.memory_store import recall
from agentic.tools import ticket_tools


def intake_node(state, config: RunnableConfig):
    ticket_id = config["configurable"]["thread_id"]
    uid = state.get("external_user_id")
    text = last_user_text(state)

    profile = {"found": False, "name": None, "is_blocked": False}
    if uid:
        res = lookup_user.invoke({"user_id": uid})
        if res["ok"]:
            profile = {"found": True, "name": res["data"]["name"], "is_blocked": res["data"]["is_blocked"]}

    memories = []
    if uid:
        try:
            memories = recall(uid, text, k=3)
        except Exception as exc:  # noqa: BLE001
            log_event(ticket_id, "intake", "memory_recall_error", error=str(exc))

    channel = state.get("channel") or "chat"
    ticket_tools.ensure_ticket(ticket_id, uid, profile["name"], channel)
    ticket_tools.add_message(ticket_id, "user", text)
    log_event(ticket_id, "intake", "ticket_received", external_user_id=uid, channel=channel,
              user_found=profile["found"], is_blocked=profile["is_blocked"], memories_recalled=len(memories),
              text=text[:300])
    return {
        "ticket_id": ticket_id, "account_id": state.get("account_id") or ACCOUNT_ID, "channel": channel,
        "user_profile": profile, "memory_context": [m["text"] for m in memories],
        # reset per-turn fields
        "classification": {}, "route": "", "retrieved": [], "confidence": 0.0,
        "resolution": "", "escalation_reason": "", "tool_usage": [],
    }
