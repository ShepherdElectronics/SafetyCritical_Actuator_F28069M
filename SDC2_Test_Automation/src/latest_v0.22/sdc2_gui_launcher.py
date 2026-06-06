#!/usr/bin/env python3
"""
SDC2 Characterization Telemetry Console

Tkinter desktop UI for:
  - selecting multiple R725 microstep firmware builds
  - Arduino CLI compile/upload
  - running SDC2 serial logger commands D/S/P/H/N/A
  - live serial log
  - live rolling telemetry plots for position and speed
  - opening live CSV / metadata / output folders
  - running event postprocess figures
  - running Allan deviation analysis figures

Requires for logging/analysis:
  pip install pyserial pandas numpy matplotlib
"""

from __future__ import annotations

import csv
import datetime as dt
import math
import os
import queue
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_OK = True
except Exception:
    FigureCanvasTkAgg = None
    Figure = None
    MATPLOTLIB_OK = False

APP_TITLE = "SDC2 Characterization Telemetry Console"

DEFAULT_PORT = "COM5"
DEFAULT_FQBN = "arduino:mbed_giga:giga:split=75_25,target_core=cm7,security=none"
DEFAULT_BASE_FQBN = "arduino:mbed_giga:giga"
DEFAULT_M4_FQBN = "arduino:mbed_giga:giga:split=75_25,target_core=cm4,security=none"
DEFAULT_BAUD = "115200"

COMMANDS = {
    "D": "Debug shakedown",
    "S": "Static Allan hold tests",
    "P": "Protocol constant-speed tests",
    "H": "High-speed 10-50 deg/s test",
    "N": "Sine velocity tests",
    "A": "ALL main tests",
}

DONE_MARKERS = [
    "ALL_TESTS_COMPLETE",
    "Debug test complete",
    "Static tests complete",
    "Official protocol constant-speed tests complete",
    "High-speed characterization complete",
    "Sine tests complete",
]

ROOT = Path(__file__).resolve().parent
PY = sys.executable or "python"
ROLLING_SAMPLES = 5000
PLOT_UPDATE_MS = 100

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
        parts = next(csv.reader([line]))
        if len(parts) not in (len(DEFAULT_SDC2_HEADER), len(DEFAULT_SDC2_HEADER_ISR)):
            return False
        float(parts[0])
        float(parts[1])
        return True
    except Exception:
        return False


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_float(x, default=math.nan):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


