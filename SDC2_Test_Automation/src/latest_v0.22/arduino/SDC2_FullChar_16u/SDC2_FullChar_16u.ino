/*
  SDC2_FullChar_16u.ino

  System:
    Arduino GIGA R1 WiFi
    Lin Engineering R725 stepper driver
    Lin Engineering 4118M-06SD-I25-A0-A24F geared stepper, 24.65:1 gearbox
    US Digital E5 encoder on rear motor shaft
    AM26LS32A differential receiver

  Purpose:
    Full SDC2 characterization at 16 microsteps.

  IMPORTANT HARDWARE SETTING:
    R725 = 16 microsteps
    SW1 = D, SW2 = D, SW3 = U, SW4 = U
    Pulses per motor rev = 200 * 16 = 3200

  Serial commands:
    ? = print menu
    D = debug short test
    S = static 50 Hz and 100 Hz
    P = official protocol constant speeds, both directions
    H = high-speed extension 10-50 deg/s, both directions
    N = sine velocity tests, peak 15 deg/s
    A = all final tests: S, P, H, N
    Z = zero encoder count
    X = stop immediately

  CSV output only. Use the included Python or MATLAB scripts for plots.
*/

// ===================== PIN MAP =====================
const int STEP_PIN = 10;
const int DIR_PIN  = 13;
const int ENC_A    = 2;
const int ENC_B    = 3;
const int ENC_Z    = 4;

// ===================== MECHANICAL CONSTANTS =====================
const double CPR = 5000.0;
const double EDGE_MULT = 2.0;              // ISR on ENC_A CHANGE
const double GEAR_RATIO = 24.65;           // motor revs per table rev
const double MICROSTEP_SETTING = 16.0;     // R725 set to 16 ustep
const double MOTOR_FULL_STEPS_PER_REV = 200.0;

const double ENCODER_COUNTS_PER_MOTOR_REV = CPR * EDGE_MULT;
const double ENCODER_COUNTS_PER_TABLE_REV = ENCODER_COUNTS_PER_MOTOR_REV * GEAR_RATIO;
const double ENCODER_COUNTS_PER_TABLE_DEG = ENCODER_COUNTS_PER_TABLE_REV / 360.0;
const double TABLE_DEG_PER_ENCODER_COUNT = 360.0 / ENCODER_COUNTS_PER_TABLE_REV;

const double DRIVER_PULSES_PER_MOTOR_REV = MOTOR_FULL_STEPS_PER_REV * MICROSTEP_SETTING;
const double DRIVER_PULSES_PER_TABLE_REV = DRIVER_PULSES_PER_MOTOR_REV * GEAR_RATIO;
const double DRIVER_PULSES_PER_TABLE_DEG = DRIVER_PULSES_PER_TABLE_REV / 360.0;
const double TABLE_DEG_PER_DRIVER_PULSE = 360.0 / DRIVER_PULSES_PER_TABLE_REV;

// ===================== CONTROL SETTINGS =====================
const unsigned int STEP_HIGH_US = 4;
const double MAX_STEP_RATE_HZ = 25000.0;     // safety cap for this firmware
const double MAX_CORRECTION_HZ_ABS = 250.0;  // low-bandwidth trim cap
const double CORRECTION_FRACTION = 0.05;     // correction <= 5% feedforward if smaller
const double KP_POS_TO_HZ = 20.0;            // position error deg -> Hz correction

// ===================== TEST TIMING =====================
// Trial length is selected from the GUI/logger before each run.
// L = super short, M = medium, F = full.
enum TrialLengthProfile { PROFILE_SUPER_SHORT, PROFILE_MEDIUM, PROFILE_FULL };
TrialLengthProfile trialLengthProfile = PROFILE_FULL;

const unsigned long SUPER_SHORT_CONST_SEGMENT_MS = 10000UL;
const unsigned long MEDIUM_CONST_SEGMENT_MS      = 30000UL;
const unsigned long FULL_CONST_SEGMENT_MS        = 60000UL;

const unsigned long SUPER_SHORT_STATIC_50_MS = 10000UL;
const unsigned long SUPER_SHORT_STATIC_100_MS = 10000UL;
const unsigned long MEDIUM_STATIC_50_MS = 60000UL;
const unsigned long MEDIUM_STATIC_100_MS = 30000UL;
const unsigned long FULL_STATIC_50_MS = 180000UL;
const unsigned long FULL_STATIC_100_MS = 90000UL;

