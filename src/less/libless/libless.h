#ifndef LIBLESS_H
#define LIBLESS_H

#include <stdint.h>

#include "codes.h"
#include "monomial_mat.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Python-facing wrapper for the official LESS generator_monomial_mul routine.
 *
 * All arrays are passed flat to avoid exposing C structure layout through
 * ctypes. Generator matrices are row-major and contain K * N_pad FQ_ELEM
 * entries. The monomial map is passed as N coefficients and N positions.
 */
void less_generator_monomial_mul(
    FQ_ELEM *res_values,
    const FQ_ELEM *generator_values,
    const FQ_ELEM *coefficients,
    const POSITION_T *permutation);

#ifdef __cplusplus
}
#endif

#endif /* LIBLESS_H */
