#include "less_monomial_sample_prikey.h"

#include <string.h>

#include "hal.h"

void triggered_monomial_sample_prikey(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
) {
    unsigned char seed[
        PRIVATE_KEY_SEED_LENGTH_BYTES
    ];

    monomial_t result;

    memcpy(
        seed,
        input,
        sizeof(seed)
    );

    /*
     * Tthe original LESS subroutine is inside the trigger region.
     *
     * This includes:
     *
     * - SHAKE/CSPRNG initialization
     * - non-zero field-element sampling
     * - initialization of the identity permutation
     * - secret-dependent permutation shuffling
     */
    trigger_high();

    monomial_sample_prikey(
        &result,
        seed
    );

    trigger_low();

    uint8_t *cursor = output;

    memcpy(
        cursor,
        result.coefficients,
        sizeof(result.coefficients)
    );

    cursor += sizeof(result.coefficients);

    /*
     * Serialize POSITION_T values explicitly as little-endian bytes.
     */
    for (
        uint32_t index = 0;
        index < N;
        index++
    ) {
        const POSITION_T position =
            result.permutation[index];

        cursor[2u * index] =
            (uint8_t)(position & 0xFFu);

        cursor[2u * index + 1u] =
            (uint8_t)(position >> 8u);
    }
}