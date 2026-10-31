#ifndef LIBLESS_H
#define LIBLESS_H

#include <stddef.h>
#include <stdint.h>

#include "codes.h"
#include "monomial_mat.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * secret_key: output buffer of less_skbytes bytes
 * public_key: output buffer of less_pkbytes bytes
 */
void less_keygen(
    uint8_t *secret_key,
    uint8_t *public_key
);

/**
 * secret_key: input secret key
 * message: input message
 * message_length: message length in bytes
 * signature: output buffer of less_sigbytes bytes
 */
void less_sign(
    const uint8_t *secret_key,
    const uint8_t *message,
    uint64_t message_length,
    uint8_t *signature
);

/**
 * public_key: input public key
 * message: input message
 * message_length: message length in bytes
 * signature: input signature
 * returns: verification result from LESS_verify()
 */
int less_verify(
    const uint8_t *public_key,
    const uint8_t *message,
    uint64_t message_length,
    const uint8_t *signature
);

extern const size_t less_skbytes;
extern const size_t less_pkbytes;
extern const size_t less_sigbytes;

// Initialize the global platform CSPRNG from the supplied seed.
void less_initialize_randombytes(
    const uint8_t *seed,
    uint32_t seed_length
);

// Functions needed to reconstruct the keygen input of generator_monomial_mul
void less_expand_private_key_seeds(
    uint8_t *g0_seed,
    uint8_t *private_monomial_seeds,
    const uint8_t *compressed_sk
);

void less_generator_rref_expand(
    FQ_ELEM *full_values,
    const FQ_ELEM *compact_values,
    const POSITION_T *column_pos
);

void less_monomial_inv(
    FQ_ELEM *res_coefficients,
    POSITION_T *res_permutation,
    const FQ_ELEM *coefficients,
    const POSITION_T *permutation
);

// Selected LESS subroutines
void less_generator_monomial_mul(
    FQ_ELEM *res_values,
    const FQ_ELEM *generator_values,
    const FQ_ELEM *coefficients,
    const POSITION_T *permutation
);

FQ_ELEM less_fq_inv(
    FQ_ELEM value
);

void less_row_mul3(
    FQ_ELEM *out,
    const FQ_ELEM *in1,
    const FQ_ELEM *in2
);

void less_generator_sample(
    FQ_ELEM *res_values,
    POSITION_T *res_column_pos,
    const unsigned char seed[SEED_LENGTH_BYTES]
);

void less_monomial_sample_prikey(
    FQ_ELEM *res_coefficients,
    POSITION_T *res_permutation,
    const unsigned char seed[PRIVATE_KEY_SEED_LENGTH_BYTES]
);

#ifdef __cplusplus
}
#endif

#endif // LIBLESS_H 