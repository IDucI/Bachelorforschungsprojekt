#include "ledz.h"
// #define XSTR(x) STR(x)
// #define STR(x) #x
// #error "waarom" XSTR(HAL_TYPE)
// #pragma message "The alue " XSTR(HAL_TYPE)

#include <hal.h>
#if HAL_TYPE == HAL_sam4s
#include "sam4s_hal.h"
#include <asf.h>
#elif HAL_TYPE == HAL_k82f
#include "fsl_gpio.h"
#include "fsl_port.h"
#include "k82f_hal.h"
#elif HAL_TYPE == HAL_pinata
#include "stm32f4xx_hal.h"
#else
#error "incorrect platform targeted"
#endif

void ledz_init() {
#if HAL_TYPE == HAL_sam4s

#elif HAL_TYPE == HAL_k82f
  CLOCK_EnableClock(kCLOCK_PortE);
#endif
}

void led1_init() {
#if HAL_TYPE == HAL_sam4s
  gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_0 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
  PORT_SetPinMux(PORTE, 2, kPORT_MuxAsGpio);
  gpio_pin_config_t trigconf = {kGPIO_DigitalOutput, 1};

  GPIO_PinInit(GPIOE, 2, &trigconf);
  GPIO_WritePinOutput(GPIOE, 2, 0);
#endif
}

void led1_off() {
#if HAL_TYPE == HAL_sam4s
  gpio_set_pin_low(PIO_PA16_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_0 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
  GPIO_WritePinOutput(GPIOE, 2, 0);
#endif
}

void led1_on() {
#if HAL_TYPE == HAL_sam4s
  gpio_set_pin_high(PIO_PA16_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_1 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
  GPIO_WritePinOutput(GPIOE, 2, 1);
#endif
}

void led1_toggle() {
#if HAL_TYPE == HAL_sam4s
  gpio_toggle_pin(PIO_PA16_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_1 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
#endif
}

void led2_init() {
#if HAL_TYPE == HAL_sam4s
  gpio_configure_pin(PIO_PA15_IDX, PIO_OUTPUT_0 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
  PORT_SetPinMux(PORTE, 1, kPORT_MuxAsGpio);
  gpio_pin_config_t trigconf = {kGPIO_DigitalOutput, 1};

  GPIO_PinInit(GPIOE, 1, &trigconf);
  GPIO_WritePinOutput(GPIOE, 1, 0);
#endif
}

void led2_off() {
#if HAL_TYPE == HAL_sam4s
  gpio_set_pin_low(PIO_PA15_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_0 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
GPIO_WritePinOutput(GPIOE, 1, 0);
#endif
}

void led2_on() {
#if HAL_TYPE == HAL_sam4s
  gpio_set_pin_high(PIO_PA15_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_1 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
GPIO_WritePinOutput(GPIOE, 1, 1);
#endif
}

void led2_toggle() {
#if HAL_TYPE == HAL_sam4s
  gpio_toggle_pin(PIO_PA15_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_1 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
#endif
}

void led3_init() {
#if HAL_TYPE == HAL_sam4s
  gpio_configure_pin(PIO_PA14_IDX, PIO_OUTPUT_0 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
  PORT_SetPinMux(PORTE, 0, kPORT_MuxAsGpio);
  gpio_pin_config_t trigconf = {kGPIO_DigitalOutput, 1};

  GPIO_PinInit(GPIOE, 0, &trigconf);
  GPIO_WritePinOutput(GPIOE, 0, 0);
#endif
}

void led3_off() {
#if HAL_TYPE == HAL_sam4s
  gpio_set_pin_low(PIO_PA14_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_0 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
GPIO_WritePinOutput(GPIOE, 0, 0);
#endif
}

void led3_on() {
#if HAL_TYPE == HAL_sam4s
  gpio_set_pin_high(PIO_PA14_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_1 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
GPIO_WritePinOutput(GPIOE, 0, 1);
#endif
}

void led3_toggle() {
#if HAL_TYPE == HAL_sam4s
  gpio_toggle_pin(PIO_PA14_IDX);
  // gpio_configure_pin(PIO_PA16_IDX, PIO_OUTPUT_1 | PIO_DEFAULT);
#elif HAL_TYPE == HAL_k82f
#endif
}
