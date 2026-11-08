"""Finalizer / Memory agent: persists the reply + status and writes long-term memory."""
from pydantic import BaseModel
from langchain_core.messages import AIMessage, SystemMessage

from agentic.config import get_llm
from agentic.logging_utils import log_event
from agentic.tools import ticket_tools
from agentic.tools.memory_store import save_memory


class MemoryNote(BaseModel):
    summary: str
    preferences: list[str]


def finalize_node(state):
    tid, uid = state["ticket_id"], state.get("external_user_id")
    last = state["messages"][-1]
    if isinstance(last, AIMessage):
        ticket_tools.add_message(tid, "ai", str(last.content))
    c = state.get("classification") or {}
    status = "resolved" if state.get("resolution") == "resolved" else "escalated"
    ticket_tools.set_ticket_status(tid, status, issue_type=c.get("issue_type"), tags=c.get("issue_type"))

    saved = 0
    if uid and c.get("issue_type") != "smalltalk":
        try:
            convo = "\n".join(f"{m.type}: {m.content}" for m in state["messages"][-6:])
            note = get_llm().with_structured_output(MemoryNote).invoke([
                SystemMessage(content="Summarise this support interaction in one sentence (issue + outcome) and list any "
                                      "explicit customer preferences (e.g. contact channel, favourite experiences, language). "
                                      "Return preferences=[] if none."),
                SystemMessage(content=f"Outcome: {status}\n{convo}")])
            save_memory(uid, "interaction", note.summary, tid)
            saved += 1
            for p in note.preferences:
                save_memory(uid, "preference", p, tid)
                saved += 1
        except Exception as exc:  # noqa: BLE001
            log_event(tid, "memory", "error", error=str(exc))
    log_event(tid, "memory", "finalized", status=status, memories_saved=saved,
              tool_usage=state.get("tool_usage"), confidence=state.get("confidence"))
    return {}
