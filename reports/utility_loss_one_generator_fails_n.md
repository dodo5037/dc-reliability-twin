# Incident report: IT load lost power: utility failure with too few generators running

> **HYPOTHETICAL.** Generated from a simulated scenario in the reliability twin. The timeline and numbers come from the simulation; the causes and actions come from a rule library for this kind of event. Not a real incident.

## Summary

Scenario: Utility loss + one generator fails, N. Outdoor temperature 46 C. Peak server inlet 40.4 C. **Root cause:** No spare generating capacity: one failure to start left the site short of power.

## Impact

| | |
|---|---|
| Peak inlet temperature | 40.4 C |
| Time above 27 C (recommended) | 42.7 min |
| Time above 32 C (allowable) | 41.8 min |
| IT load lost power | Yes |
| Servers shut down on temperature | Yes, 2.8 min after the failure |

## Timeline

| Minutes after the failure | Event |
|---|---|
| +0.0 | Utility power lost. IT rides on UPS battery; fans, pumps and chillers stop |
| +0.5 | Inlet passes 27 C (recommended limit) |
| +0.5 | Only 1 generator starts: 800 kW cannot carry 1508 kW |
| +1.3 | Inlet passes 32 C (allowable limit) |
| +2.8 | Inlet reaches 40 C: servers shut down to protect hardware |
| +2.8 | Peak inlet temperature 40.4 C |
| +5.0 | UPS battery exhausted. IT load loses power |

## Five whys

1. Why did the IT load lose power? Because the UPS battery ran out before another source carried the load.
2. Why did no source carry the load? Because the generators that started could not supply the whole site.
3. Why not? Because one generator failed to start and there was no spare (N).
4. Why did it fail to start? Unknown from this model: start failures usually trace to batteries, fuel or controls.
5. Why was that not found earlier? Because start reliability is only proven by regular tests under load.

## Contributing factors

- Generators at N
- UPS battery sized for minutes, not for a failed start
- Cooling stopped with the power, so the hall also overheated

## Corrective actions (fix what broke)

| Action | Owner (role) | Verified by |
|---|---|---|
| Find why the generator did not start; repair and test under load | Electrical technician | Successful load-bank test recorded |

## Preventive actions (stop it happening again)

| Action | Owner (role) | Verified by |
|---|---|---|
| Add one generator to reach N+1 | Infrastructure engineer | Repeat this scenario: IT keeps power |
| Monthly start test and quarterly load-bank test on every generator | Electrical technician | Test records with start time and load carried |
| Load-shedding plan for a single-generator condition | Operations lead | Plan reviewed and walked through once |

## Closing the report

The report closes when every verification above has passed and the scenario, run again with the changes, stays inside the limits.
