# Dual-core buffered capture plan for Arduino GIGA

## Goal

Use the GIGA dual-core MCU as a Tier-2-style host/target test architecture before designing a custom board.

- **M7 core:** deterministic real-time control target. It owns actuator command timing, profile/state-machine updates, feedback correction, safety, STOP/deadman behavior, and segment timing.
- **M4 core:** acquisition/logging worker. It receives compact raw samples, stores them in a ring buffer, counts drops, and later supports post-segment dumps.
- **PC host:** GUI, live preview, data storage, postprocessing, Allan/stability analysis.

## Why this is the next step

The current USB live telemetry path is useful for sanity checking, but it should not be the primary high-rate measurement path. The target should collect high-rate raw data locally while the live GUI receives a lower-rate preview. After a segment ends, the raw buffer can be dumped over USB without affecting motion.

## Included in this package

- `SDC2_RawBuffer_M4/SDC2_RawBuffer_M4.ino` — M4 buffered DAQ worker scaffold using Arduino RPC bindings.
- `SDC2_TestRunner_Menu_16u_DualCore_M7/` — M7 real-time target sketch folder for 16 microstep testing.
- `SDC2_TestRunner_Menu_256u_DualCore_M7/` — M7 real-time target sketch folder for 256 microstep testing.
- GUI architecture selector: `single_core` or `dual_core_m7_m4`.
- GUI buttons to compile/upload M4 worker and to compile/upload M4 + selected M7 target.

## Important limitation

The M4 sketch is a scaffold. The final high-rate production path should be validated on hardware. Per-sample RPC may be too slow for 1 kHz+ raw capture; if so, move to a shared-memory or lock-free buffer design. The rule remains: **M7 must never block waiting for M4**. If the M4 buffer is full, samples are dropped and a drop counter increments.

## Recommended first test

1. Select `dual_core_m7_m4` in the GUI.
2. Verify or edit the M4 FQBN. If compile fails, run `arduino-cli board listall` and select the GIGA M4 board identifier.
3. Compile/upload the M4 worker.
4. Compile/upload the selected M7 target.
5. Run `D` with `super_short` and 50 Hz live telemetry.
6. Confirm live telemetry still works exactly like the single-core version.

Only after that should the M7 target begin pushing compact raw samples to the M4 worker during segments.

## Compact raw sample format

Use integers, not CSV strings, while the segment is running:

```cpp
struct RawSample {
  uint32_t t_us;
  int32_t encoder_count;
  int32_t position_mdeg;
  int32_t target_mdeg_s;
  int32_t profile_mdeg_s;
  int32_t measured_mdeg_s;
  uint16_t state_id;
  uint16_t flags;
};
```

At roughly 28 bytes/sample:

| Raw rate | 60 s samples | Approx memory |
|---:|---:|---:|
| 100 Hz | 6,000 | 168 kB |
| 500 Hz | 30,000 | 840 kB |
| 1 kHz | 60,000 | 1.68 MB |

## Engineering rule

Live telemetry is for the operator. Buffered raw capture is for the science. The GUI should not need every sample in real time.
