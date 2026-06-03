#include "fp_arith.h"

void (*c_convert_restr_vec_to_fp)(FP_ELEM res[N], const FZ_ELEM in[N]) =
&convert_restr_vec_to_fp;