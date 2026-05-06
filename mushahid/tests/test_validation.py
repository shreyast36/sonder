import pytest
from shared.schemas import ConstraintSatisfaction
from mushahid.validation.rules import (
    check_budget, check_duration, check_pace,
    check_must_haves, check_avoid_list, run_all_checks,
)


# ── ConstraintSatisfaction.all_passed — implemented, test fully ───────────────

def test_all_passed_true_when_all_checks_pass():
    cs = ConstraintSatisfaction(
        budget_ok=True, duration_ok=True, pace_ok=True,
        must_haves_ok=True, avoid_list_ok=True,
    )
    assert cs.all_passed is True


def test_all_passed_false_if_any_check_fails():
    cs = ConstraintSatisfaction(
        budget_ok=True, duration_ok=True, pace_ok=False,
        must_haves_ok=True, avoid_list_ok=True,
    )
    assert cs.all_passed is False


@pytest.mark.parametrize("field", ["budget_ok", "duration_ok", "pace_ok", "must_haves_ok", "avoid_list_ok"])
def test_all_passed_false_for_each_individual_failure(field):
    data = dict(budget_ok=True, duration_ok=True, pace_ok=True, must_haves_ok=True, avoid_list_ok=True)
    data[field] = False
    assert ConstraintSatisfaction(**data).all_passed is False


# ── Rule functions — stubs, verify signature and NotImplementedError ──────────
# Delete the pytest.raises wrapper and add real assertions once implemented.

def test_check_budget_stub(itinerary, constraints):
    with pytest.raises(NotImplementedError):
        check_budget(itinerary, constraints)
    # TODO: itinerary.total_budget_usd=1950, constraints.budget_usd=2000 → True
    # TODO: itinerary.total_budget_usd=2150, constraints.budget_usd=2000 → False


def test_check_duration_stub(itinerary, constraints):
    with pytest.raises(NotImplementedError):
        check_duration(itinerary, constraints)
    # TODO: len(itinerary.days)=7, trip duration=7 days → True


def test_check_pace_stub(itinerary, constraints):
    with pytest.raises(NotImplementedError):
        check_pace(itinerary, constraints)
    # TODO: relaxed pace, avg 4.2 activities/day → False (exceeds threshold of 3)


def test_check_must_haves_stub(itinerary, constraints):
    with pytest.raises(NotImplementedError):
        check_must_haves(itinerary, constraints)
    # TODO: must_haves=["snorkeling"], activity tags include "snorkeling" → True


def test_check_avoid_list_stub(itinerary, constraints):
    with pytest.raises(NotImplementedError):
        check_avoid_list(itinerary, constraints)
    # TODO: avoid_list=["nightclubs"], no activity has "nightclubs" tag → True


def test_run_all_checks_stub(itinerary, constraints):
    with pytest.raises(NotImplementedError):
        run_all_checks(itinerary, constraints)
    # TODO: returns ConstraintSatisfaction with all five bool fields set
