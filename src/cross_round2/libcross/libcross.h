#ifndef LIBCROSS_H
#define LIBCROSS_H

#include <stdint.h>
#include "fp_arith.h"
#include "restr_arith.h"
#include "CROSS.h"

#ifdef __cplusplus
extern "C" {
#endif

    void cross_convert_restr_vec_to_fp(FP_ELEM res[N], const FZ_ELEM in[N]);

    void cross_restr_vec_by_fp_matrix(FP_ELEM res[N-K], const FZ_ELEM v[N], const FP_ELEM M[K][N-K]);

    void cross_fp_vec_by_fp_vec_pointwise(FP_ELEM res[N], const FP_ELEM in1[N], const FP_ELEM in2[N]);

    void cross_fz_vec_sub_n(FZ_ELEM res[N], const FZ_ELEM a[N], const FZ_ELEM b[N]);

    void cross_expand_sk(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N-K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);

    void cross_fp_vec_by_fp_matrix(FP_ELEM res[N-K], FP_ELEM e[N], FP_ELEM V_tr[K][N-K]);

#ifdef __cplusplus
}
#endif

#endif