"""Module 7: dashboard. Run with:  streamlit run app.py"""
import json
import os

import pandas as pd
import streamlit as st

from twin import cooling, maintenance, rca, reliability, scenarios
from twin.facility import DESIGNS, Facility

st.set_page_config(page_title="Dubai Data Center Reliability Twin", layout="wide")
st.title("Dubai Data Center Reliability Twin")
st.caption("An educational model of a fictional 1 MW IT hall on real Dubai weather (NOAA, 2024). Not an engineering design. "
           "Every scenario is hypothetical.")

tabs = st.tabs(["Facility", "Reliability", "Maintenance windows", "Scenario lab", "Incident report", "Telemetry"])


@st.cache_data
def weather_frame():
    w = cooling.load_weather()
    return pd.DataFrame({"time": pd.to_datetime([r["dt"] for r in w]), "temp": [r["temp"] for r in w]})


@st.cache_data
def reliability_results():
    return json.load(open("results/reliability.json"))


@st.cache_data
def maintenance_results():
    out, risks, w = maintenance.run()
    return out, risks


# ------------------------------------------------------------------ Facility
with tabs[0]:
    design = st.radio("Redundancy design", DESIGNS, index=1, horizontal=True)
    f = Facility().with_design(design)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IT load", f"{f.it_kw:,.0f} kW")
    c2.metric("Cooling load at 46 °C", f"{f.cooling_load_kw(46):,.0f} kW")
    c3.metric("Site power at 46 °C", f"{f.facility_kw(46):,.0f} kW")
    c4.metric("PUE at 46 °C", f"{cooling.hour(46)['pue']:.2f}")
    st.subheader("Units")
    st.dataframe(pd.DataFrame([{"Equipment": k, "Needed (N)": n, "Installed": inst, "Unit size (kW)": kw, "Design": d}
                               for k, (n, inst, kw, d) in f.summary().items()]), hide_index=True, use_container_width=True)
    t = st.slider("Outdoor temperature (°C)", 15, 48, 46)
    a, b, c = st.columns(3)
    a.metric("One chiller delivers", f"{f.chiller_unit_kw(t):,.0f} kW")
    b.metric("Shortfall if one chiller too few", f"{f.cooling_deficit_kw(t, f.chillers.n_needed - 1, f.crahs.n_installed):,.0f} kW")
    c.metric("Chiller COP", f"{cooling.hour(t)['cop']:.1f}")
    st.subheader("Outdoor temperature, Dubai International, 2024")
    st.line_chart(weather_frame().set_index("time")["temp"].resample("D").agg(["min", "mean", "max"]))

