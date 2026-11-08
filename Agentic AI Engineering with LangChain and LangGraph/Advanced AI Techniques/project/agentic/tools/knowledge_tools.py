"""RAG retrieval over the Uda-hub `Knowledge` table.

How it works (also documented in agentic/design/architecture.md):
1. Load all articles for the account from udahub.db.
2. Embed "title + tags + content" with OpenAI embeddings (cached on disk by content hash).
3. Embed the query, cosine similarity against all article vectors (vectors are L2-normalised,
   so a dot product is enough), return top-k with scores.
The similarity of the best hit feeds the confidence score used for escalation."""
import hashlib
import json
import numpy as np
from sqlalchemy import create_engine

from data.models import udahub
from utils import get_session
from agentic.config import UDAHUB_DB, ACCOUNT_ID, KB_EMBEDDING_CACHE
from agentic.tools.embeddings import embed_documents, embed_query


class KnowledgeIndex:
    def __init__(self, account_id: str = ACCOUNT_ID):
        self.account_id = account_id
        self.articles: list[dict] = []
        self.matrix: np.ndarray | None = None

    @staticmethod
    def _text(a: dict) -> str:
        return f"{a['title']}\nTags: {a['tags']}\n{a['content']}"

    def build(self) -> None:
        engine = create_engine(f"sqlite:///{UDAHUB_DB}", echo=False)
        with get_session(engine) as s:
            self.articles = [
                {"article_id": k.article_id, "title": k.title, "content": k.content, "tags": k.tags or ""}
                for k in s.query(udahub.Knowledge).filter_by(account_id=self.account_id).all()
            ]
        cache = {}
        if KB_EMBEDDING_CACHE.exists():
            try:
                cache = json.loads(KB_EMBEDDING_CACHE.read_text())
            except json.JSONDecodeError:
                cache = {}
        keys = [hashlib.sha256(self._text(a).encode()).hexdigest() for a in self.articles]
        missing = [i for i, k in enumerate(keys) if k not in cache]
        if missing:
            vecs = embed_documents([self._text(self.articles[i]) for i in missing])
            for i, v in zip(missing, vecs):
                cache[keys[i]] = v.tolist()
            KB_EMBEDDING_CACHE.write_text(json.dumps(cache))
        self.matrix = np.array([cache[k] for k in keys]) if keys else np.zeros((0, 1))

    def search(self, query: str, k: int = 3) -> list[dict]:
        if self.matrix is None:
            self.build()
        if not self.articles:
            return []
        scores = self.matrix @ embed_query(query)
        top = np.argsort(-scores)[:k]
        return [{**self.articles[i], "score": float(scores[i])} for i in top]


_index: KnowledgeIndex | None = None


def search_knowledge(query: str, k: int = 3) -> list[dict]:
    """Public retrieval function. Returns [] on failure (caller escalates)."""
    global _index
    try:
        if _index is None:
            _index = KnowledgeIndex()
        return _index.search(query, k)
    except Exception as exc:  # noqa: BLE001
        from agentic.logging_utils import log_event
        log_event("-", "knowledge_tools", "retrieval_error", error=str(exc))
        return []
