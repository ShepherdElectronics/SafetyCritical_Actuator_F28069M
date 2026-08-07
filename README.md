# Safety-Critical Actuator Command Controller - TI C2000 F28069M

## Overview

This project is a hardware-backed embedded safety demonstration built on a TI C2000 F28069M LaunchPad.

The firmware receives SCI/UART commands, executes an explicit safety state machine, drives an ePWM actuator-command output on GPIO0/ePWM1A, validates setpoints, rejects malformed commands, latches faults, forces output safe-low during disable/fault/invalid/timeout conditions, and reports telemetry for verification evidence.

This project is **not certified** to DO-178C, ISO 26262, ARP4754, or ARP4761. It is **standards-inspired**: it borrows the lifecycle structure, traceability discipline, safety-analysis mindset, and evidence orientation from those standards and applies them to a compact embedded-controls demonstrator.

## Implemented Behaviors

- SCI/UART command input
- Serial telemetry output
- Explicit states: `INIT`, `SELF_TEST`, `READY`, `RUN`, `FAULT_LATCHED`
- Fault codes: `NONE`, `INVALID_SETPOINT`, `SENSOR_FAULT`, `COMMS_TIMEOUT`, `SELF_TEST_FAILED`, `UNKNOWN_COMMAND`, `STALE_SEQUENCE`
- ePWM1A / GPIO0 actuator-command output
- Valid setpoint mapping: every integer setpoint from 0 through 1000 is valid. The firmware quantizes by integer division (`PWM=setpoint/10`) to whole-percent output.
  - `EN,250,sequence` -> 25% PWM
  - `EN,500,sequence` -> 50% PWM
  - `EN,750,sequence` -> 75% PWM
  - `EN,1,sequence` through `EN,9,sequence` -> valid `RUN` with 0% PWM
  - `EN,0,sequence` -> valid `RUN` with explicitly safe-low 0% PWM
  `RUN` means an accepted enabled command, not necessarily a nonzero waveform.
- Disable command forces output safe-low
- Fault command latches fault and forces output safe-low
- Invalid setpoint latches fault and forces output safe-low
- Exact command grammar rejects missing fields, trailing data, overflow, and prefix collisions; malformed input latches `UNKNOWN_COMMAND` and forces output safe-low
- Duplicate or out-of-order sequence values latch `STALE_SEQUENCE` and force output safe-low
- Bounded startup self-test checks initialized safe-state invariants and latches `SELF_TEST_FAILED` if they do not hold
- CPU Timer0 communication timeout latches `COMMS_TIMEOUT` after 100 ms without a valid control command and forces output safe-low
- Python serial tools for manual and automated verification
- Documentation package: requirements, hazard analysis, architecture, state machine, traceability, verification plan, test results, release checklist, and evidence index

## Commands

```text
RST,0
EN,250,1
DIS,2
EN,500,3
DIS,4
EN,750,5
DIS,6
EN,500,7
FLT,8
RST,9
EN,1500,10
RST,11
EN,500,12
EN,500,14
```

Malformed-command examples that must be rejected include `EN,`, `EN,500`, `EN,500,1,extra`, `EN,500,1x`, and `DISASTER,1`. The communication watchdog is refreshed only after an accepted command; `CLR` is not a valid command.


## Evidence Summary

Visual evidence is stored in `evidence/scope_captures/`.

Serial evidence is stored in `evidence/serial_logs/`.

Add these two final robustness logs:

```text
reset_while_enabled_log.txt
unknown_command_log.txt
```
