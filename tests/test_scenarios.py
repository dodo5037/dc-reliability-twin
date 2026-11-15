"""Module 4 tests: the heat balance over time and the three scenarios."""
import pytest

from twin import scenarios as S
from twin.facility import Facility


def test_nothing_happens_without_a_failure():
    f = Facility()
    o = S.simulate(f, "steady", 46.0, [])
    assert o.peak_c == pytest.approx(f.supply_air_c) and o.minutes_to_27 is None


def test_total_loss_rises_at_load_over_thermal_mass():
    f = Facility()
    o = S.simulate(f, "all cooling off", 46.0, [S.Event(0, "off", plant_running=False)], duration_min=1)
    rate = f.cooling_load_kw(46.0) / f.thermal_mass_kj_per_k * 60            # K per minute
    assert (o.temps[-1] - o.temps[0]) == pytest.approx(rate * 1.0, rel=0.02)
    assert o.minutes_to_27 == pytest.approx(f.minutes_to(27, f.cooling_load_kw(46.0)), abs=0.2)


def test_crah_capacity_grows_with_hall_temperature():
    f = Facility()
    assert f.crah_unit_kw(25.0) == pytest.approx(300)
    assert f.crah_unit_kw(31.0) > f.crah_unit_kw(25.0)
    assert f.cooling_capacity_kw(35, 3, 4) == f.cooling_capacity_kw(35, 3, 4, inlet_c=25.0)


def test_working_standby_keeps_the_hall_inside_the_recommended_range():
    o = S.crah_failure("N+1", standby_works=True)
    assert o.peak_c < 27 and o.minutes_above_27 == 0


def test_hidden_standby_fault_is_as_bad_as_no_standby_until_someone_fixes_it():
    hidden, none = S.crah_failure("N+1", standby_works=False), S.crah_failure("N")
    assert hidden.minutes_to_27 == pytest.approx(none.minutes_to_27)
    assert hidden.minutes_above_27 < none.minutes_above_27
    assert hidden.temps[-1] == pytest.approx(25.0, abs=0.5)                    # recovers after the fix


def test_n_design_loses_it_power_when_a_generator_fails_to_start():
    assert S.utility_loss("N").it_lost
    assert not S.utility_loss("N+1").it_lost


def test_chilled_water_tank_bridges_the_chiller_restart():
    no_tank, tank = S.utility_loss("N+1"), S.utility_loss("N+1", buffer_min=6)
    assert no_tank.it_shutdown_minute is not None
    assert tank.it_shutdown_minute is None and tank.peak_c < 32


def test_redundancy_does_not_help_against_a_common_mode_failure():
    a, b = S.common_mode("N+1"), S.common_mode("2N")
    assert a.it_shutdown_minute == pytest.approx(b.it_shutdown_minute)
    assert a.minutes_to_32 == pytest.approx(b.minutes_to_32)
