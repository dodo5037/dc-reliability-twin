"""Module 1 tests: energy balance, units, sizing and redundancy counts."""
import pytest

from twin import cooling
from twin.facility import Facility, installed

f = Facility()


def test_units_installed_per_design():
    assert [installed(2, d) for d in ("N", "N+1", "2N")] == [2, 3, 4]
    assert f.with_design("2N").crahs.n_installed == 8
    assert f.with_design("N").ats.n_installed == 1 and f.with_design("2N").ats.n_installed == 2


def test_cooling_load_is_internal_heat_plus_envelope_gain():
    assert f.cooling_load_kw(20) == pytest.approx(cooling.derived()["cooling_kw"])          # no gain when cooler outside
    assert f.cooling_load_kw(45) - f.cooling_load_kw(25) == pytest.approx(1.5 * 20)        # kW/K x K = kW


def test_n_units_carry_the_hottest_hour_of_the_weather_year():
    hottest = max(r["temp"] for r in cooling.load_weather())
    assert f.cooling_deficit_kw(hottest, f.chillers.n_needed, f.crahs.n_needed) == 0
    assert f.cooling_deficit_kw(hottest, f.chillers.n_needed - 1, f.crahs.n_needed) > 0


def test_chiller_capacity_at_rating_point_and_derating():
    assert f.chiller_unit_kw(35) == pytest.approx(700)
    assert f.chiller_unit_kw(45) == pytest.approx(700 * (1 - 0.12))
    assert f.chiller_unit_kw(20) > f.chiller_unit_kw(35) > f.chiller_unit_kw(47)


def test_capacity_is_set_by_the_weaker_stage():
    assert f.cooling_capacity_kw(35, 3, 2) == pytest.approx(600)      # two CRAHs limit it
    assert f.cooling_capacity_kw(35, 1, 5) == pytest.approx(700)      # one chiller limits it


def test_deficit_never_negative_and_grows_as_units_are_lost():
    d = [f.cooling_deficit_kw(46, c, 4) for c in (3, 2, 1, 0)]
    assert d[0] == 0 and d == sorted(d) and d[-1] == pytest.approx(f.cooling_load_kw(46))


def test_thermal_response_units():
    # 12,800 kJ/K warmed by 1,280 kW (= kJ/s) rises 0.1 K/s = 6 K/min
    assert f.rise_k_per_min(1280) == pytest.approx(6.0)
    assert f.minutes_to(27, 1280) == pytest.approx(2 / 6)
    assert f.minutes_to(27, 0) is None
    assert f.minutes_to(32, 300) > f.minutes_to(27, 300)


def test_power_needs_source_path_and_capacity():
    assert f.power_ok(True, 0, 2, 4, 1, 40)
    assert not f.power_ok(False, 1, 2, 4, 1, 46)        # one 800 kW generator cannot carry ~1,500 kW
    assert f.power_ok(False, 2, 2, 4, 1, 46)
    assert not f.power_ok(True, 2, 1, 4, 1, 30)         # one 600 kW UPS module cannot carry 1,000 kW
    assert not f.power_ok(True, 2, 2, 4, 0, 30)         # no transfer switch, no path
