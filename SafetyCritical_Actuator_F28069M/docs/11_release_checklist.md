# 11 - Release Checklist

## Documentation Checklist

| Item | Status |
|---|---|
| README | Complete |
| Upload README | Complete |
| Project scope | Complete |
| Hardware setup | Complete |
| Standards mapping | Complete |
| System requirements | Complete |
| Software requirements | Complete |
| Hazard analysis | Complete |
| Architecture | Complete |
| State machine | Complete |
| Traceability matrix | Complete |
| Verification plan | Complete |
| Test results | Complete |
| Release checklist | Complete |
| Evidence index | Complete |

## Firmware Checklist

| Item | Status |
|---|---|
| SCI RX/TX | Complete |
| Parser/state machine | Complete |
| ePWM1A output | Complete |
| Fault latch | Complete |
| Invalid setpoint rejection | Complete |
| Unknown/malformed command rejection | Complete |
| CPU Timer0 timeout | Complete |
| Safe-low output forcing | Complete |
| Telemetry | Complete |
| Unused SAFE_SHUTDOWN state removed from documentation basis | Complete |

## Evidence Checklist

| Evidence | Status |
|---|---|
| Serial logs folder prepared | Complete |
| Scope captures folder prepared | Complete |
| Evidence index prepared | Complete |
| Startup evidence added | Complete |
| SCI RX / parser evidence added | Complete |
| 25/50/75% PWM captures added | Complete |
| Disable safe-low captures added | Complete |
| Fault safe-low capture added | Complete |
| Invalid setpoint safe-low capture added | Complete |
| CPU Timer0 timeout evidence added | Complete |
| Final verification video added | Complete |
| Timeout transition video added | Complete |
| Reset while enabled negative-test log added | Pending |
| Unknown/malformed command log added | Pending |

## Release Decision

**Release status: nearly complete for portfolio upload.**

The main evidence package is complete. Add the two final serial-only robustness logs before marking the release fully closed:

```text
evidence/serial_logs/reset_while_enabled_log.txt
evidence/serial_logs/unknown_command_log.txt
```

The project is ready to present as a standards-inspired safety-critical embedded controls demonstration once those two logs are added. It does not claim certification to DO-178C, ISO 26262, ARP4754, or ARP4761.
