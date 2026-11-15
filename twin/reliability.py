"""Module 2: reliability engine. Monte Carlo of failures and repairs, with an analytical cross-check.

Each unit alternates between working and being repaired. Time to failure and time to repair are drawn from
exponential distributions with the published failure rate and mean repair time. The simulation walks through
many simulated years and adds up the time the hall is short of cooling or the IT load is without power.

PUBLISHED DATA (US Army TM 5-698-5, 22 July 2006, Appendix B, PREP database):
    failure rate in failures per unit-year, MTTR in hours, item number, page.
ASSUMPTIONS are marked as such in ASSUMED.
"""
from dataclasses import dataclass
from math import comb, exp

import numpy as np

from . import cooling
from .facility import Facility

HOURS = 8760.0

PUBLISHED = {
    # key: (failures per year, MTTR hours, item, page, description in the source)
    "chiller": (0.11820, 12.62, "H10-000", "B-4", "Chiller (all types)"),
    "crah": (0.01100, 2.36, "H5-000", "B-2", "Air handling unit (used for CRAH units)"),
    "generator": (0.12350, 18.28, "E18-122", "B-6", "Diesel generator, packaged, 250 kW-1.5 MW, standby"),
    "ups": (0.00938, 2.00, "E39-200", "B-12", "UPS, small computer room floor"),
    "ats": (0.05117, 4.10, "E34-100", "B-9", "Switch, automatic transfer"),
}
ASSUMED = {
    # Dubai's utility reports 0.94 customer minutes lost per customer in 2024 (DEWA Integrated Report 2024).
    # It does not publish how often a customer is interrupted, so the frequency is an assumption and the
    # mean duration is set so that frequency x duration = 0.94 minutes a year.
    "utility_minutes_lost_per_year": 0.94,          # published (DEWA, 2024)
    "utility_outages_per_year": 0.10,               # ASSUMPTION
    "generator_fail_to_start": 0.01,                # ASSUMPTION: chance one generator does not start when called
}


def unit_availability(key):
    lam, mttr = PUBLISHED[key][:2]
    mtbf = HOURS / lam
    return mtbf / (mtbf + mttr)                      # inherent availability = MTBF / (MTBF + MTTR)


def k_of_n(a, k, n):
    """Probability that at least k of n identical independent units are working."""
    return sum(comb(n, j) * a ** j * (1 - a) ** (n - j) for j in range(k, n + 1))


def analytical_cooling_unavailability(f: Facility):
    """Share of time with fewer than N chillers or fewer than N CRAH units working."""
    ok = (k_of_n(unit_availability("chiller"), f.chillers.n_needed, f.chillers.n_installed)
          * k_of_n(unit_availability("crah"), f.crahs.n_needed, f.crahs.n_installed))
    return 1 - ok


def down_intervals(rng, lam_per_year, mttr_h, horizon_h):
    """Start and end times (hours) of every repair period of one unit over the horizon."""
    mean_up = HOURS / lam_per_year
    n = int(horizon_h / (mean_up + mttr_h) * 1.3) + 50
    while True:
        up, down = rng.exponential(mean_up, n), rng.exponential(mttr_h, n)
        start = np.cumsum(up + down) - down
        if start[-1] > horizon_h:
            break
        n *= 2
    keep = start < horizon_h
    return start[keep], np.minimum(start[keep] + down[keep], horizon_h)


@dataclass
class CoolingResult:
    design: str
    years: int
    shortfall_hours_per_year: float
    events_per_year: float
    prob_event_in_a_year: float
    hours_above_27_per_year: float
    hours_above_32_per_year: float
    unavailability_mc: float
    unavailability_analytical: float
    events: int


