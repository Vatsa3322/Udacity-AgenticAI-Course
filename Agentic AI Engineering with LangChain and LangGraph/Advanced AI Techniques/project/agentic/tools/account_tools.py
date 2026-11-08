"""Support-operation tools over the CultPass database (cultpass.db).

Every tool: validates input, abstracts the DB (callers never see SQL/ORM),
and returns a structured dict: {"ok": True, "data": ...} or
{"ok": False, "error_code": "...", "message": "..."}."""
from sqlalchemy import create_engine, func
from langchain_core.tools import tool

from data.models import cultpass
from utils import get_session
from agentic.config import CULTPASS_DB


def _engine():
    return create_engine(f"sqlite:///{CULTPASS_DB}", echo=False)


def _ok(data):
    return {"ok": True, "data": data}


def _err(code, message):
    return {"ok": False, "error_code": code, "message": message}


def _find_user(s, user_id="", email=""):
    q = s.query(cultpass.User)
    if user_id:
        return q.filter_by(user_id=user_id).first()
    if email:
        return q.filter(func.lower(cultpass.User.email) == email.strip().lower()).first()
    return None


@tool
def lookup_user(user_id: str = "", email: str = "") -> dict:
    """Look up a CultPass customer by user_id or email. Returns name, email and blocked status."""
    if not user_id and not email:
        return _err("INVALID_INPUT", "Provide user_id or email.")
    try:
        with get_session(_engine()) as s:
            u = _find_user(s, user_id, email)
            if not u:
                return _err("USER_NOT_FOUND", "No customer matches those details.")
            return _ok({"user_id": u.user_id, "name": u.full_name, "email": u.email, "is_blocked": bool(u.is_blocked)})
    except Exception as exc:  # noqa: BLE001
        return _err("DB_ERROR", str(exc))


@tool
def get_subscription(user_id: str) -> dict:
    """Get the customer's subscription: status (active/cancelled), tier (basic/premium) and monthly quota."""
    if not user_id:
        return _err("INVALID_INPUT", "user_id is required.")
    try:
        with get_session(_engine()) as s:
            u = _find_user(s, user_id)
            if not u:
                return _err("USER_NOT_FOUND", "Customer not found.")
            sub = s.query(cultpass.Subscription).filter_by(user_id=user_id).first()
            if not sub:
                return _err("NO_SUBSCRIPTION", "Customer has no subscription.")
            return _ok({"subscription_id": sub.subscription_id, "status": sub.status, "tier": sub.tier,
                        "monthly_quota": sub.monthly_quota, "is_blocked": bool(u.is_blocked)})
    except Exception as exc:  # noqa: BLE001
        return _err("DB_ERROR", str(exc))


@tool
def list_reservations(user_id: str) -> dict:
    """List the customer's reservations with experience title, location, date and status."""
    if not user_id:
        return _err("INVALID_INPUT", "user_id is required.")
    try:
        with get_session(_engine()) as s:
            if not _find_user(s, user_id):
                return _err("USER_NOT_FOUND", "Customer not found.")
            rows = (s.query(cultpass.Reservation, cultpass.Experience)
                    .join(cultpass.Experience, cultpass.Reservation.experience_id == cultpass.Experience.experience_id)
                    .filter(cultpass.Reservation.user_id == user_id).all())
            return _ok([{"reservation_id": r.reservation_id, "status": r.status, "experience_id": e.experience_id,
                         "title": e.title, "location": e.location, "when": str(e.when)} for r, e in rows])
    except Exception as exc:  # noqa: BLE001
        return _err("DB_ERROR", str(exc))


@tool
def list_experiences(only_available: bool = True) -> dict:
    """List experiences in the catalog (id, title, location, date, slots, premium flag)."""
    try:
        with get_session(_engine()) as s:
            q = s.query(cultpass.Experience)
            if only_available:
                q = q.filter(cultpass.Experience.slots_available > 0)
            return _ok([{"experience_id": e.experience_id, "title": e.title, "location": e.location,
                         "when": str(e.when), "slots_available": e.slots_available,
                         "is_premium": bool(e.is_premium)} for e in q.all()])
    except Exception as exc:  # noqa: BLE001
        return _err("DB_ERROR", str(exc))


@tool
def reserve_experience(user_id: str, experience_id: str) -> dict:
    """Reserve an experience for the customer. Validates: not blocked, active subscription,
    tier vs premium experience, monthly quota, slot availability, no duplicate."""
    if not user_id or not experience_id:
        return _err("INVALID_INPUT", "user_id and experience_id are required.")
    try:
        with get_session(_engine()) as s:
            u = _find_user(s, user_id)
            if not u:
                return _err("USER_NOT_FOUND", "Customer not found.")
            if u.is_blocked:
                return _err("USER_BLOCKED", "This account is blocked; reservations are disabled.")
            sub = s.query(cultpass.Subscription).filter_by(user_id=user_id).first()
            if not sub or sub.status != "active":
                return _err("SUBSCRIPTION_INACTIVE", "An active subscription is required to reserve.")
            exp = s.query(cultpass.Experience).filter_by(experience_id=experience_id).first()
            if not exp:
                return _err("EXPERIENCE_NOT_FOUND", "That experience does not exist.")
            if exp.is_premium and sub.tier != "premium":
                return _err("TIER_TOO_LOW", "This is a premium experience; a premium tier is required.")
            if exp.slots_available <= 0:
                return _err("NO_SLOTS", "No slots left for this experience.")
            active = s.query(cultpass.Reservation).filter_by(user_id=user_id, status="reserved").all()
            if any(r.experience_id == experience_id for r in active):
                return _err("DUPLICATE", "You already reserved this experience.")
            if len(active) >= (sub.monthly_quota or 0):
                return _err("QUOTA_EXCEEDED", f"Monthly quota of {sub.monthly_quota} reached.")
            import uuid
            rid = str(uuid.uuid4())[:6]
            s.add(cultpass.Reservation(reservation_id=rid, user_id=user_id, experience_id=experience_id, status="reserved"))
            exp.slots_available -= 1
            return _ok({"reservation_id": rid, "experience": exp.title, "when": str(exp.when)})
    except Exception as exc:  # noqa: BLE001
        return _err("DB_ERROR", str(exc))


@tool
def cancel_reservation(user_id: str, reservation_id: str) -> dict:
    """Cancel one of the customer's reservations and free the slot."""
    if not user_id or not reservation_id:
        return _err("INVALID_INPUT", "user_id and reservation_id are required.")
    try:
        with get_session(_engine()) as s:
            u = _find_user(s, user_id)
            if not u:
                return _err("USER_NOT_FOUND", "Customer not found.")
            if u.is_blocked:
                return _err("USER_BLOCKED", "This account is blocked.")
            r = s.query(cultpass.Reservation).filter_by(reservation_id=reservation_id, user_id=user_id).first()
            if not r:
                return _err("RESERVATION_NOT_FOUND", "No such reservation on this account.")
            if r.status != "reserved":
                return _err("NOT_CANCELLABLE", f"Reservation is already '{r.status}'.")
            r.status = "cancelled"
            exp = s.query(cultpass.Experience).filter_by(experience_id=r.experience_id).first()
            if exp:
                exp.slots_available += 1
            return _ok({"reservation_id": reservation_id, "status": "cancelled"})
    except Exception as exc:  # noqa: BLE001
        return _err("DB_ERROR", str(exc))


ACCOUNT_TOOLS = [lookup_user, get_subscription, list_reservations, list_experiences,
                 reserve_experience, cancel_reservation]
