# 02 - Standards-Inspired Mapping

## Non-Certification Statement

This project is **not certified** to DO-178C, ISO 26262, ARP4754, or ARP4761.

It is standards-inspired because it applies selected lifecycle, traceability, hazard-analysis, verification, and objective-evidence practices from those standards to a compact embedded-controls demonstrator.

## DO-178C-Inspired Software Lifecycle Mapping

| DO-178C Concept | Project Interpretation | Artifact |
|---|---|---|
| Software planning | Define scope, assumptions, verification approach | `00_project_scope.md`, `09_verification_plan.md` |
| High-level requirements | Define externally visible system behavior | `03_system_requirements.md` |
| Low-level/software requirements | Define concrete software safety behaviors | `04_software_requirements.md` |
| Robustness testing | Verify negative cases such as reset while enabled and malformed commands | `09_verification_plan.md`, `10_test_results.md` |
| Software architecture/design | Decompose into SCI, parser, state machine, PWM, Timer0 | `06_architecture.md`, `07_state_machine.md` |
| Source code | Implement deterministic C firmware | `src/main.c` |
| Verification | Test each safety behavior | `09_verification_plan.md`, `10_test_results.md` |
| Traceability | Link requirements to hazards/tests/evidence | `08_traceability_matrix.md` |
| Objective evidence | Serial logs and oscilloscope/video captures | `evidence/` |

## ARP4754-Inspired System Development Mapping

| ARP4754 Concept | Project Interpretation | Artifact |
|---|---|---|
| Item/system definition | Define commanded actuator interface | `00_project_scope.md` |
| System requirements | Define command, telemetry, output, timeout, parser rejection, safe-state behavior | `03_system_requirements.md` |
| Functional allocation | Allocate functions to SCI, parser, state machine, PWM, Timer0 | `06_architecture.md` |
| Architecture | Define data/control flow and interfaces | `06_architecture.md` |
| Verification planning | Define pass/fail evidence before final run | `09_verification_plan.md` |

## ARP4761-Inspired Safety Assessment Mapping

| ARP4761 Concept | Project Interpretation | Artifact |
|---|---|---|
| Functional hazard assessment style | Identify unsafe actuator-command behaviors | `05_hazard_analysis.md` |
| Failure-mode thinking | Stale command, invalid setpoint, fault ignored, unsafe restart, malformed input | `05_hazard_analysis.md` |
| Derived safety requirements | Timeout, range checking, fault latch, parser rejection, safe-low output | `04_software_requirements.md` |
| Verification of mitigations | Serial/scope tests for each safety behavior | `09_verification_plan.md`, `evidence/` |

## ISO 26262-Inspired Functional Safety Mapping

| ISO 26262 Concept | Project Interpretation | Artifact |
|---|---|---|
| Item definition | C2000 actuator command controller | `00_project_scope.md` |
| HARA-style reasoning | Identify hazardous behavior and mitigation | `05_hazard_analysis.md` |
| Safety goals | Prevent stale, invalid, malformed, faulted, or unintended output | `05_hazard_analysis.md` |
| Technical safety requirements | Concrete firmware requirements | `04_software_requirements.md` |
| Verification | Tests for valid command, disable, fault, invalid setpoint, malformed input, timeout | `09_verification_plan.md` |
| Release controls | Checklist and evidence review | `11_release_checklist.md` |

## Summary

```text
hazard -> safety requirement -> architecture -> code -> test -> evidence -> traceability
```