const int SUPER_SHORT_SINE_CYCLES = 1;
const int MEDIUM_SINE_CYCLES = 3;
const int FULL_SINE_CYCLES = 5;

const double LOG_RATE_50_HZ = 50.0;
const double LOG_RATE_100_HZ = 100.0;

// Host/target architecture settings.
// The Arduino target owns motion timing; the host only configures, logs, and plots.
// Telemetry is rate-limited so serial printing cannot pace the motion loop.
unsigned long selectedTelemetryIntervalUs = 20000UL; // default 50 Hz
const unsigned long HOST_TIMEOUT_MS = 2000UL;
unsigned long lastHostHeartbeatMs = 0;
bool hostDeadmanEnabled = false;
bool hostRunArmed = false;
bool invertDirPolarity = false;

const double PROTOCOL_SPEEDS[] = {0.01, 0.03, 1.0, 3.0, 5.0, 10.0, 15.0};
const int NUM_PROTOCOL_SPEEDS = sizeof(PROTOCOL_SPEEDS) / sizeof(PROTOCOL_SPEEDS[0]);

const double HIGH_SPEEDS[] = {10.0, 20.0, 30.0, 40.0, 50.0};
const int NUM_HIGH_SPEEDS = sizeof(HIGH_SPEEDS) / sizeof(HIGH_SPEEDS[0]);

const double DEBUG_SPEEDS[] = {0.01, 0.1, 1.0, 5.0, 10.0, 15.0};
const int NUM_DEBUG_SPEEDS = sizeof(DEBUG_SPEEDS) / sizeof(DEBUG_SPEEDS[0]);

const double SINE_PERIODS[] = {3.0, 2.0, 1.0, 0.5};
const int NUM_SINE_PERIODS = sizeof(SINE_PERIODS) / sizeof(SINE_PERIODS[0]);
const double SINE_PEAK_SPEED_DEG_S = 15.0;
const int SINE_CYCLES = 5;

// ===================== ENCODER STATE =====================
volatile long encoderCount = 0;
volatile bool indexSeen = false;
volatile unsigned long isrCount = 0;

// ===================== MOTION STATE =====================
enum MotionState {
  STATE_IDLE,
  STATE_STATIC_HOLD,
  STATE_RAMP_UP,
  STATE_HOLD_SPEED,
  STATE_SINE,
  STATE_RAMP_DOWN,
  STATE_STOPPED,
  STATE_FAULT
};

bool stopRequested = false;
long zeroOffsetCounts = 0;

unsigned long runStartUs = 0;
unsigned long lastLogUs = 0;
unsigned long lastLoopUs = 0;
unsigned long maxLoopDtUs = 0;
unsigned long stepPulseCount = 0;
unsigned long missedStepRateLimitCount = 0;

String currentTestName = "NONE";
String currentLoadCase = "CENTERED";
String currentDirectionName = "CW";
String faultCode = "NONE";

MotionState state = STATE_IDLE;

double commandPositionDeg = 0.0;
double commandSpeedDegS = 0.0;
double feedforwardStepRateHz = 0.0;
double correctionStepRateHz = 0.0;
double finalStepRateHz = 0.0;
double measuredSpeedWindowDegS = 0.0;

// Step accumulator: number of pulses commanded as continuous real value.
double desiredPulseAccumulator = 0.0;
double emittedPulseAccumulator = 0.0;
unsigned long lastControlUs = 0;

// Speed estimate window
long speedWindowLastCount = 0;
unsigned long speedWindowLastUs = 0;
const unsigned long SPEED_WINDOW_US = 500000UL; // 0.5 s

// ===================== TRIAL LENGTH HELPERS =====================
const char* trialLengthName() {
  switch (trialLengthProfile) {
    case PROFILE_SUPER_SHORT: return "SUPER_SHORT";
    case PROFILE_MEDIUM: return "MEDIUM";
    case PROFILE_FULL: return "FULL";
  }
  return "FULL";
}

void setTrialLengthProfile(TrialLengthProfile profile) {
  trialLengthProfile = profile;
  Serial.print("# TRIAL_LENGTH_PROFILE,");
  Serial.println(trialLengthName());
}

unsigned long getConstSegmentMs(bool forceSuperShort) {
  if (forceSuperShort || trialLengthProfile == PROFILE_SUPER_SHORT) return SUPER_SHORT_CONST_SEGMENT_MS;
  if (trialLengthProfile == PROFILE_MEDIUM) return MEDIUM_CONST_SEGMENT_MS;
  return FULL_CONST_SEGMENT_MS;
}

