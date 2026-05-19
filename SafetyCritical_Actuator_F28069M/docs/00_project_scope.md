# 00 - Project Scope

## Purpose

This project demonstrates a compact, hardware-backed safety-critical embedded-controls workflow on TI C2000 hardware.

The controller receives SCI/UART commands, validates command data, generates an ePWM actuator-command output, latches faults, rejects malformed commands, forces the output safe-low during disable/fault/invalid/timeout conditions, and reports telemetry for verification evidence.

## Item Definition

```text
PC serial command source -> C2000 SCI parser -> safety state machine -> ePWM1A/GPIO0 output
                                      ^
                                      |
                              CPU Timer0 timeout monitor
```

The PWM output is treated as a low-power actuator-command signal only. It is measured on a scope or logic analyzer and is not connected to a real actuator or power stage.

## Version 1 Scope

| Feature | Included |
|---|---|
| TI C2000 F28069M firmware | Yes |
| SCI/UART command input | Yes |
| SCI/UART telemetry output | Yes |
| ePWM1A / GPIO0 actuator-command output | Yes |
| Explicit state machine | Yes |
| Setpoint validation | Yes |
| Malformed/unknown command rejection | Yes |
| Fault-latched safe shutdown | Yes |
| CPU Timer0 communication timeout | Yes |
| Serial/scope/video evidence | Yes |
| CAN transport | No, future work |
| RTOS | No, future work |
| Real actuator drive | No, future work |
| Certification claim | No |

## Success Criteria

| Criterion | Expected Evidence |
|---|---|
| Startup defaults to safe-low | Startup serial log and safe-low capture |
| Valid command produces proportional PWM | 25/50/75% scope captures |
| Disable command forces safe-low | Disable serial telemetry and safe-low capture |
| Fault command latches fault and forces safe-low | Fault telemetry and safe-low capture |
| Invalid setpoint latches fault and forces safe-low | Invalid-setpoint telemetry and safe-low capture |
| CPU Timer0 timeout latches fault and forces safe-low | Timeout serial log, timeout image/video |
| Reset while enabled does not bypass active safety behavior | `reset_while_enabled_log.txt` |
| Unknown/malformed commands fault safely | `unknown_command_log.txt` |
| Requirements trace to tests/evidence | Traceability matrix |
