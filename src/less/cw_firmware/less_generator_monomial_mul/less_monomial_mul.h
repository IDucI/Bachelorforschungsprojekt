#ifndef LESS_MONOMIAL_MUL_H
#define LESS_MONOMIAL_MUL_H

#include <stdint.h>

#include "codes.h"
#include "monomial_mat.h"

#define LESS_GENERATOR_BYTES (K * N_pad * sizeof(FQ_ELEM))
#define LESS_COEFFICIENT_BYTES (N * sizeof(FQ_ELEM))
#define LESS_PERMUTATION_BYTES (N * sizeof(POSITION_T))
#define LESS_INPUT_BYTES \
    (LESS_GENERATOR_BYTES + LESS_COEFFICIENT_BYTES + LESS_PERMUTATION_BYTES)
#define LESS_OUTPUT_BYTES LESS_GENERATOR_BYTES

/*
 * Input layout:
 *   1. generator matrix values, row-major: K * N_pad bytes
 *   2. monomial coefficients: N bytes
 *   3. monomial permutation: N little-endian POSITION_T values
 */
void triggered_generator_monomial_mul(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]);

#endif /* LESS_MONOMIAL_MUL_H */
