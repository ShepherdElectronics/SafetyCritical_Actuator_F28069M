# Safety-Critical Actuator Command Controller - TI C2000 F28069M

## Overview

This project is a hardware-backed embedded safety demonstration built on a TI C2000 F28069M LaunchPad.

The firmware receives SCI/UART commands, executes an explicit safety state machine, drives an ePWM actuator-command output on GPIO0/ePWM1A, validates setpoints, latches faults, forces output safe-low during disable/fault/invalid/timeout conditions, and reports telemetry for verification evidence.

This project is **not certified** to DO-178C, ISO 26262, ARP4754, or ARP4761. It is **standards-inspired**: it borrows the lifecycle structure, traceability discipline, safety-analysis mindset, and evidence orientation from those standards and applies them to a compact embedded-controls demonstrator.

## Implemented Behaviors

- SCI/UART command input
- Serial telemetry output
- Explicit states: `INIT`, `SELF_TEST`, `READY`, `RUN`, `FAULT_LATCHED`, `SAFE_SHUTDOWN`
- Fault codes: `NONE`, `INVALID_SETPOINT`, `SENSOR_FAULT`, `COMMS_TIMEOUT`, `SELF_TEST_FAILED`, `UNKNOWN_COMMAND`
- ePWM1A / GPIO0 actuator-command output
- Valid setpoint mapping:
  - `EN,250` -> 25% PWM
  - `EN,500` -> 50% PWM
  - `EN,750` -> 75% PWM
- Disable command forces output safe-low
- Fault command latches fault and forces output safe-low
- Invalid setpoint latches fault and forces output safe-low
- CPU Timer0 communication timeout latches `COMMS_TIMEOUT` and forces output safe-low
- Python serial tools for manual and automated verification
- Documentation package: requirements, hazard analysis, architecture, state machine, traceability, verification plan, test results, release checklist, and evidence index

## Project Structure

```text
SafetyCritical_Actuator_F28069M/
├── README.md
├── README_UPLOAD.md
├── PROJECT_TREE.txt
├── docs/
├── src/
│   └── main.c
├── tools/
├── ccs_notes/
└── evidence/
    ├── evidence_index.md
    ├── serial_logs/
    └── scope_captures/
```

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

Then the controller is left without a new command until CPU Timer0 timeout occurs.

## Telemetry Example

```text
STATE=RUN,FAULT=NONE,EN=1,SP=500,PWM=50,AGE=0,SEQ=3,LATCH=0
STATE=FAULT_LATCHED,FAULT=COMMS_TIMEOUT,EN=0,SP=0,PWM=0,AGE=3000,SEQ=12,LATCH=1
```

## Evidence Summary

Visual evidence is stored in:

```text
evidence/scope_captures/
```

Serial evidence is stored in:

```text
evidence/serial_logs/
```

The numbered visual evidence follows the command sequence:

```text
00_rst_ready_safe_low.png
01_en250_pwm_25pct.png
02_dis_after_25_safe_low.png
03_en500_pwm_50pct.png
04_dis_after_50_safe_low.png
05_en750_pwm_75pct.png
05b_en750_pwm_75pct_alternate.png
06_dis_after_75_safe_low.png
07_en500_before_fault_pwm_50pct.png
08_flt_sensor_fault_safe_low.png
09_rst_after_fault_safe_low.png
10_en1500_invalid_setpoint_safe_low.png
11_rst_after_invalid_setpoint_safe_low.png
12_en500_before_timeout_pwm_50pct.png
13_cpu_timer_timeout_safe_low.png
14_final_verification_scope_and_serial.mp4
15_cpu_timer_timeout_transition.mp4
```

## Build Notes

This project was developed in Code Composer Studio for the TI C2000 F28069M using controlSUITE F2806x device-support files.

The upload package intentionally excludes the full CCS workspace because CCS projects commonly contain machine-specific linked paths, generated objects, debugger state, and local workspace metadata. The portable package includes the source code, documentation, Python verification tools, build notes, and evidence structure.

See `ccs_notes/build_notes.md`.
