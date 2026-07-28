#ifndef LESS_GENERATOR_SAMPLE_H
#define LESS_GENERATOR_SAMPLE_H

#include <stdint.h>

#include "codes.h"

#define LESS_SAMPLE_VALUES_BYTES \
    (K * (N - K) * sizeof(FQ_ELEM))

#define LESS_SAMPLE_POSITIONS_BYTES \
    ((N - K) * sizeof(POSITION_T))

#define LESS_INPUT_BYTES \
    SEED_LENGTH_BYTES

#define LESS_OUTPUT_BYTES \
    (LESS_SAMPLE_VALUES_BYTES + LESS_SAMPLE_POSITIONS_BYTES)

/*
 * Input layout:
 *
 *   SEED_LENGTH_BYTES seed bytes
 *
 * Output layout:
 *
 *   1. K * (N-K) active matrix values in row-major order
 *   2. N-K little-endian POSITION_T column positions
 */
void triggered_generator_sample(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
);

#endif /* LESS_GENERATOR_SAMPLE_H */