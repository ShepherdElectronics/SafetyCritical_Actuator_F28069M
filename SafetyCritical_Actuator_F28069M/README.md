# Safety-Critical Actuator Command Controller - TI C2000 F28069M

## Overview

This project is a hardware-backed embedded safety demonstration built on a TI C2000 F28069M LaunchPad.

The firmware receives SCI/UART commands, executes an explicit safety state machine, drives an ePWM actuator-command output on GPIO0/ePWM1A, validates setpoints, rejects malformed commands, latches faults, forces output safe-low during disable/fault/invalid/timeout conditions, and reports telemetry for verification evidence.

This project is **not certified** to DO-178C, ISO 26262, ARP4754, or ARP4761. It is **standards-inspired**: it borrows the lifecycle structure, traceability discipline, safety-analysis mindset, and evidence orientation from those standards and applies them to a compact embedded-controls demonstrator.

## Implemented Behaviors

- SCI/UART command input
- Serial telemetry output
- Explicit states: `INIT`, `SELF_TEST`, `READY`, `RUN`, `FAULT_LATCHED`
- Fault codes: `NONE`, `INVALID_SETPOINT`, `SENSOR_FAULT`, `COMMS_TIMEOUT`, `SELF_TEST_FAILED`, `UNKNOWN_COMMAND`
- ePWM1A / GPIO0 actuator-command output
- Valid setpoint mapping:
  - `EN,250` -> 25% PWM
  - `EN,500` -> 50% PWM
  - `EN,750` -> 75% PWM
- Disable command forces output safe-low
- Fault command latches fault and forces output safe-low
- Invalid setpoint latches fault and forces output safe-low
- Unknown/malformed command latches `UNKNOWN_COMMAND` and forces output safe-low
- CPU Timer0 communication timeout latches `COMMS_TIMEOUT` and forces output safe-low
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
```

Additional serial-only robustness tests:

```text
RST,0
EN,500,14
RST,15
FOO,123
EN,
```

## Evidence Summary

Visual evidence is stored in `evidence/scope_captures/`.

Serial evidence is stored in `evidence/serial_logs/`.

Add these two final robustness logs:

```text
reset_while_enabled_log.txt
unknown_command_log.txt
```
