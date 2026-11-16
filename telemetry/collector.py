#!/usr/bin/env python3
"""Module 5 collector: one reading of whatever sensors this Linux machine exposes, appended to a CSV.

Standard library only. It discovers sensors instead of assuming them:
  - CPU load from /proc/stat (measured over one second) and the 1-minute load average
  - every temperature and fan the kernel exposes under /sys/class/hwmon (CPU, motherboard, NVMe,
    and SATA disks if the 'drivetemp' kernel module is loaded)
  - GPU temperature, load and fan from nvidia-smi, if that command exists
It records no hostname, IP address, user name, serial number or file path. Disk and chip names are
generic kernel labels (for example 'coretemp/Package id 0').

Run once a minute (cron, unRAID User Scripts, or a loop):   python3 collector.py /path/to/readings.csv
"""
import csv
import glob
import os
import shutil
import subprocess
import sys
import time

HWMON = os.environ.get("TWIN_HWMON", "/sys/class/hwmon")      # overridable for tests
PROC = os.environ.get("TWIN_PROC", "/proc")


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def cpu_times():
    line = (read(f"{PROC}/stat") or "").splitlines()[0].split()
    nums = [int(x) for x in line[1:]]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    return sum(nums), idle


def cpu_load_percent(interval=1.0):
    t0, i0 = cpu_times()
    time.sleep(interval)
    t1, i1 = cpu_times()
    return 100.0 * (1 - (i1 - i0) / max(1, t1 - t0))


def hwmon_readings():
    """(kind, name, value) for every temperature (deg C) and fan (rpm) under /sys/class/hwmon."""
    out = []
    for chip_dir in sorted(glob.glob(f"{HWMON}/hwmon*")):
        chip = read(f"{chip_dir}/name") or os.path.basename(chip_dir)
        for path in sorted(glob.glob(f"{chip_dir}/temp*_input")):
            raw = read(path)
            if raw is None or not raw.lstrip("-").isdigit():
                continue
            label = read(path.replace("_input", "_label")) or os.path.basename(path).replace("_input", "")
            value = int(raw) / 1000.0
            if -40 < value < 150:                                  # drop sensors that report nonsense
                out.append(("temp_c", f"{chip}/{label}", value))
        for path in sorted(glob.glob(f"{chip_dir}/fan*_input")):
            raw = read(path)
            if raw is not None and raw.isdigit():
                label = read(path.replace("_input", "_label")) or os.path.basename(path).replace("_input", "")
                out.append(("fan_rpm", f"{chip}/{label}", float(raw)))
    return out


def gpu_readings():
    if not shutil.which("nvidia-smi"):
        return []
    try:
        text = subprocess.run(["nvidia-smi", "--query-gpu=index,temperature.gpu,utilization.gpu,fan.speed",
                               "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[1].replace(".", "").isdigit():
            out.append(("temp_c", f"gpu{parts[0]}/temperature", float(parts[1])))
            if parts[2].replace(".", "").isdigit():
                out.append(("load_pct", f"gpu{parts[0]}/utilisation", float(parts[2])))
            if len(parts) > 3 and parts[3].replace(".", "").isdigit():
                out.append(("fan_pct", f"gpu{parts[0]}/fan", float(parts[3])))
    return out


def collect(interval=1.0):
    rows = [("load_pct", "cpu/utilisation", round(cpu_load_percent(interval), 2))]
    la = read(f"{PROC}/loadavg")
    if la:
        rows.append(("load_avg", "cpu/load_1min", float(la.split()[0])))
    return rows + hwmon_readings() + gpu_readings()


def append(path, rows, now=None):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "kind", "sensor", "value"])
        for kind, name, value in rows:
            w.writerow([stamp, kind, name, value])
    return len(rows)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "readings.csv"
    if "--list" in sys.argv:
        for kind, name, value in collect():
            print(f"{kind:9} {name:40} {value}")
    else:
        print(f"wrote {append(target, collect())} readings to {target}")
