# Incident report: All chillers tripped together: a shared fault defeated the redundancy

> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; the causes and actions come from a rule library for this kind of event. Not a real incident.

## Summary

Scenario: Common-mode chiller trip, 2N. Outdoor temperature 46 C. Peak server inlet 40.4 C. **Root cause:** A single shared dependency across all redundant units.

## Impact

| | |
|---|---|
| Peak inlet temperature | 40.4 C |
| Time above 27 C (recommended) | 15.8 min |
| Time above 32 C (allowable) | 14.5 min |
| IT load lost power | No |
| Servers shut down on temperature | Yes, 2.8 min after the failure |

## Timeline

| Minutes after the failure | Event |
|---|---|
| +0.0 | Shared control fault trips ALL chillers together |
| +0.5 | Inlet passes 27 C (recommended limit) |
| +1.3 | Inlet passes 32 C (allowable limit) |
| +2.8 | Inlet reaches 40 C: servers shut down to protect hardware |
| +2.8 | Peak inlet temperature 40.4 C |
| +10.0 | Fault cleared by the operator; chillers restarting |
| +15.0 | Chillers back and cooling |
| +16.3 | Inlet back below 27 C |

## Five whys

1. Why did the servers shut down? Because the hall had no cooling for longer than its thermal reserve.
2. Why no cooling? Because every chiller stopped at the same moment.
3. Why all at once, when they are redundant? Because they share something: here, one control system.
4. Why does a shared system exist? Because redundancy was counted in units, not in independent paths.
5. Why was that not caught? Because the design review checked capacity (N+1 or 2N) but not what the units have in common.

## Contributing factors

- One control system for the whole plant
- No manual or local fallback mode practised
- Chiller restart time
- No chilled-water storage

## Corrective actions (fix what broke)

| Action | Owner (role) | Verified by |
|---|---|---|
| Clear the control fault and restart the plant; keep it in local control until the cause is known | Controls engineer | Plant stable for 24 hours |

## Preventive actions (stop it happening again)

| Action | Owner (role) | Verified by |
|---|---|---|
| List every dependency shared by redundant units (controls, power feed, header, sensors) and split or back up each | Infrastructure engineer | Single-fault review signed off |
| Local control mode on each chiller, with a practised procedure | Controls engineer | Drill: plant run in local mode for one hour |
| Chilled-water storage to cover a full plant restart | Infrastructure engineer | Repeat this scenario: peak inlet stays below 32 C |

## Closing the report

The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits.
