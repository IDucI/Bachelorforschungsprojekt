#include "hal.h"
// #if defined(CW308_SAM308)
#if HAL_TYPE == HAL_pinata
// #include ""
// platform specific includes
#else
#error "incorrect platform targeted"
#endif

// #if HAL_TYPE == HAL_pinata
#if PLATFORM == PINATA
#define allocation __attribute__((section(".ccmram")))
#else
#define allocation
#endif

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "simpleserial.h"

#include "ledz.h"

#include "fp_arith.h"
static uint8_t databuffer[HASH_DIGEST_LENGTH] allocation;

#define SUBROUTINE_EXPAND_DIGEST 0x14

uint8_t subroutines(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t* x) {
    switch (scmd) {
    case SUBROUTINE_EXPAND_DIGEST: {
        led2_on();
        uint8_t result[T];
        expand_digest_to_fixed_weight(result, (databuffer));
        simpleserial_put('r', T * sizeof(uint8_t), (uint8_t*)result);
        led2_off();
        return SS_ERR_OK;
    }
    default:
        return SS_ERR_CMD;
    }

    return SS_ERR_CMD;
}
/*
uint8_t hwinfo[3] = {};

uint8_t metainfo(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t* x) {
    // if (len != 3) {
    //   return SS_ERR_LEN;
    // }
    // x[0] = hwinfo[0];
    // x[1] = hwinfo[1];

    hwinfo[2] = was_optimized();
    simpleserial_put('r', 3, hwinfo);

    return SS_ERR_OK;
}
*/
// little endian
// V2 max data packet 249 bytes. USB buffer is 200.
#define USB_PACKET_DATABUFFER_SIZE 160
uint8_t set_value(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t* x) {
    led1_on();

    if (len != USB_PACKET_DATABUFFER_SIZE && len != 3) {
        return SS_ERR_LEN;
    }

    uint32_t index = scmd & 0x7F; // uint_fast16_t

    uint8_t read_back = (scmd & 0x80) == 0x80;

    memcpy(databuffer + (index * USB_PACKET_DATABUFFER_SIZE), x, len);

    if (read_back) {
        simpleserial_put('r', len, databuffer + (index * USB_PACKET_DATABUFFER_SIZE));
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
    // io functions
    simpleserial_addcmd('s', USB_PACKET_DATABUFFER_SIZE, set_value);

    // victim function
    simpleserial_addcmd('b', 0, subroutines);

    // victim metadata readout
   //simpleserial_addcmd('m', 0, metainfo);
#else
#error "no SS_VER_1_1 for this"
#endif

    while (1) {
        simpleserial_get();
    }
}