unsigned long getStatic50Ms(bool forceSuperShort) {
  if (forceSuperShort || trialLengthProfile == PROFILE_SUPER_SHORT) return SUPER_SHORT_STATIC_50_MS;
  if (trialLengthProfile == PROFILE_MEDIUM) return MEDIUM_STATIC_50_MS;
  return FULL_STATIC_50_MS;
}

unsigned long getStatic100Ms(bool forceSuperShort) {
  if (forceSuperShort || trialLengthProfile == PROFILE_SUPER_SHORT) return SUPER_SHORT_STATIC_100_MS;
  if (trialLengthProfile == PROFILE_MEDIUM) return MEDIUM_STATIC_100_MS;
  return FULL_STATIC_100_MS;
}

int getSineCycles(bool forceSuperShort) {
  if (forceSuperShort || trialLengthProfile == PROFILE_SUPER_SHORT) return SUPER_SHORT_SINE_CYCLES;
  if (trialLengthProfile == PROFILE_MEDIUM) return MEDIUM_SINE_CYCLES;
  return FULL_SINE_CYCLES;
}


// ===================== HOST / TELEMETRY HELPERS =====================
void touchHostHeartbeat() {
  lastHostHeartbeatMs = millis();
}

void armHostDeadman() {
  hostRunArmed = true;
  touchHostHeartbeat();
}

void disarmHostDeadman() {
  hostRunArmed = false;
}

void setTelemetryHz(unsigned int hz) {
  if (hz < 1) hz = 1;
  if (hz > 100) hz = 100;
  selectedTelemetryIntervalUs = 1000000UL / hz;
  Serial.print("# TELEMETRY_RATE_HZ,");
  Serial.println(hz);
}

unsigned long getTelemetryLogPeriodUs(double requestedLogRateHz) {
  unsigned long requested = (unsigned long)(1000000.0 / requestedLogRateHz);
  // Use the slower of requested test rate and selected telemetry rate.
  // This prevents high-rate serial printing from controlling motion timing.
  if (selectedTelemetryIntervalUs > requested) return selectedTelemetryIntervalUs;
  return requested;
}

bool checkHostTimeout() {
  if (hostDeadmanEnabled && hostRunArmed && (millis() - lastHostHeartbeatMs > HOST_TIMEOUT_MS)) {
    stopRequested = true;
    faultCode = "FAULT_HOST_TIMEOUT";
    stopMotion();
    Serial.println("# FAULT_HOST_TIMEOUT,host heartbeat missing; motion stopped");
    return true;
  }
  return false;
}

// ===================== SETUP =====================
void setup() {
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENC_A, INPUT);
  pinMode(ENC_B, INPUT);
  pinMode(ENC_Z, INPUT);

  digitalWrite(STEP_PIN, LOW);
  setStepDirectionPositive(true);

  attachInterrupt(digitalPinToInterrupt(ENC_A), encoderISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_Z), indexISR, RISING);

  Serial.begin(115200);
  while (!Serial && millis() < 4000) {}

  touchHostHeartbeat();
  printHeader();
  printMenu();
}

void setStepDirectionPositive(bool positive) {
  bool dirHigh = positive;
  if (invertDirPolarity) dirHigh = !dirHigh;
  digitalWrite(DIR_PIN, dirHigh ? HIGH : LOW);
}

// ===================== LOOP =====================
void loop() {
  serviceSerial();
}

// ===================== INTERRUPTS =====================
void encoderISR() {
  bool a = digitalRead(ENC_A);
  bool b = digitalRead(ENC_B);
  if (a == b) {
    encoderCount++;
  } else {
    encoderCount--;
  }
  isrCount++;
}

void indexISR() {
  indexSeen = true;
}

