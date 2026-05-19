# 05 - Hazard Analysis

## Safety Goals

| Safety Goal | Description |
|---|---|
| SG-001 | Prevent stale commands from maintaining active actuator output. |
| SG-002 | Prevent invalid setpoints from producing excessive output. |
| SG-003 | Force output safe-low during disabled and faulted operation. |
| SG-004 | Prevent automatic restart or safety bypass after a fault. |
| SG-005 | Provide telemetry sufficient for verification and diagnosis. |
| SG-006 | Prevent malformed or unknown serial input from causing undefined actuator behavior. |

## Hazard Table

| Hazard ID | Hazard | Cause | Effect | Mitigation | Evidence |
|---|---|---|---|---|---|
| HAZ-001 | Stale command keeps output active | Host stops sending commands | Actuator command persists | CPU Timer0 command timeout | `13_cpu_timer_timeout_safe_low.png`, timeout video/log |
| HAZ-002 | Excessive output command | Invalid setpoint accepted | Excessive duty cycle | Range check and INVALID_SETPOINT fault | `10_en1500_invalid_setpoint_safe_low.png` |
| HAZ-003 | Output active during disable | Disable not enforced | Unexpected output | Force safe-low on DIS | `02`, `04`, `06` disable captures |
| HAZ-004 | Output active during fault | Fault does not control PWM | Unsafe output remains active | Fault-latched safe-low | `08_flt_sensor_fault_safe_low.png` |
| HAZ-005 | Unexpected restart or reset bypass after fault | Reset command handled without safety conditions | Uncommanded reactivation or fault-clear while enabled | Reset only while disabled; reset while enabled does not bypass active safety behavior | `reset_while_enabled_log.txt`, final log |
| HAZ-006 | Poor diagnosability | Missing state/fault data | Verification ambiguity | Structured telemetry | serial logs |
| HAZ-007 | Unsafe startup | PWM active before initialization | Output active at boot | Startup safe-low | `00_rst_ready_safe_low.png` |
| HAZ-008 | Malformed serial command causes undefined behavior | Unknown command, incomplete command, garbage input | Parser ambiguity or unintended output | Reject malformed/unknown command, latch UNKNOWN_COMMAND, force safe-low | `unknown_command_log.txt` |

## Derived Safety Requirements

| Derived Requirement | Source Hazard |
|---|---|
| Timeout shall latch COMMS_TIMEOUT and force PWM=0 | HAZ-001 |
| Invalid setpoint shall latch INVALID_SETPOINT and force PWM=0 | HAZ-002 |
| DIS shall force PWM=0 | HAZ-003 |
| FLT shall latch SENSOR_FAULT and force PWM=0 | HAZ-004 |
| RST shall clear fault only while disabled and shall not bypass safety behavior while enabled | HAZ-005 |
| Telemetry shall show state/fault/EN/SP/PWM/AGE/SEQ/LATCH | HAZ-006 |
| Unknown or malformed serial input shall latch UNKNOWN_COMMAND and force PWM=0 | HAZ-008 |
