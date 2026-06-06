#!/usr/bin/env python3
"""
SDC2 serial logger for Arduino firmware.

Commands sent to Arduino:
  D debug
  S static tests
  P official protocol constants
  H high-speed 10-50 deg/s
  N sine tests
  A all final tests

Robust behavior:
  - Stops automatically on single-test completion markers, not only ALL_TESTS_COMPLETE.
  - Keeps serial comments in *_metadata.txt.
  - Refuses to silently accept an empty/no-header CSV.
  - Sends telemetry-rate config and host heartbeat/deadman pings.
"""

import argparse
import csv
import os
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
from datetime import datetime
from pathlib import Path

try:
    import serial
except ImportError:
    print("ERROR: pyserial is required. Install with: pip install pyserial", file=sys.stderr)
    raise

DONE_MARKERS = [
    "ALL_TESTS_COMPLETE",
    "Debug test complete",
    "Static tests complete",
    "Official protocol constant-speed tests complete",
    "High-speed characterization complete",
    "High-speed extension complete",
    "Sine tests complete",
]

HEADER_STARTS = (
    "Time_s",
    "RunLabel,Mode,TestIndex,TestName",
)

DEFAULT_SDC2_HEADER = [
    "Time_s", "TestTime_s", "TestName", "LoadCase", "Direction", "State",
    "TargetSpeed_deg_s", "CommandPosition_deg", "EncoderCount",
    "ActualTablePosition_deg", "PositionError_deg",
    "FeedforwardStepRate_Hz", "CorrectionStepRate_Hz", "StepRate_Hz",
    "StepPulseCount", "ExpectedEncoderCount", "EncoderCountError",
    "MeasuredSpeed_deg_s", "LoopDt_us", "MaxLoopDt_us",
    "FaultCode", "IndexSeen", "ISRCount", "MicrostepSetting",
]

EXTRA_ISR_COLUMNS = [
    "CommandTableSpeed_deg_s", "ProfileSpeed_deg_s", "StepCommandSpeed_deg_s",
    "TelemetryDrops", "ControlTickMisses", "StepISR_Hz",
]
DEFAULT_SDC2_HEADER_ISR = DEFAULT_SDC2_HEADER + EXTRA_ISR_COLUMNS



def looks_like_numeric_data_row(line: str) -> bool:
    try:
        parts = [x.strip() for x in line.split(",")]
        if len(parts) not in (len(DEFAULT_SDC2_HEADER), len(DEFAULT_SDC2_HEADER_ISR)):
            return False
        # First two fields should be numeric time values.
        float(parts[0])
        float(parts[1])
        return True
    except Exception:
        return False


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="Serial port, e.g. COM5")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--command", default="?", help="Arduino command to send: D,S,P,H,N,A,Z,?")
    p.add_argument("--output", default="", help="Output CSV path. Default uses timestamp in runs/.")
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--max-seconds", type=float, default=0.0, help="Optional forced stop/logging duration. 0 = until done marker/Ctrl+C.")
    p.add_argument("--length", default="full", choices=["super_short", "short", "medium", "full"],
                   help="Trial length profile sent before the run command. super_short/short=L, medium=M, full=F.")
    p.add_argument("--telemetry-hz", default="50", choices=["10", "20", "50", "100"],
                   help="Target telemetry print rate. 50 Hz is the stable default for live plotting; lower values reduce serial pressure during motion.")
    p.add_argument("--dir-polarity", default="normal", choices=["normal", "inverted"],
                   help="Target DIR pin polarity. Use inverted if CW/CCW physical motion is reversed.")
    p.add_argument("--heartbeat", action="store_true", default=True,
                   help="Enable target host-deadman heartbeat while logging.")
    p.add_argument("--no-heartbeat", dest="heartbeat", action="store_false",
                   help="Disable host-deadman heartbeat.")
    return p.parse_args()


def looks_like_header(line: str) -> bool:
    return any(line.startswith(h) for h in HEADER_STARTS)


def validate_csv(path: Path, rows: int, header):
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(
            f"Raw CSV is empty or missing: {path}\n"
            "No CSV header/data was captured. Check COM port, baud, firmware command, and that the test actually started."
        )
    if header is None:
        raise RuntimeError(
            f"Raw CSV was created but no CSV header was seen: {path}\n"
            "The Arduino printed comments/status but no data header. Do not postprocess this file."
        )
    if rows <= 0:
        raise RuntimeError(
            f"Raw CSV has a header but zero data rows: {path}\n"
            "Run the test longer or use a completed non-empty CSV."
        )


