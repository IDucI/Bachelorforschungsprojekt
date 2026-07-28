#ifndef LESS_ROW_MUL3_H
#define LESS_ROW_MUL3_H

#include <stdint.h>

#include "fq_arith.h"

#define LESS_ROW_BYTES \
    ((N - K) * sizeof(FQ_ELEM))

#define LESS_INPUT_BYTES \
    (2u * LESS_ROW_BYTES)

#define LESS_OUTPUT_BYTES \
    LESS_ROW_BYTES

/*
 * Input layout:
 *   1. first row:  N-K FQ_ELEM values
 *   2. second row: N-K FQ_ELEM values
 *
 * Output layout:
 *   N-K component-wise products in the LESS field
 */
void triggered_row_mul3(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
);

#endif /* LESS_ROW_MUL3_H */