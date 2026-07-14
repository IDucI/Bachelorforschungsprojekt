#include "libless.h"

#include <string.h>

/* Defined in variants/Reference_Implementation/function_linkage.c. */
extern void (*c_generator_monomial_mul)(
    generator_mat_t *res,
    const generator_mat_t *G,
    const monomial_t *monom);

#ifdef __cplusplus
extern "C" {
#endif

void less_generator_monomial_mul(
    FQ_ELEM *res_values,
    const FQ_ELEM *generator_values,
    const FQ_ELEM *coefficients,
    const POSITION_T *permutation) {

    generator_mat_t result;
    generator_mat_t generator;
    monomial_t monomial;

    memcpy(generator.values, generator_values, sizeof(generator.values));
    memcpy(monomial.coefficients, coefficients, sizeof(monomial.coefficients));
    memcpy(monomial.permutation, permutation, sizeof(monomial.permutation));

    c_generator_monomial_mul(&result, &generator, &monomial);

    memcpy(res_values, result.values, sizeof(result.values));
}

#ifdef __cplusplus
}
#endif
