#include "LESS.h"
#include "codes.h"
#include "monomial_mat.h"
#include "rng.h"

#include <stdint.h>
#include <stdio.h>

static void write_hex(
    FILE *json,
    const uint8_t *array,
    size_t length
) {
    for (size_t i = 0; i < length; i++) {
        fprintf(json, "%02x", array[i]);
    }
}

static void write_generator(
    FILE *json,
    const generator_mat_t *generator
) {
    fprintf(json, "[");

    for (uint32_t row = 0; row < K; row++) {
        fprintf(json, "[");

        for (uint32_t col = 0; col < N; col++) {
            fprintf(
                json,
                "%u",
                (unsigned int)generator->values[row][col]
            );

            if (col + 1 < N) {
                fprintf(json, ", ");
            }
        }

        fprintf(json, "]");

        if (row + 1 < K) {
            fprintf(json, ", ");
        }
    }

    fprintf(json, "]");
}

// Reconstruct the generator matrix product from LESS key generation.
// The result is computed before RREF reduction and compression.
static void calculate_keygen_generator_product(
    generator_mat_t *result,
    const uint8_t compressed_sk[PRIVATE_KEY_SEED_LENGTH_BYTES],
    uint32_t keypair_index
) {
    SHAKE_STATE_STRUCT sk_shake_state;

    initialize_csprng(
        &sk_shake_state,
        compressed_sk,
        PRIVATE_KEY_SEED_LENGTH_BYTES
    );

    uint8_t g0_seed[SEED_LENGTH_BYTES];

    csprng_randombytes(
        g0_seed,
        SEED_LENGTH_BYTES,
        &sk_shake_state
    );

    uint8_t private_monomial_seed[
        PRIVATE_KEY_SEED_LENGTH_BYTES
    ];

    for (uint32_t i = 0; i <= keypair_index; i++) {
        csprng_randombytes(
            private_monomial_seed,
            PRIVATE_KEY_SEED_LENGTH_BYTES,
            &sk_shake_state
        );
    }

    rref_generator_mat_t g0_rref;

    generator_sample(
        &g0_rref,
        g0_seed
    );

    generator_mat_t full_g0;

    generator_rref_expand(
        &full_g0,
        &g0_rref
    );

    monomial_t q_inv;
    monomial_t q;

    monomial_sample_prikey(
        &q_inv,
        private_monomial_seed
    );

    monomial_inv(
        &q,
        &q_inv
    );

    generator_monomial_mul(
        result,
        &full_g0,
        &q
    );
}

// Generate deterministic keygen reference data for the Python tests.
int main(void) {
    uint8_t rng_seed[48];

    for (uint32_t i = 0; i < sizeof(rng_seed); i++) {
        rng_seed[i] = (uint8_t)i;
    }

    initialize_csprng(
        &platform_csprng_state,
        rng_seed,
        sizeof(rng_seed)
    );

    prikey_t sk;
    pubkey_t pk;

    LESS_keygen(
        &sk,
        &pk
    );

    char filename[100];

    snprintf(
        filename,
        sizeof(filename),
        "%s.json",
        ALG_VERSION
    );

    FILE *json = fopen(
        filename,
        "w"
    );

    if (json == NULL) {
        return 1;
    }

    fprintf(
        json,
        "{\n\"compressed_sk\":\""
    );

    write_hex(
        json,
        sk.compressed_sk,
        PRIVATE_KEY_SEED_LENGTH_BYTES
    );

    fprintf(
        json,
        "\",\n\"generator_products\":["
    );

    for (
        uint32_t keypair_index = 0;
        keypair_index < NUM_KEYPAIRS - 1;
        keypair_index++
    ) {
        generator_mat_t result;

        calculate_keygen_generator_product(
            &result,
            sk.compressed_sk,
            keypair_index
        );

        write_generator(
            json,
            &result
        );

        if (
            keypair_index + 1 <
            NUM_KEYPAIRS - 1
        ) {
            fprintf(
                json,
                ","
            );
        }
    }

    fprintf(
        json,
        "]\n}\n"
    );

    fclose(
        json
    );

    return 0;
}
