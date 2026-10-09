#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "parameters.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "pack_unpack.h"
#include "csprng_hash.h"
#include "CROSS.h"

// ========================================================================== 
// Manual declaration of expand_sk/pk. The required declarations aren't 
// available through the included headers                                                 
// ==========================================================================

#if defined(RSDP)
void expand_pk(
    FP_ELEM V_tr[K][N-K],
    const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]
);
void expand_sk(
    FZ_ELEM e_bar[N],
    FP_ELEM V_tr[K][N-K],
    const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]
);
#elif defined(RSDPG)
void expand_pk(
    FP_ELEM V_tr[K][N-K],
    FZ_ELEM W_mat[M][N-M],
    const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]
);
void expand_sk(
    FZ_ELEM e_bar[N],
    FZ_ELEM e_G_bar[M],
    FP_ELEM V_tr[K][N-K],
    FZ_ELEM W_mat[M][N-M],
    const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]
);
#endif

// Repeat the benchmark to amplify the measured workload and reduce the relative impact of fixed process overhead.
#define ITERATIONS 1000

//Prevent the compiler from removing the benchmark result.
static volatile uint64_t benchmark_sink = 0;

// ========================================================================== 
// Helper functions                                                           
// ========================================================================== 

// Fill an FZ vector with deterministic test values.
static void fill_fz(FZ_ELEM *data, size_t length){
    for (size_t i = 0; i < length; i++) {
        data[i] = (FZ_ELEM)(i % (Z + 1));
    }
}

// Fill an FP vector or matrix with deterministic test values. 
static void fill_fp(FP_ELEM *data, size_t length){
    for (size_t i = 0; i < length; i++) {
        // The generated values are reduced modulo P to obtain valid FP elements.
        data[i] = (FP_ELEM)((i * 3 + 1) % P);
    }
}

// Fill a byte buffer with deterministic test data.
static void fill_bytes(uint8_t *data, size_t length){
    for (size_t i = 0; i < length; i++) {
        data[i] = (uint8_t)(i * 17u + 31u);
    }
}

// Consume a byte buffer so the compiler cannot optimize away the result.
static void consume_bytes(const uint8_t *data, size_t length){
    uint64_t sum = 0;
    for (size_t i = 0; i < length; i++) {
        sum += data[i];
    }
    benchmark_sink = benchmark_sink + sum;
}

// Consume an FZ vector.
static void consume_fz(const FZ_ELEM *data, size_t length){
    uint64_t sum = 0;
    for (size_t i = 0; i < length; i++) {
        sum += data[i];
    }
    benchmark_sink = benchmark_sink + sum;
}

// Consume an FP vector.
static void consume_fp(const FP_ELEM *data, size_t length){
    uint64_t sum = 0;
    for (size_t i = 0; i < length; i++) {
        sum += data[i];
    }
    benchmark_sink = benchmark_sink + sum;
}


// ==========================================================================
// Benchmark implementations for complete CROSS operations
// ==========================================================================

#if defined(BENCH_CROSS_KEYGEN)
static void benchmark_CROSS_keygen(void){

    sk_t SK;
    pk_t PK;

    // Execute the complete CROSS key generation routine. The resulting secret and public key material is 
    // consumed afterwards to prevent the compiler from removing the computation.
    for (int i = 0; i < ITERATIONS; i++) {
        CROSS_keygen(&SK, &PK);
    }

    consume_bytes(
        SK.seed_sk,
        KEYPAIR_SEED_LENGTH_BYTES
    );

    consume_bytes(
        PK.seed_pk,
        KEYPAIR_SEED_LENGTH_BYTES
    );

    consume_bytes(
        PK.s,
        DENSELY_PACKED_FP_SYN_SIZE
    );
}
#endif


