# Incident report: Standby CRAH ran without cooling after a running unit failed

> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; the causes and actions come from a rule library for this kind of event. Not a real incident.

## Summary

Scenario: CRAH failure, N+1, standby hidden fault. Outdoor temperature 46 C. Peak server inlet 30.1 C. **Root cause:** No return-to-service verification after maintenance, with monitoring that could not see the fault.

## Impact

| | |
|---|---|
| Peak inlet temperature | 30.1 C |
| Time above 27 C (recommended) | 12.5 min |
| Time above 32 C (allowable) | 0.0 min |
| IT load lost power | No |
| Servers shut down on temperature | No |

## Timeline

| Minutes after the failure | Event |
|---|---|
| +0.0 | CRAH unit trips (fan motor failure) |
| +1.0 | Standby CRAH starts but does not cool (hidden fault: valve closed) |
| +2.2 | Inlet passes 27 C (recommended limit) |
| +12.0 | Peak inlet temperature 30.1 C |
| +12.0 | Technician opens the valve; standby CRAH cooling |
| +14.7 | Inlet back below 27 C |

## Five whys

1. Why did the inlet pass 27 C? Because the hall was one CRAH unit short for several minutes.
2. Why was it short when there is a standby? Because the standby started but delivered no cooling.
3. Why did it deliver no cooling? Because its chilled-water valve was closed.
4. Why was the valve closed? Because the last maintenance job ended without a return-to-service check.
5. Why did nobody notice? Because monitoring reported the unit as available from its fan status alone, and standby units are never run on a schedule.

## Contributing factors

- Maintenance procedure ends at 'return to standby' with no functional test
- 'Available' status does not check the valve or the supply-air temperature
- No routine rotation of standby units
- Peak outdoor temperature: no plant margin to compensate

## Corrective actions (fix what broke)

| Action | Owner (role) | Verified by |
|---|---|---|
| Open the valve, run the standby unit and record supply and return air temperature | Shift technician | Supply air at least 8 K below return air on the log |
| Walk down every standby unit on site for valve and breaker position | Operations lead | Signed checklist, one line per unit |

## Preventive actions (stop it happening again)

| Action | Owner (role) | Verified by |
|---|---|---|
| Add a return-to-service section to every maintenance procedure: positions, a 15-minute functional run, second-person sign-off | Infrastructure engineer | First three uses audited |
| Monitoring: a standby unit is 'available' only if its valve reports open and its last functional run passed | Controls engineer | Close a valve on a standby unit: status must change and an alarm must fire |
| Rotate standby units weekly so every unit runs under load | Controls engineer | Log shows every unit as lead within five weeks |

## Closing the report

The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits.
