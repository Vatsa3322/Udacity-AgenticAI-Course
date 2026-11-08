"""Classifier agent: structured classification of the ticket (type, urgency, complexity, sentiment)."""
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agentic.config import get_llm
from agentic.logging_utils import log_event
from agentic.state import last_user_text


class Classification(BaseModel):
    issue_type: Literal["login", "reservation", "subscription", "billing", "technical",
                        "account", "general", "smalltalk", "other"]
    urgency: Literal["low", "medium", "high"]
    complexity: Literal["simple", "moderate", "complex"]
    sentiment: Literal["positive", "neutral", "frustrated", "angry"]
    needs_account_action: bool = Field(
        description="True if resolving requires reading/changing the customer's own data "
                    "(their reservations, subscription, bookings) rather than explaining a policy/how-to.")
    wants_refund_or_dispute: bool = Field(description="True for refund requests, chargebacks, fraud/payment disputes.")
    confidence: float = Field(ge=0, le=1, description="Confidence in this classification.")
    rationale: str


PROMPT = """You classify customer-support tickets for CultPass (a cultural-experiences subscription app).
- smalltalk: ONLY pure greetings, thanks or goodbyes with no question or request. Any off-topic question
  (restaurants, weather, general knowledge) is NOT smalltalk; classify it as 'other'.
- needs_account_action=true for things like 'list my reservations', 'book X for me', 'cancel my booking', 'what is my plan'.
- needs_account_action=false for how-to / policy / troubleshooting questions answerable from help articles.
- urgency high = cannot access service / money lost / event imminent; angry sentiment = hostile or threatening.
Ticket channel: {channel}. Known customer memory: {memory}"""


def classifier_node(state):
    tid = state["ticket_id"]
    text = last_user_text(state)
    try:
        llm = get_llm().with_structured_output(Classification)
        c = llm.invoke([SystemMessage(content=PROMPT.format(channel=state.get("channel"),
                                                            memory=state.get("memory_context") or "none")),
                        HumanMessage(content=text)])
        result = c.model_dump()
    except Exception as exc:  # noqa: BLE001
        log_event(tid, "classifier", "error", error=str(exc))
        result = {"issue_type": "other", "urgency": "medium", "complexity": "complex", "sentiment": "neutral",
                  "needs_account_action": False, "wants_refund_or_dispute": False, "confidence": 0.0,
                  "rationale": f"classifier failure: {exc}"}
    log_event(tid, "classifier", "classification", **result)
    return {"classification": result}
