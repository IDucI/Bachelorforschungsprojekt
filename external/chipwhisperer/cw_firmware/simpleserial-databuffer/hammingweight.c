#include "hammingweight.h"

uint8_t was_optimized() {
  /**
   * @brief returns 0 when optimizations have been applied. Returns 1 when no optimizations have been applied like when with -O0
   * 
   */
#ifdef __OPTIMIZE__
  return 0;
#else
  return 1;
#endif
}

uint32_t triggered_getHammingWeight(const uint8_t tmp[R_BITS],
                                    const uint32_t length) {
  trigger_high();

  volatile int del= 0;
  for(del=0;del<100000;del++){
      asm("nop");
  }
  for(del=0;del<100000;del++){
      asm("nop");
  }

  uint32_t count = 0;
  for (uint32_t i = 0; i < length; i++) {
    count += tmp[i];
  }
  trigger_low();

  return count;
}