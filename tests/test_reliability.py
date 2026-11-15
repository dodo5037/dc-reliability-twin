"""Module 2 tests: the reliability maths, and Monte Carlo against the analytical answer."""
import numpy as np
import pytest

from twin import reliability as R
from twin.facility import Facility


def test_k_of_n_by_hand():
    assert R.k_of_n(0.9, 2, 2) == pytest.approx(0.81)
    assert R.k_of_n(0.9, 2, 3) == pytest.approx(0.9 ** 3 + 3 * 0.9 ** 2 * 0.1)
    assert R.k_of_n(0.9, 1, 2) == pytest.approx(1 - 0.1 ** 2)


def test_unit_availability_is_mtbf_over_mtbf_plus_mttr():
    lam, mttr = R.PUBLISHED["chiller"][:2]
    assert R.unit_availability("chiller") == pytest.approx((8760 / lam) / (8760 / lam + mttr))


def test_repair_periods_have_the_right_rate_and_length():
    rng = np.random.default_rng(0)
    s, e = R.down_intervals(rng, 2.0, 10.0, 8760 * 5000)
    assert len(s) / 5000 == pytest.approx(2.0 * 8760 / (8760 + 20), rel=0.03)      # failures per calendar year
    assert (e - s).mean() == pytest.approx(10.0, rel=0.03)
    assert (s[1:] >= e[:-1]).all()                                                  # a unit cannot fail while in repair


def test_monte_carlo_matches_analytical_for_n_design():
    f = Facility().with_design("N")
    c = R.simulate_cooling(f, years=60_000, seed=3)
    assert c.unavailability_mc == pytest.approx(c.unavailability_analytical, rel=0.05)


def test_monte_carlo_matches_analytical_for_n_plus_1(monkeypatch):
    # Published rates make an N+1 double failure too rare to count, so the comparison uses
    # deliberately bad units (20 failures a year, 24 h repairs) where it happens often.
    monkeypatch.setitem(R.PUBLISHED, "chiller", (20.0, 24.0, "test", "-", "test unit"))
    monkeypatch.setitem(R.PUBLISHED, "crah", (1e-9, 1.0, "test", "-", "never fails"))
    f = Facility().with_design("N+1")
    c = R.simulate_cooling(f, years=3_000, seed=4)
    a = R.unit_availability("chiller")
    assert c.unavailability_analytical == pytest.approx(1 - R.k_of_n(a, 2, 3), rel=1e-6)
    assert c.unavailability_mc == pytest.approx(c.unavailability_analytical, rel=0.05)


def test_more_redundancy_never_makes_it_worse():
    u = [R.analytical_cooling_unavailability(Facility().with_design(d)) for d in ("N", "N+1", "2N")]
    assert u[0] > u[1] > u[2] > 0
    p = [R.analytical_power_events_per_year(Facility().with_design(d)) for d in ("N", "N+1", "2N")]
    assert p[0] > p[1] > p[2] > 0


def test_power_monte_carlo_matches_analytical_for_n_design():
    p = R.simulate_power(Facility().with_design("N"), years=100_000, seed=5)
    assert p.loss_events_per_year == pytest.approx(p.analytical_events_per_year, rel=0.06)


def test_utility_assumption_reproduces_the_published_minutes_lost():
    mean_min = R.ASSUMED["utility_minutes_lost_per_year"] / R.ASSUMED["utility_outages_per_year"]
    assert R.ASSUMED["utility_outages_per_year"] * mean_min == pytest.approx(0.94)
