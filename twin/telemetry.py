"""Module 5 analysis: a simple thermal model fitted to real readings, and anomaly detection.

Model for one temperature sensor:   temperature = a + b x load (+ c x ambient, if an ambient sensor is chosen)
fitted by least squares. It is the same idea as the hall model: temperature follows the heat produced
(load) and the temperature of the surroundings.

Anomaly = a reading whose gap from the model is more than 4 robust standard deviations
(median absolute deviation x 1.4826), so a few bad readings do not hide themselves by inflating the spread.

Nothing here runs until real readings exist in telemetry/data/readings.csv.
"""
import csv
from collections import defaultdict

import numpy as np

THRESHOLD = 4.0


def load(path="telemetry/data/readings.csv"):
    """{sensor: {time: value}} plus the sorted list of times."""
    series = defaultdict(dict)
    with open(path) as f:
        for r in csv.DictReader(f):
            series[r["sensor"]][r["time"]] = float(r["value"])
    times = sorted({t for s in series.values() for t in s})
    return dict(series), times


def sensors(series, kind_hint):
    return sorted(k for k in series if kind_hint in k)


def fit(series, times, target, load_sensor="cpu/utilisation", ambient=None):
    """Least-squares fit of one temperature sensor against load (and ambient). Returns a dict of results."""
    cols = [load_sensor] + ([ambient] if ambient else [])
    keep = [t for t in times if t in series[target] and all(t in series[c] for c in cols)]
    if len(keep) < 30:
        raise ValueError(f"only {len(keep)} complete readings for {target}; collect at least 30")
    y = np.array([series[target][t] for t in keep])
    X = np.column_stack([np.ones(len(keep))] + [np.array([series[c][t] for t in keep]) for c in cols])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    resid = y - pred
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else 0.0
    mad = float(np.median(np.abs(resid - np.median(resid))))
    sigma = 1.4826 * mad if mad > 0 else float(resid.std()) or 1e-9
    z = (resid - np.median(resid)) / sigma
    anomalies = [{"time": t, "measured": float(a), "expected": float(p), "gap": float(a - p), "sigmas": float(s)}
                 for t, a, p, s in zip(keep, y, pred, z) if abs(s) > THRESHOLD]
    return {"target": target, "n": len(keep), "intercept": float(coef[0]), "per_load_pct": float(coef[1]),
            "per_ambient_k": float(coef[2]) if ambient else None, "r2": r2, "sigma": sigma,
            "times": keep, "measured": y.tolist(), "expected": pred.tolist(), "anomalies": anomalies}


def summary(path="telemetry/data/readings.csv"):
    """Fit every temperature sensor against CPU load. Returns {} if there is no data yet."""
    try:
        series, times = load(path)
    except FileNotFoundError:
        return {}
    out = {}
    for s in series:
        if s.startswith("cpu/") or "fan" in s.lower() or "utilisation" in s:
            continue
        try:
            out[s] = fit(series, times, s)
        except (ValueError, KeyError):
            continue
    return out
