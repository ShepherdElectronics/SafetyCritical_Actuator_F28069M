# 09 - Verification Plan

## Environment

| Item | Value |
|---|---|
| Target | TI C2000 F28069M |
| IDE | Code Composer Studio |
| Communication | SCI/UART |
| Baud | 115200 |
| PWM Output | GPIO0 / ePWM1A |
| Evidence | Serial logs, PNG scope captures, MP4 verification videos |

## Test Cases

| ID | Test | Procedure | Expected Result |
|---|---|---|---|
| TEST-001 | Startup safe state | Load/run firmware | READY, PWM=0 |
| TEST-002 | SCI command handling | Send RST/EN/DIS/FLT | Commands parsed and telemetry updated |
| TEST-003 | PWM scaling | Send EN,250 / EN,500 / EN,750 | 25/50/75% duty on GPIO0 |
| TEST-004 | Disable safe-low | Send DIS after EN | PWM=0, state READY |
| TEST-005 | Fault safe-low | Send FLT after EN | FAULT_LATCHED, SENSOR_FAULT, PWM=0 |
| TEST-006 | Invalid setpoint | Send EN,1500 | FAULT_LATCHED, INVALID_SETPOINT, PWM=0 |
| TEST-007 | CPU Timer0 timeout | Send EN,500 and stop commands | COMMS_TIMEOUT after 3000 ms, PWM=0 |
| TEST-008 | Final integrated verification | Run full automated command sequence | All command, fault, PWM, reset, and timeout behaviors verified |
| TEST-009 | Reset while enabled negative test | Send RST,0; EN,500,14; RST,15 | Reset while enabled does not bypass active safety behavior |
| TEST-010 | Unknown/malformed command handling | Send FOO,123 and/or EN, | FAULT_LATCHED, FAULT=UNKNOWN_COMMAND, EN=0, SP=0, PWM=0, LATCH=1 |

## Additional Manual Serial Tests

### TEST-009 - Reset While Enabled

```text
RST,0
EN,500,14
RST,15
```

Expected after `RST,15`:

```text
STATE=RUN,FAULT=NONE,EN=1,SP=500,PWM=50
```

or equivalent telemetry showing reset while enabled did not bypass active safety behavior.

Save as:

```text
evidence/serial_logs/reset_while_enabled_log.txt
```

### TEST-010 - Unknown/Malformed Command Handling

```text
FOO,123
EN,
```

Expected:

```text
STATE=FAULT_LATCHED,FAULT=UNKNOWN_COMMAND,EN=0,SP=0,PWM=0,LATCH=1
```

Save as:

```text
evidence/serial_logs/unknown_command_log.txt
```
