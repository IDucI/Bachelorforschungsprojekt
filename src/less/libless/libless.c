#include "libless.h"

#include <string.h>

/* Defined in variants/Reference_Implementation/function_linkage.c. */
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