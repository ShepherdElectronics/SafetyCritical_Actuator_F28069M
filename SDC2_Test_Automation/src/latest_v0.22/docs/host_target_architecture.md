# SDC2 Host/Target Architecture

This package now treats the Arduino as the **target** and the Windows/Python GUI as the **host**.

## Target: Arduino GIGA firmware

The target owns motion and safety:

| Feature | Purpose |
|---|---|
| Internal test state machine | Runs D/S/P/H/N/A locally without PC timing. |
| Nonblocking STEP generation loop | Keeps motion timing independent of GUI speed. |
| Encoder ISR independent of printing | Keeps encoder counting separate from telemetry. |
| Telemetry rate limiter | Selectable 10, 20, 50, or 100 Hz serial output. |
| Telemetry is lower priority than motion | Motion timing and STOP handling are serviced before logging. |
| Segment-complete markers | Host can stop logging cleanly at end of each mode. |
| Host heartbeat/deadman | If host disappears for about 2 s, target stops motion and faults. |
| STOP command always serviced | `X` stops motion immediately. |
| Partial-run compatibility | Captured rows remain useful even if serial disconnects. |

## Host: Python GUI/logger

The host owns configuration, visibility, and analysis:

| Feature | Purpose |
|---|---|
| Sends config before test | Microstep firmware, trial length, telemetry rate. |
| Sends one start command | D/S/P/H/N/A starts the target-owned state machine. |
| Sends heartbeat | `.` ping every ~0.5 s while logging. |
| Reads serial without pacing target | Host receives telemetry; target does not wait on plots. |
| Rolling plots only | GUI keeps last 5000 samples to avoid lag. |
| Saves raw telemetry | CSV rows are saved for postprocessing. |
| Recognizes completion markers | Logger closes cleanly at single-test completion. |
| Preserves partial CSVs | Serial crashes still preserve captured rows. |
| Validates CSV before analysis | Prevents empty/no-header postprocess failures. |

## Recommended telemetry rate

| Test type | Recommended telemetry |
|---|---:|
| First debug / high-speed motion | 10 or 20 Hz |
| Protocol motion | 20 or 50 Hz |
| Static Allan test | 50 or 100 Hz |
| Final run if stable | 50 Hz for motion, 100 Hz for static |

The key design rule is:

```text
motion timing > stop/safety > encoder counting > telemetry printing > live plotting
```

