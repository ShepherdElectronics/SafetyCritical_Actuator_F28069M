# Quick start

## 1. Set R725 microsteps

Set R725 DIP switches for 16 ustep:

```text
SW1 = D
SW2 = D
SW3 = U
SW4 = U
```

This corresponds to 3,200 pulses per motor revolution.

## 2. Upload firmware

Open:

```text
arduino/SDC2_FullChar_16u/SDC2_FullChar_16u.ino
```

Select Arduino GIGA R1 WiFi and upload.

Optional Arduino CLI example:

```bat
arduino-cli compile --fqbn arduino:mbed_giga:giga arduino\SDC2_FullChar_16u
arduino-cli upload -p COM3 --fqbn arduino:mbed_giga:giga arduino\SDC2_FullChar_16u
```

Change `COM3` to the actual port.

## 3. Run logger

From the package root:

```bat
python python\sdc2_serial_logger.py --port COM3 --command H --output runs\sdc2_16u_highspeed_10_50.csv
```

Useful commands:

| Command | Test |
|---|---|
| `D` | short debug constant-speed test |
| `S` | static 50 Hz + 100 Hz tests |
| `P` | official protocol constant-speed test: 0.01, 0.03, 1, 3, 5, 10, 15 deg/s, both directions |
| `H` | 10-50 deg/s high-speed characterization, both directions |
| `N` | sine velocity tests, peak 15 deg/s, periods 3.0, 2.0, 1.0, 0.5 s |
| `A` | all of the above except debug |
| `X` | immediate stop |
| `Z` | zero encoder count |
| `?` | print firmware menu |

## 4. Postprocess

```bat
python python\sdc2_postprocess_fullchar.py --input runs\sdc2_16u_highspeed_10_50.csv --out Boss_SDC2_16u_Analysis
```

This makes a one-folder output with figures and CSV summaries.
