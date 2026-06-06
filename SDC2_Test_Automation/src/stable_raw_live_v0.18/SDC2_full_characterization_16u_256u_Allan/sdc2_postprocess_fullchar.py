#!/usr/bin/env python3
"""
Postprocess SDC2 full characterization CSV.

Creates:
  - cleaned CSV copy
  - per-segment summary CSV
  - event-based encoder figures per test segment
  - combined speed-ratio figures

Method note:
  Raw event-speed analysis uses raw EncoderCount changes only.
  No filtering, smoothing, or grouped averaging is applied to event-speed plots.
"""

import argparse
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CPR = 5000.0
EDGE_MULT = 2.0
GEAR_RATIO = 24.65
DEG_PER_COUNT = 360.0 / (CPR * EDGE_MULT * GEAR_RATIO)


def safe_name(s: str) -> str:
    s = str(s)
    s = s.replace("-", "neg")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).replace(".", "p")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Raw CSV from logger")
    p.add_argument("--out", default="Boss_SDC2_16u_Analysis", help="Output folder")
    p.add_argument("--speed-low", type=float, default=0.80)
    p.add_argument("--speed-high", type=float, default=1.20)
    p.add_argument("--microstep", default="", help="Microstep label for plot titles, e.g. 16 or 256")
    return p.parse_args()


