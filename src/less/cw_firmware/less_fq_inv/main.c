#include "hal.h"

#if HAL_TYPE == HAL_pinata
/* Pinata-specific headers are supplied by the shared HAL. */
#else
#error "incorrect platform targeted"
#endif

#if PLATFORM == PINATA
#define allocation __attribute__((section(".ccmram")))
#else
#define allocation
#endif

#include <stdint.h>
#include <string.h>

#include "simpleserial.h"

#include "ledz.h"
#include "less_fq_inv.h"

static uint8_t databuffer[LESS_INPUT_BYTES] allocation;
static uint8_t resultbuffer[LESS_OUTPUT_BYTES] allocation;

#define SUBROUTINE_FQ_INV 0x03

uint8_t subroutines(
    uint8_t cmd,
    uint8_t scmd,
    uint8_t len,
    uint8_t *x
) {
    (void)cmd;
    (void)len;
    (void)x;

    switch (scmd) {
    case SUBROUTINE_FQ_INV:
        led2_on();

        triggered_fq_inv(
            resultbuffer,
            databuffer
        );

        simpleserial_put(
            'r',
            LESS_OUTPUT_BYTES,
            resultbuffer
        );

        led2_off();

        return SS_ERR_OK;

    default:
        return SS_ERR_CMD;
    }
}

/*
 * Same value as in the generator_monomial_mul firmware.
 * fq_inv only uses one byte, but keeping the same interface makes
 * all LESS firmware targets structurally consistent.
 */
#define USB_PACKET_DATABUFFER_SIZE 160

uint8_t set_value(
    uint8_t cmd,
    uint8_t scmd,
    uint8_t len,
    uint8_t *x
) {
    (void)cmd;

    led1_on();

    const uint32_t index = scmd & 0x7Fu;

    const uint8_t read_back =
        (scmd & 0x80u) == 0x80u;

    const uint32_t offset =
        index * USB_PACKET_DATABUFFER_SIZE;

    if (
        len == 0u ||
        len > USB_PACKET_DATABUFFER_SIZE ||
        offset + len > LESS_INPUT_BYTES
    ) {
        led1_off();
        return SS_ERR_LEN;
    }

    memcpy(
        databuffer + offset,
        x,
        len
    );

    if (read_back) {
        simpleserial_put(
            'r',
            len,
            databuffer + offset
        );
    }

    led1_off();

    return SS_ERR_OK;
}

int main(void) {
    platform_init();
    init_uart();
    trigger_setup();
    simpleserial_init();

    ledz_init();
    led1_init();
    led2_init();
    led3_init();

    led1_off();
    led2_off();
    led3_off();

#if SS_VER == SS_VER_2_1

    simpleserial_addcmd(
        's',
        USB_PACKET_DATABUFFER_SIZE,
        set_value
    );

    simpleserial_addcmd(
        'b',
        0,
        subroutines
    );

#else
#error "no SS_VER_1_1 for this"
#endif

    while (1) {
        simpleserial_get();
    }
}