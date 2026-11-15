"""Module 4: scenario lab. What happens to server inlet temperature, minute by minute, after a failure.

Heat balance on the hall, stepped every 10 seconds:
    change in temperature = (heat produced - heat removed) x time / thermal mass
When cooling comes back, any spare capacity pulls the temperature back down to the setpoint.
A CRAH coil removes more heat from hotter air, so a hall short of CRAH capacity settles at a higher temperature.
If the inlet reaches 40 C the servers shut down (ASSUMPTION).

Every scenario is HYPOTHETICAL. Timings marked ASSUMPTION are labelled assumptions.
"""
from dataclasses import dataclass, field

from .facility import Facility

STEP_S = 10


@dataclass
class Event:
    minute: float
    text: str
    chillers_up: int = None        # None = unchanged
    crahs_up: int = None
    plant_running: bool = None     # False while chillers are stopped or restarting
    it_powered: bool = None


@dataclass
class Outcome:
    name: str
    design: str
    outdoor_c: float
    minutes: list = field(default_factory=list)
    temps: list = field(default_factory=list)
    log: list = field(default_factory=list)            # (minute, text)
    peak_c: float = 0.0
    minutes_to_27: float = None
    minutes_to_32: float = None
    minutes_above_27: float = 0.0
    minutes_above_32: float = 0.0
    it_lost: bool = False
    it_shutdown_minute: float = None


def simulate(f: Facility, name, outdoor_c, events, duration_min=45):
    """Step the hall's heat balance through a list of timed events."""
    ch, cr, plant, powered = f.chillers.n_installed, f.crahs.n_installed, True, True
    t_c, o = f.supply_air_c, Outcome(name, f.chillers.design, outdoor_c)
    todo = sorted(events, key=lambda e: e.minute)
    for k in range(int(duration_min * 60 / STEP_S) + 1):
        minute = k * STEP_S / 60
        while todo and todo[0].minute <= minute + 1e-9:
            e = todo.pop(0)
            ch = e.chillers_up if e.chillers_up is not None else ch
            cr = e.crahs_up if e.crahs_up is not None else cr
            plant = e.plant_running if e.plant_running is not None else plant
            powered = e.it_powered if e.it_powered is not None else powered
            o.log.append((e.minute, e.text))
            o.it_lost = o.it_lost or e.it_powered is False
        o.minutes.append(minute)
        o.temps.append(t_c)
        if t_c >= f.limit_recommended_c:
            o.minutes_above_27 += STEP_S / 60
            o.minutes_to_27 = minute if o.minutes_to_27 is None else o.minutes_to_27
        if t_c >= f.limit_allowable_c:
            o.minutes_above_32 += STEP_S / 60
            o.minutes_to_32 = minute if o.minutes_to_32 is None else o.minutes_to_32
        if powered and t_c >= f.it_shutdown_c:                    # servers protect themselves
            powered, o.it_shutdown_minute = False, minute
            o.log.append((minute, f"Inlet reaches {f.it_shutdown_c:.0f} C: servers shut down to protect hardware"))
        load = f.cooling_load_kw(outdoor_c) if powered else 0.0
        capacity = f.cooling_capacity_kw(outdoor_c, ch if plant else 0, cr, inlet_c=t_c)
        net_kw = load - capacity                                  # positive = heating up
        if net_kw < 0 and t_c <= f.supply_air_c:
            net_kw = 0.0                                          # controls hold the setpoint, they do not overcool
        t_c = max(f.supply_air_c, t_c + net_kw * STEP_S / f.thermal_mass_kj_per_k)
    o.peak_c = max(o.temps)
    return o


# ----------------------------------------------------------------------------- the three scenarios
STANDBY_START_MIN = 1.0        # ASSUMPTION: a healthy standby unit is cooling one minute after the failure
OPERATOR_FIX_MIN = 12.0        # ASSUMPTION: time for a technician to find and fix a standby unit that did not cool


