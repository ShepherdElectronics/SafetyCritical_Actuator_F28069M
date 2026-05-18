# 01 - Hardware Setup

## Hardware Platform

| Item | Description |
|---|---|
| MCU board | TI C2000 F28069M LaunchPad |
| Communication | SCI/UART over LaunchPad COM port |
| Output | ePWM1A / GPIO0 actuator-command signal |
| Evidence tools | Python serial logger, oscilloscope, phone/camera screenshots/video |
| Power stage | Not connected in Version 1 |

## Signal Map

| Signal | Function | Use |
|---|---|---|
| GPIO28 / SCIRXDA | SCI receive | PC to C2000 command input |
| GPIO29 / SCITXDA | SCI transmit | C2000 telemetry to PC |
| GPIO0 / ePWM1A | PWM output | Actuator-command signal |
| GND | Ground reference | Scope/logic analyzer reference |

## Bench Setup

1. Connect LaunchPad USB to host PC.
2. Build/load firmware from CCS.
3. Open COM port with Python serial tool.
4. Probe GPIO0/ePWM1A with oscilloscope.
5. Connect scope ground to LaunchPad ground.
6. Run automated command sequence.
7. Capture numbered screenshots/video in evidence order.

## Expected Output Cases

| Command/Event | Expected GPIO0/ePWM1A |
|---|---|
| Startup / READY | 0% / safe-low |
| `EN,250` | 25% duty |
| `EN,500` | 50% duty |
| `EN,750` | 75% duty |
| `DIS` | 0% / safe-low |
| `FLT` | 0% / safe-low |
| `EN,1500` | 0% / safe-low |
| CPU Timer0 timeout | 0% / safe-low |

## Safety Notes

Version 1 is a low-power bench demonstration. Do not connect GPIO0/ePWM1A to high-voltage hardware, a real inverter, a motor driver, a linear actuator, or any system capable of hazardous motion.