#if defined(BENCH_CROSS_SIGN)
static void benchmark_CROSS_sign(void){

    sk_t SK;
    CROSS_sig_t sig;

    // Generate a valid secret key once before the benchmark. Key generation itself is not part of the sign measurement.
    pk_t PK;
    CROSS_keygen(&SK, &PK);

    const char message[] = "Cachegrind benchmark message";
    const uint64_t message_length = sizeof(message) - 1;

    // Execute the complete CROSS signing routine repeatedly. This includes all operations performed internally by CROSS_sign().
    for (int i = 0; i < ITERATIONS; i++) {
        CROSS_sign(
            &SK,
            message,
            message_length,
            &sig
        );
    }

    // Consume the generated signature so that the compiler cannot remove the benchmarked computation.
    consume_bytes(
        (const uint8_t *)&sig,
        sizeof(CROSS_sig_t)
    );
}
#endif


#if defined(BENCH_CROSS_VERIFY)
static void benchmark_CROSS_verify(void){

    sk_t SK;
    pk_t PK;
    CROSS_sig_t sig;

    const char message[] = "Cachegrind benchmark message";
    const uint64_t message_length = sizeof(message) - 1;

    // Generate a valid key pair and signature once before the benchmark. These preparation steps are not measured
    // as part of CROSS_verify().
    CROSS_keygen(&SK, &PK);

    CROSS_sign(
        &SK,
        message,
        message_length,
        &sig
    );

    // Execute the complete CROSS verification routine repeatedly.
    for (int i = 0; i < ITERATIONS; i++) {
        int result = CROSS_verify(
            &PK,
            message,
            message_length,
            &sig
        );

        // Include the verification result in the benchmark sink so that the compiler cannot remove the call.
        benchmark_sink += (uint64_t)result;
    }
}
#endif

// ========================================================================== 
// Benchmark implementations for selected subroutines                                    
// ========================================================================== 

#if defined(BENCH_CONVERT_RESTR_VEC_TO_FP)
static void benchmark_convert_restr_vec_to_fp(void){
    FZ_ELEM input[N];
    FP_ELEM output[N];

    fill_fz(input, N);
    for (int i = 0; i < ITERATIONS; i++) {
        convert_restr_vec_to_fp(output, input);
    }
    consume_fp(output, N);
}
#endif


#if defined(BENCH_RESTR_VEC_BY_FP_MATRIX)
static void benchmark_restr_vec_by_fp_matrix(void){
    // Input
    FZ_ELEM vector[N];
    FP_ELEM matrix[K][N - K];
    // Output
    FP_ELEM output[N - K];

    fill_fz(vector, N);
    fill_fp(&matrix[0][0], K * (N - K));
    for (int i = 0; i < ITERATIONS; i++) {
        restr_vec_by_fp_matrix(output, vector, matrix);
    }
    consume_fp(output, N - K);
}
#endif


#if defined(BENCH_FP_VEC_BY_FP_VEC_POINTWISE)
static void benchmark_fp_vec_by_fp_vec_pointwise(void){
    FP_ELEM input_a[N];
    FP_ELEM input_b[N];
    FP_ELEM output[N];

    fill_fp(input_a, N);
    fill_fp(input_b, N);
    for (int i = 0; i < ITERATIONS; i++) {
        fp_vec_by_fp_vec_pointwise(output, input_a, input_b);
    }
    consume_fp(output, N);
}
#endif


#if defined(BENCH_FP_VEC_BY_FP_MATRIX)
static void benchmark_fp_vec_by_fp_matrix(void){
    FP_ELEM vector[N];
    FP_ELEM matrix[K][N - K];
    FP_ELEM output[N - K];

    fill_fp(vector, N);
    fill_fp(&matrix[0][0], K * (N - K));
    for (int i = 0; i < ITERATIONS; i++) {
        fp_vec_by_fp_matrix(output, vector, matrix);
    }
    consume_fp(output, N - K);
}
#endif


#if defined(BENCH_FZ_VEC_SUB_N)
static void benchmark_fz_vec_sub_n(void){
    FZ_ELEM input_a[N];
    FZ_ELEM input_b[N];
    FZ_ELEM output[N];

    fill_fz(input_a, N);
    fill_fz(input_b, N);
    for (int i = 0; i < ITERATIONS; i++) {
        fz_vec_sub_n(output, input_a, input_b);
    }
    consume_fz(output, N);
}
#endif


