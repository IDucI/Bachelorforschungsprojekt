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

// Place the static buffer globally outside the subroutines function to avoid stack overflow
static FP_ELEM matrix_V_tr_buf[K][N - K] allocation;


// -----------------------------------------------------------------------------
// Public-key expansion cache
// -----------------------------------------------------------------------------
// expand_pk() can produce an output larger than one SimpleSerial packet.
// Therefore the result is transferred in several chunks.
// The cache ensures that the expensive public-key expansion is performed only
// once for a given seed. Subsequent chunk requests only read from the already
// expanded matrix.
// -----------------------------------------------------------------------------

static uint8_t expand_pk_seed_cache[KEYPAIR_SEED_LENGTH_BYTES] allocation;
static uint8_t expand_pk_cache_valid = 0;

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
// the subroutines below. Subroutine 0x15 is slightly different because its
// result is normalized in-place directly inside databuffer.
//
// If the subroutine is using chunking it is marked with 
// --- CHUNKING LOGIC BEGIN --- and end with // --- CHUNKING LOGIC END ---
// This approach will be discussed further in the report.
// -----------------------------------------------------------------------------

#define SS_OUTPUT_CHUNK_SIZE 160

#if defined(RSDPG)
// FOR RSDPG SUPPORT: Buffer for generator matrix W to avoid stack overflow
static FZ_ELEM matrix_W_buf[M][N - M];
#endif

