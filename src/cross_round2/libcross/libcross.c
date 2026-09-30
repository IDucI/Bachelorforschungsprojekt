#include "libcross.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "seedtree.h"
#include "parameters.h"
#include "csprng_hash.h"
#include "pack_unpack.h"
#include "merkle_tree.h"
#include <string.h>

// ---------------------------------------------------------------------------------------------------------------------------------------
// Manual declaration of expand_sk so that it is known due to compile problem if we make the shared lib again with make clean && make
// ---------------------------------------------------------------------------------------------------------------------------------------

#if defined(RSDPG)
    void expand_sk(FZ_ELEM e_bar[N], FZ_ELEM e_G_bar[M], FP_ELEM V_tr[K][N - K], FZ_ELEM W_mat[M][N - M], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
    void expand_pk(FP_ELEM V_tr[K][N-K], FZ_ELEM W_mat[M][N-M], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]);
#else
    void expand_sk(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N - K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
    void expand_pk(FP_ELEM V_tr[K][N-K], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]);
#endif


// ---------------------------------------------------------------------------------------------------------------------------------------
// Initialize the function pointers (Outside of guards)
// Change from extern to static, because of name conflict problem with the original function to fix the problem, use static, because it 
// encapsulates the internal pointers so that the original crypto code and the Python bridge don't disturb each other during compilation!
// Note: The exact Datantypes (f.e. FP_ELEM, FZ_ELEM) has to match towards the original function.
// ---------------------------------------------------------------------------------------------------------------------------------------

static void (*c_convert_restr_vec_to_fp)(FP_ELEM res[N], const FZ_ELEM in[N]) = convert_restr_vec_to_fp;
static void (*c_restr_vec_by_fp_matrix)(FP_ELEM res[N-K], FZ_ELEM e[N], FP_ELEM V_tr[K][N-K]) = restr_vec_by_fp_matrix;
static void (*c_fp_vec_by_fp_vec_pointwise)(FP_ELEM res[N], const FP_ELEM in1[N], const FP_ELEM in2[N]) = fp_vec_by_fp_vec_pointwise;
static void (*c_fp_vec_by_fp_matrix)(FP_ELEM res[N-K], FP_ELEM e[N], FP_ELEM V_tr[K][N-K]) = fp_vec_by_fp_matrix;
static void (*c_fz_vec_sub_n)(FZ_ELEM res[N], const FZ_ELEM a[N], const FZ_ELEM b[N]) = fz_vec_sub_n;
static void (*c_fp_vec_by_restr_vec_scaled)(FP_ELEM res[N], const FZ_ELEM e[N], const FP_ELEM chall_1,const FP_ELEM u_prime[N]) = fp_vec_by_restr_vec_scaled;
static void (*c_expand_digest_to_fixed_weight)(uint8_t fixed_weight_string[T], const uint8_t digest_chall_2[HASH_DIGEST_LENGTH]) = expand_digest_to_fixed_weight;
static void (*c_pack_fp_syn)(uint8_t out[DENSELY_PACKED_FP_SYN_SIZE], const FP_ELEM in[N-K]) = pack_fp_syn;
static void (*c_pack_fz_vec)(uint8_t out[DENSELY_PACKED_FZ_VEC_SIZE], const FZ_ELEM in[N]) = pack_fz_vec;
static uint8_t (*c_unpack_fz_vec)(FZ_ELEM out[N], const uint8_t in[DENSELY_PACKED_FZ_VEC_SIZE]) = unpack_fz_vec;
static void (*c_fz_dz_norm_n)(FZ_ELEM v[N]) = fz_dz_norm_n;

#if defined(RSDPG)
    static void (*c_fz_inf_w_by_fz_matrix)(FZ_ELEM res[N], const FZ_ELEM e[M], FZ_ELEM W_mat[M][N-M]) = fz_inf_w_by_fz_matrix;
    static void (*c_fz_vec_sub_m)(FZ_ELEM res[M], const FZ_ELEM a[M], const FZ_ELEM b[M]) = fz_vec_sub_m; 
    static void (*c_fz_dz_norm_m)(FZ_ELEM v[M]) = fz_dz_norm_m; 
    static void (*c_expand_sk)(FZ_ELEM e_bar[N], FZ_ELEM e_G_bar[M], FP_ELEM V_tr[K][N - K], FZ_ELEM W_mat[M][N - M], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]) = expand_sk;
    static void (*c_expand_pk)(FP_ELEM V_tr[K][N-K], FZ_ELEM W_mat[M][N-M], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]) = expand_pk;
#else
    static void (*c_expand_sk)(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N - K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]) = expand_sk; 
    static void (*c_expand_pk)(FP_ELEM V_tr[K][N-K], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]) = expand_pk;
