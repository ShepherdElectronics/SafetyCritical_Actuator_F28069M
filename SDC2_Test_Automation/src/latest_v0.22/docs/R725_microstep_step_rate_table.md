# R725 microstep options and target speed step-rate table

This package includes selectable firmware builds for the R725 microstep settings below. The physical R725 DIP switches must match the firmware selection in the GUI.

Formula used:

```text
STEP rate Hz = table speed deg/s * pulses_per_motor_rev * 24.65 / 360
```

| Microstep | SW1 | SW2 | SW3 | SW4 | Pulses/motor rev | Table deg/step | Hz @0.01 | Hz @0.03 | Hz @1 | Hz @10 | Hz @15 | Hz @50 |
|---:|:---:|:---:|:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | U | U | U | U | 400 | 0.036511 | 0.274 | 0.822 | 27.4 | 274 | 411 | 1369 |
| 4 | D | U | U | U | 800 | 0.018256 | 0.548 | 1.643 | 54.8 | 548 | 822 | 2739 |
| 5 | U | U | U | D | 1,000 | 0.014604 | 0.685 | 2.054 | 68.5 | 685 | 1027 | 3424 |
| 8 | U | D | U | U | 1,600 | 0.009128 | 1.096 | 3.287 | 109.6 | 1096 | 1643 | 5478 |
| 10 | D | U | U | D | 2,000 | 0.007302 | 1.369 | 4.108 | 136.9 | 1369 | 2054 | 6847 |
| 16 | D | D | U | U | 3,200 | 0.004564 | 2.191 | 6.573 | 219.1 | 2191 | 3287 | 10956 |
| 18 | U | D | D | D | 3,600 | 0.004057 | 2.465 | 7.395 | 246.5 | 2465 | 3698 | 12325 |
| 20 | U | D | U | D | 4,000 | 0.003651 | 2.739 | 8.217 | 273.9 | 2739 | 4108 | 13694 |
| 32 | U | U | D | U | 6,400 | 0.002282 | 4.382 | 13.147 | 438.2 | 4382 | 6573 | 21911 |
| 50 | D | D | U | D | 10,000 | 0.001460 | 6.847 | 20.542 | 684.7 | 6847 | 10271 | 34236 |
| 64 | D | U | D | U | 12,800 | 0.001141 | 8.764 | 26.293 | 876.4 | 8764 | 13147 | 43822 |
| 100 | U | U | D | D | 20,000 | 0.000730 | 13.694 | 41.083 | 1369.4 | 13694 | 20542 | 68472 |
| 128 | U | D | D | U | 25,600 | 0.000570 | 17.529 | 52.587 | 1752.9 | 17529 | 26293 | 87644 |
| 180 | D | D | D | D | 36,000 | 0.000406 | 24.650 | 73.950 | 2465.0 | 24650 | 36975 | 123250 |
| 200 | D | U | D | D | 40,000 | 0.000365 | 27.389 | 82.167 | 2738.9 | 27389 | 41083 | 136944 |
| 256 | D | D | D | U | 51,200 | 0.000285 | 35.058 | 105.173 | 3505.8 | 35058 | 52587 | 175289 |

## Practical starting choices

| Use case | Start here | Notes |
|---|---:|---|
| Ultra-low-speed smoothness | 128 or 256 | Highest microstep settings are useful at the very low end, but require higher command rate for speed. |
| General protocol motion | 16, 20, 32, or 50 | Good starting range for broad speed characterization. |
| High-speed characterization | 16 or 20 | Keeps command-rate demand lower. |
| Microstep sweep study | 8, 16, 20, 32, 50, 64, 128, 256 | Run the same short test matrix and compare speed tracking, smoothness, and fault/drop counts. |

## Recommended microstep sweep procedure

1. Set the R725 DIP switches to the selected microstep value.
2. Select the same microstep firmware in the GUI.
3. Use trial length `super_short` first.
4. Use live telemetry at 50 Hz for sanity checking.
5. Run `D`, then `P` or the selected protocol subset.
6. Compare measured speed, raw speed, warning/fault counts, telemetry drops, and postprocessed trial summaries.