// ===================== SERIAL / MENU =====================
void serviceSerial() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '\n' || cmd == '\r') return;

    touchHostHeartbeat();

    switch (cmd) {
      case '.': break;
      case '?': printMenu(); break;
      case 'L': setTrialLengthProfile(PROFILE_SUPER_SHORT); break;
      case 'M': setTrialLengthProfile(PROFILE_MEDIUM); break;
      case 'F': setTrialLengthProfile(PROFILE_FULL); break;
      case 'Q': setTelemetryHz(10); break;
      case 'W': setTelemetryHz(20); break;
      case 'E': setTelemetryHz(50); break;
      case 'R': setTelemetryHz(100); break;
      case 'Y': hostDeadmanEnabled = true; armHostDeadman(); Serial.println("# HOST_DEADMAN,ENABLED"); break;
      case 'O': hostDeadmanEnabled = false; disarmHostDeadman(); Serial.println("# HOST_DEADMAN,DISABLED"); break;
      case 'I': invertDirPolarity = true; Serial.println("# DIR_POLARITY,INVERTED"); break;
      case 'J': invertDirPolarity = false; Serial.println("# DIR_POLARITY,NORMAL"); break;
      case 'Z': zeroEncoder(); break;
      case 'X': requestStop("USER_STOP"); break;
      case 'D': armHostDeadman(); runDebugTest(); break;
      case 'S': armHostDeadman(); runStaticTests(false); break;
      case 'P': armHostDeadman(); runProtocolConstantSpeeds(false); break;
      case 'H': armHostDeadman(); runHighSpeedExtension(false); break;
      case 'N': armHostDeadman(); runSineTests(false); break;
      case 'A': armHostDeadman(); runAllFinal(); break;
      default:
        Serial.print("# Unknown command: "); Serial.println(cmd);
        printMenu();
        break;
    }
  }
}

void printHeader() {
  Serial.println("# SDC2 Full Characterization Firmware - 16 ustep");
  Serial.println("# FirmwareVersion,SDC2_FullChar_16u_v1");
  Serial.println("# R725_MICROSTEP_SETTING,16");
  Serial.println("# R725_DIP,SW1=D,SW2=D,SW3=U,SW4=U");
  Serial.print("# CPR,"); Serial.println(CPR, 0);
  Serial.print("# EDGE_MULT,"); Serial.println(EDGE_MULT, 0);
  Serial.print("# GEAR_RATIO,"); Serial.println(GEAR_RATIO, 5);
  Serial.print("# ENCODER_COUNTS_PER_TABLE_DEG,"); Serial.println(ENCODER_COUNTS_PER_TABLE_DEG, 6);
  Serial.print("# TABLE_DEG_PER_ENCODER_COUNT,"); Serial.println(TABLE_DEG_PER_ENCODER_COUNT, 9);
  Serial.print("# DRIVER_PULSES_PER_TABLE_DEG,"); Serial.println(DRIVER_PULSES_PER_TABLE_DEG, 6);
  Serial.print("# TABLE_DEG_PER_DRIVER_PULSE,"); Serial.println(TABLE_DEG_PER_DRIVER_PULSE, 9);
  Serial.print("# STEP_PIN,"); Serial.println(STEP_PIN);
  Serial.print("# DIR_PIN,"); Serial.println(DIR_PIN);
  Serial.print("# DIR_POLARITY,"); Serial.println(invertDirPolarity ? "INVERTED" : "NORMAL");
  Serial.print("# ENC_A,"); Serial.println(ENC_A);
  Serial.print("# ENC_B,"); Serial.println(ENC_B);
  Serial.print("# ENC_Z,"); Serial.println(ENC_Z);
  Serial.print("# TRIAL_LENGTH_PROFILE,"); Serial.println(trialLengthName());
  Serial.print("# TELEMETRY_RATE_HZ,"); Serial.println(1000000UL / selectedTelemetryIntervalUs);
  Serial.print("# HOST_TIMEOUT_MS,"); Serial.println(HOST_TIMEOUT_MS);
  Serial.println("# Method,raw encoder counts; no filtering or grouped averaging in raw CSV");
  printCsvHeader();
}

void printMenu() {
  Serial.println("# Commands:");
  Serial.println("# ? menu");
  Serial.println("# L trial length = SUPER_SHORT");
  Serial.println("# M trial length = MEDIUM");
  Serial.println("# F trial length = FULL");
  Serial.println("# Q telemetry = 10 Hz");
  Serial.println("# W telemetry = 20 Hz");
  Serial.println("# E telemetry = 50 Hz");
  Serial.println("# R telemetry = 100 Hz");
  Serial.println("# Y enable host heartbeat/deadman");
  Serial.println("# O disable host heartbeat/deadman");
  Serial.println("# I invert DIR polarity");
  Serial.println("# J normal DIR polarity");
  Serial.println("# . host heartbeat ping");
  Serial.println("# Z zero encoder count");
  Serial.println("# X stop immediately");
  Serial.println("# D short debug constant-speed test");
  Serial.println("# S static 50 Hz and 100 Hz tests");
  Serial.println("# P official protocol constant speeds, both directions");
  Serial.println("# H high-speed extension 10-50 deg/s, both directions");
  Serial.println("# N sine velocity tests, peak 15 deg/s");
  Serial.println("# A all final tests: S, P, H, N");
}

