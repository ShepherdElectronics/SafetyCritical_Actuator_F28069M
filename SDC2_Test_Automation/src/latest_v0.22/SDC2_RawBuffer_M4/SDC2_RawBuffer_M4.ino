/*
  SDC2_RawBuffer_M4.ino

  Arduino GIGA / STM32H747 M4 companion sketch.

  Purpose:
    M4-side buffered data-acquisition/logging worker scaffold.

  Important Arduino GIGA notes:
    - Upload with the same base board FQBN, but target_core=cm4 and a nonzero M4 flash split.
    - The M7 sketch must call RPC.begin() to boot the M4.
    - The M4 does not own USB Serial directly. M7 remains the USB/host-facing core.
    - The M4 must not touch the actuator pins/peripherals used by M7.

  This file intentionally avoids Serial/USB and pin I/O.

  Arduino CLI M4 build workaround:
    Some Arduino mbed_giga 4.5.0 CLI M4 builds link Serial.cpp and expect a main()
    entry point. This M4 worker provides a tiny explicit main() and a safe pin-name
    shim so the M4 worker can link without using USB Serial or GPIO mapping.
*/

#include <RPC.h>
#include "mbed.h"


// Build shim for some Arduino mbed_giga target_core=cm4 CLI builds.
// The M4 worker does not use pins or Serial, so returning NC is safe for this worker.
PinName digitalPinToPinName(unsigned char) {
  return NC;
}

struct RawSample {
  uint32_t t_us;
  int32_t encoder_count;
  int32_t position_mdeg;
  int32_t target_mdeg_s;
  int32_t profile_mdeg_s;
  int32_t measured_mdeg_s;
  uint16_t state_id;
  uint16_t flags;
};

static const uint32_t RAW_CAPACITY = 8192;
static RawSample rawBuf[RAW_CAPACITY];
static volatile uint32_t rawWrite = 0;
static volatile uint32_t rawCount = 0;
static volatile uint32_t rawDrops = 0;
static volatile uint32_t rawSession = 0;

static inline void critEnter() {
  core_util_critical_section_enter();
}

static inline void critExit() {
  core_util_critical_section_exit();
}

int rawClear() {
  critEnter();
  rawWrite = 0;
  rawCount = 0;
  rawDrops = 0;
  rawSession++;
  critExit();
  return (int)rawSession;
}

int rawStatus() {
  uint32_t c = rawCount;
  uint32_t d = rawDrops;
  if (c > 65535u) c = 65535u;
  if (d > 65535u) d = 65535u;
  return (int)((d << 16) | c);
}

int rawCountRpc() {
  return (int)rawCount;
}

int rawDropsRpc() {
  return (int)rawDrops;
}

int rawPush(uint32_t t_us,
            int32_t encoder_count,
            int32_t position_mdeg,
            int32_t target_mdeg_s,
            int32_t profile_mdeg_s,
            int32_t measured_mdeg_s,
            uint32_t state_flags) {
  const uint16_t state_id = (uint16_t)(state_flags & 0xFFFFu);
  const uint16_t flags = (uint16_t)((state_flags >> 16) & 0xFFFFu);

  critEnter();
  if (rawCount >= RAW_CAPACITY) {
    rawDrops++;
    critExit();
    return 0;
  }

  const uint32_t idx = rawWrite;
  rawBuf[idx].t_us = t_us;
  rawBuf[idx].encoder_count = encoder_count;
  rawBuf[idx].position_mdeg = position_mdeg;
  rawBuf[idx].target_mdeg_s = target_mdeg_s;
  rawBuf[idx].profile_mdeg_s = profile_mdeg_s;
  rawBuf[idx].measured_mdeg_s = measured_mdeg_s;
  rawBuf[idx].state_id = state_id;
  rawBuf[idx].flags = flags;

  rawWrite = (rawWrite + 1u) % RAW_CAPACITY;
  rawCount++;
  critExit();
  return 1;
}

int rawPing() {
  return 4242;
}

int main() {
  RPC.begin();
  RPC.bind("rawClear", rawClear);
  RPC.bind("rawStatus", rawStatus);
  RPC.bind("rawCount", rawCountRpc);
  RPC.bind("rawDrops", rawDropsRpc);
  RPC.bind("rawPush", rawPush);
  RPC.bind("rawPing", rawPing);

  while (true) {
    thread_sleep_for(10);
  }
}
