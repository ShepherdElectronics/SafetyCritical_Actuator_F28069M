# SDC2 16-microstep characterization plan

## Purpose

Determine whether 16 ustep removes the speed ceiling seen at 256 ustep and supports the faster SDC2 characterization range.

## Official protocol coverage

### Static tests

| Test | Logging rate | Duration | Expected points |
|---|---:|---:|---:|
| Static hold | 50 Hz | 180 s | 9,000 |
| Static hold | 100 Hz | 90 s | 9,000 |

### Constant-speed dynamic tests

Official speeds:

```text
0.01, 0.03, 1.0, 3.0, 5.0, 10.0, 15.0 deg/s
```

Run both directions. Use 100 Hz logging for 60 s per speed for final data.

### 10-50 deg/s extension

Because the team discussed needing 10-50 deg/s for full practical characterization, this package includes:

```text
10, 20, 30, 40, 50 deg/s
```

Run both directions. Start with debug duration before final duration.

### Sine velocity tests

Velocity profile:

```text
V = 15 sin(omega t) deg/s
```

Periods:

```text
3.0, 2.0, 1.0, 0.5 s
```

Run 5 cycles each, centered first, offset/load later.

## What to compare against 256 ustep

| Metric | Why it matters |
|---|---|
| Average measured speed | Command-following accuracy |
| Measured / target speed ratio | Easy cross-speed comparison |
| RMS event speed | Raw event-level speed ripple |
| RMS speed error | Dynamic tracking error |
| Long-gap count | Slow/stalled motion or delayed count events |
| Short-gap count | Catch-up motion or bursts |
| Final count lag | Whether command outruns actual motion |
| Loop overrun count | Firmware/logging timing health |

## Pass/fail guidance

For initial review:

```text
Good: speed ratio 0.80 to 1.20 and no severe long-gap pattern
Borderline: speed ratio 0.60 to 0.80 or visible ripple requiring tuning
Fail: speed ratio < 0.60 or repeated long-gap / no-motion warnings
```

Final acceptance should be updated if the project has a formal optical pointing or angular stability requirement.
