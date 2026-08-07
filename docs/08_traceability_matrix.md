# 08 - Traceability Matrix

| Requirement | Hazard | Implementation | Verification Evidence | Result |
|---|---|---|---|---|
| SW-REQ-001 | HAZ-007 | init sequence in `main()` | `startup_log.txt` | Pass |
| SW-REQ-002 | HAZ-007 | `Controller_ForceSafeOutput()` | `00_rst_ready_safe_low.png` | Pass |
| SW-REQ-003 | HAZ-003/004 | enum states and transitions | `final_verification_log.txt` | Pass |
| SW-REQ-004 | HAZ-005/008 | exact `parse_en_command()` grammar and numeric conversion | parser and malformed-command evidence | Pending hardware evidence |
| SW-REQ-005 | HAZ-003 | DIS branch | `02`, `04`, `06` safe-low captures | Pass |
| SW-REQ-006 | HAZ-005 | RST branch | final log, `09`, `11` reset captures, `reset_while_enabled_log.txt` | Pending additional log |
| SW-REQ-007 | HAZ-004 | FLT branch | final log, `08_flt_sensor_fault_safe_low.png` | Pass |
| SW-REQ-008 | HAZ-002 | setpoint range check | final log, `10_en1500_invalid_setpoint_safe_low.png` | Pass |
| SW-REQ-009 | HAZ-002 | `Actuator_PWM_SetPercent()` | `01`, `03`, `05` PWM captures | Pass |
| SW-REQ-010 | HAZ-003 | DIS branch and safe output | `02`, `04`, `06` disable captures | Pass |
| SW-REQ-011 | HAZ-004/008 | `Controller_LatchFault()` | `08`, `10`, `13` safe-low captures, `unknown_command_log.txt` | Pending additional log |
| SW-REQ-012 | HAZ-002 | invalid setpoint branch | `10_en1500_invalid_setpoint_safe_low.png` | Pass |
| SW-REQ-013 | HAZ-004 | FLT branch | `08_flt_sensor_fault_safe_low.png` | Pass |
| SW-REQ-014 | HAZ-001 | 100 ms CPU Timer0 + `Controller_CheckTimeout()` | 100 ms timeout capture/log | Pending 100 ms recapture |
| SW-REQ-015 | HAZ-005 | RST while disabled condition | final log, `reset_while_enabled_log.txt` | Pending additional log |
| SW-REQ-016 | HAZ-006 | `Controller_SendTelemetry()` | serial logs | Pass |
| SW-REQ-017 | HAZ-006 | one-second heartbeat | final log | Pass |
| SW-REQ-018 | HAZ-006 | `sequence` telemetry | final log | Pass |
| SW-REQ-019 | HAZ-008 | exact parser rejection path | `unknown_command_log.txt` | Pending additional log |

| SW-REQ-020 | HAZ-007 | Controller_RunSelfTest() | startup/self-test evidence | Pending hardware evidence |