def simulate_cooling(f: Facility, years=200_000, seed=1, weather=None):
    """Monte Carlo of chiller and CRAH failures against the hourly Dubai weather year (repeated)."""
    rng = np.random.default_rng(seed)
    temps = np.array([r["temp"] for r in (weather or cooling.load_weather())])
    wy = len(temps)                                   # hours in the weather year
    horizon = years * HOURS
    ev = []                                           # (time, kind, +1 down / -1 back up)
    for kind, sub, key in ((0, f.chillers, "chiller"), (1, f.crahs, "crah")):
        lam, mttr = PUBLISHED[key][:2]
        for _ in range(sub.n_installed):
            s, e = down_intervals(rng, lam, mttr, horizon)
            ev += [(t, kind, 1) for t in s] + [(t, kind, -1) for t in e]
    ev.sort()
    down = [0, 0]
    short_h = above27 = above32 = 0.0
    events, years_hit, in_event, t_prev = 0, set(), False, 0.0
    event_elapsed = 0.0
    for t, kind, step in ev:
        ch_up, cr_up = f.chillers.n_installed - down[0], f.crahs.n_installed - down[1]
        if ch_up < f.chillers.n_needed or cr_up < f.crahs.n_needed:
            a = t_prev
            while a < t - 1e-12:                      # walk the interval hour by hour through the weather
                b = min(t, np.floor(a) + 1.0)
                deficit = f.cooling_deficit_kw(float(temps[int(a) % wy]), ch_up, cr_up)
                if deficit > 0:
                    if not in_event:
                        in_event, event_elapsed = True, 0.0
                        events += 1
                        years_hit.add(int(a // HOURS))
                    dt = b - a
                    short_h += dt
                    for limit, which in ((f.limit_recommended_c, 27), (f.limit_allowable_c, 32)):
                        wait_h = f.minutes_to(limit, deficit) / 60
                        over = max(0.0, event_elapsed + dt - max(wait_h, event_elapsed))
                        if which == 27:
                            above27 += over
                        else:
                            above32 += over
                    event_elapsed += dt
                else:
                    in_event = False
                a = b
        else:
            in_event = False
        down[kind] += step
        t_prev = t
    return CoolingResult(f.chillers.design, years, short_h / years, events / years, len(years_hit) / years,
                         above27 / years, above32 / years, short_h / horizon, analytical_cooling_unavailability(f), events)


@dataclass
class PowerResult:
    design: str
    years: int
    loss_events_per_year: float
    prob_loss_in_a_year: float
    loss_hours_per_year: float
    events_from_utility_and_generators: int
    events_from_ups: int
    events_from_ats: int
    analytical_events_per_year: float


def _count_down_at(intervals, t):
    """How many units are in repair at time t."""
    return sum(int(np.searchsorted(s, t, side="right") - np.searchsorted(e, t, side="right")) for s, e in intervals)


def _shortfall_events(rng, key, sub, horizon):
    """Events and hours with fewer than N units of one kind working."""
    lam, mttr = PUBLISHED[key][:2]
    ev = []
    for _ in range(sub.n_installed):
        s, e = down_intervals(rng, lam, mttr, horizon)
        ev += [(t, 1) for t in s] + [(t, -1) for t in e]
    ev.sort()
    down, hours, events, t_prev, was_short = 0, 0.0, 0, 0.0, False
    for t, step in ev:
        short = sub.n_installed - down < sub.n_needed
        if short:
            hours += t - t_prev
            events += not was_short
        was_short = short
        down += step
        t_prev = t
    return events, hours


def analytical_power_events_per_year(f: Facility, design_temp=40.0):
    """Expected loss-of-power events a year from the same assumptions, for comparison with the simulation."""
    q = 1 - (1 - ASSUMED["generator_fail_to_start"]) * unit_availability("generator")   # a generator is not there when called
    need = int(np.ceil(f.facility_kw(design_temp) / f.generators.unit_kw))
    p_short = 1 - k_of_n(1 - q, need, f.generators.n_installed)
    mean_outage_min = ASSUMED["utility_minutes_lost_per_year"] / ASSUMED["utility_outages_per_year"]
    p_longer_than_battery = exp(-f.ups_battery_min / mean_outage_min)
    from_utility = ASSUMED["utility_outages_per_year"] * p_short * p_longer_than_battery
    def rate_below(key, sub):                          # rate of entering "fewer than N working", by state enumeration
        lam, mttr = PUBLISHED[key][:2]
        a, n, k = unit_availability(key), sub.n_installed, sub.n_needed
        # the system fails when it has exactly k working and one more fails
        return comb(n, k) * a ** k * (1 - a) ** (n - k) * k * lam
    return from_utility + rate_below("ups", f.ups) + rate_below("ats", f.ats)


def simulate_power(f: Facility, years=200_000, seed=2, weather=None):
    """Loss of power to the IT load: utility outage with too few generators, too few UPS modules, or no transfer switch."""
    rng = np.random.default_rng(seed)
    temps = np.array([r["temp"] for r in (weather or cooling.load_weather())])
    horizon = years * HOURS
    ups_events, ups_hours = _shortfall_events(rng, "ups", f.ups, horizon)
    ats_events, ats_hours = _shortfall_events(rng, "ats", f.ats, horizon)
    gens = [down_intervals(rng, *PUBLISHED["generator"][:2], horizon) for _ in range(f.generators.n_installed)]
    n_out = rng.poisson(ASSUMED["utility_outages_per_year"] * years)
    starts = rng.uniform(0, horizon, n_out)
    mean_h = ASSUMED["utility_minutes_lost_per_year"] / ASSUMED["utility_outages_per_year"] / 60
    durations = rng.exponential(mean_h, n_out)
    battery_h = f.ups_battery_min / 60
    util_events, util_hours = 0, 0.0
    for t, dur in zip(starts, durations):
        available = f.generators.n_installed - _count_down_at(gens, t)
        started = rng.binomial(available, 1 - ASSUMED["generator_fail_to_start"])
        need_kw = f.facility_kw(float(temps[int(t) % len(temps)]))
        if started * f.generators.unit_kw < need_kw and dur > battery_h:
            util_events += 1
            util_hours += dur - battery_h
    events = util_events + ups_events + ats_events
    rate = events / years
    return PowerResult(f.generators.design, years, rate, 1 - exp(-rate), (util_hours + ups_hours + ats_hours) / years,
                       util_events, ups_events, ats_events, analytical_power_events_per_year(f))


def run_all(years=200_000):
    out = {}
    for d in ("N", "N+1", "2N"):
        f = Facility().with_design(d)
        out[d] = (simulate_cooling(f, years), simulate_power(f, years))
    return out


if __name__ == "__main__":
    for d, (c, p) in run_all().items():
        print(f"{d:4} COOLING shortfall {c.shortfall_hours_per_year:9.4f} h/yr  events/yr {c.events_per_year:.5f}  "
              f"P(year) {c.prob_event_in_a_year:.5f}  >27C {c.hours_above_27_per_year:.4f} h/yr  >32C {c.hours_above_32_per_year:.4f} h/yr  "
              f"unavail MC {c.unavailability_mc:.3e} vs analytical {c.unavailability_analytical:.3e} ({c.events} events)")
        print(f"     POWER   events/yr {p.loss_events_per_year:.6f} (analytical {p.analytical_events_per_year:.6f})  P(year) {p.prob_loss_in_a_year:.6f}  "
              f"hours/yr {p.loss_hours_per_year:.5f}  from utility+gens {p.events_from_utility_and_generators}, UPS {p.events_from_ups}, ATS {p.events_from_ats}")
