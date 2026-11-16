"""Module 5 tests. The readings here are MADE UP for testing only: they are not measurements from any machine."""
import importlib.util
import os

import numpy as np
import pytest

from twin import telemetry as T

spec = importlib.util.spec_from_file_location("collector", "telemetry/collector.py")
collector = importlib.util.module_from_spec(spec)


@pytest.fixture
def fake_machine(tmp_path, monkeypatch):
    hw, proc = tmp_path / "hwmon", tmp_path / "proc"
    (hw / "hwmon0").mkdir(parents=True)
    (hw / "hwmon0" / "name").write_text("coretemp\n")
    (hw / "hwmon0" / "temp1_input").write_text("54000\n")
    (hw / "hwmon0" / "temp1_label").write_text("Package id 0\n")
    (hw / "hwmon0" / "temp2_input").write_text("999999000\n")          # nonsense reading, must be dropped
    (hw / "hwmon0" / "fan1_input").write_text("1180\n")
    proc.mkdir()
    (proc / "stat").write_text("cpu  100 0 100 800 0 0 0 0 0 0\n")
    (proc / "loadavg").write_text("0.42 0.40 0.39 1/200 1234\n")
    monkeypatch.setenv("TWIN_HWMON", str(hw))
    monkeypatch.setenv("TWIN_PROC", str(proc))
    spec.loader.exec_module(collector)
    return collector


def test_collector_reads_sysfs_and_drops_nonsense(fake_machine):
    rows = dict(((k, n), v) for k, n, v in fake_machine.hwmon_readings())
    assert rows[("temp_c", "coretemp/Package id 0")] == 54.0
    assert rows[("fan_rpm", "coretemp/fan1")] == 1180.0
    assert len(rows) == 2


def test_collector_appends_rows_with_a_header_once(fake_machine, tmp_path):
    path = str(tmp_path / "out" / "readings.csv")
    rows = fake_machine.collect(interval=0)
    fake_machine.append(path, rows, now=0)
    fake_machine.append(path, rows, now=60)
    lines = open(path).read().strip().splitlines()
    assert lines[0] == "time,kind,sensor,value" and len(lines) == 1 + 2 * len(rows)
    assert any("cpu/load_1min" in line for line in lines)


def test_collector_records_nothing_that_identifies_the_machine(fake_machine, tmp_path):
    path = str(tmp_path / "readings.csv")
    fake_machine.append(path, fake_machine.collect(interval=0))
    text = open(path).read()
    assert os.uname().nodename not in text and str(tmp_path) not in text


def made_up_series(n=400, spike_at=None):
    rng = np.random.default_rng(0)
    load = rng.uniform(5, 95, n)
    temp = 35 + 0.30 * load + rng.normal(0, 0.8, n)
    if spike_at is not None:
        temp[spike_at] += 15
    times = [f"2026-01-01 {i // 60:02d}:{i % 60:02d}:00" for i in range(n)]
    return {"cpu/utilisation": dict(zip(times, load)), "coretemp/Package id 0": dict(zip(times, temp))}, times


def test_fit_recovers_a_known_relationship():
    series, times = made_up_series()
    r = T.fit(series, times, "coretemp/Package id 0")
    assert r["intercept"] == pytest.approx(35, abs=0.5) and r["per_load_pct"] == pytest.approx(0.30, abs=0.01)
    assert r["r2"] > 0.95 and not r["anomalies"]


def test_a_spike_is_flagged_and_normal_readings_are_not():
    series, times = made_up_series(spike_at=123)
    r = T.fit(series, times, "coretemp/Package id 0")
    assert [a["time"] for a in r["anomalies"]] == [times[123]]
    assert r["anomalies"][0]["gap"] > 10


def test_fit_refuses_too_little_data():
    series, times = made_up_series(n=10)
    with pytest.raises(ValueError):
        T.fit(series, times, "coretemp/Package id 0")


def test_summary_is_empty_without_data(tmp_path):
    assert T.summary(str(tmp_path / "missing.csv")) == {}
