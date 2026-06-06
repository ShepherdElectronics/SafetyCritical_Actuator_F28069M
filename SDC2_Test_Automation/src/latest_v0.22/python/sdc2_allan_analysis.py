#!/usr/bin/env python3
"""
SDC2 Allan deviation analysis.

Reads a raw or cleaned SDC2 CSV and exports Allan deviation CSVs/figures.
The Allan calculation uses overlapping adjacent block averages at tau = m*dt.
Figures include minor grids, slope guides, and annotations.

Primary uses:
  - static hold: ActualTablePosition_deg relative to start, PositionError_deg, measured speed if available
  - dynamic trials: PositionError_deg, residual position after best-fit line removal, speed error if available

Method note: Allan plots operate on the selected logged signal. No smoothing or grouped
plotting is applied before the Allan calculation, but the Allan deviation itself is an
averaging-time statistic by definition.
"""

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

CPR = 5000.0
EDGE_MULT = 2.0
GEAR_RATIO = 24.65
DEG_PER_COUNT = 360.0 / (CPR * EDGE_MULT * GEAR_RATIO)

TEXT_COLS = {"TestName", "LoadCase", "Direction", "State", "FaultCode", "RunLabel", "Mode"}


def safe_name(x):
    x = str(x).strip().replace("-", "neg")
    x = re.sub(r"[^A-Za-z0-9_.-]+", "_", x)
    return x.replace(".", "p")


def parse_args():
    p = argparse.ArgumentParser(description="SDC2 Allan deviation analysis")
    p.add_argument("--input", required=True, help="SDC2 raw or clean CSV")
    p.add_argument("--out", default="SDC2_Allan_Analysis", help="Output folder")
    p.add_argument("--microstep", default="", help="Microstep setting label, e.g. 16 or 256")
    p.add_argument("--max-points", type=int, default=45, help="Maximum tau points per signal")
    p.add_argument("--max-tau-fraction", type=float, default=0.33, help="Use tau up to this fraction of segment duration")
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
    for col in df.columns:
        if col not in TEXT_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "TestTime_s" not in df.columns and "Time_s" in df.columns:
        df["TestTime_s"] = df["Time_s"] - df["Time_s"].iloc[0]
    if "TestTime_s" not in df.columns:
        raise RuntimeError(f"Input CSV is missing TestTime_s and Time_s: {path}")
    df = df.dropna(subset=["TestTime_s"])
    if df.empty:
        raise RuntimeError(f"Input CSV contains no valid SDC2 data rows after cleaning: {path}")
    return df


def ensure_columns(df):
    if "ActualTablePosition_deg" not in df.columns and "ActualPosition_deg" in df.columns:
        df["ActualTablePosition_deg"] = df["ActualPosition_deg"]
    if "PositionError_deg" not in df.columns and "TablePositionError_deg" in df.columns:
        df["PositionError_deg"] = df["TablePositionError_deg"]
    if "PositionError_deg" not in df.columns and {"CommandPosition_deg", "ActualTablePosition_deg"}.issubset(df.columns):
        df["PositionError_deg"] = df["CommandPosition_deg"] - df["ActualTablePosition_deg"]
    if "MeasuredSpeed_deg_s" not in df.columns and "ActualTablePosition_deg" in df.columns:
        df["MeasuredSpeed_deg_s"] = np.nan
        for _, g in df.groupby(segment_keys(df), dropna=False, sort=False):
            t = g["TestTime_s"].to_numpy(float)
            y = g["ActualTablePosition_deg"].to_numpy(float)
            if len(g) > 3 and np.nanmax(t) > np.nanmin(t):
                with np.errstate(divide="ignore", invalid="ignore"):
                    v = np.gradient(y, t)
                df.loc[g.index, "MeasuredSpeed_deg_s"] = v
    if "SpeedError_deg_s" not in df.columns and {"MeasuredSpeed_deg_s", "TargetSpeed_deg_s"}.issubset(df.columns):
        df["SpeedError_deg_s"] = df["MeasuredSpeed_deg_s"] - df["TargetSpeed_deg_s"]
    return df


def segment_keys(df):
    keys = []
    for k in ["TestName", "LoadCase", "Direction", "TargetSpeed_deg_s"]:
        if k in df.columns:
            keys.append(k)
    if not keys:
        df["TestName"] = "ALL_DATA"
        keys = ["TestName"]
    return keys


