# Incident report: Servers overheated after a utility failure although generators carried the load

> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; the causes and actions come from a rule library for this kind of event. Not a real incident.

## Summary

Scenario: Utility loss + one generator fails, N+1. Outdoor temperature 46 C. Peak server inlet 40.4 C. **Root cause:** The cooling system has no ride-through for the chiller restart time.

## Impact

| | |
|---|---|
| Peak inlet temperature | 40.4 C |
| Time above 27 C (recommended) | 6.7 min |
| Time above 32 C (allowable) | 5.2 min |
| IT load lost power | No |
| Servers shut down on temperature | Yes, 2.8 min after the failure |

## Timeline

| Minutes after the failure | Event |
|---|---|
| +0.0 | Utility power lost. IT rides on UPS battery; fans, pumps and chillers stop |
| +0.5 | 2 of 3 generators start (one fails) and take the load; fans and pumps restart |
| +0.5 | Inlet passes 27 C (recommended limit) |
| +1.3 | Inlet passes 32 C (allowable limit) |
| +2.8 | Inlet reaches 40 C: servers shut down to protect hardware |
| +2.8 | Peak inlet temperature 40.4 C |
| +5.5 | Chillers restarted and cooling |
| +7.2 | Inlet back below 27 C |

## Five whys

1. Why did the servers shut down? Because the inlet reached the shutdown temperature.
2. Why did it rise that far with power restored? Because the chillers had not restarted yet.
3. Why not? Because a chiller needs several minutes to restart after any interruption.
4. Why was there no cooling in the meantime? Because the site has no stored chilled water and the fans alone cannot remove heat.
5. Why is there no storage? Because the design sized the power backup for the outage but not the cooling gap.

## Contributing factors

- Chiller restart time longer than the hall's thermal reserve
- No chilled-water storage
- Pumps and fans not on UPS
- Peak outdoor temperature

## Corrective actions (fix what broke)

| Action | Owner (role) | Verified by |
|---|---|---|
| Restart the plant, confirm chilled-water temperature, bring IT back in stages | Operations lead | Inlet stable at setpoint for 30 minutes |

## Preventive actions (stop it happening again)

| Action | Owner (role) | Verified by |
|---|---|---|
| Add chilled-water storage sized for the chiller restart time plus margin | Infrastructure engineer | Repeat this scenario: peak inlet stays below 32 C |
| Put chilled-water pumps and CRAH fans on UPS so stored water can be used | Infrastructure engineer | Pull-the-plug test with the tank |
| Review chiller fast-restart settings with the manufacturer | Mechanical technician | Measured restart time recorded |

## Closing the report

The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits.
