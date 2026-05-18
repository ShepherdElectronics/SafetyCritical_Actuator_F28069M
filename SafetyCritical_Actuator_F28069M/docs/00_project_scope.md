# 00 - Project Scope

## Project Title

**Safety-Critical Actuator Command Controller - TI C2000 F28069M**

## Purpose

This project demonstrates a compact, hardware-backed safety-critical embedded-controls workflow on TI C2000 hardware.

The controller receives SCI/UART commands, validates command data, generates an ePWM actuator-command output, latches faults, forces the output safe-low during disable/fault/invalid/timeout conditions, and reports telemetry for verification evidence.

This project is **not certified** to DO-178C, ISO 26262, ARP4754, or ARP4761. It is **standards-inspired**: it borrows the lifecycle structure, traceability discipline, safety-analysis mindset, and objective-evidence orientation from those standards and applies them to a focused embedded-controls demonstrator.

## Item Definition

The item is a commanded actuator interface implemented on a TI C2000 F28069M LaunchPad.

```text
PC serial command source
        |
        v
C2000 SCI parser
        |
        v
Safety state machine
        |
        v
ePWM1A/GPIO0 actuator-command output
        ^
        |
CPU Timer0 timeout monitor
```

The PWM output is treated as a low-power actuator-command signal only. It is measured on an oscilloscope or logic analyzer and is not connected to a real actuator, motor driver, inverter, or high-energy system.

## Version 1 Scope

| Feature | Included |
|---|---|
| TI C2000 F28069M firmware | Yes |
| SCI/UART command input | Yes |
| SCI/UART telemetry output | Yes |
| ePWM1A / GPIO0 actuator-command output | Yes |
| Explicit safety state machine | Yes |
| Setpoint validation | Yes |
| Fault-latched safe shutdown | Yes |
| CPU Timer0 communication timeout | Yes |
| Python verification tools | Yes |
| Serial log evidence | Yes |
| Scope/photo/video visual evidence | Yes |
| CAN transport | No, future work |
| RTOS | No, future work |
| Real actuator or motor drive | No, future work |
| Certification claim | No |

## Completed Safety Behaviors

| Behavior | Status |
|---|---|
| Startup safe-low | Verified |
| SCI command receive | Verified |
| Parser/state-machine telemetry | Verified |
| 25/50/75% PWM scaling | Verified |
| Disable safe-low | Verified |
| Fault safe-low | Verified |
| Invalid setpoint safe-low | Verified |
| CPU Timer0 timeout safe-low | Verified |
| Final integrated verification run | Verified |

## Success Criteria

Version 1 is complete when the following evidence exists:

| Criterion | Expected Evidence |
|---|---|
| Startup defaults to safe-low | Startup serial log and safe-low capture |
| Valid command produces proportional PWM | 25/50/75% scope captures |
| Disable command forces safe-low | Disable serial telemetry and safe-low capture |
| Fault command latches fault and forces safe-low | Fault telemetry and safe-low capture |
| Invalid setpoint latches fault and forces safe-low | Invalid-setpoint telemetry and safe-low capture |
| CPU Timer0 timeout latches fault and forces safe-low | Timeout serial log, timeout image/video |
| Requirements trace to tests/evidence | Traceability matrix |
