# SDC2 Full ISR Real-Time Target Rewrite

This package is based on the last stable 50 Hz live-plot build, but the Arduino target firmware has been rewritten so STEP generation is no longer performed in the foreground logging/control loop.

## Target changes

- STEP pulse generation moved to a 100 kHz mbed `Ticker` ISR.
- STEP rate is commanded as a signed milli-Hz setpoint.
- Foreground motion profile updates run at a fixed 1 kHz control tick.
- Serial telemetry is rate-limited and droppable. It no longer catches up by blocking motion.
- Segment transitions reset profile speed, step rate, counters, telemetry drops, and control tick miss counters.
- Direction changes include a short settle delay before the step-rate command is enabled.
- Host heartbeat/deadman support is retained.
- STOP / X support is retained.

## CSV compatibility

The old first 24 columns are preserved so the GUI live plots and postprocessing stay compatible. New real-time diagnostic columns are appended:

- `CommandTableSpeed_deg_s`
- `ProfileSpeed_deg_s`
- `StepCommandSpeed_deg_s`
- `TelemetryDrops`
- `ControlTickMisses`
- `StepISR_Hz`

## Recommended first run

Use:

```text
Trial length: super_short
Telemetry: 50 Hz
DIR polarity: normal
Command: D
```

Then inspect live plots and the CSV. If live plots appear and the direction is correct, proceed to `P` protocol.

## Important

This is a bare-metal ISR/cooperative target architecture, not an RTOS. The host GUI is still non-real-time and should only configure, monitor, log, and analyze.