#if defined(BENCH_EXPAND_SK)
static void benchmark_expand_sk(void){
    uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES];

    fill_bytes(seed_sk, sizeof(seed_sk));

#if defined(RSDPG)
    FZ_ELEM e_bar[N];
    FZ_ELEM e_G_bar[M];
    FP_ELEM V_tr[K][N - K];
    FZ_ELEM W_mat[M][N - M];
    for (int i = 0; i < ITERATIONS; i++) {
        expand_sk(e_bar, e_G_bar, V_tr, W_mat, seed_sk);
    }
    consume_fz(e_bar, N);
    consume_fz(e_G_bar, M);
    consume_fp(&V_tr[0][0], K * (N - K));
    consume_fz(&W_mat[0][0], M * (N - M));
#else
    FZ_ELEM e_bar[N];
    FP_ELEM V_tr[K][N - K];
    for (int i = 0; i < ITERATIONS; i++) {
        expand_sk(e_bar, V_tr, seed_sk);
    }
    consume_fz(e_bar, N);
    consume_fp(&V_tr[0][0], K * (N - K));
#endif
}
#endif


#if defined(BENCH_FZ_DZ_NORM_N)
static void benchmark_fz_dz_norm_n(void){
    FZ_ELEM vector[N];

    fill_fz(vector, N);
    for (int i = 0; i < ITERATIONS; i++) {
        fz_dz_norm_n(vector);
    }
    consume_fz(vector, N);
}
#endif


#if defined(BENCH_FP_VEC_BY_RESTR_VEC_SCALED)
static void benchmark_fp_vec_by_restr_vec_scaled(void){
    FZ_ELEM e[N];
    FP_ELEM chall_1;
    FP_ELEM u_prime[N];
    FP_ELEM output[N];

    fill_fz(e, N);
    fill_fp(u_prime, N);

    chall_1 = (FP_ELEM)3;
    for (int i = 0; i < ITERATIONS; i++) {
        fp_vec_by_restr_vec_scaled(output, e, chall_1, u_prime);
    }
    consume_fp(output, N);
}
#endif


#if defined(BENCH_EXPAND_DIGEST_TO_FIXED_WEIGHT)
static void benchmark_expand_digest_to_fixed_weight(void){
    uint8_t digest[HASH_DIGEST_LENGTH];
    uint8_t output[T];

    fill_bytes(digest, sizeof(digest));
    for (int i = 0; i < ITERATIONS; i++) {
        expand_digest_to_fixed_weight(output, digest);
    }
    consume_bytes(output, T);
}
#endif


#if defined(BENCH_PACK_FP_SYN)
static void benchmark_pack_fp_syn(void){
    FP_ELEM input[N - K];
    uint8_t output[DENSELY_PACKED_FP_SYN_SIZE];

    fill_fp(input, N - K);
    for (int i = 0; i < ITERATIONS; i++) {
        pack_fp_syn(output, input);
    }
    consume_bytes(output, DENSELY_PACKED_FP_SYN_SIZE);
}
#endif

 
#if defined(BENCH_PACK_FZ_VEC)
static void benchmark_pack_fz_vec(void){
    FZ_ELEM input[N];
    uint8_t output[DENSELY_PACKED_FZ_VEC_SIZE];

    fill_fz(input, N);

    for (int i = 0; i < ITERATIONS; i++) {
        pack_fz_vec(output, input);
    }
    consume_bytes(output, DENSELY_PACKED_FZ_VEC_SIZE);
}
#endif


#if defined(BENCH_EXPAND_PK)
static void benchmark_expand_pk(void){
    uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES];

    fill_bytes(seed_pk, sizeof(seed_pk));
#if defined(RSDPG)
    FP_ELEM V_tr[K][N - K];
    FZ_ELEM W_mat[M][N - M];
    for (int i = 0; i < ITERATIONS; i++) {
        expand_pk(V_tr, W_mat, seed_pk);
    }
    consume_fp(&V_tr[0][0], K * (N - K));
    consume_fz(&W_mat[0][0], M * (N - M));
