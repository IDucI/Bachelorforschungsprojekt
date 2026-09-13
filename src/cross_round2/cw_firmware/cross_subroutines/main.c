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

#include "parameters.h"
#include "csprng_hash.h"
#include "libcross.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "pack_unpack.h"

// ------------------------------------------------------------------------------------------------------------------------
// Manual declaration of expand_sk so that it is known due to compile problem 
// ------------------------------------------------------------------------------------------------------------------------

#if defined(RSDPG)
    void expand_sk(FZ_ELEM e_bar[N], FZ_ELEM e_G_bar[M], FP_ELEM V_tr[K][N - K], FZ_ELEM W_mat[M][N - M], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
    void expand_pk(FP_ELEM V_tr[K][N-K], FZ_ELEM W_mat[M][N-M], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]);
#else
    void expand_sk(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N - K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
    void expand_pk(FP_ELEM V_tr[K][N-K], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]);
#endif

// -----------------------------------------------------------------------------
// Calculate maximum buffer size for all subroutines 
// -----------------------------------------------------------------------------

// For pure RSDP variants, this is enough for the entire buffer
#define TOTAL_BUFFER_SIZE (KEYPAIR_SEED_LENGTH_BYTES + (K * (N - K)) * sizeof(FP_ELEM) + 256)

// Global shared buffer for SimpleSerial transfer placed in .ccmram
static uint8_t databuffer[TOTAL_BUFFER_SIZE] allocation;

// Place the static buffer globally outside the subroutines function to avoid stack overflow
static FP_ELEM matrix_V_tr_buf[K][N - K];

#if defined(RSDPG)
// FOR RSDPG SUPPORT: Buffer for generator matrix W to avoid stack overflow
static FZ_ELEM matrix_W_buf[M][N - M];
#endif

// -----------------------------------------------------------------------------
// Subroutines-IDs
// -----------------------------------------------------------------------------

#define cross_convert_restr_vec_to_fp 0x03
#define cross_restr_vec_by_fp_matrix 0x04
#define cross_pack_fz_vec 0x05
#define cross_pack_fp_syn 0x06
#define cross_unpack_fz_vec 0x07          
#define cross_fz_vec_sub_n 0x08
#define cross_fp_vec_by_fp_matrix 0x09
#define cross_fp_vec_by_fp_vec_pointwise 0x10
#define cross_fz_vec_sub_m 0x11
#define cross_fz_inf_w_by_fz_matrix 0x12
#define cross_fp_vec_by_restr_vec_scaled 0x13
#define cross_expand_digest_to_fixed_weight 0x14
#define cross_fz_dz_norm_n 0x15
#define cross_fz_dz_norm_m 0x16
#define cross_expand_pk 0x17
#define cross_expand_sk 0x18

// -----------------------------------------------------------------------------
// Central subroutine control
// -----------------------------------------------------------------------------