# ------------------------------------------------------------------ Reliability
with tabs[1]:
    st.markdown("One million simulated years per design. Failures are independent, so N+1 and 2N are a best case.")
    res = reliability_results()
    rows = []
    for d in DESIGNS:
        c, p = res[d]["cooling"], res[d]["power"]
        rows.append({"Design": d, "Cooling shortfall (hours a year)": round(c["shortfall_hours_per_year"], 4),
                     "Cooling events a year": c["events_per_year"],
                     "Cooling unavailability, simulated": c["unavailability_mc"], "Cooling unavailability, exact formula": c["unavailability_analytical"],
                     "Power-loss events a year, simulated": p["loss_events_per_year"], "Power-loss events a year, formula": p["analytical_events_per_year"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    n = res["N"]["power"]
    st.markdown("**Where power loss comes from in the N design**")
    st.bar_chart(pd.DataFrame({"events": {"Single transfer switch": n["events_from_ats"], "UPS modules": n["events_from_ups"],
                                          "Utility outage + generators": n["events_from_utility_and_generators"]}}))
    st.markdown("**Published unit data** (US Army TM 5-698-5, 2006, Appendix B)")
    st.dataframe(pd.DataFrame([{"Equipment": v[4], "Failures per year": v[0], "Repair time (h)": v[1], "Item": v[2], "Page": v[3],
                                "Availability": round(reliability.unit_availability(k), 7)} for k, v in reliability.PUBLISHED.items()]),
                 hide_index=True, use_container_width=True)
    if st.button("Run a fresh simulation (20,000 years, N design)"):
        c = reliability.simulate_cooling(Facility().with_design("N"), years=20_000, seed=None)
        st.write(f"Simulated unavailability {c.unavailability_mc:.3e} against the exact formula {c.unavailability_analytical:.3e} "
                 f"({c.events:,} events).")

# ------------------------------------------------------------------ Maintenance
with tabs[2]:
    out, risks = maintenance_results()
    st.markdown("Risk of a maintenance hour = chance a remaining unit fails × kW short if it does × 2 hours to restore. "
                "Chosen with hindsight on 2024 weather, so the reductions are an upper bound.")
    st.dataframe(pd.DataFrame([{"Schedule": k, "Risk (expected kWh uncooled a year)": round(v["risk_kwh_per_year"], 2),
                                "Change vs fixed": f'{-v["reduction_vs_fixed"]:+.0%}', "Average outdoor °C during jobs": round(v["avg_temp_c"], 1)}
                               for k, v in out.items()]), hide_index=True, use_container_width=True)
    pick = st.selectbox("Show the jobs for", list(out))
    st.dataframe(pd.DataFrame(out[pick]["jobs"]), hide_index=True, use_container_width=True)
    st.markdown("**Risk of one hour of chiller maintenance through the year** (daily average)")
    wf = weather_frame().assign(risk=risks["chiller"]).set_index("time")
    st.line_chart(wf["risk"].resample("D").mean())

# ------------------------------------------------------------------ Scenario lab
with tabs[3]:
    kind = st.selectbox("Scenario", ["CRAH unit fails", "Utility loss, one generator fails to start", "All chillers trip together"])
    d = st.radio("Design", DESIGNS, index=1, horizontal=True, key="scen_design")
    temp = st.slider("Outdoor temperature (°C)", 20, 48, 46, key="scen_temp")
    if kind == "CRAH unit fails":
        works = st.checkbox("Standby unit works", value=False)
        o = scenarios.crah_failure(d, temp, works)
    elif kind == "Utility loss, one generator fails to start":
        tank = st.slider("Chilled-water storage (minutes)", 0, 10, 0)
        o = scenarios.utility_loss(d, temp, tank)
    else:
        fix = st.slider("Minutes to clear the fault", 2, 20, 10)
        o = scenarios.common_mode(d, temp, fix)
    st.session_state["outcome"] = o
    a, b, c, e = st.columns(4)
    a.metric("Peak inlet", f"{o.peak_c:.1f} °C")
    b.metric("Minutes above 27 °C", f"{o.minutes_above_27:.1f}")
    c.metric("Minutes above 32 °C", f"{o.minutes_above_32:.1f}")
    e.metric("Outcome", "Power lost" if o.it_lost else ("Shutdown" if o.it_shutdown_minute is not None else
                                                        ("Above 27 °C" if o.minutes_above_27 > 0 else "In limits")))
    st.line_chart(pd.DataFrame({"Inlet °C": o.temps, "27 °C recommended": 27.0, "32 °C allowable": 32.0}, index=pd.Index(o.minutes, name="minute")))
    st.dataframe(pd.DataFrame(o.log, columns=["Minute", "Event"]), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ Incident report
with tabs[4]:
    o = st.session_state.get("outcome")
    text = rca.report(o) if o is not None else None
    if text:
        st.download_button("Download this report (Markdown)", text, file_name="incident_report.md")
        st.markdown(text)
    else:
        st.info("The scenario selected in the Scenario lab stays inside the limits, so there is no incident to report.")

# ------------------------------------------------------------------ Telemetry
with tabs[5]:
    path = "telemetry/data/readings.csv"
    if os.path.exists(path):
        st.dataframe(pd.read_csv(path).tail(200), use_container_width=True)
    else:
        st.info("Module 5 (real telemetry from a home server) is not built yet. No data has been collected.")
