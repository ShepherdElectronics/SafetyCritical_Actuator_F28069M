# Quick Start - SDC2 16/256 ustep + Allan Package

1. Unzip the package.
2. Double-click `upload_and_run_sdc2.bat`.
3. Choose firmware:
   - `1` for 16 ustep
   - `2` for 256 ustep
4. Physically verify the R725 DIP switches match the menu.
5. Wait for compile/upload.
6. Choose the test:
   - `1` DEBUG first
   - `4` STATIC for Allan hold data
   - `3` PROTOCOL for 0.01 to 15 deg/s
   - `2` HIGHSPEED for 10 to 50 deg/s
   - `6` ALL for complete sequence
7. Open results folder from the menu with `9` or after the run with `O`.

Allan outputs are in:

```text
SDC2_results_<microstep>u/<run_label>/allan_analysis/allan_figures
```

Event-based encoder outputs are in:

```text
SDC2_results_<microstep>u/<run_label>/event_analysis
```
