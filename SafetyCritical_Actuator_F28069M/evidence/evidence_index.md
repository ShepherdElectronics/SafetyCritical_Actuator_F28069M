# Evidence Index

This package contains final verification evidence for the C2000 safety-critical actuator command controller.

## Serial Logs

Place `.txt` serial logs here:

```text
evidence/serial_logs/
```

Expected files:

- `startup_log.txt`
- `sci_rx_echo_log.txt`
- `parser_state_machine_log.txt`
- `cpu_timer_timeout_log.txt`
- `final_verification_log.txt`
- `reset_while_enabled_log.txt`
- `unknown_command_log.txt`

## Visual Evidence

Place all oscilloscope screenshots and verification videos here:

```text
evidence/scope_captures/
```

Expected files:

- `00_rst_ready_safe_low.png`
- `01_en250_pwm_25pct.png`
- `02_dis_after_25_safe_low.png`
- `03_en500_pwm_50pct.png`
- `04_dis_after_50_safe_low.png`
- `05_en750_pwm_75pct.png`
- `05b_en750_pwm_75pct_alternate.png`
- `06_dis_after_75_safe_low.png`
- `07_en500_before_fault_pwm_50pct.png`
- `08_flt_sensor_fault_safe_low.png`
- `09_rst_after_fault_safe_low.png`
- `10_en1500_invalid_setpoint_safe_low.png`
- `11_rst_after_invalid_setpoint_safe_low.png`
- `12_en500_before_timeout_pwm_50pct.png`
- `13_cpu_timer_timeout_safe_low.png`
- `14_final_verification_scope_and_serial.mp4`
- `15_cpu_timer_timeout_transition.mp4`

## Evidence Coverage

| Behavior | Expected Evidence |
|---|---|
| Startup safe state | `startup_log.txt`, `00_rst_ready_safe_low.png` |
| SCI RX command handling | `sci_rx_echo_log.txt` |
| Parser/state-machine behavior | `parser_state_machine_log.txt` |
| 25% PWM scaling | `01_en250_pwm_25pct.png` |
| Disable after 25% command | `02_dis_after_25_safe_low.png` |
| 50% PWM scaling | `03_en500_pwm_50pct.png` |
| Disable after 50% command | `04_dis_after_50_safe_low.png` |
| 75% PWM scaling | `05_en750_pwm_75pct.png`, optional `05b_en750_pwm_75pct_alternate.png` |
| Disable after 75% command | `06_dis_after_75_safe_low.png` |
| Active PWM before fault injection | `07_en500_before_fault_pwm_50pct.png` |
| Fault command safe-low | `08_flt_sensor_fault_safe_low.png` |
| Reset after fault | `09_rst_after_fault_safe_low.png` |
| Invalid setpoint safe-low | `10_en1500_invalid_setpoint_safe_low.png` |
| Reset after invalid setpoint | `11_rst_after_invalid_setpoint_safe_low.png` |
| Active PWM before timeout | `12_en500_before_timeout_pwm_50pct.png` |
| CPU Timer0 timeout safe-low | `cpu_timer_timeout_log.txt`, `13_cpu_timer_timeout_safe_low.png`, `15_cpu_timer_timeout_transition.mp4` |
| Reset while enabled negative test | `reset_while_enabled_log.txt` |
| Unknown/malformed command handling | `unknown_command_log.txt` |
| Final integrated sequence | `final_verification_log.txt`, `14_final_verification_scope_and_serial.mp4` |

## Review Note

The numbered visual evidence follows the same order as the automated verification command sequence. The serial logs provide the command/telemetry record, while the PNG and MP4 files provide oscilloscope evidence that the ePWM1A/GPIO0 actuator-command output transitions correctly between commanded PWM and safe-low states.

The two remaining robustness tests are serial-only unless additional scope evidence is desired.
