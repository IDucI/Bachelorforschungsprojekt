#ifndef LESS_FQ_INV_H
#define LESS_FQ_INV_H

#include <stdint.h>

#include "fq_arith.h"

/*
 * fq_inv receives and returns exactly one FQ_ELEM.
 *
 * For every current LESS parameter set:
 * sizeof(FQ_ELEM) == 1 byte.
 */
#define LESS_INPUT_BYTES  (sizeof(FQ_ELEM))
#define LESS_OUTPUT_BYTES (sizeof(FQ_ELEM))

/*
 * Input layout:
 *   one reduced FQ_ELEM
 *
 * Output layout:
 *   its value from the official LESS fq_inv routine
 */
void triggered_fq_inv(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
);

#endif /* LESS_FQ_INV_H */