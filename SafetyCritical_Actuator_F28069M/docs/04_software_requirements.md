# 04 - Software Requirements

| ID | Requirement | Verification |
|---|---|---|
| SW-REQ-001 | Firmware shall initialize system clock, GPIO, PIE, SCI, ePWM1, and CPU Timer0 before normal operation. | startup log |
| SW-REQ-002 | Firmware shall default to zero PWM output at startup. | `00_rst_ready_safe_low.png` |
| SW-REQ-003 | Firmware shall implement states INIT, SELF_TEST, READY, RUN, FAULT_LATCHED, and SAFE_SHUTDOWN. | final log |
| SW-REQ-004 | Firmware shall parse `EN,setpoint,seq` commands. | parser/final logs |
| SW-REQ-005 | Firmware shall parse `DIS,seq` commands. | final log and disable captures |
| SW-REQ-006 | Firmware shall parse `RST,seq` commands. | final log |
| SW-REQ-007 | Firmware shall parse `FLT,seq` commands. | final log and fault capture |
| SW-REQ-008 | Firmware shall reject setpoints below 0 or above 1000. | invalid setpoint log/capture |
| SW-REQ-009 | Firmware shall map setpoint 0-1000 to PWM percent 0-100. | 25/50/75% captures |
| SW-REQ-010 | Firmware shall force PWM safe-low when disabled. | disable captures |
| SW-REQ-011 | Firmware shall force PWM safe-low in FAULT_LATCHED. | fault/invalid/timeout captures |
| SW-REQ-012 | Firmware shall latch INVALID_SETPOINT on invalid EN command. | invalid setpoint log/capture |
| SW-REQ-013 | Firmware shall latch SENSOR_FAULT on FLT command. | fault log/capture |
| SW-REQ-014 | Firmware shall latch COMMS_TIMEOUT when command age exceeds COMMS_TIMEOUT_MS while RUN is active. | timeout log/video/capture |
| SW-REQ-015 | Firmware shall reset a latched fault only when disabled. | final log |
| SW-REQ-016 | Firmware shall report telemetry after each processed command. | serial logs |
| SW-REQ-017 | Firmware shall report heartbeat telemetry once per second. | final log |
| SW-REQ-018 | Firmware shall preserve the last accepted sequence number in telemetry. | final log |