// -----------------------------------------------------------------------------
// Help function
// -----------------------------------------------------------------------------
// Copies a chunk from concatenated memory segments into the output buffer. 
// Handles chunk data spanning multiple segments.
// -----------------------------------------------------------------------------
static void copy_output_chunk(
    uint8_t *dst,
    uint32_t offset,
    uint16_t output_len,
    const uint8_t *const segments[],
    const uint32_t segment_lengths[],
    uint8_t segment_count
) {
    uint32_t copied = 0;

    // Skip segments until the global offset falls within the current one.
    for (uint8_t i = 0; i < segment_count && copied < output_len; i++) {
        if (offset >= segment_lengths[i]) {
            offset -= segment_lengths[i];
            continue;
        }

        // Determine how many bytes are available in this segment.
        uint32_t available = segment_lengths[i] - offset;

        // Copy only what is still needed for the requested output chunk.
        uint32_t remaining = output_len - copied;
        uint32_t to_copy = (available < remaining) ? available : remaining;

        memcpy(dst + copied, segments[i] + offset, to_copy);

        // Advance the destination position and continue at the next segment.
        copied += to_copy;
        offset = 0;
    }
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
#define subroutine_expand_digest_to_fixed_weight  0x13
#define subroutine_fz_dz_norm_n                   0x14
#define subroutine_fz_dz_norm_m                   0x15
#define subroutine_expand_pk                      0x16
#define subroutine_expand_sk                      0x17

// -----------------------------------------------------------------------------
// Central subroutine control
// -----------------------------------------------------------------------------

uint8_t subroutines(uint8_t cmd, uint8_t scmd, uint8_t len, uint8_t* x) {
    switch (scmd) {

    // -------------------------------------------------------------------------
    // Subroutine 0x03: Convert Restricted Vector to Fp Element Vector
    // -------------------------------------------------------------------------

    case subroutine_convert_restr_vec_to_fp: {
        led2_on();

        // Local array for converted Fp vector elements
        FP_ELEM result[N];

        // Execute element-wise conversion from FZ vector (in databuffer) to Fp vector
        cross_convert_restr_vec_to_fp(result, (const FZ_ELEM*)databuffer);

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
        
        // Actual function call with 3 arguments:
        cross_restr_vec_by_fp_matrix(result, restr_vector, (FP_ELEM (*)[N-K]) matrix_V_tr);
        
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

    // Pack the FZ vector using the RSDPG-specific packing function.
<<<<<<< Updated upstream
    pack_fz_rsdp_g_vec(result_rsdp_g, (const FZ_ELEM*)databuffer);
=======
    cross_pack_fz_rsdp_g_vec(result_rsdp_g, (const FZ_ELEM*)databuffer);

    __asm volatile ("" ::: "memory");
    last_cycles = DWT->CYCCNT - cycle_start;
>>>>>>> Stashed changes

    // Return the packed vector to the host.
    simpleserial_put('r', DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE, result_rsdp_g);

// Standard variant (RSDP): Use the standard FZ packing format.
#else
    pack_fz_vec(result, (const FZ_ELEM*)databuffer);
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

        // Compress unpacked Fp syndrome vector into bit-packed format
        cross_pack_fp_syn(out, unpacked_input);

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
        
        // Compute element-wise vector subtraction: result = vec_a - vec_b (mod p)
        cross_fz_vec_sub_n(result, restr_vec_a, restr_vec_b);
        
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

        // Perform vector-matrix multiplication
        cross_fp_vec_by_fp_matrix(result, fp_vector, (FP_ELEM (*)[N-K]) matrix_V_tr);

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
        
        // Perform element-wise multiplication: result[i] = vec_a[i] * vec_b[i] (mod p)
        cross_fp_vec_by_fp_vec_pointwise(result, fp_vec_a, fp_vec_b);
        
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

        // Execute module-specific vector subtraction
        cross_fz_vec_sub_m(result, vec_a, vec_b);

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

        // Multiply vector e with generator matrix W to expand dimension M to N
        cross_fz_inf_w_by_fz_matrix(result, vec_e, matrix_W);

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

        // Compute combined scaling operation: result = convert(e) + (chall_1 * u_prime)
        cross_fp_vec_by_restr_vec_scaled(result, vec_e, chall_1, vec_u_prime);

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
    // Subroutine 0x13: Expand Digest to Fixed Weight Vector
    // -------------------------------------------------------------------------

    case subroutine_expand_digest_to_fixed_weight: {
        led2_on();

        // Fixed-weight vector output array of size T
        uint8_t result[T];

        // Hash, expand seed in databuffer into fixed-weight binary position vector
        cross_expand_digest_to_fixed_weight(result, databuffer);

        // --- CHUNKING LOGIC BEGIN ---
        uint16_t chunk_size = SS_OUTPUT_CHUNK_SIZE;
        uint16_t chunk_index = (len >= 1) ? x[0] : 0;
        uint32_t offset = (uint32_t)chunk_index * chunk_size;

        if (offset >= T) {
            led2_off();
            return SS_ERR_LEN;
        }

        uint16_t current_len = (T - offset < chunk_size)
            ? (uint16_t)(T - offset)
            : chunk_size;

        simpleserial_put('r', current_len, result + offset);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x14: Normalize Restricted Vector (In-Place, Dimension N)
    //
    // IMPORTANT:
    // SimpleSerial V2.1 cannot transport all N elements in one packet
    // when N > 249 bytes.
    //
    // Therefore the result is returned in chunks.
    //
    // chunk 0 -> bytes 0 .. 159
    // chunk 1 -> bytes 160 .. N-1
    // -------------------------------------------------------------------------

    case subroutine_fz_dz_norm_n: {
        led2_on();

        // Execute the actual fz_dz_norm_n operation on the input vector.
        //
        // The vector is stored directly in the data buffer and is modified
        // in place by the function.
        cross_fz_dz_norm_n((FZ_ELEM*)databuffer);

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
    // Subroutine 0x15: Normalize M 
    // -------------------------------------------------------------------------

    case subroutine_fz_dz_norm_m: {
#if defined(RSDPG)
        led2_on();

        // In-place normalization of raw elements modulo p across dimension M
        // Ensures element representations strictly conform to canonical range.
        cross_fz_dz_norm_m((FZ_ELEM*)(databuffer));

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

    // -----------------------------------------------------------------------------
    // Subroutine 0x16: Expand Public Key
    // -----------------------------------------------------------------------------
    // The pk expansion is potentially expensive, because the complete public key
    // is larger than the SimpleSerial2 packet limit, the result is transferred 
    // in multiple chunks.
    // IMPORTANT:
    // cross_expand_pk() must only be executed once for a given seed.
    // Otherwise every requested chunk would recompute the complete public key.
    //
    // The cache consists of:
    //   - matrix_V_tr_buf, matrix_W_buf (RSDPG only) and expand_pk_seed_cache
    //
    // Chunk requests only read from the already expanded matrix.
    // -----------------------------------------------------------------------------

    case subroutine_expand_pk: {
        led2_on();

        const uint8_t* seed_pk = (const uint8_t*)databuffer;

        // CACHING MECHANISM:
        // Public key expansion is computationally expensive and produces large matrices.
        // If the requested seed matches the cached seed, skip expansion and reuse matrix_V_tr_buf.
        if (!expand_pk_cache_valid || memcmp(expand_pk_seed_cache, seed_pk, KEYPAIR_SEED_LENGTH_BYTES) != 0) {
#if defined(RSDPG)
        cross_expand_pk(matrix_V_tr_buf, matrix_W_buf, seed_pk);
#else
        cross_expand_pk(matrix_V_tr_buf, seed_pk);
#endif
            // Update cache seed and set validity flag
            memcpy(expand_pk_seed_cache, seed_pk, KEYPAIR_SEED_LENGTH_BYTES);
            expand_pk_cache_valid = 1;
        }

        // --- CHUNKING LOGIC BEGIN ---
        const uint32_t v_len =
            (uint32_t)K * (N - K) * sizeof(FP_ELEM);

        const uint8_t *segments[2];
        uint32_t segment_lengths[2];
        uint8_t segment_count = 1;

        segments[0] = (const uint8_t *)matrix_V_tr_buf;
        segment_lengths[0] = v_len;

#if defined(RSDPG)
        const uint32_t w_len =
            (uint32_t)M * (N - M) * sizeof(FZ_ELEM);

        segments[1] = (const uint8_t *)matrix_W_buf;
        segment_lengths[1] = w_len;
        segment_count = 2;
#endif

        const uint32_t output_len =
            segment_lengths[0]
#if defined(RSDPG)
            + segment_lengths[1]
#endif
            ;

        const uint32_t offset =
            (uint32_t)((len >= 1) ? x[0] : 0)
            * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len =
            (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        uint8_t output_chunk[SS_OUTPUT_CHUNK_SIZE];

        copy_output_chunk(
            output_chunk,
            offset,
            current_len,
            segments,
            segment_lengths,
            segment_count
        );

        simpleserial_put('r', current_len, output_chunk);
        // --- CHUNKING LOGIC END ---

        led2_off();
        return SS_ERR_OK;
    }

    // -------------------------------------------------------------------------
    // Subroutine 0x17: Expand Secret Key (seed_sk -> secret vector e)
    // -------------------------------------------------------------------------

    case subroutine_expand_sk: {
        led2_on();

        // Input: seed for the secret key
        const uint8_t* seed_sk = (const uint8_t*)databuffer;

        // Output 1: secret vector e (placed inside databuffer right after the input seed)
        FZ_ELEM* secret_vec_e = (FZ_ELEM*)(databuffer + KEYPAIR_SEED_LENGTH_BYTES);

#if defined(RSDPG)
        // Local array for temporary e_G_bar vector
        FZ_ELEM secret_vec_e_G[M];

        // Call expand_sk with all 5 required parameters
        cross_expand_sk(secret_vec_e, secret_vec_e_G, matrix_V_tr_buf, matrix_W_buf, seed_sk);
#else
        // RSDP variant: Call expand_sk with 3 parameters
        cross_expand_sk(secret_vec_e, matrix_V_tr_buf, seed_sk);
#endif

        // --- CHUNKING LOGIC BEGIN ---
        const uint32_t e_len =
            (uint32_t)N * sizeof(FZ_ELEM);

        const uint32_t v_len =
            (uint32_t)K * (N - K) * sizeof(FP_ELEM);

        const uint8_t *segments[4];
        uint32_t segment_lengths[4];
        uint8_t segment_count = 2;

        // RSDP output: e_bar || V_tr
        segments[0] = (const uint8_t *)secret_vec_e;
        segment_lengths[0] = e_len;

        segments[1] = (const uint8_t *)matrix_V_tr_buf;
        segment_lengths[1] = v_len;

#if defined(RSDPG)
        // RSDPG output: e_bar || e_G_bar || V_tr || W_mat
        const uint32_t e_G_len =
            (uint32_t)M * sizeof(FZ_ELEM);

        const uint32_t w_len =
            (uint32_t)M * (N - M) * sizeof(FZ_ELEM);

        segments[1] = (const uint8_t *)secret_vec_e_G;
        segment_lengths[1] = e_G_len;

        segments[2] = (const uint8_t *)matrix_V_tr_buf;
        segment_lengths[2] = v_len;

        segments[3] = (const uint8_t *)matrix_W_buf;
        segment_lengths[3] = w_len;

        segment_count = 4;
#endif

        uint32_t output_len = 0;

        for (uint8_t i = 0; i < segment_count; i++) {
            output_len += segment_lengths[i];
        }

        const uint32_t offset =
            (uint32_t)((len >= 1) ? x[0] : 0)
            * SS_OUTPUT_CHUNK_SIZE;

        if (offset >= output_len) {
            led2_off();
            return SS_ERR_LEN;
        }

        const uint16_t current_len =
            (output_len - offset < SS_OUTPUT_CHUNK_SIZE)
            ? (uint16_t)(output_len - offset)
            : SS_OUTPUT_CHUNK_SIZE;

        uint8_t output_chunk[SS_OUTPUT_CHUNK_SIZE];

        copy_output_chunk(
            output_chunk,
            offset,
            current_len,
            segments,
            segment_lengths,
            segment_count
        );

        simpleserial_put('r', current_len, output_chunk);
        // --- CHUNKING LOGIC END ---

        // Invalidate public key cache as state has changed
        expand_pk_cache_valid = 0;

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
