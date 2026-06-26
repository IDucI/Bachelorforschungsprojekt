#include "libcross.h"
#include "fp_arith.h"
#include "restr_arith.h"

// Manual declaration of expand_sk so that it is known due to compile problem if we make the shared lib again with make clean && make
void expand_sk(uint8_t e_bar[N], uint8_t V_tr[K][N-K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);

// Initialize the function pointers (Outside of guards)
// Change from extern to static, because of name conflict problem with the original function to fix the problem, use static, 
// because static it encapsulates the internal pointers so that the original crypto code and the Python bridge don't disturb each other during compilation!
// Note: The exact Datantypes (f.e. FP_ELEM, FZ_ELEM) has to match towards the original function.

static void (*c_convert_restr_vec_to_fp)(FP_ELEM res[N], const FZ_ELEM in[N]) = convert_restr_vec_to_fp;
static void (*c_restr_vec_by_fp_matrix)(uint8_t *, const uint8_t *, const uint8_t (*)[N-K]) = (void (*)(uint8_t *, const uint8_t *, const uint8_t (*)[N-K]))restr_vec_by_fp_matrix;
static void (*c_fp_vec_by_fp_vec_pointwise)(FP_ELEM res[N], const FP_ELEM in1[N], const FP_ELEM in2[N]) = fp_vec_by_fp_vec_pointwise;
static void (*c_fp_vec_by_fp_matrix)(FP_ELEM res[N-K], FP_ELEM e[N], FP_ELEM V_tr[K][N-K]) = fp_vec_by_fp_matrix;
static void (*c_fz_vec_sub_n)(FZ_ELEM res[N], const FZ_ELEM a[N], const FZ_ELEM b[N]) = fz_vec_sub_n;
static void (*c_expand_sk)(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N-K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]) = expand_sk;

// Only the wrapper functions that should be visible externally go into the guard
#ifdef __cplusplus
extern "C" {
#endif

    void cross_convert_restr_vec_to_fp(FP_ELEM res[N], const FZ_ELEM in[N]) {
		// Here, call the pointer and pass through the data:
        c_convert_restr_vec_to_fp(res, in);
    }

    void cross_restr_vec_by_fp_matrix(FP_ELEM res[N-K], const FZ_ELEM v[N], const FP_ELEM M[K][N-K]) {
    	// Explicit cast on the call to prevent warnings
    	c_restr_vec_by_fp_matrix((uint8_t*)res, (const uint8_t*)v, (const uint8_t (*)[N-K])M);
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

    void cross_expand_sk(FZ_ELEM e_bar[N], FP_ELEM V_tr[K][N-K], const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]) {
        c_expand_sk(e_bar, V_tr, seed_sk);
    }

#ifdef __cplusplus
}
#endif