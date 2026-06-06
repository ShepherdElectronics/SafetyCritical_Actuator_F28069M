# Trial Length Profiles

The GUI now supports three firmware-level trial length profiles before each run.

| GUI option | Serial profile command | Constant-speed segment | Static 50 Hz | Static 100 Hz | Sine cycles per period | Purpose |
|---|---:|---:|---:|---:|---:|---|
| super_short | L | 10 s | 10 s | 10 s | 1 | Fast bring-up/debug |
| medium | M | 30 s | 60 s | 30 s | 3 | Partial characterization without waiting full protocol time |
| full | F | 60 s | 180 s | 90 s | 5 | Official/final characterization timing |

The selected profile is sent immediately before the selected test command. Example:

```text
L then P = super-short protocol constant-speed run
M then S = medium static run
F then A = full all-tests run
```

The firmware prints the active profile as:

```text
# TRIAL_LENGTH_PROFILE,SUPER_SHORT
# TRIAL_LENGTH_PROFILE,MEDIUM
# TRIAL_LENGTH_PROFILE,FULL
```

Use `super_short` first when testing the setup, serial port, plots, or telemetry UI. Use `full` only after the shorter runs look sane.
