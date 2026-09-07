#ifndef HAMMINGWEIGHT_SHIM_H
#define HAMMINGWEIGHT_SHIM_H

#include <hal.h>
#if HAL_TYPE == HAL_sam4s
#include "sam4s_hal.h"
#include <asf.h>
#elif HAL_TYPE == HAL_k82f
// #inlcude ""
#elif HAL_TYPE == HAL_pinata
// #include ""
#else
#error "incorrect platform targeted"
#endif

#include "stdint.h"

uint8_t was_optimized();

#define R_BITS 160


// #include "types.h"
uint32_t triggered_getHammingWeight(const uint8_t tmp[R_BITS], const uint32_t length);

int alternative_if(int id);

#endif // HAMMINGWEIGHT_SHIM_H