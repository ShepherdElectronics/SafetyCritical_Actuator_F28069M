import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import serial

EXPECTED_COLUMNS = [
    "RunLabel", "Mode", "TestIndex", "TestName", "State", "Time_s", "TestTime_s", "SampleRate_Hz",
    "TargetSpeed_deg_s", "MotorRPM", "SinePeriod_s", "EncoderCount",
    "ExpectedEncoderCount", "EncoderCountError", "CommandTablePosition_deg",
    "ActualMotorPosition_deg", "ActualTablePosition_deg", "TablePositionError_deg",
    "CommandTableSpeed_deg_s", "CommandMotorSpeed_deg_s", "FeedforwardStepRate_Hz",
    "CorrectionStepRate_Hz", "StepRate_Hz", "StepPulseCount", "MeasuredSpeed_deg_s",
    "SpeedError_deg_s", "LoopDt_us", "MaxLoopDt_us", "FaultCode", "MotionActive",
    "EncA", "EncB", "EncZ",
]

LEGACY_COLUMNS = [
    "RunLabel", "Mode", "TestIndex", "TestName", "Time_s", "TestTime_s", "SampleRate_Hz",
    "TargetSpeed_deg_s", "MotorRPM", "SinePeriod_s", "EncoderCount",
    "CommandTablePosition_deg", "ActualMotorPosition_deg", "ActualTablePosition_deg",
    "TablePositionError_deg", "CommandTableSpeed_deg_s", "CommandMotorSpeed_deg_s",
    "StepRate_Hz", "EncA", "EncB", "EncZ",
]


def slug(x):
    return str(x).replace(" ", "_").replace(".", "p").replace("-", "neg").replace("/", "_")


def select_mode():
    print()
    print("Select SDC2 run mode:")
    print("  1. RPM / table-speed debug sweep")
    print("  2. Full SDC2 protocol run")
    print("  3. Open-loop fixed STEP-frequency sweep")
    print("  4. Open-loop RAMPED STEP-frequency sweep, 25 Hz upward")
    print("  5. Slow encoder-plot test: 0.002, 0.003, 0.005, 0.01, 0.05, 0.1 deg/s")
    print("     NOTE: this firmware has FAST_DEBUG=true, so durations are shortened for faster debugging.")
    while True:
        choice = input("Enter 1, 2, 3, 4, or 5: ").strip()
        if choice == "1":
            return "SWEEP"
        if choice == "2":
            return "FULL"
        if choice == "3":
            return "OPENLOOP"
        if choice == "4":
            return "OPENRAMP"
        if choice == "5":
            return "SLOWPLOT"
        print("Invalid selection. Enter 1, 2, 3, 4, or 5.")


def read_serial_to_csv(port, baud, outdir, mode):
    outdir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = outdir / f"SDC2_{mode}_raw_{timestamp}.csv"
    comment_path = outdir / f"SDC2_{mode}_comments_{timestamp}.txt"

    print(f"Opening {port} at {baud} baud...")
    print("IMPORTANT: Ctrl+C stops logging and sends STOP once, but Arduino reset/power-off is the safest hard stop.")

    header_seen = False
    sent_mode = False

    with serial.Serial(port, baud, timeout=0.5) as ser, raw_path.open("w", newline="") as fout, comment_path.open("w") as fcomment:
        print("Waiting for Arduino reset/boot...")
        time.sleep(5.0)
        ser.reset_input_buffer()

        # Send mode multiple times because opening the port can reset the board.
        for _ in range(5):
            ser.write((mode + "\n").encode("utf-8"))
            ser.flush()
            time.sleep(0.3)
        sent_mode = True
        print(f"# SENT_MODE,{mode}")

        try:
            while True:
                raw = ser.readline().decode("utf-8", errors="replace").strip()
                if not raw:
                    continue

                print(raw)

                if raw.startswith("#"):
                    fcomment.write(raw + "\n")
                    fcomment.flush()
                    if "ALL_TESTS_COMPLETE" in raw:
                        print("All tests complete. Closing log.")
                        break
                    continue

                if raw.startswith("RunLabel,Mode,TestIndex,TestName"):
                    fout.write(raw + "\n")
                    fout.flush()
                    header_seen = True
                    continue

                if header_seen:
                    fout.write(raw + "\n")
                    fout.flush()

        except KeyboardInterrupt:
            print("\nCtrl+C received. Sending STOP to Arduino...")
            try:
                ser.write(b"STOP\n")
                ser.flush()
                time.sleep(0.5)
            except Exception:
                pass
            print("Logger stopped by user.")

    print(f"Saved raw CSV: {raw_path}")
    return raw_path


