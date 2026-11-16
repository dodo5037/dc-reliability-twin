# Incident report: Brief temperature excursion during a utility failure that the site rode through

> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; the causes and actions come from a rule library for this kind of event. Not a real incident.

## Summary

Scenario: Utility loss + one generator fails, N+1, 6 min chilled-water tank. Outdoor temperature 46 C. Peak server inlet 27.7 C. **Root cause:** Fans and pumps are not on UPS, so cooling stops for the generator start time.

## Impact

| | |
|---|---|
| Peak inlet temperature | 27.7 C |
| Time above 27 C (recommended) | 0.3 min |
| Time above 32 C (allowable) | 0.0 min |
| IT load lost power | No |
| Servers shut down on temperature | No |

## Timeline

| Minutes after the failure | Event |
|---|---|
| +0.0 | Utility power lost. IT rides on UPS battery; fans, pumps and chillers stop |
| +0.5 | 2 of 3 generators start (one fails) and take the load; fans and pumps restart; storage tank supplies chilled water for 6 minutes |
| +0.5 | Inlet passes 27 C (recommended limit) |
| +0.5 | Peak inlet temperature 27.7 C |
| +0.8 | Inlet back below 27 C |
| +5.5 | Chillers restarted and cooling |

## Five whys

1. Why did the inlet pass 27 C at all? Because the hall had no air movement or water flow for about half a minute.
2. Why not? Because fans and pumps stopped with the utility and only restarted when the generators took the load.
3. Why did they stop? Because they are fed from the generator-backed supply, not from the UPS.
4. Why does half a minute matter? Because a full hall with no cooling warms by several degrees a minute.
5. Why was it only brief? Because stored chilled water covered the chiller restart once the pumps were back.

## Contributing factors

- Generator start time of about 30 seconds
- Fans and pumps not on UPS
- Peak outdoor temperature

## Corrective actions (fix what broke)

| Action | Owner (role) | Verified by |
|---|---|---|
| Confirm the storage tank is recharged and all units are back in normal mode | Operations lead | Tank temperature and unit status logged |

## Preventive actions (stop it happening again)

| Action | Owner (role) | Verified by |
|---|---|---|
| Put CRAH fans and chilled-water pumps on UPS | Infrastructure engineer | Repeat this scenario: peak inlet stays below 27 C |
| Keep the tank and its controls in the monthly test plan | Mechanical technician | Monthly discharge test recorded |

## Closing the report

The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits.
