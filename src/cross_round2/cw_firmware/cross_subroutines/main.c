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

#include "stm32f4xx.h"
#include "system_stm32f4xx.h"
#include "simpleserial.h"

#include "ledz.h"

#include "parameters.h"
#include "libcross.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "pack_unpack.h"

// -----------------------------------------------------------------------------
// Calculate maximum buffer size for all subroutines 
// -----------------------------------------------------------------------------
// These buffers are allocated statically to avoid placing large temporary
// objects on the stack. The CCMRAM section is used for the main communication
// and matrix buffers to reduce pressure on the regular SRAM/stack.
// -----------------------------------------------------------------------------

// For pure RSDP variants, this is enough for the entire buffer
#define TOTAL_BUFFER_SIZE (KEYPAIR_SEED_LENGTH_BYTES + (K * (N - K)) * sizeof(FP_ELEM) + 256)

// Global shared buffer for SimpleSerial transfer placed in .ccmram
static uint8_t databuffer[TOTAL_BUFFER_SIZE] allocation;

// Stores the cycle count measured for the most recently executed subroutine.
static uint32_t last_cycles = 0u;

// -----------------------------------------------------------------------------
// SimpleSerial output chunking
// -----------------------------------------------------------------------------
// SimpleSerial V2.1 cannot transport large result buffers in a single response.
// Therefore, subroutines with outputs larger than the packet size return their
// results in multiple 160-byte chunks.
//
// The host specifies the requested chunk using x[0]. The firmware calculates
// the corresponding byte offset and transmits only that slice of the result.
//
// This chunking mechanism is used consistently for large outputs throughout
// the subroutines below. Subroutines 0x13-0x15 are handled slightly different, 
// because they operate in-place on vectors stored in databuffer.
// Their output is therefore transmitted directly from databuffer rather
// than from a separate result buffer.
//
// If the subroutine is using chunking it is marked with 
// --- CHUNKING LOGIC BEGIN --- and end with // --- CHUNKING LOGIC END ---
// This approach will be discussed further in the report.
// -----------------------------------------------------------------------------

#define SS_OUTPUT_CHUNK_SIZE 160

// -----------------------------------------------------------------------------
// Cycle counter initialization and readout
// -----------------------------------------------------------------------------
// The Cortex-M DWT cycle counter is used to measure the execution time of
// individual subroutines in CPU cycles.
//
// The counter is enabled once during initialization. Each subroutine records
// the counter before and after the mathematical operation and stores the
// difference in last_cycles.
//
// Reading the measurement separately prevents the result-transfer operation
// from being included in the measured execution time.
// -----------------------------------------------------------------------------

