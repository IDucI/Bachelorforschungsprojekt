#include "less_fq_inv.h"

#include <string.h>

#include "hal.h"

void triggered_fq_inv(
    uint8_t output[LESS_OUTPUT_BYTES],
    const uint8_t input[LESS_INPUT_BYTES]
) {
    FQ_ELEM value;
    FQ_ELEM inverse;

    /*
     * Convert the raw SimpleSerial byte buffer into the official
     * LESS FQ_ELEM type.
     */
    memcpy(
        &value,
        input,
        sizeof(value)
    );

    /*
     * Only the actual LESS fq_inv operation lies inside the
     * ChipWhisperer trigger region.
     */
    trigger_high();

    inverse = fq_inv(value);

    trigger_low();

    memcpy(
        output,
        &inverse,
        sizeof(inverse)
    );
}