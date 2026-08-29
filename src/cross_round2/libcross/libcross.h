#ifndef LIBCROSS_H
#define LIBCROSS_H

#include <stdint.h>
#include <stddef.h>
#include "fp_arith.h"
#include "restr_arith.h"
#include "CROSS.h"

#ifdef __cplusplus
extern "C" {
#endif

    /**
    * SK: output secret key
    * PK: output public key
    */
    void cross_keygen(uint8_t* SK, uint8_t* PK);

    /**
    * SK:      input secret key
    * m:       input message
    * mlen:    length of the message
    * sig:     output signature
    */
    void cross_sign(const uint8_t* SK, const uint8_t* m, uint64_t mlen, uint8_t* sig);

    /**
    * PK:      input public key
    * m:       input message
    * mlen:    length of the message
    * sig:     input signature
    * returns: 1 if valid, 0 otherwise
    */
    int cross_verify(const uint8_t* PK, const uint8_t* m, uint64_t mlen, const uint8_t* sig);

    // size of CROSS_sig_t, used by Python to allocate memory
    extern const size_t cross_sigbytes;

    void cross_convert_restr_vec_to_fp(FP_ELEM res[N], const FZ_ELEM in[N]);

    void cross_restr_vec_by_fp_matrix(FP_ELEM res[N-K], const FZ_ELEM v[N], const FP_ELEM V_tr[K][N-K]);

    void cross_fp_vec_by_fp_vec_pointwise(FP_ELEM res[N], const FP_ELEM in1[N], const FP_ELEM in2[N]);

    void cross_fz_vec_sub_n(FZ_ELEM res[N], const FZ_ELEM a[N], const FZ_ELEM b[N]);

    void cross_fp_vec_by_fp_matrix(FP_ELEM res[N-K], FP_ELEM e[N], FP_ELEM V_tr[K][N-K]);

    void cross_fz_dz_norm_n(FZ_ELEM v[N]);

    void cross_fp_vec_by_restr_vec_scaled(FP_ELEM res[N], const FZ_ELEM e[N], const FP_ELEM chall_1, const FP_ELEM u_prime[N]);

    void cross_expand_digest_to_fixed_weight(uint8_t fixed_weight_string[T], const uint8_t digest_chall_2[HASH_DIGEST_LENGTH]);

    void cross_pack_fp_syn(uint8_t out[DENSELY_PACKED_FP_SYN_SIZE], const FP_ELEM in[N-K]);

    void cross_pack_fz_vec(uint8_t out[DENSELY_PACKED_FZ_VEC_SIZE], const FZ_ELEM in[N]);

    uint8_t cross_unpack_fz_vec(FZ_ELEM out[N], const uint8_t in[DENSELY_PACKED_FZ_VEC_SIZE]);

    #if defined(RSDPG)
        void cross_fz_inf_w_by_fz_matrix(FZ_ELEM res[N], const FZ_ELEM e[M], FZ_ELEM W_mat[M][N-M]);
        void cross_fz_dz_norm_m(FZ_ELEM v[M]);
        void cross_fz_vec_sub_m(FZ_ELEM res[M], const FZ_ELEM a[M], const FZ_ELEM b[M]);
        void cross_expand_sk(FZ_ELEM e_bar[N], FZ_ELEM e_G_bar[M], FP_ELEM V_tr[K][N - K], FZ_ELEM W_mat[M][N - M], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
        void cross_expand_pk(FP_ELEM V_tr[K][N-K], FZ_ELEM W_mat[M][N-M], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]);
    #else
        void cross_expand_sk(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N - K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
        void cross_expand_pk(FP_ELEM V_tr[K][N-K], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]);
    #endif

#ifdef __cplusplus
}
#endif

#endif