"""Cooling physics for the 1 MW Dubai data hall (reused from github.com/dodo5037/dubai-datacenter-cooling).
Heat balance (Q = m cp dT), chiller COP as a fraction of Carnot, free cooling and PUE.
Every input marked A is an assumption; S is sourced (see README)."""
import csv
from collections import defaultdict

INPUTS = {
    # key: (value, unit, A/S, label, note)
    "it_kw": (1000.0, "kW", "A", "IT load", "The scenario: a 1 MW hall at constant full load"),
    "supply_air_c": (25.0, "deg C", "A", "Server inlet (supply air) temperature", "Inside the ASHRAE recommended range of 18 to 27 deg C"),
    "air_dt_k": (12.0, "K", "A", "Air temperature rise across the IT equipment", "Typical design value; return air = 37 deg C"),
    "cp_air": (1.006, "kJ/kg.K", "S", "Specific heat of air", "Physical property of dry air near 300 K"),
    "rho_air": (1.15, "kg/m3", "S", "Density of air", "Physical property of air near 30 deg C at sea level"),
    "fan_dp_pa": (400.0, "Pa", "A", "Fan static pressure", "Assumed total for coil, filters and floor"),
    "fan_eff": (0.60, "-", "A", "Fan and motor efficiency", "Assumed"),
    "elec_loss_frac": (0.06, "of IT", "A", "UPS and distribution losses", "Assumed 6% of IT load"),
    "light_frac": (0.02, "of IT", "A", "Lighting and small power", "Assumed 2% of IT load"),
    "chw_supply_c": (18.0, "deg C", "A", "Chilled-water supply temperature", "Warm-water design, 7 K below the supply air"),
    "chw_return_c": (24.0, "deg C", "A", "Chilled-water return temperature", "6 K rise"),
    "cp_water": (4.186, "kJ/kg.K", "S", "Specific heat of water", "Physical property"),
    "rho_water": (998.0, "kg/m3", "S", "Density of water", "Physical property near 20 deg C"),
    "pump_head_kpa": (250.0, "kPa", "A", "Chilled-water pump head", "Assumed"),
    "pump_eff": (0.70, "-", "A", "Pump and motor efficiency", "Assumed"),
    "cond_approach_k": (12.0, "K", "A", "Condensing temperature above outdoor air", "Assumed for an air-cooled chiller"),
    "evap_approach_k": (4.0, "K", "A", "Evaporating temperature below chilled-water supply", "Assumed"),
    "rated_cop": (2.96, "-", "S", "Chiller COP at the rating point", "10.1 EER / 3.412: minimum for air-cooled chillers, California Title 24 (2022) Table 110.2-D"),
    "rated_air_c": (35.0, "deg C", "S", "Rating point: outdoor air", "AHRI 550/590 standard rating condition (95 F), as widely quoted"),
    "rated_lwt_c": (6.7, "deg C", "S", "Rating point: leaving chilled water", "AHRI 550/590 standard rating condition (44 F), as widely quoted"),
    "fc_approach_k": (5.0, "K", "A", "Free-cooling dry cooler: water leaves this much above outdoor air", "Assumed"),
}
K = 273.15


def v(key, inputs=None):
    return (inputs or INPUTS)[key][0] if not isinstance((inputs or INPUTS)[key], (int, float)) else (inputs or INPUTS)[key]


def derived(i=None):
    g = lambda k: v(k, i)
    d = {}
    d["air_kg_s"] = g("it_kw") / (g("cp_air") * g("air_dt_k"))                 # Q = m cp dT
    d["air_m3_s"] = d["air_kg_s"] / g("rho_air")
    d["fan_kw"] = d["air_m3_s"] * g("fan_dp_pa") / g("fan_eff") / 1000          # P = V dp / eff
    d["loss_kw"] = g("it_kw") * g("elec_loss_frac")
    d["light_kw"] = g("it_kw") * g("light_frac")
    d["cooling_kw"] = g("it_kw") + d["loss_kw"] + d["light_kw"] + d["fan_kw"]   # all electricity ends as heat
    d["chw_kg_s"] = d["cooling_kw"] / (g("cp_water") * (g("chw_return_c") - g("chw_supply_c")))
    d["pump_kw"] = d["chw_kg_s"] / g("rho_water") * g("pump_head_kpa") / g("pump_eff")
    t_evap_rated = g("rated_lwt_c") - g("evap_approach_k") + K
    t_cond_rated = g("rated_air_c") + g("cond_approach_k") + K
    d["carnot_frac"] = g("rated_cop") / (t_evap_rated / (t_cond_rated - t_evap_rated))
    d["t_evap_k"] = g("chw_supply_c") - g("evap_approach_k") + K
    d["fc_full_below_c"] = g("chw_supply_c") - g("fc_approach_k")               # full free cooling at or below
    d["fc_none_above_c"] = g("chw_return_c") - g("fc_approach_k")               # no free cooling at or above
    return d