void printCsvHeader() {
  Serial.println("Time_s,TestTime_s,TestName,LoadCase,Direction,State,TargetSpeed_deg_s,CommandPosition_deg,EncoderCount,ActualTablePosition_deg,PositionError_deg,FeedforwardStepRate_Hz,CorrectionStepRate_Hz,StepRate_Hz,StepPulseCount,ExpectedEncoderCount,EncoderCountError,MeasuredSpeed_deg_s,LoopDt_us,MaxLoopDt_us,FaultCode,IndexSeen,ISRCount,MicrostepSetting");
}

// ===================== TEST RUNNERS =====================
void runAllFinal() {
  armHostDeadman();
  runStaticTests(false);
  if (stopRequested) return;
  armHostDeadman();
  runProtocolConstantSpeeds(false);
  if (stopRequested) return;
  armHostDeadman();
  runHighSpeedExtension(false);
  if (stopRequested) return;
  armHostDeadman();
  runSineTests(false);
  disarmHostDeadman();
  Serial.println("# ALL_TESTS_COMPLETE");
}

void runDebugTest() {
  Serial.println("# Starting DEBUG test at 16 ustep");
  zeroEncoder();
  for (int dir = 0; dir < 2; dir++) {
    int sign = (dir == 0) ? 1 : -1;
    for (int i = 0; i < NUM_DEBUG_SPEEDS; i++) {
      runConstantSpeedSegment(DEBUG_SPEEDS[i] * sign, getConstSegmentMs(true), LOG_RATE_100_HZ, "DEBUG_CONST", "CENTERED");
      if (stopRequested) return;
    }
  }
  disarmHostDeadman();
  Serial.println("# DEBUG test complete");
}

void runStaticTests(bool fastDebug) {
  Serial.println("# Starting static tests");
  unsigned long dur50 = getStatic50Ms(fastDebug);
  unsigned long dur100 = getStatic100Ms(fastDebug);
  runStaticSegment(dur50, LOG_RATE_50_HZ, "STATIC_50HZ_HOLD", "CENTERED");
  if (stopRequested) return;
  runStaticSegment(dur100, LOG_RATE_100_HZ, "STATIC_100HZ_HOLD", "CENTERED");
  disarmHostDeadman();
  Serial.println("# Static tests complete");
}

void runProtocolConstantSpeeds(bool fastDebug) {
  Serial.println("# Starting official protocol constant-speed tests");
  unsigned long durationMs = getConstSegmentMs(fastDebug);
  for (int dir = 0; dir < 2; dir++) {
    int sign = (dir == 0) ? 1 : -1;
    for (int i = 0; i < NUM_PROTOCOL_SPEEDS; i++) {
      runConstantSpeedSegment(PROTOCOL_SPEEDS[i] * sign, durationMs, LOG_RATE_100_HZ, "PROTOCOL_CONST", "CENTERED");
      if (stopRequested) return;
    }
  }
  disarmHostDeadman();
  Serial.println("# Official protocol constant-speed tests complete");
}

void runHighSpeedExtension(bool fastDebug) {
  Serial.println("# Starting high-speed 10-50 deg/s extension");
  unsigned long durationMs = getConstSegmentMs(fastDebug);
  for (int dir = 0; dir < 2; dir++) {
    int sign = (dir == 0) ? 1 : -1;
    for (int i = 0; i < NUM_HIGH_SPEEDS; i++) {
      runConstantSpeedSegment(HIGH_SPEEDS[i] * sign, durationMs, LOG_RATE_100_HZ, "HIGH_SPEED_10_50", "CENTERED");
      if (stopRequested) return;
    }
  }
  disarmHostDeadman();
  Serial.println("# High-speed extension complete");
}

void runSineTests(bool fastDebug) {
  Serial.println("# Starting sine velocity tests");
  for (int i = 0; i < NUM_SINE_PERIODS; i++) {
    runSineSegment(SINE_PEAK_SPEED_DEG_S, SINE_PERIODS[i], getSineCycles(fastDebug), LOG_RATE_100_HZ, "SINE_VELOCITY", "CENTERED");
    if (stopRequested) return;
  }
  disarmHostDeadman();
  Serial.println("# Sine velocity tests complete");
}

