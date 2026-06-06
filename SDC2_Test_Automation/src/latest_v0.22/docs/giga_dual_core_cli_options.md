# Arduino GIGA dual-core CLI settings used by this package

The test machine reported these menu options from:

```text
arduino-cli board details -b arduino:mbed_giga:giga
```

```text
Option: Flash split   split
  split=100_0   2MB M7 + M4 in SDRAM
  split=75_25   1.5MB M7 + 0.5MB M4
  split=50_50   1MB M7 + 1MB M4

Option: Target core   target_core
  target_core=cm7   Main Core
  target_core=cm4   M4 Co-processor

Option: Security setting   security
  security=none
```

This package defaults to:

```text
M7 FQBN: arduino:mbed_giga:giga:split=75_25,target_core=cm7,security=none
M4 FQBN: arduino:mbed_giga:giga:split=75_25,target_core=cm4,security=none
```

Upload order for dual-core buffered operation:

```text
1. Compile/upload M4 worker
2. Compile/upload selected M7 target firmware
3. Reset board
4. Launch GUI and run super_short D first
```

Role split:

| Core | Role |
|---|---|
| M7 | deterministic target-side control, state machine, safety, live telemetry |
| M4 | buffered DAQ worker scaffold / future high-rate raw capture support |
| PC host | GUI, upload automation, live visualization, CSV saving, offline analysis |

The current dual-core build is a staged implementation: the M4 worker scaffold is included and uploadable. The next validation step is confirming inter-core RPC/raw-buffer transfer on hardware and then moving high-rate raw capture into the M4 worker.

## M4 CLI compile/link workaround in V2

If the M4 worker compile fails with errors similar to:

```text
undefined reference to `digitalPinToPinName(unsigned char)'
undefined reference to `main'
```

the M4 worker in this package uses a minimal explicit `main()` and avoids USB Serial/pin I/O on M4. This matches the intended architecture: M7 owns USB/host communications and all actuator I/O, while M4 acts only as a buffered worker reached through RPC.

Arduino's GIGA dual-core documentation notes that M4 does not directly support USB Serial and that Serial-over-USB must be routed through RPC if needed. For this project, M4 should not print to USB; it should only expose RPC functions for buffering/status.
