# Incident report: Cooling shortfall after a single CRAH failure with no standby unit

> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; the causes and actions come from a rule library for this kind of event. Not a real incident.

## Summary

Scenario: CRAH failure, N, no standby. Outdoor temperature 46 C. Peak server inlet 30.5 C. **Root cause:** The design has no redundancy on air handling, so a single component failure reaches the servers.

## Impact

| | |
|---|---|
| Peak inlet temperature | 30.5 C |
| Time above 27 C (recommended) | 41.0 min |
| Time above 32 C (allowable) | 0.0 min |
| IT load lost power | No |
| Servers shut down on temperature | No |

## Timeline

| Minutes after the failure | Event |
|---|---|
| +0.0 | CRAH unit trips (fan motor failure) |
| +2.2 | Inlet passes 27 C (recommended limit) |
| +30.0 | Peak inlet temperature 30.5 C |
| +30.0 | Unit repaired and returned to service |

## Five whys

1. Why did the inlet pass 27 C? Because the hall lost one CRAH unit's worth of cooling.
2. Why was that not covered? Because the hall has exactly the number of CRAH units it needs (N) and no spare.
3. Why does it have no spare? Because the design accepted that any single CRAH failure degrades the hall.
4. Why did the unit fail without warning? Because fan motors are run to failure with no condition monitoring.
5. Why is that the practice? Because there is no vibration or bearing-temperature trend to act on.

## Contributing factors

- Single point of failure by design (N)
- No condition monitoring on fan motors
- High outdoor temperature left no chiller margin to lower the water temperature

## Corrective actions (fix what broke)

| Action | Owner (role) | Verified by |
|---|---|---|
| Repair or replace the failed fan motor and test the unit under load | Mechanical technician | Supply air back to setpoint with all units running |

## Preventive actions (stop it happening again)

| Action | Owner (role) | Verified by |
|---|---|---|
| Add one CRAH unit to reach N+1 | Infrastructure engineer | Repeat this scenario: peak inlet stays below 27 C |
| Quarterly vibration readings on every fan motor, trended | Mechanical technician | First readings on file and an alert threshold defined |

## Closing the report

The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits.
