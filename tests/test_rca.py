"""Module 6 tests: a report appears only on a breach, and its numbers are the simulation's numbers."""
import re

from twin import rca, scenarios as S
from twin.facility import Facility

f = Facility()
ALL = S.run_all()


def test_no_report_when_no_limit_is_breached():
    ok = S.crah_failure("N+1", standby_works=True)
    assert not rca.needs_report(ok) and rca.report(ok) is None


def test_every_breaching_scenario_has_a_library_entry_and_a_report():
    for o in ALL:
        if rca.needs_report(o):
            assert o.kind in rca.LIBRARY, o.name
            assert rca.report(o).startswith("# Incident report")


def test_report_numbers_come_from_the_simulation():
    o = S.crah_failure("N+1", standby_works=False)
    text = rca.report(o)
    assert f"Peak inlet temperature | {o.peak_c:.1f} C" in text
    assert f"| {o.minutes_above_27:.1f} min |" in text
    assert "HYPOTHETICAL" in text


def test_timeline_is_in_time_order_and_includes_limit_crossings():
    o = S.utility_loss("N+1")
    rows = rca.timeline(o, f)
    assert [m for m, _ in rows] == sorted(m for m, _ in rows)
    assert any("27 C" in t for _, t in rows) and any("Peak inlet" in t for _, t in rows)


def test_every_library_entry_is_complete():
    for kind, k in rca.LIBRARY.items():
        assert len(k["whys"]) == 5, kind
        assert k["corrective"] and k["preventive"] and k["factors"] and k["root"]
        for action, owner, verified in k["corrective"] + k["preventive"]:
            assert action and owner and verified


def test_reports_are_written_one_per_breach(tmp_path):
    written = rca.write_all(ALL, folder=str(tmp_path))
    assert len(written) == sum(rca.needs_report(o) for o in ALL)
    assert all(re.search(r"\.md$", p) for p in written)