def load_csv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV does not exist: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(
            f"Input CSV is empty: {path}\n"
            "No serial CSV data was captured. Run a test first and select a non-empty raw CSV."
        )
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise RuntimeError(
            f"Input CSV has no columns/data: {path}\n"
            "This usually means the logger opened the file but the Arduino never sent the CSV header."
        ) from exc
    if df.empty:
        raise RuntimeError(f"Input CSV has a header but zero rows: {path}")
    # Coerce key numeric columns
    for col in df.columns:
        if col not in ["TestName", "LoadCase", "Direction", "State", "FaultCode"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    required = ["Time_s", "TestTime_s", "TargetSpeed_deg_s", "EncoderCount"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Input CSV is missing required columns {missing}: {path}")
    df = df.dropna(subset=required)
    if df.empty:
        raise RuntimeError(f"Input CSV contains no valid SDC2 data rows after cleaning: {path}")
    return df


def segment_groups(df):
    keys = ["TestName", "LoadCase", "Direction", "TargetSpeed_deg_s"]
    for k in keys:
        if k not in df.columns:
            raise ValueError(f"Missing required column: {k}")
    return df.groupby(keys, dropna=False, sort=False)


def analyze_segment(g, speed_low=0.8, speed_high=1.2):
    t = g["TestTime_s"].to_numpy(dtype=float)
    c = g["EncoderCount"].to_numpy(dtype=float)
    s = float(g["TargetSpeed_deg_s"].iloc[0])
    direction = g["Direction"].iloc[0] if "Direction" in g else ""

    if len(t) < 2 or t[-1] <= t[0]:
        return None

    duration = t[-1] - t[0]
    count_delta = c[-1] - c[0]
    measured_speed = abs(count_delta) * DEG_PER_COUNT / duration
    expected_cps = abs(s) / DEG_PER_COUNT if abs(s) > 0 else 0.0
    expected_count_delta = expected_cps * duration
    speed_ratio = measured_speed / abs(s) if abs(s) > 0 else np.nan

    dc = np.diff(c)
    event_mask = dc != 0
    event_times = t[1:][event_mask]
    event_counts = c[1:][event_mask]

    if len(event_times) >= 2:
        event_dt = np.diff(event_times)
        event_jump = np.abs(np.diff(event_counts))
        event_speed = event_jump * DEG_PER_COUNT / event_dt
        event_t2 = event_times[1:]
        expected_dt = 1.0 / expected_cps if expected_cps > 0 else np.nan
        long_gaps = np.sum(event_dt > 2.0 * expected_dt) if expected_cps > 0 else 0
        short_gaps = np.sum(event_dt < 0.5 * expected_dt) if expected_cps > 0 else 0
        bad_speed = np.sum((event_speed < speed_low * abs(s)) | (event_speed > speed_high * abs(s))) if abs(s) > 0 else 0
        rms_event_speed = np.sqrt(np.mean(event_speed ** 2))
        rms_speed_error = np.sqrt(np.mean((event_speed - abs(s)) ** 2)) if abs(s) > 0 else np.nan
    else:
        event_dt = np.array([])
        event_speed = np.array([])
        event_t2 = np.array([])
        expected_dt = np.nan
        long_gaps = short_gaps = bad_speed = 0
        rms_event_speed = np.nan
        rms_speed_error = np.nan

    fault = "NONE"
    if "FaultCode" in g.columns:
        faults = sorted(set(str(x) for x in g["FaultCode"].dropna().unique() if str(x) not in ["", "NONE", "nan"]))
        if faults:
            fault = ";".join(faults)

    if abs(s) == 0:
        result = "STATIC"
    elif speed_low <= speed_ratio <= speed_high:
        result = "GOOD"
    elif speed_ratio < 0.4:
        result = "FAIL_LOW_SPEED"
    elif speed_ratio < speed_low:
        result = "LOW_SPEED"
    else:
        result = "HIGH_SPEED"

    return {
        "duration_s": duration,
        "count_delta": count_delta,
        "expected_count_delta": expected_count_delta,
        "measured_avg_speed_deg_s": measured_speed,
        "target_abs_speed_deg_s": abs(s),
        "speed_ratio": speed_ratio,
        "expected_dt_s": expected_dt,
        "mean_event_dt_s": np.nanmean(event_dt) if len(event_dt) else np.nan,
        "median_event_dt_s": np.nanmedian(event_dt) if len(event_dt) else np.nan,
        "std_event_dt_s": np.nanstd(event_dt) if len(event_dt) else np.nan,
        "mean_event_speed_deg_s": np.nanmean(event_speed) if len(event_speed) else np.nan,
        "median_event_speed_deg_s": np.nanmedian(event_speed) if len(event_speed) else np.nan,
        "rms_event_speed_deg_s": rms_event_speed,
        "rms_speed_error_deg_s": rms_speed_error,
        "num_long_gaps": int(long_gaps),
        "num_short_gaps": int(short_gaps),
        "num_bad_speed_events": int(bad_speed),
        "faults_observed": fault,
        "result": result,
        "event_times2": event_t2,
        "event_dt": event_dt,
        "event_speed": event_speed,
    }


def plot_segment(g, info, outpath, speed_low=0.8, speed_high=1.2, args_microstep=""):
    t = g["TestTime_s"].to_numpy(dtype=float)
    c = g["EncoderCount"].to_numpy(dtype=float)
    s = float(g["TargetSpeed_deg_s"].iloc[0])
    test = str(g["TestName"].iloc[0])
    direction = str(g["Direction"].iloc[0])
    cdelta = c - c[0]
    ideal = np.sign(info["count_delta"] if info["count_delta"] != 0 else 1) * (abs(s) / DEG_PER_COUNT) * t

    fig, axs = plt.subplots(3, 1, figsize=(13.5, 9.5), constrained_layout=True)
    ustep_note = f"{args_microstep} ustep " if args_microstep else ""
    fig.suptitle(f"SDC2 {ustep_note}raw event analysis - {test}, {direction}, target {s:g} deg/s", fontsize=14, fontweight="bold")

    axs[0].plot(t, cdelta, "-o", markersize=3, linewidth=1.2, label="Measured encoder count delta")
    axs[0].plot(t, ideal, "--", linewidth=2, label="Ideal count delta")
    axs[0].set_xlabel("Segment time (s)")
    axs[0].set_ylabel("Encoder count delta (counts)")
    axs[0].set_title("Raw encoder count delta")
    axs[0].grid(True, which="major", alpha=0.35)
    axs[0].minorticks_on(); axs[0].grid(True, which="minor", alpha=0.15)
    axs[0].legend(loc="upper left")
    txt = (
        f"Measured avg speed: {info['measured_avg_speed_deg_s']:.6g} deg/s\n"
        f"Speed ratio: {info['speed_ratio']:.3f}\n"
        f"Measured count delta: {info['count_delta']:.0f}\n"
        f"Expected count delta: {info['expected_count_delta']:.1f}\n"
        f"Result: {info['result']}\n"
        "Method: raw encoder counts; no filtering/smoothing/group averaging"
    )
    axs[0].text(0.012, 0.95, txt, transform=axs[0].transAxes, va="top", bbox=dict(facecolor="white", edgecolor="0.3"), fontsize=9)

    ev_t = info["event_times2"]
    ev_dt = info["event_dt"]
    ev_speed = info["event_speed"]
    if len(ev_t):
        axs[1].plot(ev_t, ev_dt, "-o", markersize=4, linewidth=1.2, label="Measured event interval")
        if np.isfinite(info["expected_dt_s"]):
            axs[1].axhline(info["expected_dt_s"], linestyle="--", linewidth=2, label="Expected interval")
            axs[1].axhline(2.0 * info["expected_dt_s"], linestyle=":", linewidth=1.4, label="Long-gap threshold")
            axs[1].axhline(0.5 * info["expected_dt_s"], linestyle=":", linewidth=1.4, label="Short-gap threshold")
    axs[1].set_xlabel("Segment time (s)")
    axs[1].set_ylabel("Time between count events (s/event)")
    axs[1].set_title("Encoder event timing")
    axs[1].grid(True, which="major", alpha=0.35)
    axs[1].minorticks_on(); axs[1].grid(True, which="minor", alpha=0.15)
    axs[1].legend(loc="upper left")
    txt = (
        f"Expected interval: {info['expected_dt_s']:.5g} s/event\n"
        f"Median interval: {info['median_event_dt_s']:.5g} s/event\n"
        f"Long gaps: {info['num_long_gaps']}\n"
        f"Short gaps: {info['num_short_gaps']}\n"
        f"Faults: {info['faults_observed']}"
    )
    axs[1].text(0.012, 0.95, txt, transform=axs[1].transAxes, va="top", bbox=dict(facecolor="white", edgecolor="0.3"), fontsize=9)

    if len(ev_t):
        axs[2].plot(ev_t, ev_speed, "-o", markersize=4, linewidth=1.2, label="Raw event-based speed")
        axs[2].axhline(abs(s), linestyle="--", linewidth=2, label="Target speed")
        axs[2].axhline(speed_low * abs(s), linestyle=":", linewidth=1.3, label="80% target")
        axs[2].axhline(speed_high * abs(s), linestyle=":", linewidth=1.3, label="120% target")
    axs[2].set_xlabel("Segment time (s)")
    axs[2].set_ylabel("Event-based table speed (deg/s)")
    axs[2].set_title("Connected raw event-to-event encoder speed")
    axs[2].grid(True, which="major", alpha=0.35)
    axs[2].minorticks_on(); axs[2].grid(True, which="minor", alpha=0.15)
    axs[2].legend(loc="upper left")
    txt = (
        f"Mean event speed: {info['mean_event_speed_deg_s']:.6g} deg/s\n"
        f"RMS event speed: {info['rms_event_speed_deg_s']:.6g} deg/s\n"
        f"RMS speed error: {info['rms_speed_error_deg_s']:.6g} deg/s\n"
        f"Bad speed events outside 80-120%: {info['num_bad_speed_events']}\n"
        "Event speed = count step / time between count changes"
    )
    axs[2].text(0.012, 0.95, txt, transform=axs[2].transAxes, va="top", bbox=dict(facecolor="white", edgecolor="0.3"), fontsize=9)

    fig.savefig(outpath, dpi=180)
    plt.close(fig)


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = load_csv(args.input)
    df.to_csv(out / "SDC2_clean.csv", index=False)

    rows = []
    for keys, g in segment_groups(df):
        info = analyze_segment(g, args.speed_low, args.speed_high)
        if info is None:
            continue
        test, load, direction, target = keys
        base = f"{safe_name(test)}_{safe_name(load)}_{safe_name(direction)}_{safe_name(target)}_deg_s.png"
        plot_segment(g, info, out / base, args.speed_low, args.speed_high, args.microstep)
        row = {k: v for k, v in info.items() if not isinstance(v, np.ndarray)}
        row.update({"TestName": test, "LoadCase": load, "Direction": direction, "TargetSpeed_deg_s": target})
        rows.append(row)

    summary = pd.DataFrame(rows)
    cols_front = ["TestName", "LoadCase", "Direction", "TargetSpeed_deg_s"]
    summary = summary[cols_front + [c for c in summary.columns if c not in cols_front]]
    summary.to_csv(out / "SDC2_full_characterization_summary.csv", index=False)

    # Combined figures
    motion = summary[summary["target_abs_speed_deg_s"] > 0].copy()
    if not motion.empty:
        fig, axs = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
        for direction, dg in motion.groupby("Direction"):
            axs[0].plot(dg["target_abs_speed_deg_s"], dg["measured_avg_speed_deg_s"], "-o", label=direction)
        x = np.array(sorted(motion["target_abs_speed_deg_s"].unique()))
        axs[0].plot(x, x, "--", label="Ideal 1:1")
        axs[0].set_xlabel("Target table speed magnitude (deg/s)")
        axs[0].set_ylabel("Measured average table speed (deg/s)")
        axs[0].set_title("Measured average speed vs target")
        axs[0].grid(True, which="both", alpha=0.35)
        axs[0].legend()

        labels = [f"{d}\n{v:g}" for d, v in zip(motion["Direction"], motion["target_abs_speed_deg_s"])]
        axs[1].bar(range(len(motion)), motion["speed_ratio"])
        axs[1].axhline(1.0, linestyle="--", label="Target")
        axs[1].axhline(args.speed_low, linestyle=":", label="80%")
        axs[1].axhline(args.speed_high, linestyle=":", label="120%")
        axs[1].set_xticks(range(len(motion)))
        axs[1].set_xticklabels(labels, rotation=45, ha="right")
        axs[1].set_ylabel("Measured / target speed ratio")
        axs[1].set_title("Speed tracking ratio by section")
        axs[1].grid(True, axis="y", alpha=0.35)
        axs[1].legend()
        fig.savefig(out / "SDC2_combined_summary.png", dpi=180)
        plt.close(fig)

    print(f"Saved outputs in: {out.resolve()}")
    print(f"Summary: {out / 'SDC2_full_characterization_summary.csv'}")


if __name__ == "__main__":
    main()