static void cycles_init(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;

    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

// Return the last DWT cycle count and CPU clock frequency.
// Both values are transmitted as little-endian 32-bit integers.
static uint8_t get_cycles( uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t *x) {
    (void)cmd;
    (void)scmd;
    (void)len;
    (void)x;

    uint8_t data[8];
    uint32_t values[2] = {last_cycles, SystemCoreClock};
    for (unsigned i = 0; i < 2u; i++) {
        for (unsigned b = 0; b < 4u; b++) {
            data[4u * i + b] = (uint8_t)(values[i] >> (8u * b));
        }
    }
    simpleserial_put('r', sizeof(data), data);
    return SS_ERR_OK;
}

// -----------------------------------------------------------------------------
// Subroutines-IDs
// -----------------------------------------------------------------------------

#define subroutine_convert_restr_vec_to_fp        0x03
#define subroutine_restr_vec_by_fp_matrix         0x04
#define subroutine_pack_fz_vec                    0x05
#define subroutine_pack_fp_syn                    0x06     
#define subroutine_fz_vec_sub_n                   0x07
#define subroutine_fp_vec_by_fp_matrix            0x08
#define subroutine_fp_vec_by_fp_vec_pointwise     0x09
#define subroutine_fz_vec_sub_m                   0x10
#define subroutine_fz_inf_w_by_fz_matrix          0x11
#define subroutine_fp_vec_by_restr_vec_scaled     0x12
#define subroutine_fz_dz_norm_n                   0x13
#define subroutine_fz_dz_norm_m                   0x14
#define subroutine_fp_dz_norm_synd                0x15

// -----------------------------------------------------------------------------
// Central subroutine control
// -----------------------------------------------------------------------------

uint8_t subroutines(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t* x) {
    last_cycles = 0u;
    switch (scmd) {

    // -------------------------------------------------------------------------
    // Subroutine 0x03: Convert Restricted Vector to Fp Element Vector
    // -------------------------------------------------------------------------

    case subroutine_convert_restr_vec_to_fp: {
        led2_on();

        // Local array for converted Fp vector elements
        FP_ELEM result[N];

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Execute element-wise conversion from FZ vector (in databuffer) to Fp vector
        cross_convert_restr_vec_to_fp(result, (const FZ_ELEM*)databuffer);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // --- CHUNKING LOGIC BEGIN ---
        const uint16_t output_len = (uint16_t)(N * sizeof(FP_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        // Bound-check: verify that requested offset does not exceed total data size
        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        // Compute transmission length: send 160 bytes or remaining trailing bytes
        const uint16_t current_len = (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
                ? (uint16_t)(output_len - offset)
                : SS_OUTPUT_CHUNK_SIZE;

        // Transmit requested slice over SimpleSerial response command 'r'
        simpleserial_put('r', current_len, ((uint8_t*)result) + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x04: Multiply Restricted Vector by Fp Matrix Transpose
    // -------------------------------------------------------------------------

    case subroutine_restr_vec_by_fp_matrix: {
        led2_on();
        
        // The mathematical result has the dimension (N - K)
        FP_ELEM result[N - K];
        
        // Parse input restricted vector and matrix pointer from shared buffer
        FZ_ELEM* restr_vector = (FZ_ELEM*)(databuffer);
        FP_ELEM* matrix_V_tr  = (FP_ELEM*)(databuffer + (N * sizeof(FZ_ELEM)));

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;
        
        // Actual function call with 3 arguments:
        cross_restr_vec_by_fp_matrix(result, restr_vector, (FP_ELEM (*)[N-K]) matrix_V_tr);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;
        
        // Return exactly (N - K) field elements
        simpleserial_put('r', (N - K) * sizeof(FP_ELEM), (uint8_t*)result);
        
        led2_off();
        return SS_ERR_OK;
    }
    // -------------------------------------------------------------------------
    // Subroutine 0x05: Pack Restricted Element Vector (FZ) Into Dense Format
    // Note: This isn't checking a final mathematical result, just testing a helper function.
    // -------------------------------------------------------------------------

    case subroutine_pack_fz_vec: {
        led2_on();

        uint8_t result[DENSELY_PACKED_FZ_VEC_SIZE];

// Generator variant (RSDPG): Pack FZ vector using generator-specific packing layout
#if defined(RSDPG)
    uint8_t result_rsdp_g[DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE];

    __asm volatile ("" ::: "memory");
    uint32_t cycle_start = DWT->CYCCNT;

    // Pack the FZ vector using the RSDPG-specific packing function.
    cross_pack_fz_rsdp_g_vec(result_rsdp_g, (const FZ_ELEM*)databuffer);

    __asm volatile ("" ::: "memory");
    last_cycles = DWT->CYCCNT - cycle_start;

    __asm volatile ("" ::: "memory");
    last_cycles = DWT->CYCCNT - cycle_start;

    // Return the packed vector to the host.
    simpleserial_put('r', DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE, result_rsdp_g);

// Standard variant (RSDP): Use the standard FZ packing format.
#else
    __asm volatile ("" ::: "memory");
    uint32_t cycle_start = DWT->CYCCNT;

    cross_pack_fz_vec(result, (const FZ_ELEM*)databuffer);
 
    __asm volatile ("" ::: "memory");
    last_cycles = DWT->CYCCNT - cycle_start;

    simpleserial_put('r', DENSELY_PACKED_FZ_VEC_SIZE, result);
#endif

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x06: Pack Syndrome Vector (Fp) Into Dense Format
    // Note: This isn't checking a final mathematical result, just testing a helper function.
    // -------------------------------------------------------------------------

    case subroutine_pack_fp_syn: {
        led2_on();

        // Read unpacked Fp syndrome vector from shared buffer
        FP_ELEM* unpacked_input = (FP_ELEM*)(databuffer);
        uint8_t out[DENSELY_PACKED_FP_SYN_SIZE]; 

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Compress unpacked Fp syndrome vector into bit-packed format
        cross_pack_fp_syn(out, unpacked_input);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // Return packed syndrome byte array back to host
        simpleserial_put('r', DENSELY_PACKED_FP_SYN_SIZE, out);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x07: Subtract Two Restricted Vectors (Dimension N)
    // -------------------------------------------------------------------------

    case subroutine_fz_vec_sub_n: {
        led2_on();

        FZ_ELEM result[N];
        
        // Slice input vectors a and b sequentially from shared databuffer
        FZ_ELEM* restr_vec_a = (FZ_ELEM*)(databuffer);
        FZ_ELEM* restr_vec_b = (FZ_ELEM*)(databuffer + (N * sizeof(FZ_ELEM)));

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;
        
        // Compute element-wise vector subtraction: result = vec_a - vec_b (mod p)
        cross_fz_vec_sub_n(result, restr_vec_a, restr_vec_b);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;
        
        const uint16_t output_len = (uint16_t)(N * sizeof(FZ_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len = (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        simpleserial_put('r',current_len,((uint8_t*)result) + offset);
        
        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x08: Multiply Fp Vector by Fp Matrix Transpose
    // -------------------------------------------------------------------------

    case subroutine_fp_vec_by_fp_matrix: {
        led2_on();

        FP_ELEM result[N - K];

        // Parse/Extract input vector and matrix pointer from shared buffer
        FP_ELEM* fp_vector = (FP_ELEM*)(databuffer);
        FP_ELEM* matrix_V_tr = (FP_ELEM*)(databuffer + (N * sizeof(FP_ELEM)));

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Perform vector-matrix multiplication
        cross_fp_vec_by_fp_matrix(result, fp_vector, (FP_ELEM (*)[N-K]) matrix_V_tr);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // Return (N - K) field elements back to host
        simpleserial_put('r', (N - K) * sizeof(FP_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x09: Pointwise Multiplication of Two Fp Vectors
    // -------------------------------------------------------------------------

    case subroutine_fp_vec_by_fp_vec_pointwise: {
        led2_on();

        FP_ELEM result[N];
        
        // Slice input vectors a and b from shared databuffer
        FP_ELEM* fp_vec_a = (FP_ELEM*)(databuffer);
        FP_ELEM* fp_vec_b = (FP_ELEM*)(databuffer + (N * sizeof(FP_ELEM)));

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;
        
        // Perform element-wise multiplication: result[i] = vec_a[i] * vec_b[i] (mod p)
        cross_fp_vec_by_fp_vec_pointwise(result, fp_vec_a, fp_vec_b);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;
        
        // --- CHUNKING LOGIC BEGIN ---
        const uint16_t output_len = (uint16_t)(N * sizeof(FP_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len = (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        simpleserial_put('r',current_len,((uint8_t*)result) + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x10: Vector Subtraction M 
    // -------------------------------------------------------------------------

     case subroutine_fz_vec_sub_m: {
#if defined(RSDPG)

        led2_on();

        // Interpret shared buffer as contiguous array of FZ elements
        FZ_ELEM* all_elements = (FZ_ELEM*)databuffer;

        // Extract vector A  and vector B
        FZ_ELEM* vec_a = all_elements;
        FZ_ELEM* vec_b = all_elements + M;
        FZ_ELEM result[M];

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Execute module-specific vector subtraction
        cross_fz_vec_sub_m(result, vec_a, vec_b);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        simpleserial_put('r', M * sizeof(FZ_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
#else
        return SS_ERR_CMD;
#endif
    } 

    // -------------------------------------------------------------------------
    // Subroutine 0x11: Matrix Multiplication W (only for RSDPG)
    // -------------------------------------------------------------------------

    case subroutine_fz_inf_w_by_fz_matrix: {
#if defined(RSDPG)
        led2_on();

        FZ_ELEM* all_elements = (FZ_ELEM*)databuffer;

        // Extract input vector e (dimension M) from databuffer
        const FZ_ELEM* vec_e = all_elements;

        // Cast remaining databuffer slice to 2D matrix structure W of size [M x (N - M)]
        FZ_ELEM (*matrix_W)[N - M] = (FZ_ELEM(*)[N - M])(all_elements + M);
        FZ_ELEM result[N];

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Multiply vector e with generator matrix W to expand dimension M to N
        cross_fz_inf_w_by_fz_matrix(result, vec_e, matrix_W);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // --- CHUNKING LOGIC BEGIN ---
        const uint16_t output_len = (uint16_t)(N * sizeof(FZ_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len = (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        simpleserial_put('r',current_len,((uint8_t*)result) + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
#else
        return SS_ERR_CMD;
#endif
    } 

    // -------------------------------------------------------------------------
    // Subroutine 0x12: Scaled Vector Addition (Fp Vector by Restricted Vector)
    // -------------------------------------------------------------------------

    case subroutine_fp_vec_by_restr_vec_scaled: {
        led2_on();

        FP_ELEM result[N];

        // Extract 3 arguments from contiguous shared buffer:
        // Vector e (length N)
        const FZ_ELEM* vec_e = (const FZ_ELEM*)(databuffer);

        // Parse challenge scalar and vector arguments sequentially
        uint32_t offset_chall = N * sizeof(FZ_ELEM);
        FP_ELEM chall_1 = *(FP_ELEM*)(databuffer + offset_chall);

        // Vector u_prime (dimension N - K)
        uint32_t offset_u_prime = offset_chall + sizeof(FP_ELEM);
        const FP_ELEM* vec_u_prime = (const FP_ELEM*)(databuffer + offset_u_prime);

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Compute combined scaling operation: result = convert(e) + (chall_1 * u_prime)
        cross_fp_vec_by_restr_vec_scaled(result, vec_e, chall_1, vec_u_prime);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // --- CHUNKING LOGIC BEGIN ---
        const uint16_t output_len = (uint16_t)(N * sizeof(FP_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len = (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        simpleserial_put('r',current_len,((uint8_t*)result) + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x13: Normalize Restricted Vector (In-Place, Dimension N)
    // -------------------------------------------------------------------------

    case subroutine_fz_dz_norm_n: {
        led2_on();

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Execute the actual fz_dz_norm_n operation on the input vector.
        //
        // The vector is stored directly in the data buffer and is modified
        // in place by the function.
        cross_fz_dz_norm_n((FZ_ELEM*)databuffer);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // --- CHUNKING LOGIC BEGIN ---
        // The normalized vector is already stored in databuffer.
        // Only the requested 160-byte slice is transmitted.
        uint16_t chunk_index = (len >= 1) ? x[0] : 0;

        uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        uint16_t total_output_size = N * sizeof(FZ_ELEM);

        if (offset >= total_output_size) {
            led2_off();
            return SS_ERR_LEN;
        }
        uint16_t current_len = (total_output_size - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(total_output_size - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        // Transmit normalized slice directly from databuffer
        simpleserial_put('r', current_len, ((uint8_t*)databuffer) + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x14: Normalize M (In-Place)
    // -------------------------------------------------------------------------

    case subroutine_fz_dz_norm_m: {
#if defined(RSDPG)
        led2_on();

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // In-place normalization of raw elements modulo p across dimension M
        // Ensures element representations strictly conform to canonical range.
        cross_fz_dz_norm_m((FZ_ELEM*)(databuffer));

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // --- CHUNKING LOGIC BEGIN ---
        const uint16_t output_len = (uint16_t)(M * sizeof(FZ_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset = (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len = (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        simpleserial_put('r', current_len, ((uint8_t*)databuffer) + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
#else
        return SS_ERR_CMD;
#endif
    } 
    // -------------------------------------------------------------------------
    // Subroutine 0x15: Normalize Fp Syndrome Vector (In-Place)
    // -------------------------------------------------------------------------

    case subroutine_fp_dz_norm_synd: {
        led2_on();

        // The syndrome vector is stored directly in databuffer.
        FP_ELEM* syndrome = (FP_ELEM*)databuffer;

        __asm volatile ("" ::: "memory");
        uint32_t cycle_start = DWT->CYCCNT;

        // Normalize the syndrome vector in place.
        cross_fp_dz_norm_synd(syndrome);

        __asm volatile ("" ::: "memory");
        last_cycles = DWT->CYCCNT - cycle_start;

        // --- CHUNKING LOGIC BEGIN ---
        const uint16_t output_len =
            (uint16_t)((N - K) * sizeof(FP_ELEM));

        const uint8_t chunk_index = (len >= 1) ? x[0] : 0;

        const uint32_t offset =
            (uint32_t)chunk_index * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len =
            (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
                ? (uint16_t)(output_len - offset)
                : SS_OUTPUT_CHUNK_SIZE;

        // Transmit the requested part of the normalized syndrome.
        simpleserial_put(
            'r',
            current_len,
            ((uint8_t*)syndrome) + offset
        );
        // --- CHUNKING LOGIC END ---

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

// ----------------------------------------------------------------------------
// That was provided to us, but a small explaination from us:
// The host transfers large inputs in 160-byte packets.
// The packet index encoded in scmd determines the destination offset
// within the shared databuffer.
// -----------------------------------------------------------------------------

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
    cycles_init();

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

    simpleserial_addcmd('c', 0, get_cycles);

    // victim metadata readout
   //simpleserial_addcmd('m', 0, metainfo);
#else
#error "no SS_VER_1_1 for this"
#endif

    while (1) {
        simpleserial_get();
    }
}
