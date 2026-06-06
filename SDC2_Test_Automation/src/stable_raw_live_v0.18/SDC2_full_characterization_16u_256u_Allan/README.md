# SDC2 GUI Full Characterization Package - Final

Start here:

```text
launch_sdc2_ui.bat
```

Use the GUI to select 16 ustep or 256 ustep firmware, compile/upload, run D/S/P/H/N/A, postprocess event-based plots, and run Allan analysis.

Important robustness fixes in this final package:

- Single-test completion markers now close the logger automatically.
- Empty/no-header CSV files are detected before postprocessing.
- Postprocessing and Allan scripts now give clear errors instead of Pandas EmptyDataError.
- GUI skips analysis if the raw CSV is invalid.
- R725 microstep STEP-rate reference table is included in docs.

Commands:

| Command | Meaning |
|---|---|
| D | debug shakedown |
| S | static hold / Allan source data |
| P | protocol constant-speed tests |
| H | high-speed 10-50 deg/s tests |
| N | sine velocity tests |
| A | all main tests |


---

# SDC2 Full Characterization Package - 16 ustep / 256 ustep + Allan Analysis

This package runs the SDC2 Arduino GIGA + R725 + E5 encoder characterization workflow with selectable firmware for either:

- **16 microsteps** for high-speed / full characterization attempts
- **256 microsteps** for the original ultra-slow smoothness baseline

The one-click entry point is:

```text
upload_and_run_sdc2.bat
```

## What the batch file does

1. Lets you choose **16 ustep** or **256 ustep** firmware.
2. Compiles and uploads the matching Arduino sketch with `arduino-cli`.
3. Opens the logger menu.
4. Runs the selected test and saves raw CSV data under `runs/`.
5. Runs event-based postprocessing.
6. Runs Allan deviation analysis and exports annotated figures.

## Microstep DIP settings

| Setting | R725 DIP switch setting | Use case |
|---:|---|---|
| 16 ustep | SW1=D, SW2=D, SW3=U, SW4=U | Faster characterization, 10-50 deg/s testing, lower pulse-rate burden |
| 256 ustep | SW1=D, SW2=D, SW3=D, SW4=U | Ultra-slow baseline and smoothness comparison |

Always physically set the R725 DIP switches to match the firmware before running a test.

## Logger menu

After upload, the batch menu shows:

```text
1 = DEBUG        short sanity test
2 = HIGHSPEED    10, 20, 30, 40, 50 deg/s both directions
3 = PROTOCOL     0.01, 0.03, 1, 3, 5, 10, 15 deg/s both directions
4 = STATIC       static 50 Hz and 100 Hz hold tests for Allan deviation
5 = SINE         sine velocity tests, peak 15 deg/s
6 = ALL          static + protocol + highspeed + sine
7 = MENU ONLY    send ? to Arduino and log response briefly
8 = Analyze existing CSV: event plots + Allan plots
9 = Open results folder
C = Change/upload microstep firmware
0 = Exit
```

For the entire firmware sequence, use:

```text
6 = ALL
```

For pure Allan-source static data, use:

```text
4 = STATIC
```

## Output structure

For each run, outputs are saved like this:

```text
runs/
  sdc2_16u_static_allan_source.csv
  sdc2_256u_protocol_constants.csv

SDC2_results_16u/<run_label>/
  event_analysis/
    SDC2_clean.csv
    SDC2_16u_full_characterization_summary.csv
    SDC2_16u_combined_summary.png
    per-segment event figures
  allan_analysis/
    SDC2_Allan_summary.csv
    SDC2_Allan_combined_minimum_summary.png
    allan_csv/
      per-signal Allan CSVs
    allan_figures/
      annotated Allan deviation figures
      time-series figures used for Allan input

SDC2_results_256u/<run_label>/
  same structure as above
```

## Allan analysis details

The Allan script computes overlapping Allan deviation for each segment and signal where available:

- relative table position
- position residual after best-fit line removal
- position error
- measured speed
- speed error

Figures include:

- log-log Allan deviation plot
- minor grids
- slope guides: -0.5, 0, +0.5, +1
- annotations for segment, microstep setting, minimum Allan deviation, tau at minimum, and estimator method
- companion time-series figure showing the raw signal used as Allan input

