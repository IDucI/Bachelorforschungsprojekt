#include "hal.h"

#if HAL_TYPE != HAL_pinata
#error "incorrect platform targeted"
#endif

#if PLATFORM == PINATA
#define ccm_allocation __attribute__((section(".ccmram")))
#else
#define ccm_allocation
#endif

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "stm32f4xx.h"
#include "system_stm32f4xx.h"
#include "simpleserial.h"
#include "ledz.h"
#include "codes.h"
#include "fq_arith.h"
#include "monomial_mat.h"
#include "LESS.h"

#define LESS_FQ_INV                  0x03
#define LESS_ROW_MUL3                0x04
#define LESS_GENERATOR_SAMPLE        0x05
#define LESS_MONOMIAL_SAMPLE_PRIKEY  0x06
#define LESS_GENERATOR_MONOMIAL_MUL  0x07
#define LESS_KEYGEN                  0x18
#define LESS_SIGN                    0x19
#define LESS_VERIFY                  0x1A

#define INPUT_CHUNK_SIZE  160u
#define OUTPUT_CHUNK_SIZE 160u

#define FQ_INV_INPUT_BYTES  sizeof(FQ_ELEM)
#define FQ_INV_OUTPUT_BYTES sizeof(FQ_ELEM)

#define ROW_MUL3_ROW_BYTES    ((N - K) * sizeof(FQ_ELEM))
#define ROW_MUL3_INPUT_BYTES  (2u * ROW_MUL3_ROW_BYTES)
#define ROW_MUL3_OUTPUT_BYTES ROW_MUL3_ROW_BYTES

#define GENERATOR_SAMPLE_INPUT_BYTES SEED_LENGTH_BYTES
#define GENERATOR_SAMPLE_VALUES_BYTES (K * (N - K) * sizeof(FQ_ELEM))
#define GENERATOR_SAMPLE_POSITIONS_BYTES ((N - K) * sizeof(POSITION_T))
#define GENERATOR_SAMPLE_OUTPUT_BYTES \
    (GENERATOR_SAMPLE_VALUES_BYTES + GENERATOR_SAMPLE_POSITIONS_BYTES)

#define MONOMIAL_SAMPLE_INPUT_BYTES PRIVATE_KEY_SEED_LENGTH_BYTES
#define MONOMIAL_SAMPLE_COEFFICIENT_BYTES (N * sizeof(FQ_ELEM))
#define MONOMIAL_SAMPLE_PERMUTATION_BYTES (N * sizeof(POSITION_T))
#define MONOMIAL_SAMPLE_OUTPUT_BYTES \
    (MONOMIAL_SAMPLE_COEFFICIENT_BYTES + MONOMIAL_SAMPLE_PERMUTATION_BYTES)

#define GENERATOR_BYTES (K * N_pad * sizeof(FQ_ELEM))
#define GENERATOR_MONOMIAL_MUL_INPUT_BYTES \
    (GENERATOR_BYTES + N * sizeof(FQ_ELEM) + N * sizeof(POSITION_T))
#define GENERATOR_MONOMIAL_MUL_OUTPUT_BYTES GENERATOR_BYTES

#if !defined(CATEGORY) || CATEGORY == 252
#define LESS_GENERATOR_MONOMIAL_MUL_SUPPORTED 1
#define LESS_MAX_INPUT_BYTES GENERATOR_MONOMIAL_MUL_INPUT_BYTES
#else
#define LESS_GENERATOR_MONOMIAL_MUL_SUPPORTED 0
#define LESS_MAX_INPUT_BYTES ROW_MUL3_INPUT_BYTES
#endif

_Static_assert(sizeof(POSITION_T) == 2u, "POSITION_T must be 16 bit");
_Static_assert(offsetof(rref_generator_mat_t, column_pos) == GENERATOR_SAMPLE_VALUES_BYTES,
    "unexpected rref_generator_mat_t layout");
_Static_assert(sizeof(rref_generator_mat_t) == GENERATOR_SAMPLE_OUTPUT_BYTES,
    "unexpected rref_generator_mat_t size");
_Static_assert(offsetof(monomial_t, permutation) == MONOMIAL_SAMPLE_COEFFICIENT_BYTES,
    "unexpected monomial_t layout");
_Static_assert(sizeof(monomial_t) == MONOMIAL_SAMPLE_OUTPUT_BYTES, "unexpected monomial_t size");

// Buffer for input data received in SimpleSerial chunks.
static uint8_t databuffer[LESS_MAX_INPUT_BYTES] ccm_allocation;

