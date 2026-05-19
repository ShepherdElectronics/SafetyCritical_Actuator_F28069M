# 03 - System Requirements

| ID | Requirement | Verification |
|---|---|---|
| SYS-REQ-001 | The system shall receive actuator commands over SCI/UART. | `sci_rx_echo_log.txt`, `final_verification_log.txt` |
| SYS-REQ-002 | The system shall transmit controller telemetry over SCI/UART. | serial logs |
| SYS-REQ-003 | The system shall generate a PWM actuator-command output on ePWM1A/GPIO0. | PWM scope captures |
| SYS-REQ-004 | The system shall force the PWM output safe-low at startup. | `00_rst_ready_safe_low.png` |
| SYS-REQ-005 | The system shall force the PWM output safe-low when disabled. | disable captures |
| SYS-REQ-006 | The system shall force the PWM output safe-low during fault-latched operation. | fault/invalid/timeout captures |
| SYS-REQ-007 | The system shall reject invalid setpoints outside 0-1000. | `10_en1500_invalid_setpoint_safe_low.png` |
| SYS-REQ-008 | The system shall latch safety faults until reset while disabled. | final verification log, `reset_while_enabled_log.txt` |
| SYS-REQ-009 | The system shall detect stale command input using CPU Timer0 time. | timeout log/video/capture |
| SYS-REQ-010 | The system shall report state, fault, enable status, setpoint, PWM percent, age, sequence, and latch status. | serial logs |
| SYS-REQ-011 | The system shall be testable on a low-power bench setup without a real actuator. | hardware setup and evidence |
| SYS-REQ-012 | The system shall reject unknown or malformed serial commands without producing active actuator output. | `unknown_command_log.txt` |
