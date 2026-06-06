# File Manifest

## Main runner
- `upload_and_run_sdc2.bat` - select 16/256 ustep, compile, upload, run logger, run event analysis, run Allan analysis.

## Arduino sketches
- `SDC2_TestRunner_Menu_16u/SDC2_TestRunner_Menu_16u.ino` - firmware configured for 16 microsteps.
- `SDC2_TestRunner_Menu_256u/SDC2_TestRunner_Menu_256u.ino` - firmware configured for 256 microsteps.

## Python
- `sdc2_serial_logger.py` - logs Arduino serial CSV.
- `sdc2_postprocess_fullchar.py` - raw event-based encoder analysis.
- `sdc2_allan_analysis.py` - overlapping Allan deviation analysis and annotated figures.

## Documentation
- `README.md` - main package readme.
- `docs/SDC2_16u_256u_Allan_quick_start.md` - condensed workflow.
- `docs/SDC2_16ustep_test_plan.md` - original 16 ustep test plan.

## Reference
- `reference/` - protocol/context and previous 256 ustep report/figures.
- `reference/allan/` - Allan deviation reference PDFs.
