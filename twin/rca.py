"""Module 6: automatic incident report.

When a scenario (or, later, a real anomaly) takes the inlet above the recommended limit, this writes a
root-cause report: summary, impact, timeline, five whys, contributing factors, corrective and preventive
actions, and how each action is verified.

How it works: the numbers and the timeline come from the simulation. The causes and actions come from a
small rule library below, one entry per kind of event. It is a template filled with data, not a diagnosis:
a real investigation starts from evidence on site. Every report is marked HYPOTHETICAL.
"""
from .facility import Facility

LIBRARY = {
    "crah_no_standby": {
        "title": "Cooling shortfall after a single CRAH failure with no standby unit",
        "whys": ["Why did the inlet pass 27 C? Because the hall lost one CRAH unit's worth of cooling.",
                 "Why was that not covered? Because the hall has exactly the number of CRAH units it needs (N) and no spare.",
                 "Why does it have no spare? Because the design accepted that any single CRAH failure degrades the hall.",
                 "Why did the unit fail without warning? Because fan motors are run to failure with no condition monitoring.",
                 "Why is that the practice? Because there is no vibration or bearing-temperature trend to act on."],
        "root": "The design has no redundancy on air handling, so a single component failure reaches the servers.",
        "factors": ["Single point of failure by design (N)", "No condition monitoring on fan motors", "High outdoor temperature left no chiller margin to lower the water temperature"],
        "corrective": [("Repair or replace the failed fan motor and test the unit under load", "Mechanical technician", "Supply air back to setpoint with all units running")],
        "preventive": [("Add one CRAH unit to reach N+1", "Infrastructure engineer", "Repeat this scenario: peak inlet stays below 27 C"),
                       ("Quarterly vibration readings on every fan motor, trended", "Mechanical technician", "First readings on file and an alert threshold defined")],
    },
    "crah_hidden_fault": {
        "title": "Standby CRAH ran without cooling after a running unit failed",
        "whys": ["Why did the inlet pass 27 C? Because the hall was one CRAH unit short for several minutes.",
                 "Why was it short when there is a standby? Because the standby started but delivered no cooling.",
                 "Why did it deliver no cooling? Because its chilled-water valve was closed.",
                 "Why was the valve closed? Because the last maintenance job ended without a return-to-service check.",
                 "Why did nobody notice? Because monitoring reported the unit as available from its fan status alone, and standby units are never run on a schedule."],
        "root": "No return-to-service verification after maintenance, with monitoring that could not see the fault.",
        "factors": ["Maintenance procedure ends at 'return to standby' with no functional test", "'Available' status does not check the valve or the supply-air temperature",
                    "No routine rotation of standby units", "Peak outdoor temperature: no plant margin to compensate"],
        "corrective": [("Open the valve, run the standby unit and record supply and return air temperature", "Shift technician", "Supply air at least 8 K below return air on the log"),
                       ("Walk down every standby unit on site for valve and breaker position", "Operations lead", "Signed checklist, one line per unit")],
        "preventive": [("Add a return-to-service section to every maintenance procedure: positions, a 15-minute functional run, second-person sign-off", "Infrastructure engineer", "First three uses audited"),
                       ("Monitoring: a standby unit is 'available' only if its valve reports open and its last functional run passed", "Controls engineer", "Close a valve on a standby unit: status must change and an alarm must fire"),
                       ("Rotate standby units weekly so every unit runs under load", "Controls engineer", "Log shows every unit as lead within five weeks")],
    },
    "utility_too_few_generators": {
        "title": "IT load lost power: utility failure with too few generators running",
        "whys": ["Why did the IT load lose power? Because the UPS battery ran out before another source carried the load.",
                 "Why did no source carry the load? Because the generators that started could not supply the whole site.",
                 "Why not? Because one generator failed to start and there was no spare (N).",
                 "Why did it fail to start? Unknown from this model: start failures usually trace to batteries, fuel or controls.",
                 "Why was that not found earlier? Because start reliability is only proven by regular tests under load."],
        "root": "No spare generating capacity: one failure to start left the site short of power.",
        "factors": ["Generators at N", "UPS battery sized for minutes, not for a failed start", "Cooling stopped with the power, so the hall also overheated"],
        "corrective": [("Find why the generator did not start; repair and test under load", "Electrical technician", "Successful load-bank test recorded")],
        "preventive": [("Add one generator to reach N+1", "Infrastructure engineer", "Repeat this scenario: IT keeps power"),
                       ("Monthly start test and quarterly load-bank test on every generator", "Electrical technician", "Test records with start time and load carried"),
                       ("Load-shedding plan for a single-generator condition", "Operations lead", "Plan reviewed and walked through once")],
    },
    "utility_no_storage": {
        "title": "Servers overheated after a utility failure although generators carried the load",
        "whys": ["Why did the servers shut down? Because the inlet reached the shutdown temperature.",
                 "Why did it rise that far with power restored? Because the chillers had not restarted yet.",
                 "Why not? Because a chiller needs several minutes to restart after any interruption.",
                 "Why was there no cooling in the meantime? Because the site has no stored chilled water and the fans alone cannot remove heat.",
                 "Why is there no storage? Because the design sized the power backup for the outage but not the cooling gap."],
        "root": "The cooling system has no ride-through for the chiller restart time.",
        "factors": ["Chiller restart time longer than the hall's thermal reserve", "No chilled-water storage", "Pumps and fans not on UPS", "Peak outdoor temperature"],
        "corrective": [("Restart the plant, confirm chilled-water temperature, bring IT back in stages", "Operations lead", "Inlet stable at setpoint for 30 minutes")],
        "preventive": [("Add chilled-water storage sized for the chiller restart time plus margin", "Infrastructure engineer", "Repeat this scenario: peak inlet stays below 32 C"),
                       ("Put chilled-water pumps and CRAH fans on UPS so stored water can be used", "Infrastructure engineer", "Pull-the-plug test with the tank"),
                       ("Review chiller fast-restart settings with the manufacturer", "Mechanical technician", "Measured restart time recorded")],
    },
    "utility_ride_through": {
        "title": "Brief temperature excursion during a utility failure that the site rode through",
        "whys": ["Why did the inlet pass 27 C at all? Because the hall had no air movement or water flow for about half a minute.",
                 "Why not? Because fans and pumps stopped with the utility and only restarted when the generators took the load.",
                 "Why did they stop? Because they are fed from the generator-backed supply, not from the UPS.",
                 "Why does half a minute matter? Because a full hall with no cooling warms by several degrees a minute.",
                 "Why was it only brief? Because stored chilled water covered the chiller restart once the pumps were back."],
        "root": "Fans and pumps are not on UPS, so cooling stops for the generator start time.",
        "factors": ["Generator start time of about 30 seconds", "Fans and pumps not on UPS", "Peak outdoor temperature"],
        "corrective": [("Confirm the storage tank is recharged and all units are back in normal mode", "Operations lead", "Tank temperature and unit status logged")],
        "preventive": [("Put CRAH fans and chilled-water pumps on UPS", "Infrastructure engineer", "Repeat this scenario: peak inlet stays below 27 C"),
                       ("Keep the tank and its controls in the monthly test plan", "Mechanical technician", "Monthly discharge test recorded")],
    },
    "common_mode": {
        "title": "All chillers tripped together: a shared fault defeated the redundancy",
        "whys": ["Why did the servers shut down? Because the hall had no cooling for longer than its thermal reserve.",
                 "Why no cooling? Because every chiller stopped at the same moment.",
                 "Why all at once, when they are redundant? Because they share something: here, one control system.",
                 "Why does a shared system exist? Because redundancy was counted in units, not in independent paths.",
                 "Why was that not caught? Because the design review checked capacity (N+1 or 2N) but not what the units have in common."],
        "root": "A single shared dependency across all redundant units.",
        "factors": ["One control system for the whole plant", "No manual or local fallback mode practised", "Chiller restart time", "No chilled-water storage"],
        "corrective": [("Clear the control fault and restart the plant; keep it in local control until the cause is known", "Controls engineer", "Plant stable for 24 hours")],
        "preventive": [("List every dependency shared by redundant units (controls, power feed, header, sensors) and split or back up each", "Infrastructure engineer", "Single-fault review signed off"),
                       ("Local control mode on each chiller, with a practised procedure", "Controls engineer", "Drill: plant run in local mode for one hour"),
                       ("Chilled-water storage to cover a full plant restart", "Infrastructure engineer", "Repeat this scenario: peak inlet stays below 32 C")],
    },
}