// ===================== SEGMENTS =====================
void runStaticSegment(unsigned long durationMs, double logRateHz, const char* testName, const char* loadCase) {
  prepareSegment(testName, loadCase, 0.0);
  state = STATE_STATIC_HOLD;
  unsigned long durationUs = durationMs * 1000UL;
  unsigned long logPeriodUs = getTelemetryLogPeriodUs(logRateHz);
  runStartUs = micros();
  lastLogUs = runStartUs;
  lastControlUs = runStartUs;
  lastLoopUs = runStartUs;
  maxLoopDtUs = 0;
  speedWindowLastCount = readEncoderCount();
  speedWindowLastUs = runStartUs;

  while (!stopRequested && (micros() - runStartUs) < durationUs) {
    if (checkHostTimeout()) break;
    updateLoopTiming();
    updateSpeedEstimate();
    commandSpeedDegS = 0.0;
    feedforwardStepRateHz = 0.0;
    correctionStepRateHz = 0.0;
    finalStepRateHz = 0.0;

    unsigned long now = micros();
    if (now - lastLogUs >= logPeriodUs) {
      lastLogUs += logPeriodUs;
      logCsvRow(now);
    }
    serviceStopOnly();
  }
  stopMotion();
}

void runConstantSpeedSegment(double targetSpeedDegS, unsigned long durationMs, double logRateHz, const char* testName, const char* loadCase) {
  prepareSegment(testName, loadCase, targetSpeedDegS);
  unsigned long durationUs = durationMs * 1000UL;
  unsigned long logPeriodUs = getTelemetryLogPeriodUs(logRateHz);
  unsigned long rampUs = min((unsigned long)3000000UL, durationUs / 5UL);
  unsigned long rampDownStartUs = durationUs - rampUs;

  runStartUs = micros();
  lastLogUs = runStartUs;
  lastControlUs = runStartUs;
  lastLoopUs = runStartUs;
  maxLoopDtUs = 0;
  desiredPulseAccumulator = 0.0;
  emittedPulseAccumulator = 0.0;
  speedWindowLastCount = readEncoderCount();
  speedWindowLastUs = runStartUs;

  while (!stopRequested && (micros() - runStartUs) < durationUs) {
    if (checkHostTimeout()) break;
    unsigned long now = micros();
    unsigned long elapsed = now - runStartUs;
    updateLoopTiming();
    updateSpeedEstimate();

    double scale = 1.0;
    if (elapsed < rampUs) {
      state = STATE_RAMP_UP;
      scale = (double)elapsed / (double)rampUs;
    } else if (elapsed > rampDownStartUs) {
      state = STATE_RAMP_DOWN;
      scale = (double)(durationUs - elapsed) / (double)rampUs;
      if (scale < 0.0) scale = 0.0;
    } else {
      state = STATE_HOLD_SPEED;
      scale = 1.0;
    }

    double targetNow = targetSpeedDegS * scale;
    updateFeedforwardMotion(targetNow, now);
    emitDueSteps();

    if (now - lastLogUs >= logPeriodUs) {
      lastLogUs += logPeriodUs;
      logCsvRow(now);
    }
    serviceStopOnly();
  }
  stopMotion();
}

void runSineSegment(double peakSpeedDegS, double periodSec, int cycles, double logRateHz, const char* testName, const char* loadCase) {
  prepareSegment(testName, loadCase, peakSpeedDegS);
  state = STATE_SINE;
  unsigned long durationUs = (unsigned long)(periodSec * cycles * 1000000.0);
  unsigned long logPeriodUs = getTelemetryLogPeriodUs(logRateHz);
  double omega = 2.0 * PI / periodSec;

  runStartUs = micros();
  lastLogUs = runStartUs;
  lastControlUs = runStartUs;
  lastLoopUs = runStartUs;
  maxLoopDtUs = 0;
  desiredPulseAccumulator = 0.0;
  emittedPulseAccumulator = 0.0;
  speedWindowLastCount = readEncoderCount();
  speedWindowLastUs = runStartUs;

  while (!stopRequested && (micros() - runStartUs) < durationUs) {
    if (checkHostTimeout()) break;
    unsigned long now = micros();
    double tsec = (now - runStartUs) / 1000000.0;
    updateLoopTiming();
    updateSpeedEstimate();

    double targetNow = peakSpeedDegS * sin(omega * tsec);
    updateFeedforwardMotion(targetNow, now);
    emitDueSteps();

    if (now - lastLogUs >= logPeriodUs) {
      lastLogUs += logPeriodUs;
      logCsvRow(now);
    }
    serviceStopOnly();
  }
  stopMotion();
}