class SDC2UI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1320x860")
        self.minsize(1050, 700)

        self.process = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread = None

        self.last_csv = tk.StringVar(value="")
        self.last_run_dir = tk.StringVar(value="")
        self.last_metadata = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Ready")

        self.port = tk.StringVar(value=DEFAULT_PORT)
        self.fqbn = tk.StringVar(value=DEFAULT_FQBN)
        self.fqbn_m4 = tk.StringVar(value=DEFAULT_M4_FQBN)
        self.architecture = tk.StringVar(value="single_core")
        self.baud = tk.StringVar(value=DEFAULT_BAUD)
        self.microstep = tk.StringVar(value="16")
        self.command = tk.StringVar(value="D")
        self.trial_length = tk.StringVar(value="super_short")
        self.telemetry_hz = tk.StringVar(value="50")
        self.dir_polarity = tk.StringVar(value="normal")
        self.auto_postprocess = tk.BooleanVar(value=True)
        self.auto_allan = tk.BooleanVar(value=True)
        self.max_seconds = tk.StringVar(value="0")

        self.live_lock = threading.Lock()
        self.live_header: list[str] | None = None
        self.live_rows_seen = 0
        self.live_start_wall = None
        self.live_time = deque(maxlen=ROLLING_SAMPLES)
        self.live_pos = deque(maxlen=ROLLING_SAMPLES)
        self.live_speed = deque(maxlen=ROLLING_SAMPLES)          # firmware/provided speed, may be filtered/smoothed
        self.live_raw_speed = deque(maxlen=ROLLING_SAMPLES)      # host-computed raw d(position)/dt from consecutive samples
        self.live_cmd_speed = deque(maxlen=ROLLING_SAMPLES)
        self.live_error = deque(maxlen=ROLLING_SAMPLES)
        self.live_encoder_count = deque(maxlen=ROLLING_SAMPLES)
        self.live_encoder_delta = deque(maxlen=ROLLING_SAMPLES)
        self.live_step_rate = deque(maxlen=ROLLING_SAMPLES)
        self.live_raw_rows = deque(maxlen=200)
        self.live_last_pos_for_raw = math.nan
        self.live_last_t_for_raw = math.nan
        self.live_last_encoder_for_raw = math.nan
        self.live_state = ""
        self.live_fault = "NONE"
        self.live_warning_count = 0
        self.live_last_line_time = None

        self.sample_count_var = tk.StringVar(value="0")
        self.elapsed_var = tk.StringVar(value="0.0 s")
        self.latest_speed_var = tk.StringVar(value="n/a")
        self.latest_raw_speed_var = tk.StringVar(value="n/a")
        self.mean_speed_var = tk.StringVar(value="n/a")
        self.rms_error_var = tk.StringVar(value="n/a")
        self.warning_var = tk.StringVar(value="none")
        self.state_var = tk.StringVar(value="n/a")
        self.fault_var = tk.StringVar(value="NONE")

        self._build_ui()
        self.after(100, self._drain_log_queue)
        self.after(PLOT_UPDATE_MS, self._update_live_plots)

    # ---------------- UI construction ----------------
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        title = ttk.Label(self, text="SDC2 Characterization Telemetry Console", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        top = ttk.Frame(self)
        top.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        for c in range(8):
            top.columnconfigure(c, weight=1)

        settings = ttk.LabelFrame(top, text="Connection / firmware")
        settings.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=(0, 8), pady=4)
        for c in range(4):
            settings.columnconfigure(c, weight=1)

        ttk.Label(settings, text="Port").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(settings, textvariable=self.port, width=12).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        ttk.Label(settings, text="Baud").grid(row=0, column=1, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(settings, textvariable=self.baud, width=12).grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 8))

        ttk.Label(settings, text="M7 FQBN").grid(row=0, column=2, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(settings, textvariable=self.fqbn, width=28).grid(row=1, column=2, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        ttk.Label(settings, text="Architecture").grid(row=4, column=0, sticky="w", padx=8, pady=(4, 2))
        self.arch_box = ttk.Combobox(settings, textvariable=self.architecture, values=["single_core", "dual_core_m7_m4"], state="readonly")
        self.arch_box.grid(row=4, column=1, sticky="ew", padx=8, pady=(4, 2))
        self.arch_box.current(0)
        ttk.Label(settings, text="M4 FQBN").grid(row=4, column=2, sticky="w", padx=8, pady=(4, 2))
        ttk.Entry(settings, textvariable=self.fqbn_m4, width=24).grid(row=4, column=3, sticky="ew", padx=8, pady=(4, 2))
        ttk.Button(settings, text="Compile/upload M4 worker", command=self.compile_upload_m4_worker).grid(row=5, column=2, sticky="ew", padx=8, pady=4)
        ttk.Button(settings, text="Compile/upload M4 + selected M7", command=self.compile_upload_dual_core).grid(row=5, column=3, sticky="ew", padx=8, pady=4)

        ttk.Label(settings, text="Microstep firmware / DIP setting").grid(row=2, column=0, sticky="w", padx=8, pady=(4, 2))
        self.microstep_box = ttk.Combobox(
            settings, textvariable=self.microstep, state="readonly", width=18,
            values=[
                "2", "4", "5", "8", "10", "16", "18", "20",
                "32", "50", "64", "100", "128", "180", "200", "256"
            ],
        )
        self.microstep_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        self.microstep_box.set("16")
        self.microstep_box.bind("<<ComboboxSelected>>", self._microstep_combo_changed)

        ttk.Button(settings, text="Compile selected firmware", command=self.compile_firmware).grid(row=2, column=2, sticky="ew", padx=8, pady=4)
        ttk.Button(settings, text="Upload selected firmware", command=self.upload_firmware).grid(row=2, column=3, sticky="ew", padx=8, pady=4)
        ttk.Button(settings, text="Compile + upload", command=self.compile_upload_firmware).grid(row=3, column=2, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        runf = ttk.LabelFrame(top, text="Run tests")
        runf.grid(row=0, column=4, columnspan=4, sticky="nsew", padx=(8, 0), pady=4)
        for c in range(4):
            runf.columnconfigure(c, weight=1)

        ttk.Label(runf, text="Test command").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.cmd_box = ttk.Combobox(runf, textvariable=self.command, values=[f"{k} - {v}" for k, v in COMMANDS.items()], state="readonly")
        self.cmd_box.grid(row=1, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 8))
        self.cmd_box.current(0)
        self.cmd_box.bind("<<ComboboxSelected>>", self._command_combo_changed)

        ttk.Checkbutton(runf, text="Auto postprocess event plots", variable=self.auto_postprocess).grid(row=2, column=0, columnspan=2, sticky="w", padx=8)
        ttk.Checkbutton(runf, text="Auto Allan analysis", variable=self.auto_allan).grid(row=2, column=2, columnspan=2, sticky="w", padx=8)

        ttk.Label(runf, text="Trial length").grid(row=3, column=0, sticky="w", padx=8, pady=(6, 2))
        self.length_box = ttk.Combobox(
            runf,
            textvariable=self.trial_length,
            values=[
                "super_short - fastest debug",
                "medium - partial characterization",
                "full - official durations"
            ],
            state="readonly"
        )
        self.length_box.grid(row=3, column=1, columnspan=3, sticky="ew", padx=8, pady=(6, 2))
        self.length_box.current(0)
        self.length_box.bind("<<ComboboxSelected>>", self._length_combo_changed)

        ttk.Label(runf, text="Telemetry rate").grid(row=4, column=0, sticky="w", padx=8, pady=(6, 2))
        self.telemetry_box = ttk.Combobox(
            runf,
            textvariable=self.telemetry_hz,
            values=["10 - safest high-speed", "20 - conservative motion", "50 - recommended live plotting", "100 - static/Allan only"],
            state="readonly"
        )
        self.telemetry_box.grid(row=4, column=1, columnspan=3, sticky="ew", padx=8, pady=(6, 2))
        self.telemetry_box.current(2)
        self.telemetry_box.bind("<<ComboboxSelected>>", self._telemetry_combo_changed)

        ttk.Label(runf, text="DIR polarity").grid(row=5, column=0, sticky="w", padx=8, pady=(6, 2))
        self.dir_box = ttk.Combobox(
            runf,
            textvariable=self.dir_polarity,
            values=["normal", "inverted"],
            state="readonly"
        )
        self.dir_box.grid(row=5, column=1, sticky="ew", padx=8, pady=(6, 2))
        self.dir_box.current(0)

        ttk.Label(runf, text="Max seconds, 0 = until firmware complete/Ctrl stop").grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))
        ttk.Entry(runf, textvariable=self.max_seconds, width=10).grid(row=6, column=2, sticky="ew", padx=8, pady=(6, 2))

        ttk.Button(runf, text="Run selected test", command=self.run_selected_test).grid(row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Button(runf, text="Compile/upload + run", command=self.compile_upload_run).grid(row=7, column=2, columnspan=2, sticky="ew", padx=8, pady=8)

        # Notebook: log / live plots / summary
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=14, pady=6)

        self.log_tab = ttk.Frame(self.notebook)
        self.plot_tab = ttk.Frame(self.notebook)
        self.raw_tab = ttk.Frame(self.notebook)
        self.summary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="Live Log")
        self.notebook.add(self.plot_tab, text="Live Plots")
        self.notebook.add(self.raw_tab, text="Raw Live Data")
        self.notebook.add(self.summary_tab, text="Summary")
        self._build_log_tab()
        self._build_plot_tab()
        self._build_raw_tab()
        self._build_summary_tab()

        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, sticky="ew", padx=14, pady=8)
        for c in range(10):
            actions.columnconfigure(c, weight=1)

        ttk.Button(actions, text="Analyze existing CSV", command=self.analyze_existing_csv).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(actions, text="Run Allan existing CSV", command=self.allan_existing_csv).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(actions, text="Open last CSV", command=self.open_last_csv).grid(row=0, column=2, sticky="ew", padx=3)
        ttk.Button(actions, text="Open live log/meta", command=self.open_last_metadata).grid(row=0, column=3, sticky="ew", padx=3)
        ttk.Button(actions, text="Open plots folder", command=self.open_plots_folder).grid(row=0, column=4, sticky="ew", padx=3)
        ttk.Button(actions, text="Open last run folder", command=self.open_last_run_folder).grid(row=0, column=5, sticky="ew", padx=3)
        ttk.Button(actions, text="Open root folder", command=self.open_root_folder).grid(row=0, column=6, sticky="ew", padx=3)
        ttk.Button(actions, text="Stop/kill process", command=self.stop_process).grid(row=0, column=7, sticky="ew", padx=3)
        ttk.Button(actions, text="Clear log", command=lambda: self.log_text.delete("1.0", tk.END)).grid(row=0, column=8, sticky="ew", padx=3)
        ttk.Button(actions, text="Quit", command=self.destroy).grid(row=0, column=9, sticky="ew", padx=3)

        status = ttk.LabelFrame(self, text="Last output")
        status.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 8))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="Last CSV:").grid(row=0, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status, textvariable=self.last_csv).grid(row=0, column=1, sticky="ew", padx=8, pady=2)
        ttk.Label(status, text="Last run dir:").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status, textvariable=self.last_run_dir).grid(row=1, column=1, sticky="ew", padx=8, pady=2)
        ttk.Label(status, text="Status:").grid(row=2, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(status, textvariable=self.status_text).grid(row=2, column=1, sticky="ew", padx=8, pady=2)

        self.log("Ready. Pick 16 or 256 µstep, compile/upload, then run D/S/P/H/N/A.")
        self.log("Live plots update continuously from unbuffered serial output and use a rolling buffer of the last 5000 parsed CSV rows.")
        self.log("Raw Live Data tab shows unsmoothed row-to-row speed and encoder-count deltas for sanity checking.")
        self.log("For the full sequence, use command A - ALL main tests.")
        self.log("Dual-core mode uploads the M4 buffered DAQ worker scaffold plus selected M7 real-time target.")

    def _build_log_tab(self):
        self.log_tab.rowconfigure(0, weight=1)
        self.log_tab.columnconfigure(0, weight=1)
        self.log_text = tk.Text(self.log_tab, wrap="word", font=("Consolas", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self.log_tab, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _build_plot_tab(self):
        self.plot_tab.rowconfigure(0, weight=1)
        self.plot_tab.columnconfigure(0, weight=1)
        if not MATPLOTLIB_OK:
            ttk.Label(self.plot_tab, text="Matplotlib is not available. Install with: pip install matplotlib").grid(row=0, column=0, padx=20, pady=20)
            self.fig = None
            self.canvas = None
            self.ax_pos = None
            self.ax_speed = None
            return
        self.fig = Figure(figsize=(10, 7), dpi=100)
        self.ax_pos = self.fig.add_subplot(311)
        self.ax_speed = self.fig.add_subplot(312)
        self.ax_raw = self.fig.add_subplot(313)
        self.fig.tight_layout(pad=2.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_tab)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _build_raw_tab(self):
        self.raw_tab.rowconfigure(1, weight=1)
        self.raw_tab.columnconfigure(0, weight=1)
        note = (
            "Raw view shows unsmoothed, row-by-row telemetry. "
            "RawSpeed_host is computed live as d(ActualTablePosition_deg)/dt between consecutive samples; "
            "EncoderDelta is the raw encoder-count change between rows. Use this to catch quantization, stalls, reversals, and telemetry artifacts."
        )
        ttk.Label(self.raw_tab, text=note, wraplength=1150).grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        cols = ("Time_s", "State", "Direction", "EncoderCount", "EncoderDelta", "RawSpeed_host", "MeasuredSpeed", "CommandSpeed", "StepRate", "Fault")
        self.raw_tree = ttk.Treeview(self.raw_tab, columns=cols, show="headings", height=18)
        widths = {
            "Time_s": 95, "State": 115, "Direction": 80, "EncoderCount": 110, "EncoderDelta": 95,
            "RawSpeed_host": 120, "MeasuredSpeed": 120, "CommandSpeed": 120, "StepRate": 95, "Fault": 150,
        }
        for c in cols:
            self.raw_tree.heading(c, text=c)
            self.raw_tree.column(c, width=widths.get(c, 100), anchor="center")
        self.raw_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        yscroll = ttk.Scrollbar(self.raw_tab, orient="vertical", command=self.raw_tree.yview)
        yscroll.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.raw_tree.configure(yscrollcommand=yscroll.set)

    def _build_summary_tab(self):
        self.summary_tab.columnconfigure(1, weight=1)
        rows = [
            ("Samples received", self.sample_count_var),
            ("Elapsed time", self.elapsed_var),
            ("Latest measured speed", self.latest_speed_var),
            ("Latest raw d(pos)/dt speed", self.latest_raw_speed_var),
            ("Mean measured speed", self.mean_speed_var),
            ("RMS position error", self.rms_error_var),
            ("Warnings", self.warning_var),
            ("Latest state", self.state_var),
            ("Latest fault", self.fault_var),
        ]
        for r, (label, var) in enumerate(rows):
            ttk.Label(self.summary_tab, text=label + ":", font=("Segoe UI", 11, "bold")).grid(row=r, column=0, sticky="w", padx=18, pady=8)
            ttk.Label(self.summary_tab, textvariable=var, font=("Consolas", 11)).grid(row=r, column=1, sticky="ew", padx=8, pady=8)
        note = (
            "Live telemetry is parsed from raw serial CSV rows. It is only a sanity check; "
            "final figures come from the saved raw CSV and postprocessing scripts."
        )
        ttk.Label(self.summary_tab, text=note, wraplength=900).grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=18, pady=18)

    # ---------------- logging / live telemetry ----------------
    def log(self, msg):
        self.log_queue.put(str(msg))

    def _drain_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _reset_live_telemetry(self):
        with self.live_lock:
            self.live_header = None
            self.live_rows_seen = 0
            self.live_start_wall = dt.datetime.now()
            self.live_time.clear()
            self.live_pos.clear()
            self.live_speed.clear()
            self.live_raw_speed.clear()
            self.live_cmd_speed.clear()
            self.live_error.clear()
            self.live_encoder_count.clear()
            self.live_encoder_delta.clear()
            self.live_step_rate.clear()
            self.live_raw_rows.clear()
            self.live_last_pos_for_raw = math.nan
            self.live_last_t_for_raw = math.nan
            self.live_last_encoder_for_raw = math.nan
            self.live_state = ""
            self.live_fault = "NONE"
            self.live_warning_count = 0
            self.live_last_line_time = None
        self.status_text.set("Telemetry reset; waiting for CSV header")

    def _handle_stdout_line(self, line: str):
        stripped = line.strip()
        if not stripped:
            return
        if stripped.startswith("RunLabel,") or stripped.startswith("Time_s"):
            try:
                header = next(csv.reader([stripped]))
            except Exception:
                return
            with self.live_lock:
                self.live_header = [h.strip() for h in header]
                self.live_rows_seen = 0
            self.status_text.set("CSV header seen; live telemetry active")
            return
        if stripped.startswith("#"):
            if "WARN" in stripped or "ERROR" in stripped:
                with self.live_lock:
                    self.live_warning_count += 1
            for marker in DONE_MARKERS:
                if marker in stripped:
                    self.status_text.set(f"Firmware completion marker: {marker}")
            return
        with self.live_lock:
            header = list(self.live_header) if self.live_header else None
        try:
            parts = next(csv.reader([stripped]))
        except Exception:
            return
        if not header:
            if looks_like_numeric_data_row(stripped):
                header = DEFAULT_SDC2_HEADER_ISR[:] if len(parts) == len(DEFAULT_SDC2_HEADER_ISR) else DEFAULT_SDC2_HEADER[:]
                with self.live_lock:
                    self.live_header = header
                    self.live_rows_seen = 0
                self.status_text.set("No header seen; synthesized SDC2 header from first data row")
            else:
                return
        if len(parts) != len(header):
            return
        row = {header[i]: parts[i].strip() for i in range(len(header))}
        t = safe_float(row.get("Time_s"), safe_float(row.get("TestTime_s")))
        pos = safe_float(row.get("ActualTablePosition_deg"), safe_float(row.get("TablePosition_deg")))
        speed = safe_float(row.get("MeasuredSpeed_deg_s"), safe_float(row.get("MeasuredTableSpeed_deg_s")))
        cmd_speed = safe_float(row.get("StepCommandSpeed_deg_s"), safe_float(row.get("CommandTableSpeed_deg_s"), safe_float(row.get("ProfileSpeed_deg_s"), safe_float(row.get("TargetSpeed_deg_s")))))
        err = safe_float(row.get("TablePositionError_deg"), math.nan)
        enc = safe_float(row.get("EncoderCount"), math.nan)
        step_rate = safe_float(row.get("StepRate_Hz"), math.nan)
        state = row.get("State", "")
        direction = row.get("Direction", "")
        fault = row.get("FaultCode", "NONE") or "NONE"
        # Raw host-side speed: unsmoothed derivative of the encoder-derived table position.
        # This intentionally exposes quantization/jitter and is separate from firmware-provided MeasuredSpeed_deg_s.
        with self.live_lock:
            prev_t = self.live_last_t_for_raw
            prev_pos = self.live_last_pos_for_raw
            prev_enc = self.live_last_encoder_for_raw
        raw_speed = math.nan
        enc_delta = math.nan
        if math.isfinite(t) and math.isfinite(pos) and math.isfinite(prev_t) and math.isfinite(prev_pos) and t != prev_t:
            raw_speed = (pos - prev_pos) / (t - prev_t)
        if math.isfinite(enc) and math.isfinite(prev_enc):
            enc_delta = enc - prev_enc
        if not math.isfinite(t):
            return
        with self.live_lock:
            self.live_rows_seen += 1
            self.live_time.append(t)
            self.live_pos.append(pos)
            self.live_speed.append(speed)
            self.live_raw_speed.append(raw_speed)
            self.live_cmd_speed.append(cmd_speed)
            self.live_error.append(err)
            self.live_encoder_count.append(enc)
            self.live_encoder_delta.append(enc_delta)
            self.live_step_rate.append(step_rate)
            self.live_raw_rows.append({
                "Time_s": t, "State": state, "Direction": direction, "EncoderCount": enc,
                "EncoderDelta": enc_delta, "RawSpeed_host": raw_speed, "MeasuredSpeed": speed,
                "CommandSpeed": cmd_speed, "StepRate": step_rate, "Fault": fault,
            })
            self.live_last_t_for_raw = t
            self.live_last_pos_for_raw = pos
            self.live_last_encoder_for_raw = enc
            self.live_state = state
            self.live_fault = fault
            if fault and fault != "NONE" and "0" != fault:
                if "WARN" in fault or "ERROR" in fault or "FAULT" in fault:
                    self.live_warning_count += 1
            self.live_last_line_time = dt.datetime.now()

    def _update_live_plots(self):
        with self.live_lock:
            t = list(self.live_time)
            pos = list(self.live_pos)
            spd = list(self.live_speed)
            raw_spd = list(self.live_raw_speed)
            cmd = list(self.live_cmd_speed)
            err = list(self.live_error)
            enc_delta = list(self.live_encoder_delta)
            raw_rows = list(self.live_raw_rows)
            rows_seen = self.live_rows_seen
            state = self.live_state
            fault = self.live_fault
            warning_count = self.live_warning_count
        self.sample_count_var.set(str(rows_seen))
        if t:
            t0 = t[0]
            trel = [x - t0 for x in t]
            elapsed = trel[-1]
            self.elapsed_var.set(f"{elapsed:.1f} s")
            finite_spd = [x for x in spd if math.isfinite(x)]
            finite_raw_spd = [x for x in raw_spd if math.isfinite(x)]
            finite_err = [x for x in err if math.isfinite(x)]
            if finite_spd:
                self.latest_speed_var.set(f"{finite_spd[-1]:.6g} deg/s")
                self.mean_speed_var.set(f"{sum(finite_spd)/len(finite_spd):.6g} deg/s")
            else:
                self.latest_speed_var.set("n/a")
                self.mean_speed_var.set("n/a")
            if finite_raw_spd:
                self.latest_raw_speed_var.set(f"{finite_raw_spd[-1]:.6g} deg/s")
            else:
                self.latest_raw_speed_var.set("n/a")
            if finite_err:
                rms = math.sqrt(sum(x*x for x in finite_err) / len(finite_err))
                self.rms_error_var.set(f"{rms:.6g} deg")
            else:
                self.rms_error_var.set("n/a")
            self.warning_var.set("none" if warning_count == 0 else str(warning_count))
            self.state_var.set(state or "n/a")
            self.fault_var.set(fault or "NONE")
            self._draw_plots(trel, pos, spd, cmd, raw_spd, enc_delta)
            self._update_raw_table(raw_rows)
        self.after(PLOT_UPDATE_MS, self._update_live_plots)

    def _draw_plots(self, trel, pos, spd, cmd, raw_spd=None, enc_delta=None):
        if not MATPLOTLIB_OK or self.canvas is None or self.ax_pos is None or self.ax_speed is None:
            return
        self.ax_pos.clear()
        self.ax_speed.clear()
        if trel:
            pos_vals = [p if math.isfinite(p) else math.nan for p in pos]
            spd_vals = [v if math.isfinite(v) else math.nan for v in spd]
            raw_vals = [v if math.isfinite(v) else math.nan for v in (raw_spd or [])]
            enc_delta_vals = [v if math.isfinite(v) else math.nan for v in (enc_delta or [])]
            cmd_vals = [v if math.isfinite(v) else math.nan for v in cmd]
            self.ax_pos.plot(trel, pos_vals, linewidth=1.2, label="Encoder/table position")
            self.ax_pos.set_xlabel("Recent run time (s)")
            self.ax_pos.set_ylabel("Position (deg)")
            self.ax_pos.set_title("Live Encoder/Table Position vs Time")
            self.ax_pos.grid(True, which="major", alpha=0.30)
            self.ax_pos.grid(True, which="minor", alpha=0.12)
            self.ax_pos.minorticks_on()
            self.ax_pos.legend(loc="best")

            self.ax_speed.plot(trel, cmd_vals, linewidth=1.2, label="Command speed")
            self.ax_speed.plot(trel, spd_vals, linewidth=1.0, label="Measured speed (firmware)")
            if raw_vals:
                self.ax_speed.plot(trel, raw_vals, linewidth=0.7, alpha=0.55, label="Raw speed d(pos)/dt")
            self.ax_speed.set_xlabel("Recent run time (s)")
            self.ax_speed.set_ylabel("Speed (deg/s)")
            self.ax_speed.set_title("Live Speed: Command, Firmware Speed, and Raw Row-to-Row Speed")
            self.ax_speed.grid(True, which="major", alpha=0.30)
            self.ax_speed.grid(True, which="minor", alpha=0.12)
            self.ax_speed.minorticks_on()
            self.ax_speed.legend(loc="best")

            if hasattr(self, "ax_raw"):
                self.ax_raw.clear()
                if enc_delta_vals:
                    self.ax_raw.plot(trel, enc_delta_vals, linewidth=0.8, label="Raw encoder count delta / row")
                self.ax_raw.set_xlabel("Recent run time (s)")
                self.ax_raw.set_ylabel("Counts/row")
                self.ax_raw.set_title("Raw Encoder Increment Between Telemetry Rows")
                self.ax_raw.grid(True, which="major", alpha=0.30)
                self.ax_raw.grid(True, which="minor", alpha=0.12)
                self.ax_raw.minorticks_on()
                self.ax_raw.legend(loc="best")
        self.fig.tight_layout(pad=2.5)
        self.canvas.draw_idle()

    def _update_raw_table(self, raw_rows):
        if not hasattr(self, "raw_tree"):
            return
        # Refresh the small table at plot cadence. It intentionally shows only the most recent rows.
        try:
            for item in self.raw_tree.get_children():
                self.raw_tree.delete(item)
            for row in raw_rows[-80:]:
                def fmt(x, nd=6):
                    if isinstance(x, str):
                        return x
                    try:
                        if math.isfinite(float(x)):
                            return f"{float(x):.{nd}g}"
                    except Exception:
                        pass
                    return ""
                vals = (
                    fmt(row.get("Time_s")),
                    row.get("State", ""),
                    row.get("Direction", ""),
                    fmt(row.get("EncoderCount"), 0),
                    fmt(row.get("EncoderDelta"), 0),
                    fmt(row.get("RawSpeed_host")),
                    fmt(row.get("MeasuredSpeed")),
                    fmt(row.get("CommandSpeed")),
                    fmt(row.get("StepRate")),
                    row.get("Fault", ""),
                )
                self.raw_tree.insert("", "end", values=vals)
            children = self.raw_tree.get_children()
            if children:
                self.raw_tree.see(children[-1])
        except Exception:
            pass

    # ---------------- commands ----------------

    def _length_combo_changed(self, event=None):
        """Store only the length profile token from the displayed combobox text."""
        value = event.widget.get() if event is not None else self.trial_length.get()
        if value:
            self.trial_length.set(value.split(" ", 1)[0])

    def _telemetry_combo_changed(self, event=None):
        """Store only the numeric telemetry rate from the displayed combobox text."""
        value = event.widget.get() if event is not None else self.telemetry_hz.get()
        if value:
            self.telemetry_hz.set(value.split(" ", 1)[0])

    def _command_combo_changed(self, event=None):
        value = event.widget.get()
        if value:
            self.command.set(value.split(" ", 1)[0])

    def _microstep_combo_changed(self, event=None):
        """Normalize microstep selection to just the numeric token."""
        value = event.widget.get() if event is not None else self.microstep.get()
        if value:
            self.microstep.set(value.split(" ", 1)[0].strip())

    def selected_sketch(self):
        ms = self.microstep.get()
        if self.architecture.get() == "dual_core_m7_m4":
            sketch_name = f"SDC2_TestRunner_Menu_{ms}u_DualCore_M7"
        else:
            sketch_name = f"SDC2_TestRunner_Menu_{ms}u"
        sketch_dir = ROOT / sketch_name
        return sketch_name, sketch_dir

    def selected_m4_sketch(self):
        sketch_name = "SDC2_RawBuffer_M4"
        sketch_dir = ROOT / sketch_name
        return sketch_name, sketch_dir

    def run_command(self, cmd, cwd=None, after=None, parse_telemetry=False):
        if self.process is not None and self.process.poll() is None:
            messagebox.showwarning("Process running", "A process is already running. Stop it first or wait for it to finish.")
            return
        self.worker_thread = threading.Thread(target=self._run_command_worker, args=(cmd, cwd or ROOT, after, parse_telemetry), daemon=True)
        self.worker_thread.start()

    def _run_command_worker(self, cmd, cwd, after, parse_telemetry):
        self.log("")
        self.log("> " + " ".join(str(x) for x in cmd))
        self.log(f"cwd: {cwd}")
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            self.process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                shell=False,
                env=env,
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                clean = line.rstrip()
                if parse_telemetry:
                    self._handle_stdout_line(clean)
                self.log(clean)
            rc = self.process.wait()
            self.log(f"Process finished with exit code {rc}")
            self.process = None
            if rc == 0 and after:
                after()
        except Exception as e:
            self.process = None
            self.log(f"ERROR: {e}")

    def compile_upload_m4_worker(self):
        _, sketch_dir = self.selected_m4_sketch()
        if not sketch_dir.exists():
            messagebox.showerror("Missing M4 sketch", f"M4 sketch folder not found:\n{sketch_dir}")
            return
        def upload_after():
            self.run_command(["arduino-cli", "upload", "-p", self.port.get(), "--fqbn", self.fqbn_m4.get(), str(sketch_dir)])
        self.log("Compiling M4 buffered DAQ worker using GIGA menu options: split=75_25,target_core=cm4,security=none")
        self.run_command(["arduino-cli", "compile", "--fqbn", self.fqbn_m4.get(), str(sketch_dir)], after=upload_after)

    def compile_upload_dual_core(self):
        _, m4_dir = self.selected_m4_sketch()
        _, m7_dir = self.selected_sketch()
        if not m4_dir.exists() or not m7_dir.exists():
            messagebox.showerror("Missing sketch", f"Missing M4 or M7 sketch folder:\n{m4_dir}\n{m7_dir}")
            return
        self.architecture.set("dual_core_m7_m4")
        def upload_m7_after_compile():
            self.run_command(["arduino-cli", "upload", "-p", self.port.get(), "--fqbn", self.fqbn.get(), str(m7_dir)])
        def compile_m7_after_m4_upload():
            self.run_command(["arduino-cli", "compile", "--fqbn", self.fqbn.get(), str(m7_dir)], after=upload_m7_after_compile)
        def upload_m4_after_compile():
            self.run_command(["arduino-cli", "upload", "-p", self.port.get(), "--fqbn", self.fqbn_m4.get(), str(m4_dir)], after=compile_m7_after_m4_upload)
        self.log("Dual-core upload sequence: compile/upload M4 worker first, then compile/upload selected M7 target. Uses same GIGA FQBN with target_core menu options.")
        self.run_command(["arduino-cli", "compile", "--fqbn", self.fqbn_m4.get(), str(m4_dir)], after=upload_m4_after_compile)

    def compile_firmware(self):
        _, sketch_dir = self.selected_sketch()
        if not sketch_dir.exists():
            messagebox.showerror("Missing sketch", f"Sketch folder not found:\n{sketch_dir}")
            return
        self.run_command(["arduino-cli", "compile", "--fqbn", self.fqbn.get(), str(sketch_dir)])

    def upload_firmware(self):
        _, sketch_dir = self.selected_sketch()
        if not sketch_dir.exists():
            messagebox.showerror("Missing sketch", f"Sketch folder not found:\n{sketch_dir}")
            return
        self.run_command(["arduino-cli", "upload", "-p", self.port.get(), "--fqbn", self.fqbn.get(), str(sketch_dir)])

    def compile_upload_firmware(self):
        _, sketch_dir = self.selected_sketch()
        if not sketch_dir.exists():
            messagebox.showerror("Missing sketch", f"Sketch folder not found:\n{sketch_dir}")
            return
        def upload_after():
            self.run_command(["arduino-cli", "upload", "-p", self.port.get(), "--fqbn", self.fqbn.get(), str(sketch_dir)])
        self.run_command(["arduino-cli", "compile", "--fqbn", self.fqbn.get(), str(sketch_dir)], after=upload_after)

    def compile_upload_run(self):
        _, sketch_dir = self.selected_sketch()
        def run_after_upload():
            self.after(1500, self.run_selected_test)
        def upload_after_compile():
            self.run_command(["arduino-cli", "upload", "-p", self.port.get(), "--fqbn", self.fqbn.get(), str(sketch_dir)], after=run_after_upload)
        self.run_command(["arduino-cli", "compile", "--fqbn", self.fqbn.get(), str(sketch_dir)], after=upload_after_compile)

    def make_run_paths(self, command):
        ms = self.microstep.get()
        stamp = now_stamp()
        length_tag = self.trial_length.get().split(" ", 1)[0]
        run_dir = ROOT / "SDC2_GUI_results" / f"{ms}u" / f"{command}_{length_tag}_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_csv = run_dir / f"SDC2_{ms}u_{command}_{stamp}.csv"
        metadata = raw_csv.with_name(raw_csv.stem + "_metadata.txt")
        self.last_run_dir.set(str(run_dir))
        self.last_csv.set(str(raw_csv))
        self.last_metadata.set(str(metadata))
        return run_dir, raw_csv

    def run_selected_test(self):
        cmd_value = self.command.get()
        if " " in cmd_value:
            cmd_value = cmd_value.split(" ", 1)[0]
        if cmd_value not in COMMANDS:
            messagebox.showerror("Invalid command", "Pick one of D/S/P/H/N/A.")
            return
        self._reset_live_telemetry()
        run_dir, raw_csv = self.make_run_paths(cmd_value)
        max_seconds = self.max_seconds.get().strip() or "0"
        length_value = self.trial_length.get().split(" ", 1)[0].strip() or "super_short"
        telemetry_value = self.telemetry_hz.get().split(" ", 1)[0].strip() or "50"
        args = [PY, "-u", str(ROOT / "python" / "sdc2_serial_logger.py"),
                "--port", self.port.get(),
                "--baud", self.baud.get(),
                "--command", cmd_value,
                "--length", length_value,
                "--telemetry-hz", telemetry_value,
                "--dir-polarity", self.dir_polarity.get(),
                "--output", str(raw_csv),
                "--max-seconds", max_seconds]
        self.log(f"Selected trial length: {length_value}")
        self.log(f"Selected telemetry rate: {telemetry_value} Hz")
        self.log(f"Selected DIR polarity: {self.dir_polarity.get()}")
        def after_logger():
            self.log(f"Logger finished. Raw CSV: {raw_csv}")
            if not self._valid_csv_for_analysis(raw_csv):
                self.log("Skipping postprocess/Allan analysis because the CSV is not valid.")
                return
            if self.auto_postprocess.get():
                self._run_postprocess(raw_csv, run_dir)
            elif self.auto_allan.get():
                self._run_allan(raw_csv, run_dir)
        self.run_command(args, after=after_logger, parse_telemetry=True)

    def _run_postprocess(self, raw_csv, run_dir):
        out = Path(run_dir) / "event_postprocess"
        args = [PY, str(ROOT / "python" / "sdc2_postprocess_fullchar.py"),
                "--input", str(raw_csv),
                "--out", str(out),
                "--microstep", self.microstep.get()]
        def after_post():
            self.log(f"Postprocess finished. Output: {out}")
            if self.auto_allan.get():
                self._run_allan(raw_csv, run_dir)
        self.run_command(args, after=after_post)

    def _run_allan(self, raw_csv, run_dir):
        out = Path(run_dir) / "allan_analysis"
        args = [PY, str(ROOT / "python" / "sdc2_allan_analysis.py"),
                "--input", str(raw_csv),
                "--out", str(out),
                "--microstep", self.microstep.get()]
        self.run_command(args, after=lambda: self.log(f"Allan analysis finished. Output: {out}"))

    def _valid_csv_for_analysis(self, raw_csv):
        raw_csv = Path(raw_csv)
        if not raw_csv.exists():
            self.log(f"ERROR: CSV does not exist: {raw_csv}")
            return False
        if raw_csv.stat().st_size == 0:
            self.log(f"ERROR: CSV is empty, skipping analysis: {raw_csv}")
            return False
        try:
            with raw_csv.open("r", encoding="utf-8", errors="replace") as f:
                first = f.readline().strip()
                second = f.readline().strip()
        except Exception as e:
            self.log(f"ERROR: could not read CSV header: {e}")
            return False
        if not (first.startswith("Time_s") or first.startswith("RunLabel,")):
            self.log(f"ERROR: CSV does not start with expected SDC2 header: {raw_csv}")
            self.log(f"First line: {first}")
            return False
        if not second:
            self.log(f"ERROR: CSV has header but no data rows: {raw_csv}")
            return False
        return True

    # ---------------- file actions ----------------
    def analyze_existing_csv(self):
        csv_path = filedialog.askopenfilename(title="Select SDC2 CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not csv_path:
            return
        run_dir = Path(csv_path).resolve().parent / "GUI_reanalysis"
        run_dir.mkdir(exist_ok=True)
        self.last_csv.set(csv_path)
        self.last_run_dir.set(str(run_dir))
        self.last_metadata.set(str(Path(csv_path).with_name(Path(csv_path).stem + "_metadata.txt")))
        if self._valid_csv_for_analysis(Path(csv_path)):
            self._run_postprocess(Path(csv_path), run_dir)

    def allan_existing_csv(self):
        csv_path = filedialog.askopenfilename(title="Select SDC2 CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not csv_path:
            return
        run_dir = Path(csv_path).resolve().parent / "GUI_allan_reanalysis"
        run_dir.mkdir(exist_ok=True)
        self.last_csv.set(csv_path)
        self.last_run_dir.set(str(run_dir))
        self.last_metadata.set(str(Path(csv_path).with_name(Path(csv_path).stem + "_metadata.txt")))
        if self._valid_csv_for_analysis(Path(csv_path)):
            self._run_allan(Path(csv_path), run_dir)

    def open_last_csv(self):
        self._open_path_from_var(self.last_csv, "No CSV available yet.")

    def open_last_metadata(self):
        self._open_path_from_var(self.last_metadata, "No metadata/log file available yet.")

    def open_plots_folder(self):
        run_dir = Path(self.last_run_dir.get().strip()) if self.last_run_dir.get().strip() else None
        if not run_dir:
            messagebox.showinfo("No run", "No run folder yet.")
            return
        candidates = [
            run_dir / "event_postprocess" / "figures",
            run_dir / "event_postprocess",
            run_dir / "allan_analysis" / "allan_figures",
            run_dir / "allan_analysis",
            run_dir,
        ]
        for p in candidates:
            if p.exists():
                self._open_folder(p)
                return
        messagebox.showerror("Missing folder", str(run_dir))

    def open_last_run_folder(self):
        path = self.last_run_dir.get().strip()
        if not path:
            messagebox.showinfo("No folder", "No run folder yet.")
            return
        self._open_folder(Path(path))

    def open_root_folder(self):
        self._open_folder(ROOT)

    def _open_path_from_var(self, var, missing_msg):
        path = var.get().strip()
        if not path:
            messagebox.showinfo("No file", missing_msg)
            return
        p = Path(path)
        if not p.exists():
            messagebox.showerror("Missing file", str(p))
            return
        self._open_file(p)

    def _open_file(self, path: Path):
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _open_folder(self, path: Path):
        if not path.exists():
            messagebox.showerror("Missing folder", str(path))
            return
        self._open_file(path)

    def stop_process(self):
        if self.process is None or self.process.poll() is not None:
            self.log("No active subprocess to stop.")
            return
        if messagebox.askyesno("Stop process", "Kill the running subprocess? If the motor is moving, use hardware stop/reset too."):
            try:
                self.process.terminate()
                self.log("Sent terminate to subprocess.")
            except Exception as e:
                self.log(f"Terminate failed: {e}")


if __name__ == "__main__":
    app = SDC2UI()
    app.mainloop()
