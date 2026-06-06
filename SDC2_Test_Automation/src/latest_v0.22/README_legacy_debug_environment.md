# SDC2 Debug Final One-Click Environment

This package is the current SDC2 Arduino/Python test environment with the slow-plot option and the new debugging additions discussed in chat.

## One-click run

1. Put this whole folder here or similar:

```text
C:\Users\Jonathan\Documents\Phase2_testing\SDC2_Debug_Final
```

2. Double-click:

```text
upload_and_run_sdc2.bat
```

The batch file will:

```text
compile the Arduino sketch
upload it to the Arduino GIGA on COM5
start the Python logger at 921600 baud
prompt for the test mode
save CSVs, split trial CSVs, summary, and PNG plots
```

## Menu options

```text
1 = SWEEP     closed-loop speed sweep
2 = FULL      full protocol
3 = OPENLOOP  fixed STEP-frequency sweep, no encoder correction
4 = OPENRAMP  ramped STEP-frequency sweep
5 = SLOWPLOT  slow encoder smoothness plot test
```

Option 5 runs:

```text
static hold
0.002 deg/s
0.003 deg/s
0.005 deg/s
0.010 deg/s
0.050 deg/s
0.100 deg/s
```

## Important setting

The firmware currently has:

```cpp
const bool FAST_DEBUG = true;
```

This shortens runs for faster debugging. Set it to `false` in `SDC2_TestRunner_Menu.ino` for long final characterization runs.

Debug timing with `FAST_DEBUG = true`:

```text
static holds: about 10 s
SLOWPLOT segments: about 45 s each
OPENRAMP: shorter ramp/hold/down sections
FULL/SWEEP: shortened segments
```

## New firmware architecture

The code now treats smooth speed as the main goal:

```text
feedforward STEP-rate command = main smooth motion source
encoder feedback = low-bandwidth background trim
position loop = useful for startup/zeroing/drift correction, not aggressive position chasing
```

Closed-loop correction is capped dynamically:

```cpp
maxCorrection_Hz = max(2 Hz, 0.10 * abs(feedforwardStepRate_Hz))
```

and is also limited by:

```cpp
MAX_CORRECTION_STEP_RATE_HZ
```

## New serial commands

While running, the Python logger sends `STOP` on Ctrl+C. You can also use these commands from a serial terminal:

```text
STOP      immediate stop
PAUSE     pause motion without resetting the board
RESUME    resume after pause
ZERO      zero encoder count and command position
STATUS    print current state/count/speed/step info
MARK text add a marker line to the comment log
```

## New CSV columns

The new CSV header is:

```text
RunLabel,Mode,TestIndex,TestName,State,Time_s,TestTime_s,SampleRate_Hz,
TargetSpeed_deg_s,MotorRPM,SinePeriod_s,EncoderCount,ExpectedEncoderCount,
EncoderCountError,CommandTablePosition_deg,ActualMotorPosition_deg,
ActualTablePosition_deg,TablePositionError_deg,CommandTableSpeed_deg_s,
CommandMotorSpeed_deg_s,FeedforwardStepRate_Hz,CorrectionStepRate_Hz,
StepRate_Hz,StepPulseCount,MeasuredSpeed_deg_s,SpeedError_deg_s,
LoopDt_us,MaxLoopDt_us,FaultCode,MotionActive,EncA,EncB,EncZ
```

Most important debug columns:

```text
State
FeedforwardStepRate_Hz
CorrectionStepRate_Hz
StepRate_Hz
StepPulseCount
ExpectedEncoderCount
EncoderCount
EncoderCountError
MeasuredSpeed_deg_s
SpeedError_deg_s
LoopDt_us
MaxLoopDt_us
FaultCode
MotionActive
```

## New plots

Python now saves the original plots plus additional debug plots:

```text
08_step_rate_split.png
09_encoder_count_error.png
10_smoothness_residual_overlay.png
11_loop_timing.png
```

The smoothness residual plot subtracts a best-fit line from each moving trial, which is better for judging constant-speed smoothness than raw position error.

## Hardware reminder

This code assumes:

```text
D10 = STEP
D13 = DIR
D2  = Encoder A
D3  = Encoder B
D4  = Encoder Z/index/logged only
D12 = diagnostic step-pulse LED
Gear ratio = 24.65:1
Encoder before gearbox
Microstep setting = 256 in code and on R725 hardware
Baud = 921600
```

If you change the R725 microstep DIP setting, update this line in the Arduino sketch to match:

```cpp
const double MICROSTEP_SETTING = 256.0;
```
