#include "less_row_mul3.h"

#include <string.h>

#include "hal.h"

void triggered_row_mul3(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
) {
    FQ_ELEM in1[N - K];
    FQ_ELEM in2[N - K];
    FQ_ELEM result[N - K];

    const uint8_t *cursor = input;

    memcpy(
        in1,
        cursor,
        sizeof(in1)
    );

    cursor += sizeof(in1);

    memcpy(
        in2,
        cursor,
        sizeof(in2)
    );

    trigger_high();

    row_mul3(
        result,
        in1,
        in2
    );

    trigger_low();

    memcpy(
        output,
        result,
        sizeof(result)
    );
}