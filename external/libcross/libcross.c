#include "libcross.h"

#ifdef __cplusplus
extern "C" {
#endif

	extern void (*c_convert_restr_vec_to_fp)(FP_ELEM res[N], const FZ_ELEM in[N]);

	void cross_convert_restr_vec_to_fp(FP_ELEM res[N], const FZ_ELEM in[N]) {
		c_convert_restr_vec_to_fp(res, in);
	}

#ifdef __cplusplus
}
#endif