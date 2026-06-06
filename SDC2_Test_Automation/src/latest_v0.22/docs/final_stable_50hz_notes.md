# SDC2 final stable 50 Hz live-plot package

This package intentionally uses the last stable live-plot / direction-fix architecture rather than the aggressive real-time rewrite.

## Main decision

The stable default telemetry rate is now **50 Hz** because testing showed the commanded-speed spikes disappeared when telemetry was increased to 50 Hz. The package therefore keeps the old GUI-compatible telemetry header and live-plot parser while preserving the useful target/host features.

## Included features

- Tkinter telemetry-console UI launched by `launch_sdc2_ui.bat`
- 16 ustep and 256 ustep firmware options
- Trial length profiles: super_short, medium, full
- Telemetry-rate selector: 10, 20, 50, 100 Hz; default = 50 Hz
- DIR polarity selector: normal/inverted
- Header-missing recovery in the logger
- Serial exception / partial-run preservation
- Live plots using the old stable columns:
  - `Time_s`
  - `ActualTablePosition_deg`
  - `CommandTableSpeed_deg_s` or `TargetSpeed_deg_s` fallback
  - `MeasuredSpeed_deg_s`
  - `State`
  - `FaultCode`
- Event-based postprocessing and Allan deviation analysis

## Real-time strategy kept conservative

The next real-time improvements should be incremental:

1. Keep telemetry at 50 Hz unless serial pressure appears again.
2. Keep old column names for GUI compatibility.
3. Add new diagnostic columns only as aliases, not replacements.
4. Reset command/profile variables at segment boundaries.
5. Break plots by trial/state in postprocessing.
6. Move STEP generation to a hardware timer only after the current target/host setup is stable.

## Recommended first run

```text
Trial length: super_short
Telemetry rate: 50 Hz
DIR polarity: normal
Command: D
```

Then run:

```text
P = protocol constant-speed test
S = static Allan test
H = 10-50 deg/s high-speed extension
```
