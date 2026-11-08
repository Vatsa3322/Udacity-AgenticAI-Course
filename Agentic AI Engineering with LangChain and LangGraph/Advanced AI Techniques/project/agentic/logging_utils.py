"""Structured, searchable JSON-lines logging (one JSON object per line)."""
import json
from datetime import datetime, timezone
from agentic.config import LOG_FILE


def log_event(ticket_id: str, node: str, event: str, **data) -> dict:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket_id,
        "node": node,
        "event": event,
        **data,
    }
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
    except OSError:
        pass  # logging must never break the workflow
    return record


def search_logs(**filters) -> list[dict]:
    """Return log records whose top-level fields equal all given filters.
    Example: search_logs(ticket_id="1", event="routing_decision")"""
    if not LOG_FILE.exists():
        return []
    out = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if all(rec.get(k) == v for k, v in filters.items()):
                out.append(rec)
    return out
