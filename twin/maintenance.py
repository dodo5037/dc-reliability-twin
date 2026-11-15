"""Module 3: maintenance-window optimizer.

Taking a unit offline for planned maintenance turns an N+1 system into an N system for a few hours.
If a second unit of the same kind fails in that window, the hall is short of cooling. How short depends
on the weather in that hour: chillers lose capacity in heat and the hall gains more heat from outside.

Risk of one hour of maintenance = (chance a remaining unit fails in that hour) x (kW short if it does)
                                  x (hours to put the unit under maintenance back in service)
It is an expected amount of uncooled heat, in kWh. Lower is better.

ASSUMPTIONS (labelled): how often and how long each unit is maintained, and the time to abort a job.
The schedule is chosen with hindsight on the 2024 weather year; a real planner would use a forecast.
"""
from dataclasses import dataclass
from datetime import datetime

from . import cooling
from .facility import Facility
from .reliability import PUBLISHED, HOURS

PLAN = {
    # kind: (jobs per unit per year, hours per job)          ASSUMPTIONS
    "chiller": (4, 8),
    "crah": (2, 4),
}
RESTORE_HOURS = 2.0          # ASSUMPTION: time to abort the job and return the unit to service
DAY_SHIFT = range(7, 17)     # jobs must start and finish inside 07:00-17:00 for the "day shift" strategies


@dataclass
class Job:
    kind: str
    unit: int
    number: int          # 1st, 2nd ... job of the year for this unit
    month: int           # month the fixed schedule puts it in
    hours: int


def weather():
    w = cooling.load_weather()
    for r in w:
        r["t"] = datetime.strptime(r["dt"], "%Y-%m-%d %H:%M")
    return w


def hourly_risk(f: Facility, kind, w):
    """Expected kWh of uncooled heat for each hour of the year if one unit of this kind is offline."""
    lam = PUBLISHED[kind][0]
    sub = f.chillers if kind == "chiller" else f.crahs
    working = sub.n_installed - 1                       # one is under maintenance
    p_fail = working * lam / HOURS                      # chance that one of the others fails in a given hour
    out = []
    for r in w:
        ch = working - 1 if kind == "chiller" else f.chillers.n_installed
        cr = working - 1 if kind == "crah" else f.crahs.n_installed
        out.append(p_fail * f.cooling_deficit_kw(r["temp"], ch, cr) * RESTORE_HOURS)
    return out