uint8_t subroutines(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t* x) {
    switch (scmd) {

    // -------------------------------------------------------------------------
    // Subroutine 0x03: Convert Restricted Vector to Fp Element Vector
    // -------------------------------------------------------------------------

    case cross_convert_restr_vec_to_fp: {
        led2_on();

        // The mathematical result has the dimension (N)
        FP_ELEM result[N];

        // Pointer assignment within our received data buffer & read input restricted vector from shared buffer
        FZ_ELEM* restr_input = (FZ_ELEM*)(databuffer);

        // Convert restricted vector elements to full field elements (Fp)
        convert_restr_vec_to_fp(result, restr_input);

        // Return N field elements back to host
        simpleserial_put('r', N * sizeof(FP_ELEM), (uint8_t*)result);
        
        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x04: Multiply Restricted Vector by Fp Matrix Transpose
    // -------------------------------------------------------------------------

    case cross_restr_vec_by_fp_matrix: {
        led2_on();
        
        // The mathematical result has the dimension (N - K)
        FP_ELEM result[N - K];
        
        // Parse input restricted vector and matrix pointer from shared buffer
        FZ_ELEM* restr_vector = (FZ_ELEM*)(databuffer);
        FP_ELEM* matrix_V_tr  = (FP_ELEM*)(databuffer + (N * sizeof(FZ_ELEM)));
        
        // Actual function call with 3 arguments:
        // 1. Output storage, 2. Input vector, 3. Input matrix
        // Perform vector-matrix multiplication: result = restr_vector * V^T
        restr_vec_by_fp_matrix(result, restr_vector, (uint8_t (*)[N-K]) matrix_V_tr);
        
        // Return exactly (N - K) field elements
        simpleserial_put('r', (N - K) * sizeof(FP_ELEM), (uint8_t*)result);
        
        led2_off();
        return SS_ERR_OK;
    }
    // -------------------------------------------------------------------------
    // Subroutine 0x05: Pack Restricted Element Vector (FZ) Into Dense Format
    // Note: This isn't checking a final mathematical result, just testing a helper function.
    // -------------------------------------------------------------------------

    case cross_pack_fz_vec: {
        led2_on();

        // Read unpacked vector from shared buffer
        FZ_ELEM* unpacked_input = (FZ_ELEM*)(databuffer);
        uint8_t out[DENSELY_PACKED_FZ_VEC_SIZE];    

        // Compress unpacked FZ vector into bit-packed representation
        pack_fz_vec(out, unpacked_input);

        // Return packed byte array back to host
        simpleserial_put('r', DENSELY_PACKED_FZ_VEC_SIZE, out);

        led2_off();
        return SS_ERR_OK;
    }
    // -------------------------------------------------------------------------
    // Subroutine 0x06: Pack Syndrome Vector (Fp) Into Dense Format
    // Note: This isn't checking a final mathematical result, just testing a helper function.
    // -------------------------------------------------------------------------

    case cross_pack_fp_syn: {
        led2_on();

        // Read unpacked Fp syndrome vector from shared buffer
        FP_ELEM* unpacked_input = (FP_ELEM*)(databuffer);
        uint8_t out[DENSELY_PACKED_FP_SYN_SIZE]; 

        // Compress unpacked Fp syndrome vector into bit-packed format
        pack_fp_syn(out, unpacked_input);

        // Return packed syndrome byte array back to host
        simpleserial_put('r', DENSELY_PACKED_FP_SYN_SIZE, out);

        led2_off();
        return SS_ERR_OK;
    }
    // -------------------------------------------------------------------------
    // Subroutine 0x07: Unpack Dense Format Into Restricted Element Vector (FZ)
    // -------------------------------------------------------------------------

    case cross_unpack_fz_vec: {
        led2_on();

        // Output unpacked vector has dimension (N)
        FZ_ELEM result[N];

        // Pointer to raw packed bytes in shared buffer
        uint8_t* packed_input = (uint8_t*)(databuffer);

        // Expand packed byte array back into FZ vector elements
        unpack_fz_vec(result, packed_input);

        // Return N unpacked FZ elements back to host
        simpleserial_put('r', N * sizeof(FZ_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x08: Subtract Two Restricted Vectors (Dimension N)
    // -------------------------------------------------------------------------

    case cross_fz_vec_sub_n: {
        led2_on();


        FZ_ELEM result[N];
        
        // Parse the two input vectors from shared buffer
        FZ_ELEM* restr_vec_a = (FZ_ELEM*)(databuffer);
        FZ_ELEM* restr_vec_b = (FZ_ELEM*)(databuffer + (N * sizeof(FZ_ELEM)));
        
        // Compute element-wise vector subtraction: result = vec_a - vec_b (mod p)
        fz_vec_sub_n(result, restr_vec_a, restr_vec_b);
        
        // Return exactly N elements (of type FZ_ELEM)
        simpleserial_put('r', N * sizeof(FZ_ELEM), (uint8_t*)result);
        
        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x09: Multiply Fp Vector by Fp Matrix Transpose
    // -------------------------------------------------------------------------

    case cross_fp_vec_by_fp_matrix: {
        led2_on();

        FP_ELEM result[N - K];

        // Parse input vector and matrix pointer from shared buffer
        FP_ELEM* fp_vector = (FP_ELEM*)(databuffer);
        FP_ELEM* matrix_V_tr = (FP_ELEM*)(databuffer + (N * sizeof(FP_ELEM)));

        // Perform vector-matrix multiplication: result = fp_vector * V^T
        fp_vec_by_fp_matrix(result, fp_vector, (uint8_t (*)[N-K]) matrix_V_tr);

        // Return (N - K) field elements back to host
        simpleserial_put('r', (N - K) * sizeof(FP_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x10: Pointwise Multiplication of Two Fp Vectors
    // -------------------------------------------------------------------------

    case cross_fp_vec_by_fp_vec_pointwise: {
        led2_on();

        FP_ELEM result[N];
        
        // Set pointer to the two input vectors in the data buffer
        FP_ELEM* fp_vec_a = (FP_ELEM*)(databuffer);
        FP_ELEM* fp_vec_b = (FP_ELEM*)(databuffer + (N * sizeof(FP_ELEM)));
        
        // Call the pointwise multiplication of the shared library
        fp_vec_by_fp_vec_pointwise(result, fp_vec_a, fp_vec_b);
        
        // Send the result (N elements of type FP_ELEM) back to Python
        simpleserial_put('r', N * sizeof(FP_ELEM), (uint8_t*)result);
    
        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x11: Vector Subtraction M 
    // -------------------------------------------------------------------------

     case cross_fz_vec_sub_m: {
#if defined(RSDPG)

        led2_on();

        // Interpret shared buffer as contiguous array of FZ elements
        FZ_ELEM* all_elements = (FZ_ELEM*)databuffer;

        // Extract vector A  and vector B
        FZ_ELEM* vec_a = all_elements;
        FZ_ELEM* vec_b = all_elements + M;
        FZ_ELEM result[M];

        // Execute module-specific vector subtraction
        fz_vec_sub_m(result, vec_a, vec_b);

        simpleserial_put('r', M * sizeof(FZ_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
#else
        return SS_ERR_CMD;
#endif
    } 

    // -------------------------------------------------------------------------
    // Subroutine 0x12: Matrix Multiplication W (only for RSDPG)
    // -------------------------------------------------------------------------

    case cross_fz_inf_w_by_fz_matrix: {
#if defined(RSDPG)
        led2_on();

        FZ_ELEM* all_elements = (FZ_ELEM*)databuffer;

        // Extract input vector e (dimension M) from databuffer
        const FZ_ELEM* vec_e = all_elements;

        // Cast remaining databuffer slice to 2D matrix structure W of size [M x (N - M)]
        FZ_ELEM (*matrix_W)[N - M] = (FZ_ELEM(*)[N - M])(all_elements + M);
        FZ_ELEM result[N];

        // Perform specialized product of Restricted Vector e with generator matrix W
        // Expanding length M input to full length N representation.
        fz_inf_w_by_fz_matrix(result, vec_e, matrix_W);

        simpleserial_put('r', N * sizeof(FZ_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
#else
        return SS_ERR_CMD;
#endif
    } 

    // -------------------------------------------------------------------------
    // Subroutine 0x13: Scaled Vector Addition (Fp Vector by Restricted Vector)
    // -------------------------------------------------------------------------

    case cross_fp_vec_by_restr_vec_scaled: {
        led2_on();

        FP_ELEM result[N];

        // Extract 3 arguments from contiguous shared buffer:
        // Vector e (length N)
        const FZ_ELEM* vec_e = (const FZ_ELEM*)(databuffer);

        // Scalar challenge_1
        uint32_t offset_chall = N * sizeof(FZ_ELEM);
        FP_ELEM chall_1 = *(FP_ELEM*)(databuffer + offset_chall);

        // Vector u_prime (length N - K)
        uint32_t offset_u_prime = offset_chall + sizeof(FP_ELEM);
        const FP_ELEM* vec_u_prime = (const FP_ELEM*)(databuffer + offset_u_prime);

        // Perform combined scaling operation
        fp_vec_by_restr_vec_scaled(result, vec_e, chall_1, vec_u_prime);

        // Return N field elements back to host
        simpleserial_put('r', N * sizeof(FP_ELEM), (uint8_t*)result);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x14: Expand Digest to Fixed Weight Vector
    // -------------------------------------------------------------------------

    case cross_expand_digest_to_fixed_weight: {
        led2_on();

        uint8_t result[T];

        // Expand input seed/digest in shared buffer into fixed-weight vector
        expand_digest_to_fixed_weight(result, databuffer);

        // Send result back to Python (T bytes)
        simpleserial_put('r', T * sizeof(uint8_t), result);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x15: Normalize Restricted Vector (In-Place, Dimension N)
    // -------------------------------------------------------------------------

    case cross_fz_dz_norm_n: {
        led2_on();

        // Normalize raw representation into standard range in-place
        fz_dz_norm_n( (FZ_ELEM*)(databuffer));

        // Return normalized N elements back to host
        simpleserial_put('r', N * sizeof(FZ_ELEM), databuffer);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x16: Normalize M 
    // -------------------------------------------------------------------------

    case cross_fz_dz_norm_m: {
#if defined(RSDPG)
        led2_on();

        // In-place normalization of raw elements modulo p across dimension M
        // Ensures element representations strictly conform to canonical range.
        fz_dz_norm_m((FZ_ELEM*)(databuffer));

        // Transmit normalized vector of length M back 
        simpleserial_put('r', M * sizeof(FZ_ELEM), databuffer);

        led2_off();
        return SS_ERR_OK;
#else
        return SS_ERR_CMD;
#endif
    } 

    // -------------------------------------------------------------------------
    // Subroutine 0x17: Expand Public Key
    // -------------------------------------------------------------------------

    case cross_expand_pk: {
        led2_on();

        const uint8_t* seed_pk = (const uint8_t*)databuffer;
        
#if defined(RSDPG)
        // FOR RSDPG SUPPORT: Pass additional matrix_W_buf parameter
        expand_pk(matrix_V_tr_buf, matrix_W_buf, seed_pk);
#else
        expand_pk(matrix_V_tr_buf, seed_pk);
#endif

        uint16_t pk_len = (uint16_t)(K * (N - K) * sizeof(FP_ELEM));
        uint8_t* data_ptr = (uint8_t*)matrix_V_tr_buf;

        // The chunk index arrives as the first payload byte (x[0]); defaults to 0 if no payload was sent. Chunking is required here because 
        // the full matrix (up to several KB) exceeds SimpleSerial2's single-packet limit (~249 bytes) - each chunk is requested via its own 'b' call.
        uint16_t chunk_size = 200;  // safely under the ~249-byte SSv2.1 limit
        uint16_t chunk_index = (len >= 1) ? x[0] : 0;
        uint32_t offset = (uint32_t)chunk_index * chunk_size;

        if (offset >= pk_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        uint16_t current_len = (pk_len - offset < chunk_size) ? (uint16_t)(pk_len - offset) : chunk_size;
        simpleserial_put('r', current_len, data_ptr + offset);

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x18: Expand Secret Key (seed_sk -> secret vector e)
    // -------------------------------------------------------------------------

    case cross_expand_sk: {
        led2_on();

        // Input: seed for the secret key
        const uint8_t* seed_sk = (const uint8_t*)databuffer;

        // Output 1: secret vector e (placed inside databuffer right after the input seed)
        FZ_ELEM* secret_vec_e = (FZ_ELEM*)(databuffer + KEYPAIR_SEED_LENGTH_BYTES);

#if defined(RSDPG)
        // Local array for temporary e_G_bar vector
        FZ_ELEM secret_vec_e_G[M];

        // Call expand_sk with all 5 required parameters
        expand_sk(secret_vec_e, secret_vec_e_G, matrix_V_tr_buf, matrix_W_buf, seed_sk);
#else
        // RSDP variant: Call expand_sk with 3 parameters
        expand_sk(secret_vec_e, matrix_V_tr_buf, seed_sk);
#endif

        // Return the expanded secret vector e back to the host
        simpleserial_put('r', N * sizeof(FZ_ELEM), (uint8_t*)secret_vec_e);

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

// -----------------------------------------------------------------------------
// SimpleSerial Handlers & Main Loop
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