def crah_failure(design="N+1", outdoor_c=46.0, standby_works=True):
    """A running CRAH unit fails on a 46 C afternoon."""
    f = Facility().with_design(design)
    n, inst = f.crahs.n_needed, f.crahs.n_installed
    ev = [Event(2, "CRAH unit trips (fan motor failure)", crahs_up=min(inst, n) - 1)]
    if inst > n and standby_works:
        ev.append(Event(2 + STANDBY_START_MIN, "Standby CRAH is running and cooling", crahs_up=n))
    elif inst > n:
        ev.append(Event(2 + STANDBY_START_MIN, "Standby CRAH starts but does not cool (hidden fault: valve closed)"))
        ev.append(Event(2 + OPERATOR_FIX_MIN, "Technician opens the valve; standby CRAH cooling", crahs_up=n))
    else:
        ev.append(Event(2 + OPERATOR_FIX_MIN + 18, "Unit repaired and returned to service", crahs_up=n))
    label = "works" if standby_works else "hidden fault"
    return simulate(f, f"CRAH failure, {design}" + (f", standby {label}" if inst > n else ", no standby"), outdoor_c, ev)


def utility_loss(design="N+1", outdoor_c=46.0, buffer_min=0.0):
    """Utility fails; one generator does not start. Cooling stops until generators carry the load and the chillers restart.

    buffer_min: minutes of chilled water held in a storage tank (ASSUMPTION; 0 = none)."""
    f = Facility().with_design(design)
    started = f.generators.n_installed - 1
    enough = started * f.generators.unit_kw >= f.facility_kw(outdoor_c)
    g = f.generator_start_s / 60
    ev = [Event(2, "Utility power lost. IT rides on UPS battery; fans, pumps and chillers stop", plant_running=False, crahs_up=0)]
    if enough:
        ev.append(Event(2 + g, f"{started} of {f.generators.n_installed} generators start (one fails) and take the load; fans and pumps restart",
                        crahs_up=f.crahs.n_installed))
        if buffer_min > 0:
            ev[-1].plant_running = True
            ev[-1].text += f"; storage tank supplies chilled water for {buffer_min:g} minutes"
            if buffer_min < f.chiller_restart_min:
                ev.append(Event(2 + g + buffer_min, "Storage tank exhausted before the chillers are back", plant_running=False))
        ev.append(Event(2 + g + f.chiller_restart_min, "Chillers restarted and cooling", plant_running=True))
    else:
        ev.append(Event(2 + g, f"Only {started} generator starts: {started * f.generators.unit_kw:.0f} kW cannot carry {f.facility_kw(outdoor_c):.0f} kW"))
        ev.append(Event(2 + f.ups_battery_min, "UPS battery exhausted. IT load loses power", it_powered=False))
    tank = f", {buffer_min:g} min chilled-water tank" if buffer_min else ""
    return simulate(f, f"Utility loss + one generator fails, {design}{tank}", outdoor_c, ev)


def common_mode(design="2N", outdoor_c=46.0, fix_min=10.0):
    """One fault stops every chiller at once (for example a shared control system). Redundancy does not help."""
    f = Facility().with_design(design)
    ev = [Event(2, "Shared control fault trips ALL chillers together", plant_running=False),
          Event(2 + fix_min, "Fault cleared by the operator; chillers restarting"),
          Event(2 + fix_min + f.chiller_restart_min, "Chillers back and cooling", plant_running=True)]
    return simulate(f, f"Common-mode chiller trip, {design}", outdoor_c, ev)


def run_all():
    return [crah_failure("N"), crah_failure("N+1", standby_works=True), crah_failure("N+1", standby_works=False),
            utility_loss("N"), utility_loss("N+1"), utility_loss("N+1", buffer_min=6), utility_loss("2N", buffer_min=6),
            common_mode("N+1"), common_mode("2N")]


def table(outcomes):
    def m(x):
        return "never" if x is None else f"{x - 2:.1f} min"       # minutes after the failure at minute 2
    return [{"scenario": o.name, "peak_c": round(o.peak_c, 1), "to_27": m(o.minutes_to_27), "to_32": m(o.minutes_to_32),
             "minutes_above_27": round(o.minutes_above_27, 1), "minutes_above_32": round(o.minutes_above_32, 1),
             "it_power_lost": o.it_lost,
             "thermal_shutdown": "no" if o.it_shutdown_minute is None else f"after {o.it_shutdown_minute - 2:.1f} min"} for o in outcomes]


if __name__ == "__main__":
    for r in table(run_all()):
        print(f'{r["scenario"]:62} peak {r["peak_c"]:5.1f} C  27 C after {r["to_27"]:>9}  32 C after {r["to_32"]:>9}  '
              f'above 27: {r["minutes_above_27"]:5.1f} min  above 32: {r["minutes_above_32"]:5.1f} min  power lost: {r["it_power_lost"]}  thermal shutdown: {r["thermal_shutdown"]}')
