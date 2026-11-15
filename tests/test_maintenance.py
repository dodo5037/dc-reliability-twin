"""Module 3 tests: the risk measure and the optimizer's constraints."""
from itertools import product

import pytest

from twin import maintenance as M
from twin.facility import Facility

out, risks, w = M.run()
f = Facility()
jl = M.jobs(f)
FIXED = "Fixed: 09:00 on a set day each month"


def test_job_list_matches_the_plan():
    assert sum(j.kind == "chiller" for j in jl) == f.chillers.n_installed * M.PLAN["chiller"][0] == 12
    assert sum(j.kind == "crah" for j in jl) == f.crahs.n_installed * M.PLAN["crah"][0] == 10


def test_chiller_risk_rises_with_outdoor_temperature():
    pairs = sorted(zip([r["temp"] for r in w], risks["chiller"]))
    assert all(a[1] <= b[1] + 1e-12 for a, b in zip(pairs, pairs[1:]))
    assert max(risks["chiller"]) / min(risks["chiller"]) > 2


def test_hourly_risk_formula_by_hand():
    lam = M.PUBLISHED["chiller"][0]
    t = w[0]["temp"]
    expected = 2 * lam / 8760 * f.cooling_deficit_kw(t, 1, 5) * M.RESTORE_HOURS     # 2 chillers left, then 1
    assert risks["chiller"][0] == pytest.approx(expected)


def test_every_optimised_schedule_beats_the_fixed_one():
    base = out[FIXED]["risk_kwh_per_year"]
    for name, o in out.items():
        assert o["risk_kwh_per_year"] <= base + 1e-12, name
    assert out["Any month (60 days apart per unit), any time"]["risk_kwh_per_year"] <= out["Same month, best hours, any time of day"]["risk_kwh_per_year"]


def test_no_two_units_of_one_kind_offline_together():
    index = {r["dt"]: i for i, r in enumerate(w)}
    for name, o in out.items():
        if name == FIXED:
            continue
        for kind in M.PLAN:
            used = []
            for j in o["jobs"]:
                if j["kind"] == kind:
                    s = index[j["start"]]
                    used += list(range(s, s + j["hours"]))
            assert len(used) == len(set(used)), (name, kind)


def test_day_shift_and_same_month_constraints_hold():
    for j, row in zip(jl, out["Same month, best day, day shift (07:00-17:00)"]["jobs"]):
        hour = int(row["start"][11:13])
        assert 7 <= hour and hour + row["hours"] - 1 <= 16
        assert int(row["start"][5:7]) == j.month


def test_greedy_equals_brute_force_on_a_small_case():
    small_w = w[:48]
    r = {"chiller": risks["chiller"][:48], "crah": risks["crah"][:48]}
    two = [M.Job("chiller", 0, 1, 1, 8), M.Job("chiller", 1, 1, 1, 8)]
    got = M.total_risk(two, M.optimise(two, r, small_w, same_month=True), r)
    best = min(M.total_risk(two, [a, b], r) for a, b in product(range(40), repeat=2) if abs(a - b) >= 8)
    assert got == pytest.approx(best, rel=0.02)
