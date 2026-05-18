# 06 - Architecture

## High-Level Architecture

```text
PC Python Tool
   |
   | SCI/UART command
   v
SCI RX -> line buffer -> command parser -> safety controller state machine
                                             |             ^
                                             v             |
                                      ePWM1A/GPIO0    CPU Timer0 tick
                                             |
                                             v
                                      Scope/logic analyzer

Safety controller -> telemetry formatter -> SCI TX -> PC log
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| SCI driver functions | Configure SCI-A, receive command bytes, transmit telemetry |
| Command parser | Parse EN, DIS, RST, FLT, CLR command strings |
| Safety controller | Maintain state, fault, latch, setpoint, PWM percent, sequence, age |
| PWM driver | Configure ePWM1A/GPIO0 and apply safe-low or commanded duty |
| Timer0 ISR | Generate millisecond tick for timeout monitor |
| Telemetry formatter | Print state/fault/command/output evidence |
| Python tools | Send commands, capture logs, assist scope recording |

## Safety Architecture Rule

The PWM driver does not decide whether output is safe. The safety controller decides the permitted PWM percent. Faults, disable, invalid commands, and timeout all route through `Controller_ForceSafeOutput()`.
