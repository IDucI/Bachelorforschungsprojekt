"""Data containers for intermediate values collected during CROSS key generation
and signing.

The result objects group firmware-relevant subroutine inputs and outputs and
link shared values between containers.
"""

from dataclasses import dataclass, field

@dataclass
class FzVecSubNData:
    """
    Intermediate values for fz_vec_sub_n during CROSS_sign().

    One entry is stored per signing round:
        e_bar, e_bar_prime[i] -> fz_vec_sub_n -> v_bar[i]
    """
    e_bar: list = field(default_factory=list)
    e_bar_prime: list = field(default_factory=list)
    v_bar: list = field(default_factory=list)

@dataclass
class ConvertRestrVecToFpData:
    """
    Intermediate values for convert_restr_vec_to_fp during CROSS_sign().

    One entry is stored per signing round:
        v_bar[i] -> convert_restr_vec_to_fp -> v[i]
    """
    v_bar: list = field(init=False)
    v: list = field(default_factory=list)

@dataclass
class KeygenFzDzNormNData:
    """
    Intermediate values for fz_dz_norm_n during CROSS_keygen().

    The input and corresponding output are stored as:
        e_bar_in -> fz_dz_norm_n -> e_bar_out
    """
    e_bar_in: list = field(init=False)
    e_bar_out: list = field(default_factory=list)

@dataclass
class SignFzDzNormNData:
    """
    Intermediate values for both calls to fz_dz_norm_n during CROSS_sign().

    One entry is stored per signing round:
        v_bar_in[i] -> fz_dz_norm_n -> v_bar_out[i]

    For RSDPG, an additional entry is stored per signing round:
        e_bar_prime_in[i] -> fz_dz_norm_n -> e_bar_prime_out[i]
    """
    v_bar_in: list = field(init=False)
    v_bar_out: list = field(default_factory=list)

    e_bar_prime_in: list = field(init=False)
    e_bar_prime_out: list = field(default_factory=list)

@dataclass
class FpVecByFpVecPointwiseData:
    """
    Intermediate values for fp_vec_by_fp_vec_pointwise during CROSS_sign().

    One entry is stored per signing round:
        u_prime[i], v[i] -> fp_vec_by_fp_vec_pointwise -> u[i]
    """
    v: list = field(init=False)
    u_prime: list = field(default_factory=list)
    u: list = field(default_factory=list)

@dataclass
class FpVecByFpMatrixData:
    """
    Intermediate values for fp_vec_by_fp_matrix during CROSS_sign().

    One entry is stored per signing round:
        u[i], V_tr -> fp_vec_by_fp_matrix -> s_prime[i]
    """
    u : list = field(init=False)
    V_tr: list = field(default_factory=list)
    s_prime: list = field(default_factory=list)

@dataclass
class PackFpSynData:
    """
    Intermediate values for pack_fp_syn during CROSS_sign().

    One entry is stored per signing round:
        s_prime_in[i] -> pack_fp_syn -> s_prime_out[i]
    """
    s_prime_in: list = field(init=False)
    s_prime_out: list = field(default_factory=list)

@dataclass
class FpDzNormSyndData:
    """
    Intermediate values for fp_dz_norm_synd during CROSS_sign().

    One entry is stored per signing round:
        s_prime_in[i] -> fp_dz_norm_synd -> s_prime_out[i]
    """
    s_prime_in: list = field(default_factory=list)
    s_prime_out: list = field(default_factory=list)

@dataclass
class FpVecByRestrVecScaledData:
    """
    Intermediate values for fp_vec_by_restr_vec_scaled during CROSS_sign().

    One entry is stored per signing round:
        e_bar_prime[i], chall_1[i], u_prime[i] -> fp_vec_by_restr_vec_scaled -> y[i]
    """
    e_bar_prime: list = field(init=False)
    chall_1: list = field(default_factory=list)
    u_prime: list = field(init=False)
    y: list = field(default_factory=list)

@dataclass
class PackFzVecData:
    """
    Intermediate values for pack_fz_vec during CROSS_sign().

    One entry is stored per signing round:
        v_bar_in[i] -> pack_fz_vec -> v_bar_out[i]
    """
    v_bar_in: list = field(init=False)
    v_bar_out: list = field(default_factory=list)

@dataclass
class PackFzRsdpGVecData:
    """
    Intermediate values for pack_fz_rsdp_g_vec during CROSS_sign().

    One entry is stored per signing round:
        v_G_bar_in[i] -> pack_fz_rsdp_g_vec -> v_G_bar_out[i]
    """
    v_G_bar_in: list = field(init=False)
    v_G_bar_out: list = field(default_factory=list)

@dataclass
class FzVecSubMData:
    """
    Intermediate values for fz_vec_sub_m during CROSS_sign().

    One entry is stored per signing round:
        e_G_bar, e_G_bar_prime[i] -> fz_vec_sub_m -> v_G_bar[i]
    """
    e_G_bar: list = field(default_factory=list)
    e_G_bar_prime: list = field(default_factory=list)
    v_G_bar: list = field(default_factory=list)

@dataclass
class FzDzNormMData:
    """
    Intermediate values for fz_dz_norm_m during CROSS_sign().

    One entry is stored per signing round:
        v_G_bar_in[i] -> fz_dz_norm_m -> v_G_bar_out[i]
    """
    v_G_bar_in: list = field(init=False)
    v_G_bar_out: list = field(default_factory=list)