def jobs(f: Facility):
    """The year's job list. Chillers: one job a month, units in turn. CRAHs: one job a month from January."""
    out = []
    n_ch, n_cr = f.chillers.n_installed, f.crahs.n_installed
    for i in range(n_ch * PLAN["chiller"][0]):
        out.append(Job("chiller", i % n_ch, i // n_ch + 1, 1 + (i * 12) // (n_ch * PLAN["chiller"][0]), PLAN["chiller"][1]))
    for i in range(n_cr * PLAN["crah"][0]):
        out.append(Job("crah", i % n_cr, i // n_cr + 1, 1 + (i * 12) // (n_cr * PLAN["crah"][0]), PLAN["crah"][1]))
    return out


def window_risk(risk, start, hours):
    return sum(risk[start:start + hours])


def fixed_schedule(job_list, w):
    """Baseline: every job starts at 09:00 on a fixed day of its month (the 5th for chillers, the 12th for CRAHs)."""
    index = {(r["t"].month, r["t"].day, r["t"].hour): i for i, r in enumerate(w)}
    return [index[(j.month, 5 if j.kind == "chiller" else 12, 9)] for j in job_list]


def optimise(job_list, risks, w, same_month=True, day_shift=False, min_gap_days=60):
    """Pick a start hour for every job, lowest risk first, never two units of one kind offline together.

    same_month=True keeps each job in the month the fixed schedule uses (only the day and hour move).
    same_month=False lets a job move anywhere in the year, as long as jobs on the same unit stay
    at least min_gap_days apart.
    """
    n = len(w)
    busy = {"chiller": [False] * n, "crah": [False] * n}
    placed = {}                                            # (kind, unit) -> list of start hours
    starts = [None] * len(job_list)
    order = sorted(range(len(job_list)), key=lambda i: -job_list[i].hours)
    for i in order:
        j = job_list[i]
        risk, best, best_start = risks[j.kind], None, None
        for s in range(0, n - j.hours):
            t0, t1 = w[s]["t"], w[s + j.hours - 1]["t"]
            if same_month and (t0.month != j.month or t1.month != j.month):
                continue
            if day_shift and not (t0.hour in DAY_SHIFT and t1.hour in DAY_SHIFT and t0.date() == t1.date()):
                continue
            if any(busy[j.kind][s:s + j.hours]):
                continue
            if not same_month and any(abs(s - p) < min_gap_days * 24 for p in placed.get((j.kind, j.unit), [])):
                continue
            r = window_risk(risk, s, j.hours)
            if best is None or r < best:
                best, best_start = r, s
        starts[i] = best_start
        placed.setdefault((j.kind, j.unit), []).append(best_start)
        for h in range(best_start, best_start + j.hours):
            busy[j.kind][h] = True
    return starts


def total_risk(job_list, starts, risks):
    return sum(window_risk(risks[j.kind], s, j.hours) for j, s in zip(job_list, starts))


def describe(job_list, starts, risks, w):
    rows = []
    for j, s in zip(job_list, starts):
        temps = [w[h]["temp"] for h in range(s, s + j.hours)]
        rows.append({"kind": j.kind, "unit": j.unit + 1, "job": j.number, "start": w[s]["dt"], "hours": j.hours,
                     "avg_temp_c": round(sum(temps) / len(temps), 1), "max_temp_c": max(temps),
                     "risk_kwh": window_risk(risks[j.kind], s, j.hours)})
    return rows


def run(f: Facility = None):
    f = f or Facility()                                    # N+1 by default
    w = weather()
    risks = {k: hourly_risk(f, k, w) for k in PLAN}
    jl = jobs(f)
    schedules = {
        "Fixed: 09:00 on a set day each month": fixed_schedule(jl, w),
        "Same month, best day, day shift (07:00-17:00)": optimise(jl, risks, w, same_month=True, day_shift=True),
        "Same month, best hours, any time of day": optimise(jl, risks, w, same_month=True, day_shift=False),
        "Any month (60 days apart per unit), day shift": optimise(jl, risks, w, same_month=False, day_shift=True),
        "Any month (60 days apart per unit), any time": optimise(jl, risks, w, same_month=False, day_shift=False),
    }
    base = total_risk(jl, schedules["Fixed: 09:00 on a set day each month"], risks)
    out = {}
    for name, starts in schedules.items():
        rows = describe(jl, starts, risks, w)
        tot = total_risk(jl, starts, risks)
        out[name] = {"risk_kwh_per_year": tot, "reduction_vs_fixed": 1 - tot / base,
                     "by_kind": {k: sum(r["risk_kwh"] for r in rows if r["kind"] == k) for k in PLAN},
                     "avg_temp_c": sum(r["avg_temp_c"] * r["hours"] for r in rows) / sum(r["hours"] for r in rows),
                     "jobs": rows}
    return out, risks, w


if __name__ == "__main__":
    out, risks, w = run()
    for name, o in out.items():
        print(f'{name:48} risk {o["risk_kwh_per_year"]:.3f} kWh/yr  reduction {o["reduction_vs_fixed"]:6.1%}  '
              f'avg temp during jobs {o["avg_temp_c"]:.1f} C  chiller {o["by_kind"]["chiller"]:.3f}  crah {o["by_kind"]["crah"]:.4f}')
    for k in PLAN:
        r = risks[k]
        print(k, "hourly risk min %.5f max %.5f ratio %.2f" % (min(r), max(r), max(r) / min(r)))
    for row in out["Any month (60 days apart per unit), any time"]["jobs"][:6]:
        print(row)
