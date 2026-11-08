"""Run AFTER notebook 01: makes subscriptions/reservations deterministic so tests are reproducible.
Safe to re-run any time; it resets the state the tests and demo modify.

    python seed_test_data.py
"""
import uuid
from sqlalchemy import create_engine
from data.models import cultpass
from utils import get_session
from agentic.config import CULTPASS_DB

PLAN = {  # user_id: (status, tier, monthly_quota)
    "a4ab87": ("active", "basic", 4),       # Alice  - BLOCKED
    "f556c0": ("active", "premium", 4),     # Bob    - active premium (happy path)
    "88382b": ("active", "basic", 2),       # Cathy  - active basic
    "888fb2": ("active", "basic", 4),       # David  - BLOCKED
    "f1f10d": ("cancelled", "basic", 4),    # Eva    - cancelled subscription
    "e6376d": ("active", "premium", 4),     # Frank  - active premium
}
DEFAULT_SLOTS = 10
ALICE = "a4ab87"   # keeps the two reservations created by notebook 01

engine = create_engine(f"sqlite:///{CULTPASS_DB}", echo=False)

with get_session(engine) as s:
    # 1. Deterministic subscriptions
    for uid, (status, tier, quota) in PLAN.items():
        sub = s.query(cultpass.Subscription).filter_by(user_id=uid).first()
        if sub:
            sub.status, sub.tier, sub.monthly_quota = status, tier, quota

    # 2. Reset reservations: remove everyone's except Alice's (from notebook 01)
    s.query(cultpass.Reservation).filter(cultpass.Reservation.user_id != ALICE).delete()

    # 3. Reset slots so tests/demo don't drift
    for exp in s.query(cultpass.Experience).all():
        exp.slots_available = DEFAULT_SLOTS

    # 4. Give Bob one known reservation (Samba Night at Lapa)
        # reset reservations so tests are repeatable (keep Alice's original ones)
    s.query(cultpass.Reservation).filter(cultpass.Reservation.user_id != "a4ab87").delete()
    exp = s.query(cultpass.Experience).filter_by(title="Samba Night at Lapa").first()
    if exp:
        s.add(cultpass.Reservation(reservation_id=str(uuid.uuid4())[:6], user_id="f556c0",
                                   experience_id=exp.experience_id, status="reserved"))
        exp.slots_available -= 1

print("Seeded deterministic test data.")