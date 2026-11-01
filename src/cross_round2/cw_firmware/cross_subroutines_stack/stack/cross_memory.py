import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libcross" / "cross"))

from cross_params import get_params, PARAMETER_SETS

with open(Path(__file__).with_name("cross_memory.csv"), "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Variant", "Subroutine", "CCMRAM_Bytes", "Stack_Buffer_Bytes", "Total_Bytes"])

    for algorithm, category, optimization in PARAMETER_SETS:
        p = get_params(algorithm, category, optimization)

        fz_size = 1
        fp_size = 2 if p.algorithm == "RSDPG" else 1

        # void convert_restr_vec_to_fp(FP_ELEM res[N], const FZ_ELEM in[N])
        convert_restr_vec_to_fp = (p.n * fz_size, p.n * fp_size)
        # void restr_vec_by_fp_matrix(FP_ELEM res[N-K], FZ_ELEM e[N], FP_ELEM V_tr[K][N-K])
        restr_vec_by_fp_matrix = (p.n * fz_size + p.k * (p.n - p.k) * fp_size, (p.n - p.k) * fp_size)
        # void pack_fz_vec(uint8_t out[DENSELY_PACKED_FZ_VEC_SIZE], const FZ_ELEM in[N])
        # void pack_fz_rsdp_g_vec(uint8_t out[DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE], const FZ_ELEM in[M])
        if p.algorithm == "RSDPG":
            pack_fz_vec = (p.m * fz_size, p.densely_packed_fz_rsdp_g_vec_size)
        else:
            pack_fz_vec = (p.n * fz_size, p.densely_packed_fz_vec_size)
        # void pack_fp_syn(uint8_t out[DENSELY_PACKED_FP_SYN_SIZE], const FP_ELEM in[N-K])
        pack_fp_syn = ((p.n - p.k) * fp_size, p.densely_packed_fp_syn_size)
        # void fz_vec_sub_n(FZ_ELEM res[N], const FZ_ELEM a[N], const FZ_ELEM b[N])
        fz_vec_sub_n = (2 * p.n * fz_size, p.n * fz_size)
        # void fz_vec_sub_m(FZ_ELEM res[M], const FZ_ELEM a[M], const FZ_ELEM b[M])
        if p.algorithm == "RSDPG": fz_vec_sub_m = (2 * p.m * fz_size, p.m * fz_size)
        # void fp_vec_by_fp_matrix(FP_ELEM res[N-K], FP_ELEM e[N], FP_ELEM V_tr[K][N-K])
        fp_vec_by_fp_matrix = (p.n * fp_size + p.k * (p.n - p.k) * fp_size, (p.n - p.k) * fp_size)
        # void fp_vec_by_fp_vec_pointwise(FP_ELEM res[N], const FP_ELEM in1[N], const FP_ELEM in2[N])
        fp_vec_by_fp_vec_pointwise = (2 * p.n * fp_size, p.n * fp_size)
        # void fz_inf_w_by_fz_matrix(FZ_ELEM res[N], const FZ_ELEM e[M], FZ_ELEM W_mat[M][N-M])
        if p.algorithm == "RSDPG": fz_inf_w_by_fz_matrix = (p.m * fz_size + p.m * (p.n - p.m) * fz_size, p.n * fz_size)
        # void fp_vec_by_restr_vec_scaled(FP_ELEM res[N], const FZ_ELEM e[N], const FP_ELEM chall_1, const FP_ELEM u_prime[N])
        fp_vec_by_restr_vec_scaled = (p.n * fz_size + fp_size + p.n * fp_size, p.n * fp_size)
        # void fz_dz_norm_n(FZ_ELEM v[N])
        fz_dz_norm_n = (p.n * fz_size, 0)
        # void fz_dz_norm_m(FZ_ELEM v[M])
        if p.algorithm == "RSDPG": fz_dz_norm_m = (p.m * fz_size, 0)
        # void fp_dz_norm_synd(FP_ELEM v[N-K])
        fp_dz_norm_synd = ((p.n - p.k) * fp_size, 0)
        # void CROSS_keygen(sk_t *SK, pk_t *PK)
        keygen = (2 * p.keypair_seed_length_bytes + p.densely_packed_fp_syn_size, 0)
        # void CROSS_sign(const sk_t *SK, const char *m, uint64_t mlen, CROSS_sig_t *sig)
        # IMPORTANT: Message size varies and is not included in the calculation.
        sign = (p.keypair_seed_length_bytes + 0 + p.sig_size, 0)
        # int CROSS_verify(const pk_t *PK, const char *m, uint64_t mlen, const CROSS_sig_t *sig)
        verify = (p.keypair_seed_length_bytes + p.densely_packed_fp_syn_size + p.sig_size, 0)

        memory = {
            "convert_restr_vec_to_fp": convert_restr_vec_to_fp,
            "restr_vec_by_fp_matrix": restr_vec_by_fp_matrix,
            "pack_fz_rsdp_g_vec" if p.algorithm == "RSDPG" else "pack_fz_vec": pack_fz_vec,
            "pack_fp_syn": pack_fp_syn,
            "fz_vec_sub_n": fz_vec_sub_n,
            "fp_vec_by_fp_matrix": fp_vec_by_fp_matrix,
            "fp_vec_by_fp_vec_pointwise": fp_vec_by_fp_vec_pointwise,
            "fp_vec_by_restr_vec_scaled": fp_vec_by_restr_vec_scaled,
            "fz_dz_norm_n": fz_dz_norm_n,
            "fp_dz_norm_synd": fp_dz_norm_synd,
            "keygen": keygen,
            "sign": sign,
            "verify": verify,
        }

        if p.algorithm == "RSDPG":
            memory["fz_vec_sub_m"] = fz_vec_sub_m
            memory["fz_inf_w_by_fz_matrix"] = fz_inf_w_by_fz_matrix
            memory["fz_dz_norm_m"] = fz_dz_norm_m

        for name, (ccmram, stack) in memory.items():
            writer.writerow([p.version, name, ccmram, stack, ccmram + stack])