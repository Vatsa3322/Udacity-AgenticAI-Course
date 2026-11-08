"""Persistence of tickets/messages/status in the Uda-hub core DB (udahub.db)."""
import uuid
from sqlalchemy import create_engine

from data.models import udahub
from utils import get_session
from agentic.config import UDAHUB_DB, ACCOUNT_ID
from agentic.logging_utils import log_event


def _engine():
    return create_engine(f"sqlite:///{UDAHUB_DB}", echo=False)


def ensure_ticket(ticket_id, external_user_id, user_name, channel, account_id=ACCOUNT_ID) -> dict:
    try:
        with get_session(_engine()) as s:
            if s.query(udahub.Ticket).filter_by(ticket_id=ticket_id).first():
                return {"ok": True, "created": False}
            ext = external_user_id or f"anonymous-{ticket_id}"
            user = s.query(udahub.User).filter_by(account_id=account_id, external_user_id=ext).first()
            if not user:
                user = udahub.User(user_id=str(uuid.uuid4()), account_id=account_id,
                                   external_user_id=ext, user_name=user_name or "Anonymous")
                s.add(user)
                s.flush()
            s.add(udahub.Ticket(ticket_id=ticket_id, account_id=account_id, user_id=user.user_id, channel=channel))
            s.flush()
            s.add(udahub.TicketMetadata(ticket_id=ticket_id, status="open", main_issue_type=None, tags=None))
        return {"ok": True, "created": True}
    except Exception as exc:  # noqa: BLE001
        log_event(ticket_id, "ticket_tools", "db_error", op="ensure_ticket", error=str(exc))
        return {"ok": False, "error": str(exc)}


def add_message(ticket_id: str, role: str, content: str) -> dict:
    try:
        with get_session(_engine()) as s:
            s.add(udahub.TicketMessage(message_id=str(uuid.uuid4()), ticket_id=ticket_id, role=role, content=content))
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        log_event(ticket_id, "ticket_tools", "db_error", op="add_message", error=str(exc))
        return {"ok": False, "error": str(exc)}


def set_ticket_status(ticket_id: str, status: str, issue_type: str | None = None, tags: str | None = None) -> dict:
    try:
        with get_session(_engine()) as s:
            meta = s.query(udahub.TicketMetadata).filter_by(ticket_id=ticket_id).first()
            if not meta:
                return {"ok": False, "error": "metadata not found"}
            meta.status = status
            if issue_type:
                meta.main_issue_type = issue_type
            if tags:
                meta.tags = tags
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        log_event(ticket_id, "ticket_tools", "db_error", op="set_ticket_status", error=str(exc))
        return {"ok": False, "error": str(exc)}
