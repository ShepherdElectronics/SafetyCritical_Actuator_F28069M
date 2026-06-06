# Live Raw Data View

This build adds a raw live-data view in addition to the normal smoothed/firmware speed trace.

## What changed

The GUI now shows:

- `Measured speed (firmware)` — the speed value reported by the target firmware. This may be filtered, averaged, or derived over a firmware window.
- `Raw speed d(pos)/dt` — host-computed row-to-row derivative from consecutive `ActualTablePosition_deg` samples. This is intentionally unsmoothed.
- `Raw encoder count delta / row` — change in `EncoderCount` between consecutive telemetry rows.
- `Raw Live Data` tab — a table of the most recent raw telemetry rows with time, state, direction, encoder count, encoder delta, raw host speed, measured firmware speed, command speed, step rate, and fault field.

## Why this matters

The smoothed speed trace is good for seeing average tracking. The raw trace is better for catching:

- quantization at very low speeds,
- direction/sign mistakes,
- sudden stalls,
- telemetry dropouts,
- actuator command discontinuities,
- state-transition artifacts,
- motion that is happening even when the smoothed speed hides it.

## How to use it

Use the regular `Live Plots` tab for the high-level sanity check. Then open `Raw Live Data` when the smooth speed trace looks suspicious.

For clean raw viewing, start with:

```text
Trial length: super_short
Telemetry: 50 Hz
Command: D
```

At very low speeds, the raw derivative may look choppy because the position feedback changes in discrete counts. That is expected. The raw view is meant to expose this instead of hiding it.
