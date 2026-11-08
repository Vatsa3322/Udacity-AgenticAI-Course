"""Knowledge Resolver agent: RAG over the KB + confidence scoring + escalation signal."""
from pydantic import BaseModel
from langchain_core.messages import AIMessage, SystemMessage

from agentic.config import get_llm, KB_MIN_SIMILARITY, KB_CONFIDENCE_THRESHOLD
from agentic.logging_utils import log_event
from agentic.state import last_user_text
from agentic.tools.knowledge_tools import search_knowledge


class KBAnswer(BaseModel):
    answerable: bool
    answer: str
    confidence: float
    article_ids: list[str]


PROMPT = """You are a CultPass support agent. Answer the customer's question using ONLY the knowledge-base
articles below. Follow the article's 'Suggested phrasing' style when available. If the articles do not
contain the answer, set answerable=false. confidence is 0-1 (how completely the articles answer it).
Never invent policies, prices or refunds.

ARTICLES:
{articles}

Customer memory (may personalise tone, not facts): {memory}"""


def knowledge_node(state):
    tid = state["ticket_id"]
    query = last_user_text(state)
    hits = search_knowledge(query, k=3)
    summary = [{"title": h["title"], "score": round(h["score"], 3)} for h in hits]
    top = hits[0]["score"] if hits else 0.0

    if not hits or top < KB_MIN_SIMILARITY:
        log_event(tid, "knowledge", "no_relevant_article", top_score=top, hits=summary)
        return {"retrieved": hits, "confidence": top, "resolution": "needs_escalation",
                "escalation_reason": "no_relevant_knowledge"}

    articles = "\n\n".join(f"[{h['article_id']}] {h['title']}\n{h['content']}" for h in hits)
    try:
        out = get_llm().with_structured_output(KBAnswer).invoke(
            [SystemMessage(content=PROMPT.format(articles=articles, memory=state.get("memory_context") or "none")),
             *state["messages"][-6:]])
    except Exception as exc:  # noqa: BLE001
        log_event(tid, "knowledge", "error", error=str(exc))
        return {"retrieved": hits, "confidence": 0.0, "resolution": "needs_escalation",
                "escalation_reason": "knowledge_agent_error"}

    retrieval_conf = max(0.0, min(1.0, (top - 0.25) / 0.40))
    confidence = round(0.5 * retrieval_conf + 0.5 * out.confidence, 3)
    ok = out.answerable and confidence >= KB_CONFIDENCE_THRESHOLD
    log_event(tid, "knowledge", "kb_answer", top_score=round(top, 3), llm_confidence=out.confidence,
              confidence=confidence, answerable=out.answerable, resolved=ok,
              article_ids=out.article_ids, hits=summary)
    if not ok:
        return {"retrieved": hits, "confidence": confidence, "resolution": "needs_escalation",
                "escalation_reason": "low_confidence_kb_answer"}
    return {"messages": [AIMessage(content=out.answer)], "retrieved": hits, "confidence": confidence,
            "resolution": "resolved"}
