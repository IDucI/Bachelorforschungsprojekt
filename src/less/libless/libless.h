#ifndef LIBLESS_H
#define LIBLESS_H

#include <stdint.h>

#include "codes.h"
#include "monomial_mat.h"

#ifdef __cplusplus
extern "C" {
#endif

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

#endif /* LIBLESS_H */