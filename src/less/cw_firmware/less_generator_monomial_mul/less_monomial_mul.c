#include "less_monomial_mul.h"

#include <string.h>

#include "hal.h"

void triggered_generator_monomial_mul(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]) {

    generator_mat_t generator;
    generator_mat_t result;
    monomial_t monomial;

    const uint8_t *cursor = input;

    memcpy(generator.values, cursor, sizeof(generator.values));
    cursor += sizeof(generator.values);

    memcpy(monomial.coefficients, cursor, sizeof(monomial.coefficients));
    cursor += sizeof(monomial.coefficients);

    /* The host sends POSITION_T values in little-endian byte order. */
    for (uint32_t index = 0; index < N; index++) {
        monomial.permutation[index] =
            (POSITION_T)cursor[2u * index] |
            ((POSITION_T)cursor[2u * index + 1u] << 8u);
    }

    trigger_high();
    generator_monomial_mul(&result, &generator, &monomial);
    trigger_low();

    memcpy(output, result.values, sizeof(result.values));
}