def main():
    args = parse_args()

    if not args.output:
        os.makedirs("runs", exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = os.path.join("runs", f"sdc2_{args.command}_{stamp}.csv")
    else:
        outdir = os.path.dirname(args.output)
        if outdir:
            os.makedirs(outdir, exist_ok=True)

    out_path = Path(args.output)
    print(f"Opening {args.port} at {args.baud} baud")
    print(f"Output CSV: {out_path}")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.10, write_timeout=1, rtscts=False, dsrdtr=False)
    except serial.SerialException as e:
        print(f"ERROR: Could not open serial port {args.port}: {e}", file=sys.stderr)
        sys.exit(2)

    time.sleep(2.5)
    try:
        ser.reset_input_buffer()
    except serial.SerialException as e:
        print(f"WARNING: Could not clear input buffer: {e}")

    cmd = args.command.strip().upper()
    length_key = args.length.strip().lower()
    length_cmd = {"super_short": "L", "short": "L", "medium": "M", "full": "F"}.get(length_key, "F")
    print(f"Sending trial length profile: {length_key} ({length_cmd})")
    ser.write((length_cmd + "\n").encode("ascii"))
    ser.flush()
    time.sleep(0.10)

    telemetry_cmd = {"10": "Q", "20": "W", "50": "E", "100": "R"}[str(args.telemetry_hz)]
    print(f"Sending telemetry rate: {args.telemetry_hz} Hz ({telemetry_cmd})")
    ser.write((telemetry_cmd + "\n").encode("ascii"))
    ser.flush()
    time.sleep(0.10)

    if args.heartbeat:
        print("Enabling target host-deadman heartbeat (Y)")
        ser.write(b"Y\n")
        ser.flush()
        time.sleep(0.10)

    dir_cmd = "I" if args.dir_polarity == "inverted" else "J"
    print(f"Sending DIR polarity: {args.dir_polarity} ({dir_cmd})")
    ser.write((dir_cmd + "\n").encode("ascii"))
    ser.flush()
    time.sleep(0.10)

    print(f"Sending command: {cmd}")
    ser.write((cmd + "\n").encode("ascii"))
    ser.flush()

    start = time.time()
    csv_started = False
    header = None
    rows = 0
    comments = []
    completion_marker = ""

    serial_error = ""
    last_heartbeat = time.time()

    try:
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = None
            try:
                while True:
                    if args.heartbeat and (time.time() - last_heartbeat) >= 0.50:
                        try:
                            ser.write(b".\n")
                            ser.flush()
                        except serial.SerialException as e:
                            serial_error = str(e)
                            print(f"WARNING: Serial heartbeat write failed: {serial_error}")
                            comments.append("# LOGGER_HEARTBEAT_WRITE_EXCEPTION," + serial_error.replace("\n", " "))
                            break
                        last_heartbeat = time.time()

                    if args.max_seconds > 0 and (time.time() - start) > args.max_seconds:
                        print("Max seconds reached. Sending stop command X.")
                        ser.write(b"X\n")
                        ser.flush()
                        comments.append("# LOGGER_MAX_SECONDS_REACHED")
                        break

                    try:
                        raw = ser.readline()
                    except serial.SerialException as e:
                        serial_error = str(e)
                        print(f"WARNING: Serial read failed: {serial_error}")
                        comments.append("# LOGGER_SERIAL_EXCEPTION," + serial_error.replace("\n", " "))
                        comments.append("# LOGGER_NOTE,CSV is partial if completion marker was not seen")
                        break

                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    print(line, flush=True)

                    if line.startswith("#"):
                        comments.append(line)
                        for marker in DONE_MARKERS:
                            if marker in line:
                                completion_marker = marker
                                print(f"Completion marker seen: {marker}", flush=True)
                                raise StopIteration
                        continue

                    if looks_like_header(line):
                        header = [x.strip() for x in line.split(",")]
                        writer = csv.writer(f)
                        writer.writerow(header)
                        f.flush()
                        csv_started = True
                        continue

                    parts = [x.strip() for x in line.split(",")]

                    # Some firmware builds print the CSV header at boot. The logger may clear
                    # the input buffer before sending the selected command, so the run can
                    # begin with numeric data rows and no header. If this exact 24-column
                    # SDC2 data row format is detected, synthesize the correct header and
                    # keep the data instead of producing an empty CSV.
                    if (not csv_started) and looks_like_numeric_data_row(line):
                        header = DEFAULT_SDC2_HEADER_ISR[:] if len(parts) == len(DEFAULT_SDC2_HEADER_ISR) else DEFAULT_SDC2_HEADER[:]
                        writer = csv.writer(f)
                        writer.writerow(header)
                        csv_started = True
                        comments.append("# LOGGER_SYNTHESIZED_HEADER_FROM_FIRST_DATA_ROW")

                    if csv_started and writer is not None:
                        if len(parts) == len(header):
                            writer.writerow(parts)
                            rows += 1
                            if rows % 100 == 0:
                                f.flush()
                        else:
                            comments.append("# MALFORMED," + line)
                    else:
                        # Non-CSV status/noise before header. Preserve it in metadata.
                        comments.append("# DATA_BEFORE_HEADER," + line)
            except StopIteration:
                pass
            except KeyboardInterrupt:
                print("\nCtrl+C received. Sending stop command X.")
                comments.append("# LOGGER_KEYBOARD_INTERRUPT")
                try:
                    ser.write(b"X\n")
                    ser.flush()
                except Exception:
                    pass
            finally:
                f.flush()
    finally:
        try:
            ser.close()
        except Exception:
            pass

    meta_path = out_path.with_name(out_path.stem + "_metadata.txt")
    with meta_path.open("w", encoding="utf-8") as mf:
        mf.write(f"port={args.port}\n")
        mf.write(f"baud={args.baud}\n")
        mf.write(f"command={cmd}\n")
        mf.write(f"length={args.length}\n")
        mf.write(f"telemetry_hz={args.telemetry_hz}\n")
        mf.write(f"heartbeat={args.heartbeat}\n")
        mf.write(f"output={out_path}\n")
        mf.write(f"rows={rows}\n")
        mf.write(f"header_seen={header is not None}\n")
        mf.write(f"completion_marker={completion_marker}\n")
        mf.write(f"serial_error={serial_error}\n")
        mf.write("\n# Serial comments\n")
        for c in comments:
            mf.write(c + "\n")

    print(f"Saved CSV: {out_path}")
    print(f"Rows: {rows}")
    print(f"Saved metadata: {meta_path}")

    try:
        validate_csv(out_path, rows, header)
    except RuntimeError as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(2)

    if serial_error and rows > 0:
        print("WARNING: Serial port failed/disconnected before a clean completion marker.")
        print("The CSV contains captured rows and was saved for partial-run analysis.")
        print("If the motor/Arduino kept moving, reset the board or power-cycle the driver before starting another run.")


if __name__ == "__main__":
    main()
