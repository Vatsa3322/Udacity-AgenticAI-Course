"""Long-term memory: persistent SQLite table + semantic recall (embeddings).
Keyed by the customer's external_user_id so it survives across tickets/threads."""
import json
import sqlite3
from datetime import datetime, timezone
import numpy as np

from agentic.config import MEMORY_DB
from agentic.tools.embeddings import embed_documents, embed_query


def _conn() -> sqlite3.Connection:
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(MEMORY_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS long_term_memory(
        id INTEGER PRIMARY KEY AUTOINCREMENT, external_user_id TEXT NOT NULL,
        kind TEXT NOT NULL, text TEXT NOT NULL, ticket_id TEXT,
        embedding TEXT, created_at TEXT NOT NULL)""")
    return c


def save_memory(external_user_id: str, kind: str, text: str, ticket_id: str | None = None) -> None:
    """kind: 'interaction' (resolved issue summary) or 'preference'."""
    try:
        emb = json.dumps(embed_documents([text])[0].tolist())
    except Exception:  # noqa: BLE001 - still store text if embedding fails
        emb = None
    with _conn() as c:
        c.execute("INSERT INTO long_term_memory(external_user_id,kind,text,ticket_id,embedding,created_at) VALUES(?,?,?,?,?,?)",
                  (external_user_id, kind, text, ticket_id, emb, datetime.now(timezone.utc).isoformat()))


def recall(external_user_id: str, query: str, k: int = 3) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT kind,text,ticket_id,embedding,created_at FROM long_term_memory "
                         "WHERE external_user_id=? ORDER BY id DESC", (external_user_id,)).fetchall()
    if not rows:
        return []
    items = [{"kind": r[0], "text": r[1], "ticket_id": r[2], "created_at": r[4]} for r in rows]
    try:
        q = embed_query(query)
        scored = []
        for it, r in zip(items, rows):
            s = float(np.array(json.loads(r[3])) @ q) if r[3] else 0.0
            scored.append((s, it))
        scored.sort(key=lambda x: -x[0])
        return [{**it, "score": s} for s, it in scored[:k]]
    except Exception:  # noqa: BLE001 - fall back to most recent
        return items[:k]
