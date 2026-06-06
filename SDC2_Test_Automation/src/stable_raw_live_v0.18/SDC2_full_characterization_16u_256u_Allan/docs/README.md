# SDC2 full characterization package - 16 microsteps

This package is for the Arduino GIGA + R725 + 4118 geared stepper + E5 encoder + AM26LS32 SDC2 setup at **16 microsteps**.

## Hardware setting

Set the R725 DIP switches for **16 microsteps**:

| Microstep | SW1 | SW2 | SW3 | SW4 | Pulses / motor rev |
|---:|---|---|---|---|---:|
| 16 uSTEP | D | D | U | U | 3,200 |

The firmware constant is already set to:

```cpp
const double MICROSTEP_SETTING = 16.0;
```

## Current pin map

| Signal | Arduino GIGA pin | Notes |
|---|---:|---|
| STEP | D10 | R725 STEP input |
| DIR | D13 | R725 DIR input |
| Encoder A | D2 | AM26LS32 output, interrupt |
| Encoder B | D3 | AM26LS32 output |
| Encoder Z | D4 | optional index, logged |
| 5V | 5V | AM26LS32 / R725 logic rail |
| GND | GND | common logic ground |

## What is included

- `arduino/SDC2_FullChar_16u/SDC2_FullChar_16u.ino`  
  Firmware for static, constant-speed, 10-50 deg/s, and sine tests at 16 microsteps.

- `python/sdc2_serial_logger.py`  
  Serial logger that sends a test command to the Arduino and saves raw CSV.

- `python/sdc2_postprocess_fullchar.py`  
  Postprocessor that creates cleaned CSVs, per-segment summaries, event timing plots, speed-ratio plots, RMS speed/error tables, and one output folder.

- `matlab/Plot_All_SDC2_Event_Timing_Final_OneFolder.m`  
  MATLAB event-based encoder plotter, adapted from the prior 256-ustep analysis.

- `matlab/Analyze_SDC2_Full_Characterization_16u.m`  
  MATLAB summary plotting for full characterization.

- `docs/SDC2_16ustep_test_plan.md`  
  Recommended test flow.

- `docs/SDC2_16ustep_quick_start.md`  
  Step-by-step run instructions.

## Recommended run order

1. Set R725 to 16 ustep: SW1 D, SW2 D, SW3 U, SW4 U.
2. Upload the Arduino sketch.
3. Run a short debug test first.
4. Run the official protocol speeds.
5. Run the 10-50 deg/s extension.
6. Run sine tests only after constant-speed motion is sane.
7. Postprocess data with Python or MATLAB.

## Important analysis note

The event-speed analysis uses raw encoder count transitions. It does **not** apply filtering, smoothing, or grouped averaging unless explicitly stated in the generated summary plots.