#else
    FP_ELEM V_tr[K][N - K];
    for (int i = 0; i < ITERATIONS; i++) {
        expand_pk(V_tr, seed_pk);
    }
    consume_fp(&V_tr[0][0], K * (N - K));
#endif
}
#endif


#if defined(BENCH_FZ_INF_W_BY_FZ_MATRIX)
#if defined(RSDPG)
static void benchmark_fz_inf_w_by_fz_matrix(void){
    FZ_ELEM e[M];
    FZ_ELEM W_mat[M][N - M];
    FZ_ELEM output[N];

    fill_fz(e, M);
    fill_fz(&W_mat[0][0], M * (N - M));
    for (int i = 0; i < ITERATIONS; i++) {
        fz_inf_w_by_fz_matrix(
            output,
            e,
            W_mat
        );
    }
    consume_fz(output, N);
}
#endif

#endif


#if defined(BENCH_FZ_VEC_SUB_M)
#if defined(RSDPG)
static void benchmark_fz_vec_sub_m(void){
    FZ_ELEM input_a[M];
    FZ_ELEM input_b[M];
    FZ_ELEM output[M];

    fill_fz(input_a, M);
    fill_fz(input_b, M);
    for (int i = 0; i < ITERATIONS; i++) {
        fz_vec_sub_m(output, input_a, input_b);
    }
    consume_fz(output, M);
}
#endif
#endif


#if defined(BENCH_FZ_DZ_NORM_M)
#if defined(RSDPG)
static void benchmark_fz_dz_norm_m(void){
    FZ_ELEM vector[M];

    fill_fz(vector, M);
    for (int i = 0; i < ITERATIONS; i++) {
        fz_dz_norm_m(vector);
    }
    consume_fz(vector, M);
}
#endif
#endif


int main(void){
#if defined(BENCH_CROSS_KEYGEN)

    benchmark_CROSS_keygen();

#elif defined(BENCH_CROSS_SIGN)

    benchmark_CROSS_sign();

#elif defined(BENCH_CROSS_VERIFY)

    benchmark_CROSS_verify();

#elif defined(BENCH_CONVERT_RESTR_VEC_TO_FP)

    benchmark_convert_restr_vec_to_fp();

#elif defined(BENCH_RESTR_VEC_BY_FP_MATRIX)

    benchmark_restr_vec_by_fp_matrix();

#elif defined(BENCH_FP_VEC_BY_FP_VEC_POINTWISE)

    benchmark_fp_vec_by_fp_vec_pointwise();

#elif defined(BENCH_FP_VEC_BY_FP_MATRIX)

    benchmark_fp_vec_by_fp_matrix();

#elif defined(BENCH_FZ_VEC_SUB_N)

    benchmark_fz_vec_sub_n();

#elif defined(BENCH_EXPAND_SK)

    benchmark_expand_sk();

#elif defined(BENCH_FZ_DZ_NORM_N)

    benchmark_fz_dz_norm_n();

#elif defined(BENCH_FP_VEC_BY_RESTR_VEC_SCALED)

    benchmark_fp_vec_by_restr_vec_scaled();

#elif defined(BENCH_EXPAND_DIGEST_TO_FIXED_WEIGHT)

    benchmark_expand_digest_to_fixed_weight();

#elif defined(BENCH_PACK_FP_SYN)

    benchmark_pack_fp_syn();

#elif defined(BENCH_PACK_FZ_VEC)

    benchmark_pack_fz_vec();

#elif defined(BENCH_EXPAND_PK)

    benchmark_expand_pk();

#elif defined(BENCH_FZ_INF_W_BY_FZ_MATRIX)

    benchmark_fz_inf_w_by_fz_matrix();

#elif defined(BENCH_FZ_VEC_SUB_M)

    benchmark_fz_vec_sub_m();

#elif defined(BENCH_FZ_DZ_NORM_M)

    benchmark_fz_dz_norm_m();

#else
    // Error handling with specific print, if no valid benchmark was selected.
    fprintf(stderr, "No benchmark selected.\n");
    return 1;

#endif
    // Print the sink value as a sanity check.
    printf("Benchmark completed. Sink = %llu\n",
           (unsigned long long)benchmark_sink);

    return 0;
}