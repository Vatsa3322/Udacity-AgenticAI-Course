"""Deterministic tool tests (no LLM). Require notebooks 01+02 and seed_test_data.py to have been run."""
import pytest
from agentic.config import CULTPASS_DB

pytestmark = pytest.mark.skipif(not CULTPASS_DB.exists(), reason="run notebook 01 first")
from agentic.tools.account_tools import (lookup_user, get_subscription, list_reservations,
                                         list_experiences, reserve_experience, cancel_reservation)

BOB, ALICE, EVA, CATHY = "f556c0", "a4ab87", "f1f10d", "88382b"


def test_lookup_user_ok_and_not_found():
    assert lookup_user.invoke({"user_id": BOB})["data"]["name"] == "Bob Stone"
    assert lookup_user.invoke({"email": "BOB.STONE@granite.com"})["ok"]
    assert lookup_user.invoke({"user_id": "nope"})["error_code"] == "USER_NOT_FOUND"
    assert lookup_user.invoke({})["error_code"] == "INVALID_INPUT"


def test_subscription_and_blocked_flag():
    assert get_subscription.invoke({"user_id": BOB})["data"]["tier"] == "premium"
    assert lookup_user.invoke({"user_id": ALICE})["data"]["is_blocked"] is True


def test_blocked_user_cannot_reserve():
    exp = list_experiences.invoke({})["data"][0]["experience_id"]
    assert reserve_experience.invoke({"user_id": ALICE, "experience_id": exp})["error_code"] == "USER_BLOCKED"


def test_cancelled_subscription_cannot_reserve():
    exp = list_experiences.invoke({})["data"][0]["experience_id"]
    assert reserve_experience.invoke({"user_id": EVA, "experience_id": exp})["error_code"] == "SUBSCRIPTION_INACTIVE"

def _clear_reservations(user_id):
    """Cancel any active reservations so the test is repeatable."""
    for r in list_reservations.invoke({"user_id": user_id})["data"]:
        if r["status"] == "reserved":
            cancel_reservation.invoke({"user_id": user_id, "reservation_id": r["reservation_id"]})

            
def test_basic_tier_cannot_reserve_premium_and_reserve_cancel_roundtrip():
    _clear_reservations(CATHY)
    try:
        exps = list_experiences.invoke({})["data"]
        premium = next(e for e in exps if e["is_premium"])
        assert reserve_experience.invoke({"user_id": CATHY, "experience_id": premium["experience_id"]})["error_code"] == "TIER_TOO_LOW"
        standard = next(e for e in exps if not e["is_premium"])
        r = reserve_experience.invoke({"user_id": CATHY, "experience_id": standard["experience_id"]})
        assert r["ok"], r
        assert reserve_experience.invoke({"user_id": CATHY, "experience_id": standard["experience_id"]})["error_code"] == "DUPLICATE"
        assert cancel_reservation.invoke({"user_id": CATHY, "reservation_id": r["data"]["reservation_id"]})["ok"]
        # another customer cannot cancel Cathy's reservation
        assert cancel_reservation.invoke({"user_id": BOB, "reservation_id": r["data"]["reservation_id"]})["error_code"] in {"RESERVATION_NOT_FOUND", "NOT_CANCELLABLE"}
    finally:
        _clear_reservations(CATHY)


def test_list_reservations():
    assert list_reservations.invoke({"user_id": ALICE})["ok"]
