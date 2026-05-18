# Upload Summary - Safety-Critical Actuator Command Controller

## Project Title

Safety-Critical Actuator Command Controller - TI C2000 F28069M

## One-Line Description

Built a TI C2000 safety-critical actuator command controller with SCI command input, ePWM actuator output, explicit state-machine control, invalid-command rejection, fault-latched safe shutdown, CPU Timer0 communication timeout, telemetry, requirements traceability, and serial/scope verification evidence.

## Standards-Inspired Framing

This project is not certified to DO-178C, ISO 26262, ARP4754, or ARP4761. It is standards-inspired because it applies their common engineering pattern at project scale:

```text
system definition -> requirements -> hazard analysis -> derived safety requirements -> architecture -> implementation -> verification -> traceability -> objective evidence -> release review
```

## Specific Standards Connection

- **DO-178C inspired:** software requirements, design decomposition, source-code implementation, verification cases, requirements-to-test traceability, configuration/release notes, and evidence artifacts.
- **ARP4754 inspired:** system-level requirements, functional allocation to command input / state machine / PWM output / timer monitor, architecture definition, and integration planning.
- **ARP4761 inspired:** hazard identification, failure-mode thinking, derived safety requirements, fault-latched behavior, and safe-state verification.
- **ISO 26262 inspired:** item definition, HARA-style hazard reasoning, safety goals, technical safety requirements, verification evidence, and release controls.

## What To Review

- `src/main.c` - firmware implementation
- `docs/02_standards_mapping.md` - detailed standards mapping
- `docs/05_hazard_analysis.md` - hazards and mitigations
- `docs/08_traceability_matrix.md` - requirements to evidence
- `docs/10_test_results.md` - final verification results
- `docs/11_release_checklist.md` - release checklist
- `tools/serial_auto_scope_demo.py` - automated verification driver
- `evidence/evidence_index.md` - evidence map
- `evidence/scope_captures/` - numbered oscilloscope captures and verification videos
- `evidence/serial_logs/` - serial telemetry logs

## Evidence Note

The evidence is numbered to match the automated command sequence. Serial logs provide the command/telemetry record. PNG and MP4 files provide visual proof that the ePWM1A/GPIO0 actuator-command output transitions correctly between commanded PWM and safe-low states.

## Certification Statement

This project does not claim certification or compliance to DO-178C, ISO 26262, ARP4754, or ARP4761. It is a standards-inspired portfolio demonstration of embedded safety workflow, deterministic firmware behavior, verification discipline, and objective evidence collection.