def load_data(csv_path):
    df = pd.read_csv(csv_path)

    # Support both the new diagnostic CSV and older package logs.
    missing_new = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_new:
        missing_legacy = [c for c in LEGACY_COLUMNS if c not in df.columns]
        if missing_legacy:
            raise ValueError(f"Missing expected columns. New missing: {missing_new}; legacy missing: {missing_legacy}")
        # Add diagnostic columns for old files so plotting still works.
        if "State" not in df.columns:
            df.insert(4, "State", "LEGACY")
        for c, default in {
            "ExpectedEncoderCount": np.nan,
            "EncoderCountError": np.nan,
            "FeedforwardStepRate_Hz": np.nan,
            "CorrectionStepRate_Hz": np.nan,
            "StepPulseCount": np.nan,
            "MeasuredSpeed_deg_s": np.nan,
            "SpeedError_deg_s": np.nan,
            "LoopDt_us": np.nan,
            "MaxLoopDt_us": np.nan,
            "FaultCode": "NONE",
            "MotionActive": np.nan,
        }.items():
            if c not in df.columns:
                df[c] = default

    text_cols = {"RunLabel", "Mode", "TestName", "State", "FaultCode"}
    for col in df.columns:
        if col not in text_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Time_s", "TestIndex", "CommandTablePosition_deg", "ActualTablePosition_deg"])
    if df.empty:
        return df

    # If firmware-provided measured speed exists, keep it. Also compute an offline gradient speed.
    df["MeasuredTableSpeed_Gradient_deg_s"] = np.nan
    for tid, g in df.groupby("TestIndex"):
        if len(g) > 2:
            t = g["TestTime_s"].to_numpy()
            y = g["ActualTablePosition_deg"].to_numpy()
            with np.errstate(divide="ignore", invalid="ignore"):
                v = np.gradient(y, t)
            df.loc[g.index, "MeasuredTableSpeed_Gradient_deg_s"] = v

    if "MeasuredSpeed_deg_s" in df.columns and df["MeasuredSpeed_deg_s"].notna().any():
        df["MeasuredTableSpeed_deg_s"] = df["MeasuredSpeed_deg_s"]
    else:
        df["MeasuredTableSpeed_deg_s"] = df["MeasuredTableSpeed_Gradient_deg_s"]

    if "SpeedError_deg_s" not in df.columns or not df["SpeedError_deg_s"].notna().any():
        df["SpeedError_deg_s"] = df["MeasuredTableSpeed_deg_s"] - df["CommandTableSpeed_deg_s"]

    df["AbsError_deg"] = df["TablePositionError_deg"].abs()

    # Smoothness residual: actual position minus best-fit line per trial.
    df["PositionResidual_deg"] = np.nan
    for tid, g in df.groupby("TestIndex"):
        if len(g) > 5:
            t = g["TestTime_s"].to_numpy()
            y = g["ActualTablePosition_deg"].to_numpy()
            ok = np.isfinite(t) & np.isfinite(y)
            if ok.sum() > 5:
                m, b = np.polyfit(t[ok], y[ok], 1)
                residual = y - (m * t + b)
                df.loc[g.index, "PositionResidual_deg"] = residual
    return df


def split_trials(df, outdir):
    split_dir = outdir / "split_trials_csv"
    split_dir.mkdir(parents=True, exist_ok=True)
    for tid, g in df.groupby("TestIndex"):
        name = g["TestName"].iloc[0]
        target = g["TargetSpeed_deg_s"].iloc[0]
        mode = g["Mode"].iloc[0]
        file_name = f"{int(tid):03d}_{slug(mode)}_{slug(name)}_spd_{target:+.3f}.csv"
        g.to_csv(split_dir / file_name, index=False)


