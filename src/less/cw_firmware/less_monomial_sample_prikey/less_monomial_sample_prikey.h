#ifndef LESS_MONOMIAL_SAMPLE_PRIKEY_H
#define LESS_MONOMIAL_SAMPLE_PRIKEY_H

#include <stdint.h>

#include "monomial_mat.h"

#define LESS_COEFFICIENT_BYTES \
    (N * sizeof(FQ_ELEM))

#define LESS_PERMUTATION_BYTES \
    (N * sizeof(POSITION_T))

#define LESS_INPUT_BYTES \
    PRIVATE_KEY_SEED_LENGTH_BYTES

#define LESS_OUTPUT_BYTES \
    (LESS_COEFFICIENT_BYTES + LESS_PERMUTATION_BYTES)

/*
 * Input layout:
 *
 *   PRIVATE_KEY_SEED_LENGTH_BYTES seed bytes
 *
 * Output layout:
 *
 *   1. N non-zero FQ_ELEM coefficients
 *   2. N little-endian POSITION_T permutation values
 */
void triggered_monomial_sample_prikey(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
);

#endif /* LESS_MONOMIAL_SAMPLE_PRIKEY_H */