#include "libless.h"

#include <string.h>

#include "rng.h"

#ifdef LIBLESS_HIGH_LEVEL
#include "LESS.h"
#endif

// Defined in variants/Reference_Implementation/function_linkage.c
extern void (*c_generator_monomial_mul)(
    generator_mat_t *res,
    const generator_mat_t *G,
    const monomial_t *monom
);

extern FQ_ELEM (*c_fq_inv)(
    FQ_ELEM value
);

extern void (*c_row_mul3)(
    FQ_ELEM *out,
    const FQ_ELEM *in1,
    const FQ_ELEM *in2
);

extern void (*c_generator_sample)(
    rref_generator_mat_t *res,
    const unsigned char seed[SEED_LENGTH_BYTES]
);

extern void (*c_monomial_sample_prikey)(
    monomial_t *res,
    const unsigned char seed[PRIVATE_KEY_SEED_LENGTH_BYTES]
);

#ifdef __cplusplus
extern "C" {
#endif

#ifdef LIBLESS_HIGH_LEVEL
// -------------------------------------------------------------------------
// High-level API                                                           
// -------------------------------------------------------------------------

void less_keygen(
    uint8_t *secret_key,
    uint8_t *public_key
) {
    prikey_t sk;
    pubkey_t pk;

    LESS_keygen(&sk, &pk);

    memcpy(secret_key, &sk, sizeof(prikey_t));
    memcpy(public_key, &pk, sizeof(pubkey_t));
}

void less_sign(
    const uint8_t *secret_key,
    const uint8_t *message,
    uint64_t message_length,
    uint8_t *signature
) {
    prikey_t sk;
    sign_t sig;

    memcpy(&sk, secret_key, sizeof(prikey_t));
    memset(&sig, 0, sizeof(sign_t));

    LESS_sign(
        &sk,
        (const char *)message,
        message_length,
        &sig
    );

    memcpy(signature, &sig, sizeof(sign_t));
}

int less_verify(
    const uint8_t *public_key,
    const uint8_t *message,
    uint64_t message_length,
    const uint8_t *signature
) {
    pubkey_t pk;
    sign_t sig;

    memcpy(&pk, public_key, sizeof(pubkey_t));
    memcpy(&sig, signature, sizeof(sign_t));

    return LESS_verify(
        &pk,
        (const char *)message,
        message_length,
        &sig
    );
}

const size_t less_skbytes = sizeof(prikey_t);
const size_t less_pkbytes = sizeof(pubkey_t);
const size_t less_sigbytes = sizeof(sign_t);
#endif

// -------------------------------------------------------------------------
// Functions for internal state calculation                                 
// -------------------------------------------------------------------------

void less_initialize_randombytes(
    const uint8_t *seed,
    uint32_t seed_length
) {
    initialize_csprng(
        &platform_csprng_state,
        seed,
        seed_length
    );
}

void less_expand_private_key_seeds(
    uint8_t *g0_seed,
    uint8_t *private_monomial_seeds,
    const uint8_t *compressed_sk
) {
    SHAKE_STATE_STRUCT sk_shake_state;

    initialize_csprng(
        &sk_shake_state,
        compressed_sk,
        PRIVATE_KEY_SEED_LENGTH_BYTES
    );

    csprng_randombytes(
        g0_seed,
        SEED_LENGTH_BYTES,
        &sk_shake_state
    );

    for (uint32_t i = 0; i < NUM_KEYPAIRS - 1; i++) {
        csprng_randombytes(
            private_monomial_seeds
                + i * PRIVATE_KEY_SEED_LENGTH_BYTES,
            PRIVATE_KEY_SEED_LENGTH_BYTES,
            &sk_shake_state
        );
    }
}

void less_generator_rref_expand(
    FQ_ELEM *full_values,
    const FQ_ELEM *compact_values,
    const POSITION_T *column_pos
) {
    rref_generator_mat_t compact;
    generator_mat_t full;

    for (uint32_t row = 0; row < K; row++) {
        memcpy(
            compact.values[row],
            compact_values + row * (N - K),
            (N - K) * sizeof(FQ_ELEM)
        );
    }

    memcpy(
        compact.column_pos,
        column_pos,
        (N - K) * sizeof(POSITION_T)
    );

    generator_rref_expand(&full, &compact);

    memcpy(
        full_values,
        full.values,
        sizeof(full.values)
    );
}

void less_monomial_inv(
    FQ_ELEM *res_coefficients,
    POSITION_T *res_permutation,
    const FQ_ELEM *coefficients,
    const POSITION_T *permutation
) {
    monomial_t input;
    monomial_t result;

    memcpy(
        input.coefficients,
        coefficients,
        sizeof(input.coefficients)
    );

    memcpy(
        input.permutation,
        permutation,
        sizeof(input.permutation)
    );

    monomial_inv(&result, &input);

    memcpy(
        res_coefficients,
        result.coefficients,
        sizeof(result.coefficients)
    );

    memcpy(
        res_permutation,
        result.permutation,
        sizeof(result.permutation)
    );
}

// ------------------------------------------------------------------------- 
// Selected subroutines                                                      
// ------------------------------------------------------------------------- 

void less_generator_monomial_mul(
    FQ_ELEM *res_values,
    const FQ_ELEM *generator_values,
    const FQ_ELEM *coefficients,
    const POSITION_T *permutation
) {
    generator_mat_t result;
    generator_mat_t generator;
    monomial_t monomial;

    memcpy(
        generator.values,
        generator_values,
        sizeof(generator.values)
    );

    memcpy(
        monomial.coefficients,
        coefficients,
        sizeof(monomial.coefficients)
    );

    memcpy(
        monomial.permutation,
        permutation,
        sizeof(monomial.permutation)
    );

    c_generator_monomial_mul(
        &result,
        &generator,
        &monomial
    );

    memcpy(
        res_values,
        result.values,
        sizeof(result.values)
    );
}

FQ_ELEM less_fq_inv(
    FQ_ELEM value
) {
    return c_fq_inv(value);
}

void less_row_mul3(
    FQ_ELEM *out,
    const FQ_ELEM *in1,
    const FQ_ELEM *in2
) {
    c_row_mul3(
        out,
        in1,
        in2
    );
}

void less_generator_sample(
    FQ_ELEM *res_values,
    POSITION_T *res_column_pos,
    const unsigned char seed[SEED_LENGTH_BYTES]
) {
    rref_generator_mat_t result;

    c_generator_sample(
        &result,
        seed
    );

    for (uint32_t row = 0; row < K; row++) {
        memcpy(
            res_values + row * (N - K),
            result.values[row],
            (N - K) * sizeof(FQ_ELEM)
        );
    }

    memcpy(
        res_column_pos,
        result.column_pos,
        (N - K) * sizeof(POSITION_T)
    );
}

void less_monomial_sample_prikey(
    FQ_ELEM *res_coefficients,
    POSITION_T *res_permutation,
    const unsigned char seed[PRIVATE_KEY_SEED_LENGTH_BYTES]
) {
    monomial_t result;

    c_monomial_sample_prikey(
        &result,
        seed
    );

    memcpy(
        res_coefficients,
        result.coefficients,
        sizeof(result.coefficients)
    );

    memcpy(
        res_permutation,
        result.permutation,
        sizeof(result.permutation)
    );
}

#ifdef __cplusplus
}
#endif