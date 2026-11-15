# Dubai Data Center Reliability Twin

**Question:** in a Dubai data hall, when can we safely take a cooling or power unit offline for maintenance, and what is the real risk of each redundancy design?

An educational model of a fictional 1 MW IT hall. **Not an engineering design.** Work in progress: modules are added one at a time.

| # | Module | Status |
|---|---|---|
| 1 | Facility model: power chain, cooling, N / N+1 / 2N, thermal response (`twin/facility.py`, `twin/cooling.py`) | Done |
| 2 | Reliability engine (Monte Carlo against published failure rates) | Next |
| 3 | Maintenance-window optimizer | Planned |
| 4 | Scenario lab | Planned |
| 5 | Real telemetry from a home server | Planned |
| 6 | Automatic incident report | Planned |
| 7 | Dashboard | Planned |

Weather: NOAA Integrated Surface Database, Dubai International Airport, 2024, hourly. The cooling physics is reused from [dubai-datacenter-cooling](https://github.com/dodo5037/dubai-datacenter-cooling).

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -m pytest -q
```

Author: Abderrahmane Messaoudi, Industrial Engineering & Engineering Management, University of Sharjah
