#include "less_generator_sample.h"

#include <string.h>

#include "hal.h"

void triggered_generator_sample(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
) {
    unsigned char seed[SEED_LENGTH_BYTES];
    rref_generator_mat_t result;

    memcpy(
        seed,
        input,
        sizeof(seed)
    );

    /*
     * The original LESS generator_sample operation is measured.
     *
     * This includes:
     *
     * - SHAKE/CSPRNG initialization
     * - XOF extraction
     * - rejection sampling
     * - matrix-value generation
     * - column-position generation
     */
    trigger_high();

    generator_sample(
        &result,
        seed
    );

    trigger_low();

    uint8_t *cursor = output;

    /*
     * Serialize the active K * (N-K) values in row-major order.
     */
    for (uint32_t row = 0; row < K; row++) {
        memcpy(
            cursor,
            result.values[row],
            (N - K) * sizeof(FQ_ELEM)
        );

        cursor += (
            (N - K) * sizeof(FQ_ELEM)
        );
    }

    /*
     * Serialize each POSITION_T explicitly in little-endian format.
     */
    for (
        uint32_t index = 0;
        index < (N - K);
        index++
    ) {
        const POSITION_T position =
            result.column_pos[index];

        cursor[2u * index] =
            (uint8_t)(position & 0xFFu);

        cursor[2u * index + 1u] =
            (uint8_t)(position >> 8u);
    }
}