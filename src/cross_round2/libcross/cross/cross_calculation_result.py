from dataclasses import dataclass, field

@dataclass
class ExpandSkData:
    e_bar: list = field(default_factory=list)
    V_tr: list = field(default_factory=list)
    # RSDPG parts (optional)
    e_G_bar: list | None = field(default_factory=list)
    W_mat: list | None = field(default_factory=list)

@dataclass
class FzVecSubNData:
    e_bar: list = field(init=False)
    e_bar_prime: list = field(default_factory=list)
    v_bar: list = field(default_factory=list)

@dataclass
class ConvertRestrVecToFpData:
    v_bar: list = field(init=False)
    v: list = field(default_factory=list)

# Contains the intermediate values for both calls in Cross_sign
@dataclass
class FzDzNormNData:
    v_bar_in: list = field(init=False)
    v_bar_out: list = field(default_factory=list)

    e_bar_prime_in: list | None = field(init=False)
    e_bar_prime_out: list  | None = field(default_factory=list)

@dataclass
class FpVecByFpVecPointwiseData:
    v: list = field(init=False)
    u_prime: list = field(default_factory=list)
    u: list = field(default_factory=list)

@dataclass
class FpVecByFpMatrixData:
    u : list = field(init=False)
    V_tr: list = field(init=False)
    s_prime: list = field(default_factory=list)

@dataclass
class PackFpSynData:
    s_prime_in: list = field(default_factory=list)
    s_prime_out: list = field(default_factory=list)

@dataclass
class FpVecByRestrVecScaledData:
    e_bar_prime: list = field(init=False)
    chall_1: list = field(default_factory=list)
    u_prime: list = field(init=False)
    y: list = field(default_factory=list)

@dataclass
class ExpandDigestToFixedWeightData:
    digest_chall_2: bytes = field(default_factory=bytes)
    chall_2: list = field(default_factory=list)

@dataclass
class PackFzVecData:
    v_bar_in: list | None = field(init=False)
    v_bar_out: list |None = field(default_factory=list)

@dataclass
class PackFzRsdpGVecData:
    v_G_bar_in: list | None = field(init=False)
    v_G_bar_out: list | None = field(default_factory=list)

@dataclass
class FzVecSubMData:
    e_G_bar: list | None = field(init=False)
    e_G_bar_prime: list  | None = field(default_factory=list)
    v_G_bar: list  | None = field(default_factory=list)

@dataclass
class FzDzNormMData:
    v_G_bar_in: list | None = field(init=False)
    v_G_bar_out: list | None = field(default_factory=list)

@dataclass
class FzInfWByFzMatrixData:
    e_G_bar_prime: list | None = field(init=False)
    e_bar_prime: list | None = field(default_factory=list)
    W_mat: list | None = field(init=False)

@dataclass
class CalculationResult:
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
    seed_pk  : bytes
    root_seed: bytes
    salt     : bytes
    signature: bytes = field(init=False)

    expand_sk: ExpandSkData = field(default_factory=ExpandSkData)
    fz_vec_sub_n: FzVecSubNData = field(default_factory=FzVecSubNData)
    convert_restr_vec_to_fp: ConvertRestrVecToFpData = field(default_factory=ConvertRestrVecToFpData)
    fz_dz_norm_n: FzDzNormNData = field(default_factory=FzDzNormNData)
    fp_vec_by_fp_vec_pointwise: FpVecByFpVecPointwiseData = field(default_factory=FpVecByFpVecPointwiseData)
    fp_vec_by_fp_matrix: FpVecByFpMatrixData = field(default_factory=FpVecByFpMatrixData)
    pack_fp_syn: PackFpSynData = field(default_factory=PackFpSynData)
    fp_vec_by_restr_vec_scaled: FpVecByRestrVecScaledData = field(default_factory=FpVecByRestrVecScaledData)
    expand_digest_to_fixed_weight: ExpandDigestToFixedWeightData = field(default_factory=ExpandDigestToFixedWeightData)
    pack_fz_vec: PackFzVecData = field(default_factory=PackFzVecData)
    pack_fz_rsdp_g_vec: PackFzRsdpGVecData = field(default_factory=PackFzRsdpGVecData)
    fz_vec_sub_m: FzVecSubMData = field(default_factory=FzVecSubMData)
    fz_dz_norm_m: FzDzNormMData = field(default_factory=FzDzNormMData)
    fz_inf_w_by_fz_matrix: FzInfWByFzMatrixData = field(default_factory=FzInfWByFzMatrixData)

    def __post_init__(self):
        self.fz_vec_sub_n.e_bar = self.expand_sk.e_bar
        self.convert_restr_vec_to_fp.v_bar = self.fz_vec_sub_n.v_bar
        self.fz_dz_norm_n.v_bar_in = self.fz_vec_sub_n.v_bar
        self.fp_vec_by_fp_vec_pointwise.v = self.convert_restr_vec_to_fp.v
        self.fp_vec_by_fp_matrix.u = self.fp_vec_by_fp_vec_pointwise.u
        self.fp_vec_by_fp_matrix.V_tr = self.expand_sk.V_tr
        self.fp_vec_by_restr_vec_scaled.e_bar_prime = self.fz_vec_sub_n.e_bar_prime
        self.fp_vec_by_restr_vec_scaled.u_prime = self.fp_vec_by_fp_vec_pointwise.u_prime
        self.fz_vec_sub_m.e_G_bar = self.expand_sk.e_G_bar
        self.fz_dz_norm_m.v_G_bar_in = self.fz_vec_sub_m.v_G_bar
        self.fz_inf_w_by_fz_matrix.e_G_bar_prime = self.fz_vec_sub_m.e_G_bar_prime
        self.fz_inf_w_by_fz_matrix.W_mat = self.expand_sk.W_mat
        self.fz_dz_norm_n.e_bar_prime_in = self.fz_inf_w_by_fz_matrix.e_bar_prime
        self.pack_fz_vec.v_bar_in = self.fz_dz_norm_n.v_bar_out
        self.pack_fz_rsdp_g_vec.v_G_bar_in = self.fz_dz_norm_m.v_G_bar_out