def save_summary(df, outdir):
    rows = []
    for tid, g in df.groupby("TestIndex"):
        rows.append({
            "TestIndex": int(tid),
            "RunLabel": g["RunLabel"].iloc[0],
            "Mode": g["Mode"].iloc[0],
            "TestName": g["TestName"].iloc[0],
            "TargetSpeed_deg_s": g["TargetSpeed_deg_s"].iloc[0],
            "MotorRPM": g["MotorRPM"].iloc[0],
            "SinePeriod_s": g["SinePeriod_s"].iloc[0],
            "SampleRate_Hz": g["SampleRate_Hz"].median(),
            "Duration_s": g["TestTime_s"].max() - g["TestTime_s"].min(),
            "N": len(g),
            "MeanMeasuredSpeed_deg_s": g["MeasuredTableSpeed_deg_s"].mean(),
            "StdMeasuredSpeed_deg_s": g["MeasuredTableSpeed_deg_s"].std(),
            "MeanSpeedError_deg_s": g["SpeedError_deg_s"].mean(),
            "MeanPositionError_deg": g["TablePositionError_deg"].mean(),
            "RMSError_deg": np.sqrt(np.mean(g["TablePositionError_deg"] ** 2)),
            "MaxAbsError_deg": g["AbsError_deg"].max(),
            "FinalCommandPosition_deg": g["CommandTablePosition_deg"].iloc[-1],
            "FinalActualPosition_deg": g["ActualTablePosition_deg"].iloc[-1],
            "FinalError_deg": g["TablePositionError_deg"].iloc[-1],
            "MeanStepRate_Hz": g["StepRate_Hz"].mean(),
            "MeanFeedforwardStepRate_Hz": g.get("FeedforwardStepRate_Hz", pd.Series(dtype=float)).mean(),
            "MeanCorrectionStepRate_Hz": g.get("CorrectionStepRate_Hz", pd.Series(dtype=float)).mean(),
            "FinalStepPulseCount": g.get("StepPulseCount", pd.Series([np.nan])).iloc[-1],
            "MeanEncoderCountError": g.get("EncoderCountError", pd.Series(dtype=float)).mean(),
            "MaxAbsEncoderCountError": g.get("EncoderCountError", pd.Series(dtype=float)).abs().max(),
            "MeanLoopDt_us": g.get("LoopDt_us", pd.Series(dtype=float)).mean(),
            "MaxLoopDt_us": g.get("MaxLoopDt_us", pd.Series(dtype=float)).max(),
            "FaultCodes": ";".join(sorted(set(map(str, g.get("FaultCode", pd.Series(["NONE"])).dropna())))),
            "RMSPositionResidual_deg": np.sqrt(np.nanmean(g.get("PositionResidual_deg", pd.Series(dtype=float)) ** 2)),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(outdir / "SDC2_trial_summary.csv", index=False)
    return summary


def fig_path(outdir, name):
    plot_dir = outdir / "figures"
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir / name


def plot_all(df, summary, outdir):
    if df.empty:
        print("No data rows to plot.")
        return

    plt.figure(figsize=(14, 7))
    plt.plot(df["Time_s"], df["CommandTablePosition_deg"], label="Command position")
    plt.plot(df["Time_s"], df["ActualTablePosition_deg"], label="Encoder-derived position", alpha=0.8)
    plt.xlabel("Run time [s]")
    plt.ylabel("Table position [deg]")
    plt.title("SDC2 Commanded vs Encoder-Derived Table Position")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(fig_path(outdir, "01_command_vs_actual_position.png"), dpi=200)
    plt.close()

    plt.figure(figsize=(14, 6))
    plt.plot(df["Time_s"], df["TablePositionError_deg"])
    plt.xlabel("Run time [s]")
    plt.ylabel("Position error [deg]")
    plt.title("SDC2 Following Error")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(fig_path(outdir, "02_following_error.png"), dpi=200)
    plt.close()

    plt.figure(figsize=(14, 6))
    plt.plot(df["Time_s"], df["CommandTableSpeed_deg_s"], label="Command speed")
    plt.plot(df["Time_s"], df["MeasuredTableSpeed_deg_s"], label="Measured speed", alpha=0.7)
    plt.xlabel("Run time [s]")
    plt.ylabel("Speed [deg/s]")
    plt.title("SDC2 Commanded vs Measured Speed")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(fig_path(outdir, "03_command_vs_measured_speed.png"), dpi=200)
    plt.close()

    # Error overlay for non-static trials.
    moving = df[~df["TestName"].str.contains("STATIC", na=False)].copy()
    if not moving.empty:
        plt.figure(figsize=(14, 8))
        for tid, g in moving.groupby("TestIndex"):
            label = f"{int(tid)} {g['TestName'].iloc[0]} {g['TargetSpeed_deg_s'].iloc[0]:+.3f} dps"
            plt.plot(g["TestTime_s"], g["TablePositionError_deg"], label=label, linewidth=0.8)
        plt.xlabel("Trial time [s]")
        plt.ylabel("Position error [deg]")
        plt.title("Moving Trials: Following Error Overlay")
        plt.grid(True)
        plt.legend(fontsize=6, ncol=2)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "04_moving_error_overlay.png"), dpi=200)
        plt.close()

    const_summary = summary[summary["TestName"].str.contains("SWEEP|CONST|SLOWPLOT", na=False)].copy()
    if not const_summary.empty:
        plt.figure(figsize=(10, 6))
        plt.scatter(const_summary["TargetSpeed_deg_s"], const_summary["MeanSpeedError_deg_s"])
        plt.axhline(0, linewidth=1)
        plt.xlabel("Target speed [deg/s]")
        plt.ylabel("Mean measured speed - command [deg/s]")
        plt.title("Speed Bias vs Target Speed")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "05_speed_bias_vs_target.png"), dpi=200)
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.scatter(const_summary["TargetSpeed_deg_s"].abs(), const_summary["RMSError_deg"])
        plt.xlabel("Absolute target speed [deg/s]")
        plt.ylabel("RMS position error [deg]")
        plt.title("RMS Position Error vs Speed")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "06_rms_error_vs_speed.png"), dpi=200)
        plt.close()

    static_df = df[df["TestName"].str.contains("STATIC", na=False)].copy()
    if not static_df.empty:
        plt.figure(figsize=(12, 6))
        for tid, g in static_df.groupby("TestIndex"):
            rel = g["ActualTablePosition_deg"] - g["ActualTablePosition_deg"].iloc[0]
            plt.plot(g["TestTime_s"], rel, label=g["TestName"].iloc[0])
        plt.xlabel("Trial time [s]")
        plt.ylabel("Relative drift [deg]")
        plt.title("Static Drift")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "07_static_drift.png"), dpi=200)
        plt.close()


    # New diagnostics: step rate split, loop timing, encoder count error, residual smoothness.
    if {"FeedforwardStepRate_Hz", "CorrectionStepRate_Hz", "StepRate_Hz"}.issubset(df.columns):
        plt.figure(figsize=(14, 6))
        plt.plot(df["Time_s"], df["FeedforwardStepRate_Hz"], label="Feedforward step rate")
        plt.plot(df["Time_s"], df["CorrectionStepRate_Hz"], label="Correction step rate", alpha=0.8)
        plt.plot(df["Time_s"], df["StepRate_Hz"], label="Total step rate", alpha=0.5)
        plt.xlabel("Run time [s]")
        plt.ylabel("STEP rate [Hz]")
        plt.title("Feedforward / Correction / Total STEP Rate")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "08_step_rate_split.png"), dpi=200)
        plt.close()

    if "EncoderCountError" in df.columns and df["EncoderCountError"].notna().any():
        plt.figure(figsize=(14, 6))
        plt.plot(df["Time_s"], df["EncoderCountError"])
        plt.xlabel("Run time [s]")
        plt.ylabel("Expected encoder count - actual count [counts]")
        plt.title("Encoder Count Error")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "09_encoder_count_error.png"), dpi=200)
        plt.close()

    if "PositionResidual_deg" in df.columns and df["PositionResidual_deg"].notna().any():
        plt.figure(figsize=(14, 7))
        for tid, g in moving.groupby("TestIndex") if not moving.empty else []:
            label = f"{int(tid)} {g['TestName'].iloc[0]} {g['TargetSpeed_deg_s'].iloc[0]:+.3f} dps"
            plt.plot(g["TestTime_s"], g["PositionResidual_deg"], label=label, linewidth=0.8)
        plt.xlabel("Trial time [s]")
        plt.ylabel("Position residual vs best-fit line [deg]")
        plt.title("Smoothness Residual Overlay")
        plt.grid(True)
        plt.legend(fontsize=6, ncol=2)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "10_smoothness_residual_overlay.png"), dpi=200)
        plt.close()

    if "LoopDt_us" in df.columns and df["LoopDt_us"].notna().any():
        plt.figure(figsize=(14, 5))
        plt.plot(df["Time_s"], df["LoopDt_us"], label="LoopDt_us")
        if "MaxLoopDt_us" in df.columns:
            plt.plot(df["Time_s"], df["MaxLoopDt_us"], label="MaxLoopDt_us", alpha=0.8)
        plt.xlabel("Run time [s]")
        plt.ylabel("Loop time [us]")
        plt.title("Loop Timing / Jitter")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(fig_path(outdir, "11_loop_timing.png"), dpi=200)
        plt.close()

