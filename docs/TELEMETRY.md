# Module 5: collecting real readings from a home server

**Status:** the collector and the analysis are written and tested on a fake sensor tree. They have **not been run on a real server yet**, so the steps below are untested on real hardware. Expect to adjust them.

## What the collector records

One row per sensor per run: time, kind, sensor name, value. It discovers what the machine has:
- CPU load (from `/proc/stat`) and the 1-minute load average
- every temperature and fan under `/sys/class/hwmon` (CPU, motherboard, NVMe; SATA disks only if the kernel's `drivetemp` module is loaded)
- GPU temperature, load and fan if `nvidia-smi` exists

It records **no hostname, IP address, user name, serial number or path**. Check the CSV yourself before committing it.

## 1. See what your server exposes

Copy `telemetry/collector.py` to the server, then:

```bash
python3 collector.py --list
```

If the server has no Python (stock unRAID does not), run it in a container instead. The container needs to see the host's `/sys` sensors; whether it does depends on your Docker settings:

```bash
docker run --rm -v /path/to/collector.py:/collector.py:ro python:3.12-alpine python /collector.py --list
```

No disk temperatures? Try `modprobe drivetemp` on the server, then list again.

## 2. Collect once a minute for a few days

With cron, or the unRAID "User Scripts" plugin on a custom schedule of `* * * * *`:

```bash
python3 /path/to/collector.py /path/to/readings.csv
```

Vary the load while it runs (a transcode, a parity check, an idle night), or the model has nothing to learn from.

## 3. Analyse

Copy the CSV to `telemetry/data/readings.csv` in this repository and open the dashboard's Telemetry tab, or:

```bash
python -c "from twin import telemetry as T; [print(k, round(v['r2'],2), len(v['anomalies'])) for k, v in T.summary().items()]"
```

## What the analysis does

For each temperature sensor: temperature = a + b x CPU load, fitted by least squares. A reading more than 4 robust standard deviations from the model is an anomaly. If the server has a sensor that follows room temperature, `telemetry.fit(..., ambient="that sensor")` adds it to the model.

## Limits

- A CPU's temperature lags its load by seconds to minutes; this model ignores the lag.
- Fan speed changes with temperature, which bends the straight line.
- Without a room-temperature sensor, a hot day looks like an anomaly.
- A home server is not a data hall. This shows the method (model from first principles, fit, residuals, anomalies) on real hardware, nothing more.