@dataclass
class SignFzInfWByFzMatrixData:
    """
    Intermediate values for fz_inf_w_by_fz_matrix during CROSS_sign().

    One entry is stored per signing round:
        e_G_bar_prime[i], W_mat -> fz_inf_w_by_fz_matrix -> e_bar_prime[i]
    """
    e_G_bar_prime: list = field(init=False)
    e_bar_prime: list = field(default_factory=list)
    W_mat: list = field(default_factory=list)

@dataclass
class KeygenFzInfWByFzMatrixData:
    """
    Intermediate values for fz_inf_w_by_fz_matrix during CROSS_keygen().

    The inputs and corresponding output are stored as:
        e_G_bar, W_mat -> fz_inf_w_by_fz_matrix -> e_bar
    """
    e_bar: list = field(default_factory=list)
    e_G_bar: list = field(default_factory=list)
    W_mat: list = field(default_factory=list)

@dataclass
class RestrVecByFpMatrixData:
    """
    Intermediate values for restr_vec_by_fp_matrix during CROSS_keygen().

    The input values and corresponding output are stored as:
        (e_bar, V_tr) -> restr_vec_by_fp_matrix -> s
    """
    s: list = field(default_factory=list)
    e_bar: list = field(default_factory=list)
    V_tr: list = field(default_factory=list)


@dataclass
class KeygenCalculationResult:
    """
    Stores intermediate values for all board-relevant subroutines while reproducing CROSS_keygen().

    Each subroutine has its own data container.
    Shared values are linked between containers in post_init to mirror the data flow of the reference implementation.
    """
    seed_sk  : bytes
    pk  : bytes = field(default_factory=bytes) #seed_pk || s

    fz_inf_w_by_fz_matrix: KeygenFzInfWByFzMatrixData = field(default_factory=KeygenFzInfWByFzMatrixData)
    fz_dz_norm_n: KeygenFzDzNormNData = field(default_factory=KeygenFzDzNormNData)
    restr_vec_by_fp_matrix: RestrVecByFpMatrixData = field(default_factory=RestrVecByFpMatrixData)

    def __post_init__(self):
        self.fz_dz_norm_n.e_bar_in = self.fz_inf_w_by_fz_matrix.e_bar

@dataclass
class SignCalculationResult:
    """
    Stores intermediate values for all board-relevant subroutines while reproducing CROSS_sign().

    Each subroutine has its own data container. 
    Shared values are linked between containers in post_init to mirror the data flow of the reference implementation.

    Note:
    The final response-packing calls to pack_fz_vec / pack_fz_rsdp_g_vec inside the chall_2-managed publication loop are not stored separately, 
    since they reuse intermediate values that are already available.
    """
    # Original seeds and salt used to generate this set of intermediates
    seed_sk  : bytes
    pk  : bytes
    root_seed: bytes
    salt     : bytes
    signature: bytes = field(init=False)

    fz_vec_sub_n: FzVecSubNData = field(default_factory=FzVecSubNData)
    convert_restr_vec_to_fp: ConvertRestrVecToFpData = field(default_factory=ConvertRestrVecToFpData)
    fz_dz_norm_n: SignFzDzNormNData = field(default_factory=SignFzDzNormNData)
    fp_vec_by_fp_vec_pointwise: FpVecByFpVecPointwiseData = field(default_factory=FpVecByFpVecPointwiseData)
    fp_vec_by_fp_matrix: FpVecByFpMatrixData = field(default_factory=FpVecByFpMatrixData)
    fp_dz_norm_synd: FpDzNormSyndData = field(default_factory=FpDzNormSyndData)
    pack_fp_syn: PackFpSynData = field(default_factory=PackFpSynData)
    fp_vec_by_restr_vec_scaled: FpVecByRestrVecScaledData = field(default_factory=FpVecByRestrVecScaledData)
    pack_fz_vec: PackFzVecData = field(default_factory=PackFzVecData)
    pack_fz_rsdp_g_vec: PackFzRsdpGVecData = field(default_factory=PackFzRsdpGVecData)
    fz_vec_sub_m: FzVecSubMData = field(default_factory=FzVecSubMData)
    fz_dz_norm_m: FzDzNormMData = field(default_factory=FzDzNormMData)
    fz_inf_w_by_fz_matrix: SignFzInfWByFzMatrixData = field(default_factory=SignFzInfWByFzMatrixData)

    def __post_init__(self):
        self.convert_restr_vec_to_fp.v_bar = self.fz_vec_sub_n.v_bar
        self.fz_dz_norm_n.v_bar_in = self.fz_vec_sub_n.v_bar
        self.fp_vec_by_fp_vec_pointwise.v = self.convert_restr_vec_to_fp.v
        self.fp_vec_by_fp_matrix.u = self.fp_vec_by_fp_vec_pointwise.u
        self.fp_vec_by_restr_vec_scaled.e_bar_prime = self.fz_vec_sub_n.e_bar_prime
        self.fp_vec_by_restr_vec_scaled.u_prime = self.fp_vec_by_fp_vec_pointwise.u_prime
        self.fz_dz_norm_m.v_G_bar_in = self.fz_vec_sub_m.v_G_bar
        self.fz_inf_w_by_fz_matrix.e_G_bar_prime = self.fz_vec_sub_m.e_G_bar_prime
        self.fz_dz_norm_n.e_bar_prime_in = self.fz_inf_w_by_fz_matrix.e_bar_prime
        self.pack_fz_vec.v_bar_in = self.fz_dz_norm_n.v_bar_out
        self.pack_fz_rsdp_g_vec.v_G_bar_in = self.fz_dz_norm_m.v_G_bar_out
        self.fp_dz_norm_synd.s_prime_in = self.fp_vec_by_fp_matrix.s_prime
        self.pack_fp_syn.s_prime_in = self.fp_dz_norm_synd.s_prime_out