def hour(t_out, i=None, d=None):
    g = lambda k: v(k, i)
    d = d or derived(i)
    t_cond = t_out + g("cond_approach_k") + K
    cop = d["carnot_frac"] * d["t_evap_k"] / (t_cond - d["t_evap_k"])
    fc = max(0.0, min(1.0, (g("chw_return_c") - g("fc_approach_k") - t_out) / (g("chw_return_c") - g("chw_supply_c"))))
    chiller = d["cooling_kw"] * (1 - fc) / cop
    total = g("it_kw") + d["loss_kw"] + d["light_kw"] + d["fan_kw"] + d["pump_kw"] + chiller
    return {"t_cond_k": t_cond, "cop": cop, "fc": fc, "chiller_kw": chiller, "total_kw": total, "pue": total / g("it_kw")}


def load_weather(path="data/dubai_2024_hourly.csv"):
    return [{"dt": r["datetime_gst"], "month": int(r["month"]), "temp": float(r["temp_c"]), "dew": float(r["dewpoint_c"]),
             "filled": int(r["temp_filled"])} for r in csv.DictReader(open(path))]


def run(i=None, weather=None):
    d = derived(i)
    w = weather or load_weather()
    rows = [dict(r, **hour(r["temp"], i, d)) for r in w]
    it = v("it_kw", i)
    by = defaultdict(list)
    for r in rows:
        by[r["month"]].append(r)

    def summary(rs):
        n = len(rs)
        return {"hours": n, "avg_temp": sum(r["temp"] for r in rs) / n, "max_temp": max(r["temp"] for r in rs),
                "avg_cop": sum(r["cop"] for r in rs) / n, "pue": sum(r["total_kw"] for r in rs) / (it * n),
                "chiller_mwh": sum(r["chiller_kw"] for r in rs) / 1000, "total_mwh": sum(r["total_kw"] for r in rs) / 1000,
                "fc_any_hours": sum(r["fc"] > 0 for r in rs), "fc_full_hours": sum(r["fc"] >= 1 for r in rs),
                "hours_40_plus": sum(r["temp"] >= 40 for r in rs), "peak_chiller_kw": max(r["chiller_kw"] for r in rs),
                "max_pue": max(r["pue"] for r in rs), "min_pue": min(r["pue"] for r in rs)}
    monthly = {m: summary(rs) for m, rs in sorted(by.items())}
    annual = summary(rows)
    annual["fc_energy_share"] = sum(r["fc"] for r in rows) / len(rows)
    annual["air_econ_hours"] = sum(r["temp"] <= 27 and r["dew"] <= 15 for r in rows)
    annual["filled_hours"] = sum(r["filled"] > 0 for r in rows)
    return d, rows, monthly, annual


if __name__ == "__main__":
    d, rows, monthly, annual = run()
    for k, x in d.items():
        print(f"{k:18} {x:10.3f}")
    print("month hours avgT maxT  COP   PUE  chillerMWh fc_any 40+")
    for m, s in monthly.items():
        print(f"{m:5} {s['hours']:5} {s['avg_temp']:5.1f} {s['max_temp']:4.1f} {s['avg_cop']:5.2f} {s['pue']:5.3f} {s['chiller_mwh']:8.1f} {s['fc_any_hours']:5} {s['hours_40_plus']:4}")
    print({k: round(x, 3) for k, x in annual.items()})
    for t in (15, 25, 35, 40, 46, 47):
        h = hour(t)
        print(t, "COP %.2f chiller %.0f kW PUE %.3f fc %.2f" % (h["cop"], h["chiller_kw"], h["pue"], h["fc"]))
