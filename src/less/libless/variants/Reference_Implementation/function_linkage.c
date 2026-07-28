#include "codes.h"
#include "fq_arith.h"
#include "monomial_mat.h"

/*
 * Keep the original LESS functions unchanged and expose stable function
 * pointers for the small libless wrapper layer.
 */
void (*c_generator_monomial_mul)(
    generator_mat_t *res,
    const generator_mat_t *G,
    const monomial_t *monom
) = &generator_monomial_mul;

FQ_ELEM (*c_fq_inv)(
    FQ_ELEM value
) = &fq_inv;

void (*c_row_mul3)(
    FQ_ELEM *out,
    const FQ_ELEM *in1,
    const FQ_ELEM *in2
) = &row_mul3;

void (*c_generator_sample)(
    rref_generator_mat_t *res,
    const unsigned char seed[SEED_LENGTH_BYTES]
) = &generator_sample;

void (*c_monomial_sample_prikey)(
    monomial_t *res,
    const unsigned char seed[PRIVATE_KEY_SEED_LENGTH_BYTES]
) = &monomial_sample_prikey;