def needs_report(o, f: Facility = None):
    f = f or Facility()
    return o.minutes_above_27 > 0 or o.it_lost


def timeline(o, f: Facility):
    """Events from the simulation plus the moments the inlet crossed each limit, in time order."""
    rows = list(o.log)
    if o.minutes_to_27 is not None:
        rows.append((o.minutes_to_27, f"Inlet passes {f.limit_recommended_c:.0f} C (recommended limit)"))
    if o.minutes_to_32 is not None:
        rows.append((o.minutes_to_32, f"Inlet passes {f.limit_allowable_c:.0f} C (allowable limit)"))
    peak_minute = o.minutes[o.temps.index(o.peak_c)]
    rows.append((peak_minute, f"Peak inlet temperature {o.peak_c:.1f} C"))
    back = next((m for m, t in zip(o.minutes, o.temps) if m > peak_minute and t < f.limit_recommended_c), None)
    if back is not None and o.minutes_to_27 is not None:
        rows.append((back, f"Inlet back below {f.limit_recommended_c:.0f} C"))
    return sorted(set(rows))


def report(o, f: Facility = None):
    """Markdown incident report for one outcome, or None if no limit was breached."""
    f = f or Facility()
    if not needs_report(o, f):
        return None
    k = LIBRARY[o.kind]
    t0 = o.log[0][0] if o.log else 0.0
    lines = [f"# Incident report: {k['title']}", "",
             "> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; "
             "the causes and actions come from a rule library for this kind of event. Not a real incident.", "",
             "## Summary", "",
             f"Scenario: {o.name}. Outdoor temperature {o.outdoor_c:.0f} C. Peak server inlet {o.peak_c:.1f} C. "
             f"**Root cause:** {k['root']}", "",
             "## Impact", "", "| | |", "|---|---|",
             f"| Peak inlet temperature | {o.peak_c:.1f} C |",
             f"| Time above {f.limit_recommended_c:.0f} C (recommended) | {o.minutes_above_27:.1f} min |",
             f"| Time above {f.limit_allowable_c:.0f} C (allowable) | {o.minutes_above_32:.1f} min |",
             f"| IT load lost power | {'Yes' if o.it_lost else 'No'} |",
             f"| Servers shut down on temperature | {'Yes, ' + format(o.it_shutdown_minute - t0, '.1f') + ' min after the failure' if o.it_shutdown_minute is not None else 'No'} |", "",
             "## Timeline", "", "| Minutes after the failure | Event |", "|---|---|"]
    lines += [f"| {m - t0:+.1f} | {text} |" for m, text in timeline(o, f)]
    lines += ["", "## Five whys", ""] + [f"{i}. {w}" for i, w in enumerate(k["whys"], 1)]
    lines += ["", "## Contributing factors", ""] + [f"- {x}" for x in k["factors"]]
    lines += ["", "## Corrective actions (fix what broke)", "", "| Action | Owner (role) | Verified by |", "|---|---|---|"]
    lines += [f"| {a} | {who} | {v} |" for a, who, v in k["corrective"]]
    lines += ["", "## Preventive actions (stop it happening again)", "", "| Action | Owner (role) | Verified by |", "|---|---|---|"]
    lines += [f"| {a} | {who} | {v} |" for a, who, v in k["preventive"]]
    lines += ["", "## Closing the report", "",
              "The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits."]
    return "\n".join(lines) + "\n"


def write_all(outcomes, folder="reports"):
    import os
    import re
    os.makedirs(folder, exist_ok=True)
    written = []
    for o in outcomes:
        text = report(o)
        if text:
            path = f"{folder}/{re.sub(r'[^a-z0-9]+', '_', o.name.lower()).strip('_')}.md"
            open(path, "w").write(text)
            written.append(path)
    return written


if __name__ == "__main__":
    from . import scenarios
    for p in write_all(scenarios.run_all()):
        print("wrote", p)
