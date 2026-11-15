"""Module 1: the facility model. A fictional 1 MW IT hall in Dubai.

Power chain:  utility -> ATS -> UPS (with battery) -> PDUs -> IT        generators back up the utility
Cooling:      chillers (outdoor, air-cooled) -> chilled water -> CRAH units -> hall air

Each subsystem has N units needed for full load and a redundancy design: "N", "N+1" or "2N".
Everything marked ASSUMPTION is a labelled assumption, not a measurement or a vendor figure.
"""
from dataclasses import dataclass, field

from . import cooling

DESIGNS = ("N", "N+1", "2N")


def installed(n_needed, design):
    """Units installed for a design: N -> n, N+1 -> n+1, 2N -> 2n."""
    return {"N": n_needed, "N+1": n_needed + 1, "2N": 2 * n_needed}[design]


@dataclass
class Subsystem:
    name: str
    n_needed: int            # units needed to carry the full load (the "N")
    unit_kw: float           # capacity of one unit at its rating condition
    design: str = "N+1"

    @property
    def n_installed(self):
        return installed(self.n_needed, self.design)


@dataclass
class Facility:
    it_kw: float = 1000.0
    # --- cooling (ASSUMPTIONS unless noted) ---
    supply_air_c: float = 25.0             # server inlet setpoint, inside ASHRAE recommended 18-27 C
    limit_recommended_c: float = 27.0      # ASHRAE TC 9.9 (2021) recommended upper limit
    limit_allowable_c: float = 32.0        # class A1 allowable upper limit, as reported by secondary sources
    envelope_kw_per_k: float = 1.5         # heat gain through walls and ventilation per K above the hall temperature
    chiller_derate_per_k: float = 0.012    # air-cooled chiller loses 1.2% of capacity per K of outdoor air above 35 C
    chiller_rating_c: float = 35.0         # outdoor temperature at which unit_kw is rated
    thermal_mass_kj_per_k: float = 12800.0 # hall air (2,400 m3) plus the part of the equipment that warms in the first minutes
    it_shutdown_c: float = 40.0            # servers shut themselves down at this inlet temperature to protect hardware
    # --- power (ASSUMPTIONS) ---
    ups_battery_min: float = 5.0           # battery run time at full load
    generator_start_s: float = 30.0        # time for generators to start and take load
    chiller_restart_min: float = 5.0       # chillers need this long to restart after a power interruption
    # --- subsystems ---
    chillers: Subsystem = field(default_factory=lambda: Subsystem("chiller", 2, 700.0))
    crahs: Subsystem = field(default_factory=lambda: Subsystem("crah", 4, 300.0))
    ups: Subsystem = field(default_factory=lambda: Subsystem("ups", 2, 600.0))
    generators: Subsystem = field(default_factory=lambda: Subsystem("generator", 2, 800.0))
    pdus: Subsystem = field(default_factory=lambda: Subsystem("pdu", 4, 300.0))
    ats: Subsystem = field(default_factory=lambda: Subsystem("ats", 1, 2000.0, "N"))

    def __post_init__(self):
        self.base = cooling.derived()          # air flow, fan, losses, internal cooling load, Carnot fraction

    def with_design(self, design, cooling_only=False):
        """A copy with every redundant subsystem set to one design."""
        f = Facility(it_kw=self.it_kw)
        for s in (f.chillers, f.crahs) + (() if cooling_only else (f.ups, f.generators, f.pdus)):
            s.design = design
        if not cooling_only:
            f.ats.design = "N" if design == "N" else "2N"       # one ATS, or one per path
        return f

    # ---------------- cooling ----------------
    def cooling_load_kw(self, t_out):
        """Heat to remove: everything electrical in the hall plus heat leaking in from outside."""
        return self.base["cooling_kw"] + self.envelope_kw_per_k * max(0.0, t_out - self.supply_air_c)

    def chiller_unit_kw(self, t_out):
        """Capacity of one chiller at this outdoor temperature (falls in heat, rises a little in cool air)."""
        return self.chillers.unit_kw * (1 - self.chiller_derate_per_k * (t_out - self.chiller_rating_c))

    def crah_unit_kw(self, inlet_c=None):
        """Capacity of one CRAH. A coil moves heat in proportion to the temperature difference between the
        return air and the chilled water, so a hotter hall gets more out of the same coil (ASSUMPTION: linear)."""
        if inlet_c is None:
            return self.crahs.unit_kw
        air_dt, chw = cooling.INPUTS["air_dt_k"][0], cooling.INPUTS["chw_supply_c"][0]
        return self.crahs.unit_kw * (inlet_c + air_dt - chw) / (self.supply_air_c + air_dt - chw)

    def cooling_capacity_kw(self, t_out, chillers_up, crahs_up, inlet_c=None):
        """The weaker of the two stages sets what the hall can reject."""
        return min(chillers_up * self.chiller_unit_kw(t_out), crahs_up * self.crah_unit_kw(inlet_c))

    def cooling_deficit_kw(self, t_out, chillers_up, crahs_up):
        return max(0.0, self.cooling_load_kw(t_out) - self.cooling_capacity_kw(t_out, chillers_up, crahs_up))

    def chillers_needed(self, t_out):
        """Fewest chillers that carry the load at this outdoor temperature."""
        load, unit, n = self.cooling_load_kw(t_out), self.chiller_unit_kw(t_out), 1
        while n * unit < load - 1e-9:
            n += 1
        return n

    # ---------------- thermal response ----------------
    def rise_k_per_min(self, deficit_kw):
        """Heat balance on the hall: dT/dt = uncooled heat / thermal mass."""
        return deficit_kw / self.thermal_mass_kj_per_k * 60

    def minutes_to(self, limit_c, deficit_kw, start_c=None):
        """Minutes until the inlet reaches a limit at a constant deficit (None if it never does)."""
        start = self.supply_air_c if start_c is None else start_c
        if deficit_kw <= 0:
            return None
        return max(0.0, limit_c - start) / self.rise_k_per_min(deficit_kw)

    # ---------------- power ----------------
    def facility_kw(self, t_out):
        """Total electrical demand at this outdoor temperature (IT + losses + fans + pumps + chillers)."""
        return cooling.hour(t_out)["total_kw"]

    def power_ok(self, utility_up, generators_up, ups_up, pdus_up, ats_up, t_out):
        """True if IT is powered in steady state: a source, a transfer path, enough UPS and PDU capacity."""
        source = utility_up or generators_up * self.generators.unit_kw >= self.facility_kw(t_out)
        return bool(source and ats_up >= 1 and ups_up * self.ups.unit_kw >= self.it_kw
                    and pdus_up * self.pdus.unit_kw >= self.it_kw)

    def summary(self):
        return {s.name: (s.n_needed, s.n_installed, s.unit_kw, s.design)
                for s in (self.chillers, self.crahs, self.ups, self.generators, self.pdus, self.ats)}