// ===================== CONTROL =====================
void prepareSegment(const char* testName, const char* loadCase, double targetSpeedDegS) {
  stopRequested = false;
  faultCode = "NONE";
  currentTestName = String(testName);
  currentLoadCase = String(loadCase);
  currentDirectionName = targetSpeedDegS >= 0.0 ? "CW" : "CCW";
  setStepDirectionPositive(targetSpeedDegS >= 0.0);
  commandSpeedDegS = 0.0;
  feedforwardStepRateHz = 0.0;
  correctionStepRateHz = 0.0;
  finalStepRateHz = 0.0;
  stepPulseCount = 0;
  missedStepRateLimitCount = 0;
  commandPositionDeg = getActualTablePositionDeg();
  desiredPulseAccumulator = 0.0;
  emittedPulseAccumulator = 0.0;
  Serial.print("# Starting segment,");
  Serial.print(currentTestName); Serial.print(",target,"); Serial.println(targetSpeedDegS, 6);
}

void updateFeedforwardMotion(double targetSpeedDegS, unsigned long nowUs) {
  double dt = (nowUs - lastControlUs) / 1000000.0;
  if (dt < 0) dt = 0;
  if (dt > 0.1) dt = 0.1;
  lastControlUs = nowUs;

  commandSpeedDegS = targetSpeedDegS;
  commandPositionDeg += commandSpeedDegS * dt;

  double actualPos = getActualTablePositionDeg();
  double posError = commandPositionDeg - actualPos;

  feedforwardStepRateHz = commandSpeedDegS * DRIVER_PULSES_PER_TABLE_DEG;

  double correctionLimit = max(2.0, min(MAX_CORRECTION_HZ_ABS, abs(feedforwardStepRateHz) * CORRECTION_FRACTION));
  correctionStepRateHz = KP_POS_TO_HZ * posError;
  if (correctionStepRateHz > correctionLimit) correctionStepRateHz = correctionLimit;
  if (correctionStepRateHz < -correctionLimit) correctionStepRateHz = -correctionLimit;

  finalStepRateHz = feedforwardStepRateHz + correctionStepRateHz;

  if (abs(finalStepRateHz) > MAX_STEP_RATE_HZ) {
    finalStepRateHz = (finalStepRateHz > 0 ? 1 : -1) * MAX_STEP_RATE_HZ;
    faultCode = "WARN_STEP_RATE_LIMIT";
    missedStepRateLimitCount++;
  }

  setStepDirectionPositive(finalStepRateHz >= 0.0);
  desiredPulseAccumulator += abs(finalStepRateHz) * dt;
}

void emitDueSteps() {
  unsigned long pulsesToEmit = 0;
  if (desiredPulseAccumulator > emittedPulseAccumulator) {
    double due = desiredPulseAccumulator - emittedPulseAccumulator;
    pulsesToEmit = (unsigned long)floor(due);
  }

  // Prevent serial logging stalls from creating a huge burst.
  if (pulsesToEmit > 25) {
    pulsesToEmit = 25;
    if (faultCode == "NONE") faultCode = "WARN_STEP_BACKLOG_LIMIT";
  }

  for (unsigned long i = 0; i < pulsesToEmit; i++) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(STEP_HIGH_US);
    digitalWrite(STEP_PIN, LOW);
    emittedPulseAccumulator += 1.0;
    stepPulseCount++;
  }
}

void stopMotion() {
  feedforwardStepRateHz = 0.0;
  correctionStepRateHz = 0.0;
  finalStepRateHz = 0.0;
  digitalWrite(STEP_PIN, LOW);
  state = STATE_STOPPED;
  Serial.println("# Segment complete");
}

void requestStop(const char* reason) {
  stopRequested = true;
  faultCode = String(reason);
  stopMotion();
  Serial.print("# Stop requested,"); Serial.println(reason);
}

void serviceStopOnly() {
  while (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == '\n' || cmd == '\r') continue;
    touchHostHeartbeat();
    if (cmd == 'X') {
      requestStop("USER_STOP");
    } else if (cmd == 'Z') {
      zeroEncoder();
    } else if (cmd == '.') {
      // heartbeat only
    }
  }
}

