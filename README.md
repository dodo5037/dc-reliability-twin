# Dubai Data Center Reliability Twin

**Question:** in a Dubai data hall, when can we safely take a cooling or power unit offline for maintenance, and what is the real risk of each redundancy design?

An educational model of a fictional 1 MW IT hall. **Not an engineering design.** Work in progress: modules are added one at a time.

| # | Module | Status |
|---|---|---|
| 1 | Facility model: power chain, cooling, N / N+1 / 2N, thermal response (`twin/facility.py`, `twin/cooling.py`) | Done |
| 2 | Reliability engine: Monte Carlo of failures and repairs, checked against the analytical answer (`twin/reliability.py`) | Done |
| 3 | Maintenance-window optimizer | Next |
| 4 | Scenario lab | Planned |
| 5 | Real telemetry from a home server | Planned |
| 6 | Automatic incident report | Planned |
| 7 | Dashboard | Planned |

## Results so far (module 2)

One million simulated years per design. Failures are independent; common-cause failures are not modelled yet, so the N+1 and 2N figures are a best case.

| Design | Cooling shortfall | Cooling shortfall event | Loss of IT power |
|---|---|---|---|
| N | 3.1 hours a year | about once every 3.6 years | about once every 14 years |
| N+1 | 0.0007 hours a year | about once every 8,400 years | about once every 48,000 years |
| 2N | none in a million years | (analytical: 2 x 10^-11 of the time) | about once every 370,000 years |

- In the N design, 72% of power-loss events come from the single transfer switch and 26% from the UPS, not from the utility.
- The simulation agrees with the exact formula: cooling unavailability for N is 3.511 x 10^-4 simulated against 3.523 x 10^-4 analytical.
- For N+1 and 2N the events are so rare that simulation alone is unreliable; the analytical figure is the better number there.

**Failure data:** US Army TM 5-698-5 (22 July 2006), Appendix B: chiller H10-000 (0.1182 failures a year, 12.62 h repair, p. B-4), air handling unit H5-000 (0.0110, 2.36 h, p. B-2), standby diesel generator E18-122 (0.1235, 18.28 h, p. B-6), UPS E39-200 (0.00938, 2.00 h, p. B-12), automatic transfer switch E34-100 (0.05117, 4.10 h, p. B-9). **Utility:** DEWA reports 0.94 customer minutes lost per customer in 2024 (DEWA Integrated Report 2024).

**Assumptions:** 0.1 utility interruptions a year (DEWA does not publish frequency; the mean duration is set so the total is 0.94 minutes); each generator has a 1% chance of not starting; a failed transfer switch means no power path; 5 minutes of UPS battery.

Weather: NOAA Integrated Surface Database, Dubai International Airport, 2024, hourly. The cooling physics is reused from [dubai-datacenter-cooling](https://github.com/dodo5037/dubai-datacenter-cooling).

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -m pytest -q
```

Author: Abderrahmane Messaoudi, Industrial Engineering & Engineering Management, University of Sharjah