## Important method distinction

Event-speed figures use raw encoder count-change timing and state explicitly:

```text
raw encoder counts; no filtering/smoothing/group averaging
```

Allan deviation is different: it is intentionally an averaging-time statistic. The Allan script does not pre-smooth the input signal, but Allan deviation itself evaluates how signal variation changes as averaging time `tau` changes.

## Files of interest

```text
upload_and_run_sdc2.bat                      main one-click runner
sdc2_serial_logger.py                        serial CSV logger
sdc2_postprocess_fullchar.py                 event-based plots and summaries
sdc2_allan_analysis.py                       Allan deviation analysis and figures
SDC2_TestRunner_Menu_16u/                    Arduino sketch for 16 ustep
SDC2_TestRunner_Menu_256u/                   Arduino sketch for 256 ustep
reference/allan/                             Allan deviation reference PDFs
reference/SDC2_256ustep_TI_Style_Report...  prior 256 ustep review PDF
```

## GUI launcher

A simple Tkinter UI is included:

```text
launch_sdc2_ui.bat
```

The UI can:

```text
select 16 or 256 microstep firmware
compile/upload with arduino-cli
run D/S/P/H/N/A commands
save raw CSVs under SDC2_GUI_results
run event-based postprocessing
run Allan deviation analysis
open the output folder
```

Recommended order:

```text
1. Set physical R725 DIP switches to match 16 or 256 microstep selection.
2. Open launch_sdc2_ui.bat.
3. Select microstep firmware.
4. Click Compile + upload.
5. Run D first, then S/P/H/N, then A only after the smaller tests behave.
```

## GUI telemetry console update

Launch with:

```text
launch_sdc2_ui.bat
```

The GUI now includes:

- Live Log tab for serial output.
- Live Plots tab with rolling encoder/table position vs time and commanded/measured speed vs time.
- Summary tab with sample count, elapsed time, latest/mean speed, RMS position error, warnings, state, and fault code.
- Buttons to open the last raw CSV, live metadata/log file, plots folder, last run folder, and package root.
- Rolling telemetry buffer limited to the last 5,000 parsed CSV rows so Tkinter does not lag during long runs.
- Live plots are only a sanity check. Final figures are still generated from the saved raw CSV by the event postprocessor and Allan analysis scripts.

Recommended flow:

```text
1. Select the microstep firmware that matches the R725 DIP switches.
2. Compile + upload.
3. Run D first and watch the live plots.
4. Run S, P, H, or N individually.
5. Run A only after the smaller tests behave.
6. Use Open last CSV / Open plots folder to inspect outputs immediately.
```

## Serial read crash fix note

If Windows reports `ClearCommError failed` during a run, the logger now saves any captured rows as a partial CSV instead of discarding the data. This usually means the Arduino reset/disconnected or another process touched the COM port while the run was active. If this occurs, reset/power-cycle the Arduino/driver before starting another test.

## Trial length profiles

The GUI has a **Trial length** dropdown:

```text
super_short = fastest debug timing
medium      = partial characterization timing
full        = official/final timing
```

The GUI sends a profile command before the test command:

```text
L = super_short
M = medium
F = full
```

Then it sends the selected test command (`D`, `S`, `P`, `H`, `N`, or `A`). Details are in `docs/trial_length_profiles.md`.

## Host/target safety update

The current package uses a target/host model:

- Arduino target owns motion timing, test sequencing, encoder counting, and safety stop.
- Python host configures tests, sends a heartbeat, logs telemetry, plots rolling previews, and runs offline analysis.
- Telemetry rate is selectable: 10, 20, 50, or 100 Hz.
- The logger sends a heartbeat ping during active runs; if the target loses heartbeat for about 2 s, firmware enters `FAULT_HOST_TIMEOUT` and stops motion.

See `docs/host_target_architecture.md`.


## ISR real-time rewrite

See `docs/full_isr_realtime_rewrite_notes.md`. This build uses a target-side ISR STEP generator, 1 kHz control/profile tick, preserved GUI-compatible CSV columns, and appended real-time diagnostic columns.