def tau_grid(n, dt, max_points=45, max_tau_fraction=0.33):
    max_m = max(1, int(math.floor(n * max_tau_fraction)))
    max_m = min(max_m, max(1, n // 2 - 1))
    if max_m < 1:
        return np.array([], dtype=int)
    if max_m <= max_points:
        ms = np.arange(1, max_m + 1, dtype=int)
    else:
        ms = np.unique(np.round(np.logspace(0, math.log10(max_m), max_points)).astype(int))
    return ms[ms >= 1]


def overlapping_allan(x, dt, max_points=45, max_tau_fraction=0.33):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 8 or not np.isfinite(dt) or dt <= 0:
        return pd.DataFrame(columns=["tau_s", "m_samples", "adev", "avar", "num_pairs"])
    ms = tau_grid(n, dt, max_points, max_tau_fraction)
    rows = []
    csum = np.concatenate([[0.0], np.cumsum(x)])
    for m in ms:
        if n < 2*m + 2:
            continue
        # Overlapping block averages y_i = mean(x[i:i+m])
        y = (csum[m:] - csum[:-m]) / m
        dy = np.diff(y)
        dy = dy[np.isfinite(dy)]
        if len(dy) < 2:
            continue
        avar = 0.5 * np.mean(dy**2)
        adev = math.sqrt(avar)
        rows.append({"tau_s": m*dt, "m_samples": m, "adev": adev, "avar": avar, "num_pairs": len(dy)})
    return pd.DataFrame(rows)


def best_fit_residual(t, y):
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(t) & np.isfinite(y)
    out = np.full_like(y, np.nan, dtype=float)
    if ok.sum() < 5:
        return out
    p = np.polyfit(t[ok], y[ok], 1)
    out[ok] = y[ok] - np.polyval(p, t[ok])
    return out


def add_minor_grid(ax):
    ax.grid(True, which="major", alpha=0.35)
    ax.minorticks_on()
    ax.grid(True, which="minor", alpha=0.15)


def plot_allan(adev_df, outpath, title, ylabel, signal_note, segment_note, microstep=""):
    if adev_df.empty:
        return
    fig, ax = plt.subplots(figsize=(10.8, 7.0), constrained_layout=True)
    ax.loglog(adev_df["tau_s"], adev_df["adev"], "-o", linewidth=1.8, markersize=5, label="Overlapping Allan deviation")
    add_minor_grid(ax)
    ax.set_xlabel("Averaging time, tau (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold")

    # Guide slopes anchored near the middle/minimum region.
    tau = adev_df["tau_s"].to_numpy(float)
    adev = adev_df["adev"].to_numpy(float)
    ok = np.isfinite(tau) & np.isfinite(adev) & (tau > 0) & (adev > 0)
    if ok.sum() >= 3:
        tau_ok = tau[ok]
        adev_ok = adev[ok]
        idx_anchor = int(np.nanargmin(adev_ok))
        ta = tau_ok[idx_anchor]
        ya = adev_ok[idx_anchor]
        x0 = max(tau_ok.min(), ta / 3.0)
        x1 = min(tau_ok.max(), ta * 3.0)
        if x1 <= x0:
            x0, x1 = tau_ok.min(), tau_ok.max()
        xg = np.array([x0, x1])
        slope_defs = [(-0.5, "slope -0.5 white noise"), (0.0, "slope 0 bias/flicker floor"), (0.5, "slope +0.5 random walk"), (1.0, "slope +1 drift")]
        for k, label in slope_defs:
            yg = ya * (xg / ta) ** k
            ax.loglog(xg, yg, linestyle="--", linewidth=1.1, alpha=0.75, label=label)
        min_tau = tau_ok[idx_anchor]
        min_adev = adev_ok[idx_anchor]
    else:
        min_tau = np.nan
        min_adev = np.nan

    ax.legend(loc="best", fontsize=8)
    note = (
        f"{segment_note}\n"
        f"{signal_note}\n"
        f"Microstep setting: {microstep if microstep else 'from CSV/package'}\n"
        f"Min ADEV: {min_adev:.4g} at tau={min_tau:.4g} s\n"
        "Estimator: overlapping adjacent block averages\n"
        "Interpretation: -0.5 white noise, 0 flicker/bias floor, +0.5 random walk, +1 drift"
    )
    ax.text(0.02, 0.02, note, transform=ax.transAxes, va="bottom", ha="left", fontsize=8.5,
            bbox=dict(facecolor="white", edgecolor="0.35", alpha=0.92))
    fig.savefig(outpath, dpi=190)
    plt.close(fig)


def plot_time_series(t, y, outpath, title, ylabel, note):
    fig, ax = plt.subplots(figsize=(10.8, 4.8), constrained_layout=True)
    ax.plot(t, y, "-", linewidth=1.2)
    add_minor_grid(ax)
    ax.set_xlabel("Segment time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold")
    ax.text(0.02, 0.98, note, transform=ax.transAxes, va="top", ha="left", fontsize=8.5,
            bbox=dict(facecolor="white", edgecolor="0.35", alpha=0.92))
    fig.savefig(outpath, dpi=190)
    plt.close(fig)


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fig_dir = out / "allan_figures"
    csv_dir = out / "allan_csv"
    fig_dir.mkdir(exist_ok=True)
    csv_dir.mkdir(exist_ok=True)

    df = ensure_columns(load_csv(args.input))
    keys = segment_keys(df)
    summary_rows = []

    for key_vals, g in df.groupby(keys, dropna=False, sort=False):
        if not isinstance(key_vals, tuple):
            key_vals = (key_vals,)
        key_dict = dict(zip(keys, key_vals))
        test = str(key_dict.get("TestName", "SEGMENT"))
        load = str(key_dict.get("LoadCase", ""))
        direction = str(key_dict.get("Direction", ""))
        target = key_dict.get("TargetSpeed_deg_s", np.nan)
        base = safe_name("_".join([test, load, direction, str(target)]))

        t = g["TestTime_s"].to_numpy(float)
        order = np.argsort(t)
        t = t[order]
        if len(t) < 8 or np.nanmax(t) <= np.nanmin(t):
            continue
        dt = float(np.nanmedian(np.diff(t)))
        duration = float(np.nanmax(t) - np.nanmin(t))
        segment_note = f"Segment: {test}, {load}, {direction}, target={target} deg/s, duration={duration:.2f} s"

        signals = []
        if "ActualTablePosition_deg" in g.columns:
            y = g["ActualTablePosition_deg"].to_numpy(float)[order]
            signals.append(("actual_position_relative_deg", y - y[0], "Allan deviation of relative table position (deg)", "Relative encoder-derived table position"))
            signals.append(("position_residual_deg", best_fit_residual(t, y), "Allan deviation of position residual (deg)", "Position residual after best-fit line removal"))
        if "PositionError_deg" in g.columns:
            signals.append(("position_error_deg", g["PositionError_deg"].to_numpy(float)[order], "Allan deviation of position error (deg)", "Command minus encoder position error"))
        if "MeasuredSpeed_deg_s" in g.columns:
            signals.append(("measured_speed_deg_s", g["MeasuredSpeed_deg_s"].to_numpy(float)[order], "Allan deviation of measured speed (deg/s)", "Logged or gradient-estimated measured table speed"))
        if "SpeedError_deg_s" in g.columns:
            signals.append(("speed_error_deg_s", g["SpeedError_deg_s"].to_numpy(float)[order], "Allan deviation of speed error (deg/s)", "Measured speed minus command speed"))

        for sig_name, y, ylabel, signal_note in signals:
            ok = np.isfinite(y)
            if ok.sum() < 8:
                continue
            # Use only finite samples while preserving approximate dt assumption.
            y2 = y[ok]
            t2 = t[ok]
            adev = overlapping_allan(y2, dt, args.max_points, args.max_tau_fraction)
            if adev.empty:
                continue
            csv_path = csv_dir / f"allan_{base}_{sig_name}.csv"
            fig_path = fig_dir / f"allan_{base}_{sig_name}.png"
            ts_path = fig_dir / f"timeseries_{base}_{sig_name}.png"
            adev.to_csv(csv_path, index=False)
            plot_allan(adev, fig_path, f"SDC2 Allan deviation - {sig_name}", ylabel, signal_note, segment_note, args.microstep)
            plot_time_series(t2, y2, ts_path, f"SDC2 time series used for Allan - {sig_name}", ylabel.replace("Allan deviation of ", ""),
                             segment_note + "\nRaw logged signal used as Allan input; no pre-smoothing.")
            min_idx = int(np.nanargmin(adev["adev"].to_numpy(float)))
            row = {
                **key_dict,
                "Signal": sig_name,
                "SampleDt_s": dt,
                "Duration_s": duration,
                "N": int(ok.sum()),
                "MinADEV": float(adev["adev"].iloc[min_idx]),
                "TauAtMinADEV_s": float(adev["tau_s"].iloc[min_idx]),
                "FirstTau_s": float(adev["tau_s"].iloc[0]),
                "LastTau_s": float(adev["tau_s"].iloc[-1]),
                "NumTauPoints": int(len(adev)),
                "CSV": str(csv_path.name),
                "Figure": str(fig_path.name),
            }
            summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out / "SDC2_Allan_summary.csv", index=False)

    # Combined summary by signal type.
    if not summary.empty:
        fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
        for sig, sg in summary.groupby("Signal"):
            label_base = sg.get("TargetSpeed_deg_s", pd.Series([np.nan]*len(sg))).astype(str)
            x = np.arange(len(sg))
            ax.plot(x, sg["MinADEV"], "-o", label=sig)
        ax.set_yscale("log")
        ax.set_xlabel("Segment index within summary table")
        ax.set_ylabel("Minimum Allan deviation (signal units)")
        ax.set_title("SDC2 Allan minimum summary by signal", fontweight="bold")
        add_minor_grid(ax)
        ax.legend(fontsize=8)
        ax.text(0.02, 0.02, "See SDC2_Allan_summary.csv for exact segment, signal, tau, and figure filenames.",
                transform=ax.transAxes, va="bottom", fontsize=9, bbox=dict(facecolor="white", edgecolor="0.35"))
        fig.savefig(out / "SDC2_Allan_combined_minimum_summary.png", dpi=190)
        plt.close(fig)

    print(f"Saved Allan analysis in: {out.resolve()}")
    print(f"Summary: {out / 'SDC2_Allan_summary.csv'}")


if __name__ == "__main__":
    main()
