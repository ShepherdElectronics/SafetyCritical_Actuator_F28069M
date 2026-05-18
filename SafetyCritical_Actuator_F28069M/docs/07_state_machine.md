# 07 - State Machine

## States

| State | Meaning | PWM |
|---|---|---|
| INIT | Startup initialization | 0 |
| SELF_TEST | Startup self-test placeholder | 0 |
| READY | Healthy, disabled, waiting for enable | 0 |
| RUN | Enabled, valid command active | commanded |
| FAULT_LATCHED | Fault latched, reset required | 0 |
| SAFE_SHUTDOWN | Reserved final safe state | 0 |

## Transition Table

| Current State | Event | Next State | Output |
|---|---|---|---|
| INIT | init complete | SELF_TEST | 0 |
| SELF_TEST | pass | READY | 0 |
| READY | valid EN | RUN | commanded |
| RUN | DIS | READY | 0 |
| RUN | FLT | FAULT_LATCHED | 0 |
| RUN | invalid setpoint | FAULT_LATCHED | 0 |
| RUN | COMMS_TIMEOUT | FAULT_LATCHED | 0 |
| FAULT_LATCHED | RST while disabled | READY | 0 |
| FAULT_LATCHED | EN | FAULT_LATCHED | 0 |

## Invariants

- If state is not RUN, PWM shall be 0.
- If `fault_latched` is true, PWM shall be 0.
- If `enabled` is false, PWM shall be 0.
- A timeout shall not leave the controller in RUN.
- A fault shall not clear automatically.