def analyze_csv(csv_path, outdir):
    df = load_data(csv_path)
    clean_path = outdir / "SDC2_clean.csv"
    df.to_csv(clean_path, index=False)
    split_trials(df, outdir)
    summary = save_summary(df, outdir)
    plot_all(df, summary, outdir)
    print(f"Clean CSV: {clean_path}")
    print(f"Summary: {outdir / 'SDC2_trial_summary.csv'}")
    print(f"Split CSVs: {outdir / 'split_trials_csv'}")
    print(f"Figures: {outdir / 'figures'}")


def main():
    parser = argparse.ArgumentParser(description="SDC2 one-click logger and plotter")
    parser.add_argument("--port", default="COM5")
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--outdir", default="SDC2_results")
    parser.add_argument("--mode", default=None, choices=["SWEEP", "FULL", "OPENLOOP", "OPENRAMP", "SLOWPLOT"])
    parser.add_argument("--csv", default=None, help="Analyze existing CSV instead of logging")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.csv:
        analyze_csv(Path(args.csv), outdir)
        return

    mode = args.mode or select_mode()
    csv_path = read_serial_to_csv(args.port, args.baud, outdir, mode)

    try:
        analyze_csv(csv_path, outdir)
    except Exception as e:
        print(f"Post-processing failed: {e}")
        print("Raw CSV was still saved.")


if __name__ == "__main__":
    main()