#endif

// Only the wrapper functions that should be visible externally go into the guard
#ifdef __cplusplus
extern "C" {
#endif

    // -----------------------------------------------------------------------
    // High-Level API
    // -----------------------------------------------------------------------

    void cross_keygen(uint8_t* SK, uint8_t* PK) {
        sk_t sk;
        pk_t pk;
        CROSS_keygen(&sk, &pk);
        memcpy(SK, &sk, sizeof(sk_t));
        memcpy(PK, &pk, sizeof(pk_t));
    }

    void cross_sign(const uint8_t* SK, const uint8_t* m, uint64_t mlen, uint8_t* sig) {
        sk_t sk;
        memcpy(&sk, SK, sizeof(sk_t));
        CROSS_sig_t signature;
        CROSS_sign(&sk, (const char*)m, mlen, &signature);
        memcpy(sig, &signature, sizeof(CROSS_sig_t));
    }

    int cross_verify(const uint8_t* PK, const uint8_t* m, uint64_t mlen, const uint8_t* sig) {
        pk_t pk;
        memcpy(&pk, PK, sizeof(pk_t));
        CROSS_sig_t signature;
        memcpy(&signature, sig, sizeof(CROSS_sig_t));
        return CROSS_verify(&pk, (const char*)m, mlen, &signature);
    }

    // -----------------------------------------------------------------------
    // Functions for internal state calculation
    // -----------------------------------------------------------------------

    void cross_randombytes(uint8_t* out, unsigned long long len) {
        randombytes(out, len);
    }

    void cross_gen_seed_tree(uint8_t * seed_tree, uint8_t * root_seed, uint8_t * salt) {
        gen_seed_tree(seed_tree, root_seed, salt);
    }

    void cross_seed_leaves(uint8_t * round_seeds, uint8_t * seed_tree) {
        seed_leaves(round_seeds, seed_tree);
    }

    void cross_csprng_initialize(CSPRNG_STATE_T* const csprng_state, const uint8_t * const seed, const uint32_t seed_len_bytes, const uint16_t dsc) {
        csprng_initialize(csprng_state, seed, seed_len_bytes, dsc);
    }

    #if defined(RSDP)
    void cross_csprng_fz_vec(FZ_ELEM res[N], CSPRNG_STATE_T* const csprng_state) {
        csprng_fz_vec(res, csprng_state);
    }
    #elif defined(RSDPG)
    void cross_csprng_fz_inf_w(FZ_ELEM res[M], CSPRNG_STATE_T* const csprng_state) {
        csprng_fz_inf_w(res, csprng_state);
    }
    #endif

    void cross_csprng_fp_vec(FP_ELEM res[N], CSPRNG_STATE_T* const csprng_state) {
        csprng_fp_vec(res, csprng_state);
    }

    void cross_fp_dz_norm_synd(FP_ELEM v[N-K]) {
        fp_dz_norm_synd(v);
    }

    void cross_hash(uint8_t digest[HASH_DIGEST_LENGTH], const unsigned char* const m, const uint64_t mlen, const uint16_t dsc) {
        hash(digest, m, mlen, dsc);
    }

    void cross_tree_root(uint8_t root[HASH_DIGEST_LENGTH], uint8_t tree[NUM_NODES_MERKLE_TREE * HASH_DIGEST_LENGTH], uint8_t leaves[T][HASH_DIGEST_LENGTH]) {
        tree_root(root, tree, leaves);
    }

    void cross_csprng_fp_vec_chall_1(FP_ELEM res[T], CSPRNG_STATE_T* const csprng_state) {
        csprng_fp_vec_chall_1(res, csprng_state);
    }

    void cross_fp_dz_norm(FP_ELEM v[N]) {
        fp_dz_norm(v);
    }

    void cross_pack_fp_vec(uint8_t out[DENSELY_PACKED_FP_VEC_SIZE], const FP_ELEM in[N]) {
        pack_fp_vec(out, in);
    }

    uint16_t cross_tree_proof(uint8_t mtp[HASH_DIGEST_LENGTH * TREE_NODES_TO_STORE], const uint8_t tree[NUM_NODES_MERKLE_TREE * HASH_DIGEST_LENGTH], const uint8_t leaves_to_reveal[T]) {
        return tree_proof(mtp, tree, leaves_to_reveal);
    }

    int cross_seed_path(unsigned char* seed_storage, const unsigned char seed_tree[NUM_NODES_SEED_TREE * SEED_LENGTH_BYTES], const unsigned char indices_to_publish[T]) {
        return seed_path(seed_storage, seed_tree, indices_to_publish);
    }

    #if defined(RSDPG)
    void cross_pack_fz_rsdp_g_vec(uint8_t out[DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE], const FZ_ELEM in[M]) {
        pack_fz_rsdp_g_vec(out, in);
    }
    #endif

    void cross_csprng_randombytes(unsigned char* const x, unsigned long long xlen, CSPRNG_STATE_T* const csprng_state) {
        csprng_randombytes(x, xlen, csprng_state);
    }
    // -----------------------------------------------------------------------
    // Subroutines
    // -----------------------------------------------------------------------

    void cross_convert_restr_vec_to_fp(FP_ELEM res[N], const FZ_ELEM in[N]) {
		// Here, call the pointer and pass through the data:
        c_convert_restr_vec_to_fp(res, in);
    }

    void cross_restr_vec_by_fp_matrix(FP_ELEM res[N-K], const FZ_ELEM v[N], const FP_ELEM V_tr[K][N-K]) {
    	c_restr_vec_by_fp_matrix(res, (FZ_ELEM*)v, (FP_ELEM (*)[N-K])V_tr);
	}

    void cross_fp_vec_by_fp_vec_pointwise(FP_ELEM res[N], const FP_ELEM in1[N], const FP_ELEM in2[N]) { 
        c_fp_vec_by_fp_vec_pointwise(res, in1, in2);
    }

    void cross_fp_vec_by_fp_matrix(FP_ELEM res[N-K], FP_ELEM e[N], FP_ELEM V_tr[K][N-K]) {
        c_fp_vec_by_fp_matrix(res, e, V_tr);
    }

    void cross_fz_vec_sub_n(FZ_ELEM res[N], const FZ_ELEM a[N], const FZ_ELEM b[N]) { 
        c_fz_vec_sub_n(res, a, b);
    }

    void cross_fz_dz_norm_n(FZ_ELEM v[N]) {
            c_fz_dz_norm_n(v);
    }

    
    #if defined(RSDPG)
        void cross_fz_vec_sub_m(FZ_ELEM res[M], const FZ_ELEM a[M], const FZ_ELEM b[M]) {
            c_fz_vec_sub_m(res, a, b);
        }
        void cross_fz_inf_w_by_fz_matrix(FZ_ELEM res[N], const FZ_ELEM e[M], FZ_ELEM W_mat[M][N-M]) {
            c_fz_inf_w_by_fz_matrix(res, e, W_mat); 
        }
        void cross_fz_dz_norm_m(FZ_ELEM v[M]) {
            c_fz_dz_norm_m(v);
        }
        void cross_expand_sk(FZ_ELEM e_bar[N], FZ_ELEM e_G_bar[M], FP_ELEM V_tr[K][N - K], FZ_ELEM W_mat[M][N - M], 
                             const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]) {
            c_expand_sk(e_bar, e_G_bar, V_tr, W_mat, seed_sk);
        }
        void cross_expand_pk(FP_ELEM V_tr[K][N-K], FZ_ELEM W_mat[M][N-M], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]) {
            c_expand_pk(V_tr, W_mat, seed_pk);
        }
    #else
        void cross_expand_sk(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N - K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]) {
            c_expand_sk(e_bar, V_tr, seed_sk);
        }
        void cross_expand_pk(FP_ELEM V_tr[K][N - K], const uint8_t seed_pk[KEYPAIR_SEED_LENGTH_BYTES]) {
            c_expand_pk(V_tr, seed_pk);
        }
    #endif


    void cross_fp_vec_by_restr_vec_scaled(FP_ELEM res[N], const FZ_ELEM e[N], const FP_ELEM chall_1, const FP_ELEM u_prime[N]) {
        c_fp_vec_by_restr_vec_scaled(res, e, chall_1, u_prime);
    }

    void cross_expand_digest_to_fixed_weight(uint8_t fixed_weight_string[T], const uint8_t digest_chall_2[HASH_DIGEST_LENGTH]) {
        c_expand_digest_to_fixed_weight(fixed_weight_string, digest_chall_2);
    }

    void cross_pack_fp_syn(uint8_t out[DENSELY_PACKED_FP_SYN_SIZE], const FP_ELEM in[N-K]) {
        c_pack_fp_syn(out, in);
    }

    void cross_pack_fz_vec(uint8_t out[DENSELY_PACKED_FZ_VEC_SIZE], const FZ_ELEM in[N]) {
        c_pack_fz_vec(out, in);
    }

    uint8_t cross_unpack_fz_vec(FZ_ELEM out[N], const uint8_t in[DENSELY_PACKED_FZ_VEC_SIZE]) {
        return c_unpack_fz_vec(out, in);
    }
    

#ifdef __cplusplus
}
#endif