// ===================== LOGGING =====================
void logCsvRow(unsigned long nowUs) {
  double timeS = nowUs / 1000000.0;
  double testTimeS = (nowUs - runStartUs) / 1000000.0;
  long enc = readEncoderCount();
  long encZeroed = enc - zeroOffsetCounts;
  double actualPos = encZeroed * TABLE_DEG_PER_ENCODER_COUNT;
  double positionError = commandPositionDeg - actualPos;
  long expectedEncoderCount = (long)round(commandPositionDeg * ENCODER_COUNTS_PER_TABLE_DEG);
  long encoderCountError = expectedEncoderCount - encZeroed;

  Serial.print(timeS, 6); Serial.print(',');
  Serial.print(testTimeS, 6); Serial.print(',');
  Serial.print(currentTestName); Serial.print(',');
  Serial.print(currentLoadCase); Serial.print(',');
  Serial.print(currentDirectionName); Serial.print(',');
  Serial.print(stateToString(state)); Serial.print(',');
  Serial.print(commandSpeedDegS, 6); Serial.print(',');
  Serial.print(commandPositionDeg, 6); Serial.print(',');
  Serial.print(encZeroed); Serial.print(',');
  Serial.print(actualPos, 6); Serial.print(',');
  Serial.print(positionError, 6); Serial.print(',');
  Serial.print(feedforwardStepRateHz, 6); Serial.print(',');
  Serial.print(correctionStepRateHz, 6); Serial.print(',');
  Serial.print(finalStepRateHz, 6); Serial.print(',');
  Serial.print(stepPulseCount); Serial.print(',');
  Serial.print(expectedEncoderCount); Serial.print(',');
  Serial.print(encoderCountError); Serial.print(',');
  Serial.print(measuredSpeedWindowDegS, 6); Serial.print(',');
  Serial.print(getLastLoopDtUs()); Serial.print(',');
  Serial.print(maxLoopDtUs); Serial.print(',');
  Serial.print(faultCode); Serial.print(',');
  Serial.print(indexSeen ? 1 : 0); Serial.print(',');
  Serial.print(isrCount); Serial.print(',');
  Serial.println(MICROSTEP_SETTING, 0);
}

void updateSpeedEstimate() {
  unsigned long now = micros();
  if (now - speedWindowLastUs >= SPEED_WINDOW_US) {
    long cNow = readEncoderCount();
    double dt = (now - speedWindowLastUs) / 1000000.0;
    long dc = cNow - speedWindowLastCount;
    measuredSpeedWindowDegS = ((double)dc * TABLE_DEG_PER_ENCODER_COUNT) / dt;
    speedWindowLastCount = cNow;
    speedWindowLastUs = now;
  }
}

unsigned long lastLoopDtUsValue = 0;
void updateLoopTiming() {
  unsigned long now = micros();
  lastLoopDtUsValue = now - lastLoopUs;
  lastLoopUs = now;
  if (lastLoopDtUsValue > maxLoopDtUs) maxLoopDtUs = lastLoopDtUsValue;
  if (lastLoopDtUsValue > 25000UL && faultCode == "NONE") {
    faultCode = "WARN_LOOP_OVERRUN";
  }
}

unsigned long getLastLoopDtUs() {
  return lastLoopDtUsValue;
}

// ===================== HELPERS =====================
long readEncoderCount() {
  noInterrupts();
  long c = encoderCount;
  interrupts();
  return c;
}

void zeroEncoder() {
  zeroOffsetCounts = readEncoderCount();
  commandPositionDeg = 0.0;
  desiredPulseAccumulator = 0.0;
  emittedPulseAccumulator = 0.0;
  stepPulseCount = 0;
  Serial.println("# Encoder zeroed");
}

double getActualTablePositionDeg() {
  long encZeroed = readEncoderCount() - zeroOffsetCounts;
  return encZeroed * TABLE_DEG_PER_ENCODER_COUNT;
}

const char* stateToString(MotionState s) {
  switch (s) {
    case STATE_IDLE: return "IDLE";
    case STATE_STATIC_HOLD: return "STATIC_HOLD";
    case STATE_RAMP_UP: return "RAMP_UP";
    case STATE_HOLD_SPEED: return "HOLD_SPEED";
    case STATE_SINE: return "SINE";
    case STATE_RAMP_DOWN: return "RAMP_DOWN";
    case STATE_STOPPED: return "STOPPED";
    case STATE_FAULT: return "FAULT";
    default: return "UNKNOWN";
  }
}
