# 07 - State Machine

## States

| State | Meaning | PWM |
|---|---|---|
| INIT | Startup initialization | 0 |
| SELF_TEST | Verify initialized controller invariants and ePWM safe-low state | 0 or FAULT_SELF_TEST_FAILED |
| READY | Healthy, disabled, waiting for enable | 0 |
| RUN | Enabled, valid command accepted | commanded PWM, including explicitly safe-low 0% for setpoints 0-9 |
| FAULT_LATCHED | Fault latched, reset required | 0 |

## Transition Table

| Current State | Event | Next State | Output |
|---|---|---|---|
| INIT | init complete | SELF_TEST | 0 |
| SELF_TEST | pass | READY | 0 |
| SELF_TEST | invariant failure | FAULT_LATCHED | 0 |
| READY | valid EN | RUN | commanded |
| RUN | DIS | READY | 0 |
| RUN | FLT | FAULT_LATCHED | 0 |
| RUN | invalid setpoint | FAULT_LATCHED | 0 |
| RUN | malformed/unknown command | FAULT_LATCHED | 0 |
| RUN | COMMS_TIMEOUT | FAULT_LATCHED | 0 |
| RUN | RST while enabled | RUN | unchanged / no safety bypass |
| READY | malformed/unknown command | FAULT_LATCHED | 0 |
| FAULT_LATCHED | RST while disabled | READY | 0 |
| FAULT_LATCHED | EN | FAULT_LATCHED | 0 |

## Invariants

- If state is not RUN, PWM shall be 0.
- If `fault_latched` is true, PWM shall be 0.
- If `enabled` is false, PWM shall be 0.
- `enabled=1` and `state=RUN` do not imply a nonzero waveform: setpoints 0-9 are valid and intentionally quantize to 0% PWM.
- A timeout shall not leave the controller in RUN.
- A fault shall not clear automatically.
- Unknown or malformed command input shall not produce active PWM.
- Reset while enabled shall not bypass active safety behavior.
