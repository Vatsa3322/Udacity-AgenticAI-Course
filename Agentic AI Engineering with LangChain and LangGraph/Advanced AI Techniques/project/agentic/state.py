from typing import Optional
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage


class TicketState(MessagesState):
    """Shared state passed between all agents (nodes).
    `messages` is the short-term conversation memory (checkpointed by thread_id)."""
    ticket_id: str
    account_id: str
    channel: str
    external_user_id: Optional[str]
    user_profile: dict          # {"found", "name", "is_blocked"}
    memory_context: list        # long-term memories recalled for this user
    classification: dict        # output of the Classifier
    route: str                  # supervisor decision
    retrieved: list             # RAG results
    confidence: float
    resolution: str             # "resolved" | "needs_escalation" | "escalated"
    escalation_reason: str
    tool_usage: list            # [{"tool","args","ok","error_code"}]


def last_user_text(state) -> str:
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""