// Share the result memory between the selected subroutines.
typedef union {
    FQ_ELEM fq_inverse;
    FQ_ELEM row_mul3[N - K];
    rref_generator_mat_t generator_sample;
    monomial_t monomial_sample;

#if LESS_GENERATOR_MONOMIAL_MUL_SUPPORTED
    generator_mat_t generator_monomial_mul;
#endif

} less_result_workspace_t;

static less_result_workspace_t result_workspace;

static uint32_t result_length = 0u;
static uint32_t last_cycles = 0u;

// Enable the DWT cycle counter for runtime measurements.
static void cycles_init(void){
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0u;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

// Return the last DWT cycle count and CPU clock frequency.
// Both values are transmitted as little-endian 32-bit integers.
static uint8_t get_cycles(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *x){
    (void)cmd;
    (void)scmd;
    (void)len;
    (void)x;

    uint8_t data[8];
    uint32_t values[2] = {last_cycles, SystemCoreClock};

    for (unsigned i = 0; i < 2u; i++){
        for (unsigned b = 0; b < 4u; b++){
            data[4u * i + b] = (uint8_t)(values[i] >> (8u * b));
        }
    }
    simpleserial_put('r', sizeof(data), data);
    return SS_ERR_OK;
}

#if LESS_GENERATOR_MONOMIAL_MUL_SUPPORTED
static generator_mat_t generator_input;
#endif

// Encode 16-bit positions as little-endian bytes.
static void serialize_positions(uint8_t *output, const POSITION_T *positions, uint32_t count){
    for (uint32_t i = 0; i < count; i++){
        const POSITION_T value = positions[i];
        output[2u * i] = (uint8_t)(value & 0xFFu);
        output[2u * i + 1u] = (uint8_t)(value >> 8u);
    }
}

// Decode 16-bit positions from little-endian bytes.
static void deserialize_positions(POSITION_T *positions, const uint8_t *input, uint32_t count){
    for (uint32_t i = 0; i < count; i++){
        positions[i] = (POSITION_T)input[2u * i] | ((POSITION_T)input[2u * i + 1u] << 8u);
    }
}

// Execute the subroutine selected by the SimpleSerial subcommand.
uint8_t subroutines(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *x){
    (void)cmd;
    (void)len;
    (void)x;

    led2_on();

    result_length = 0u;
    last_cycles = 0u;

    switch (scmd){
    // Compute the multiplicative inverse of a field element.
    // Input and output each contain one FQ_ELEM.
    case LESS_FQ_INV: {
        FQ_ELEM value;
        memcpy(&value, databuffer, FQ_INV_INPUT_BYTES);

        uint32_t cycle_start = DWT->CYCCNT;
        __asm__ volatile("" ::: "memory");
        result_workspace.fq_inverse = fq_inv(value);
        __asm__ volatile("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        result_length = FQ_INV_OUTPUT_BYTES;
        break;
    }

    // Multiply two rows element-wise in the finite field.
    // Input: two consecutive rows of N-K elements.
    // Output: one row of N-K elements.
    case LESS_ROW_MUL3: {
        const FQ_ELEM *in1 = (const FQ_ELEM *)databuffer;
        const FQ_ELEM *in2 = (const FQ_ELEM *)(databuffer + ROW_MUL3_ROW_BYTES);

        uint32_t cycle_start = DWT->CYCCNT;
        __asm__ volatile("" ::: "memory");
        row_mul3(result_workspace.row_mul3, in1, in2);
        __asm__ volatile("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        result_length = ROW_MUL3_OUTPUT_BYTES;
        break;
    }

    // Expand a seed into generator matrix values and column positions.
    // Input: SEED_LENGTH_BYTES bytes.
    // Output: K*(N-K) field elements and N-K column positions.
    case LESS_GENERATOR_SAMPLE: {
        unsigned char seed[SEED_LENGTH_BYTES];
        rref_generator_mat_t *result = &result_workspace.generator_sample;
        memcpy(seed, databuffer, GENERATOR_SAMPLE_INPUT_BYTES);

        uint32_t cycle_start = DWT->CYCCNT;
        generator_sample(result, seed);
        last_cycles = DWT->CYCCNT - cycle_start;

        // Encode column positions as little-endian 16-bit values.
        serialize_positions((uint8_t *)result->column_pos, result->column_pos, N - K);
        result_length = GENERATOR_SAMPLE_OUTPUT_BYTES;
        break;
    }

    // Sample a monomial transformation from a private-key seed.
    // Input: PRIVATE_KEY_SEED_LENGTH_BYTES bytes.
    // Output: N coefficients and a permutation of N positions.
    case LESS_MONOMIAL_SAMPLE_PRIKEY: {
        unsigned char seed[PRIVATE_KEY_SEED_LENGTH_BYTES];
        monomial_t *result = &result_workspace.monomial_sample;
        memcpy(seed, databuffer, MONOMIAL_SAMPLE_INPUT_BYTES);

        uint32_t cycle_start = DWT->CYCCNT;
        monomial_sample_prikey(result, seed);
        last_cycles = DWT->CYCCNT - cycle_start;

        // Encode the permutation as little-endian 16-bit values.
        serialize_positions((uint8_t *)result->permutation, result->permutation, N);
        result_length = MONOMIAL_SAMPLE_OUTPUT_BYTES;
        break;
    }

    // Apply a monomial transformation to a generator matrix.
    // Input: generator matrix, coefficients and permutation.
    // Output: transformed generator matrix.
    // Disabled for Category 3 and 5 due to STM32 memory constraints.
    case LESS_GENERATOR_MONOMIAL_MUL: {
    #if LESS_GENERATOR_MONOMIAL_MUL_SUPPORTED
        monomial_t monomial;
        generator_mat_t *result = &result_workspace.generator_monomial_mul;

        // Parse the generator matrix and monomial data from the input buffer.
        const uint8_t *cursor = databuffer;
        memcpy(generator_input.values, cursor, sizeof(generator_input.values));
        cursor += sizeof(generator_input.values);
        memcpy(monomial.coefficients, cursor, sizeof(monomial.coefficients));
        cursor += sizeof(monomial.coefficients);

        deserialize_positions(monomial.permutation, cursor, N);

        uint32_t cycle_start = DWT->CYCCNT;
        generator_monomial_mul(result, &generator_input, &monomial);
        last_cycles = DWT->CYCCNT - cycle_start;

        result_length = GENERATOR_MONOMIAL_MUL_OUTPUT_BYTES;
        break;
    #else
        led2_off();
        return SS_ERR_CMD;
    #endif
    }

    // Complete key generation, signing and verification
    // Used for static stack analysis.
    case LESS_KEYGEN: {
        LESS_keygen((prikey_t *)databuffer, (pubkey_t *)databuffer);
        break;
    }

    case LESS_SIGN: {
        (void)LESS_sign((const prikey_t *)databuffer, (const char *)databuffer, 0, (sign_t *)databuffer);
        break;
    }

    case LESS_VERIFY: {
        (void)LESS_verify((const pubkey_t *)databuffer, (const char *)databuffer, 0, (const sign_t *)databuffer);
        break;
    }

    default:
        led2_off();
        return SS_ERR_CMD;
    }
    led2_off();
    return SS_ERR_OK;
}

// Receive input data in chunks of up to 160 bytes.
// The subcommand specifies the chunk index in databuffer.
// Reject transfers exceeding the allocated input buffer.
uint8_t set_value(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *x){
    (void)cmd;

    led1_on();

    const uint32_t offset = (uint32_t)scmd * INPUT_CHUNK_SIZE;

    if (len == 0u || len > INPUT_CHUNK_SIZE || offset + len > LESS_MAX_INPUT_BYTES){
        led1_off();
        return SS_ERR_LEN;
    }

    memcpy(databuffer + offset, x, len);

    led1_off();
    return SS_ERR_OK;
}

// Return the last subroutine result in chunks of up to 160 bytes.
// The host specifies the chunk index as a little-endian 16-bit value.
// The final chunk may be shorter than 160 bytes.
uint8_t get_result(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *x){
    (void)cmd;
    (void)scmd;

    if (len != 2u || result_length == 0u){
        return SS_ERR_LEN;
    }

    const uint32_t chunk_index = (uint32_t)x[0] | ((uint32_t)x[1] << 8u);
    const uint32_t offset = chunk_index * OUTPUT_CHUNK_SIZE;

    if (offset >= result_length){
        return SS_ERR_LEN;
    }

    const uint32_t remaining = result_length - offset;
    const uint8_t current_length = (remaining < OUTPUT_CHUNK_SIZE) ? (uint8_t)remaining : (uint8_t)OUTPUT_CHUNK_SIZE;

    simpleserial_put('r', current_length, ((uint8_t *)&result_workspace) + offset);
    return SS_ERR_OK;
}

// Initialize the board and register the SimpleSerial commands.
int main(void){
    platform_init();
    init_uart();
    trigger_setup();
    simpleserial_init();
    cycles_init();

    ledz_init();

    led1_init();
    led2_init();
    led3_init();

    led1_off();
    led2_off();
    led3_off();

#if SS_VER == SS_VER_2_1
    simpleserial_addcmd('s', INPUT_CHUNK_SIZE, set_value);
    simpleserial_addcmd('b', 0, subroutines);
    simpleserial_addcmd('g', 2, get_result);
    simpleserial_addcmd('c', 0, get_cycles);
#else
#error "no SS_VER_1_1 for this"
#endif
    while (1){
        simpleserial_get();
    }
}