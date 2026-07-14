#include "codes.h"
#include "monomial_mat.h"

/*
 * Keep the original LESS function unchanged and expose it through a stable
 * function pointer used by libless.c.
 */
void (*c_generator_monomial_mul)(
    generator_mat_t *res,
    const generator_mat_t *G,
    const monomial_t *monom) = &generator_monomial_mul;
