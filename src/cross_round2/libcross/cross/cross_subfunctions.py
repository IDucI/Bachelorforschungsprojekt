import ctypes
from ctypes import c_uint16, c_uint32, c_uint64, c_uint8, POINTER, c_ulonglong, c_int
from typing import List, Tuple


# CSPRNG_STATE_T maps to shake128incctx for Category 1 and shake256incctx for Category 3/5.
# Both use uint64_t ctx[26].
class c_csprng_state(ctypes.Structure):
    _fields_ =[("ctx", ctypes.c_uint64 *26)]


class CrossSubfunctions:
    def __init__(self, cross) -> None:
        self.cross = cross
        self.params = cross.params
        self.algorithm = self.params.algorithm

        self.FZ_ELEM = c_uint8
        self.FP_ELEM = c_uint16 if self.algorithm == "RSDPG" else c_uint8

        self.n = self.params.n
        self.k = self.params.k
        self.m = self.params.m
        self.t = self.params.t
        self.w = self.params.w
        
        self.tree_nodes_to_store        = self.params.tree_nodes_to_store

        self.seed_length_bytes          = self.params.seed_length_bytes
        self.keypair_seed_length_bytes  = self.params.keypair_seed_length_bytes
        self.hash_digest_length         = self.params.hash_digest_length
        self.salt_length_bytes          = self.params.salt_length_bytes
        self.num_nodes_merkle_tree      = self.params.num_nodes_merkle_tree
        self.num_nodes_seed_tree        = self.params.num_nodes_seed_tree
        self.densely_packed_fp_vec_size = self.params.densely_packed_fp_vec_size
        self.densely_packed_fp_syn_size = self.params.densely_packed_fp_syn_size
        self.densely_packed_fz_vec_size = self.params.densely_packed_fz_vec_size

        if self.algorithm == "RSDPG":
            self.densely_packed_fz_rsdp_g_vec_size = self.params.densely_packed_fz_rsdp_g_vec_size

    def load_dll(self):
        """Declares ctypes argument and return types for the CROSS subfunctions."""

        # ------------------------------------------------------------------------
        #  Functions for internal state calculation
        # ------------------------------------------------------------------------

        self.cross.c_cross.cross_randombytes.argtypes = [POINTER(c_uint8), c_ulonglong]
        self.cross.c_cross.cross_randombytes.restype = None

        self.cross.c_cross.cross_gen_seed_tree.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_gen_seed_tree.restype = None

        self.cross.c_cross.cross_seed_leaves.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_seed_leaves.restype = None

        self.cross.c_cross.cross_csprng_initialize.argtypes = [POINTER(c_csprng_state), POINTER(c_uint8), c_uint32, c_uint16]
        self.cross.c_cross.cross_csprng_initialize.restype = None

        if self.algorithm == "RSDP":
            self.cross.c_cross.cross_csprng_fz_vec.argtypes = [POINTER(self.FZ_ELEM), POINTER(c_csprng_state)]
            self.cross.c_cross.cross_csprng_fz_vec.restype = None

        elif self.algorithm == "RSDPG":
            self.cross.c_cross.cross_csprng_fz_inf_w.argtypes = [POINTER(self.FZ_ELEM), POINTER(c_csprng_state)]
            self.cross.c_cross.cross_csprng_fz_inf_w.restype = None

        self.cross.c_cross.cross_csprng_fp_vec.argtypes = [POINTER(self.FP_ELEM), POINTER(c_csprng_state)]
        self.cross.c_cross.cross_csprng_fp_vec.restype = None

        self.cross.c_cross.cross_fp_dz_norm_synd.argtypes = [POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_dz_norm_synd.restype = None

        self.cross.c_cross.cross_hash.argtypes = [POINTER(c_uint8), POINTER(c_uint8), c_uint64, c_uint16]
        self.cross.c_cross.cross_hash.restype = None

        self.cross.c_cross.cross_tree_root.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_tree_root.restype = None

        self.cross.c_cross.cross_csprng_fp_vec_chall_1.argtypes = [POINTER(self.FP_ELEM), POINTER(c_csprng_state)]
        self.cross.c_cross.cross_csprng_fp_vec_chall_1.restype = None

        self.cross.c_cross.cross_fp_dz_norm.argtypes = [POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_dz_norm.restype = None

        self.cross.c_cross.cross_pack_fp_vec.argtypes = [POINTER(c_uint8), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_pack_fp_vec.restype = None

        self.cross.c_cross.cross_tree_proof.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_tree_proof.restype = c_uint16

        self.cross.c_cross.cross_seed_path.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_seed_path.restype = c_int

        self.cross.c_cross.cross_csprng_randombytes.argtypes = [POINTER(c_uint8), c_ulonglong, POINTER(c_csprng_state)]
        self.cross.c_cross.cross_csprng_randombytes.restype = None
            
        # ------------------------------------------------------------------------
        #  Firmware Subroutines
        # ------------------------------------------------------------------------

        if self.algorithm == "RSDPG":
            self.cross.c_cross.cross_pack_fz_rsdp_g_vec.argtypes = [POINTER(c_uint8), POINTER(self.FZ_ELEM)]
            self.cross.c_cross.cross_pack_fz_rsdp_g_vec.restype = None

        self.cross.c_cross.cross_convert_restr_vec_to_fp.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM)]
        self.cross.c_cross.cross_convert_restr_vec_to_fp.restype = None

        self.cross.c_cross.cross_restr_vec_by_fp_matrix.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_restr_vec_by_fp_matrix.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FP_ELEM), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_matrix.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FP_ELEM), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_vec_by_fp_matrix.restype = None 

        self.cross.c_cross.cross_fz_vec_sub_n.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM)]
        self.cross.c_cross.cross_fz_vec_sub_n.restype = None

        if self.algorithm == "RSDP":
            self.cross.c_cross.cross_expand_sk.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FP_ELEM), POINTER(c_uint8)]
        elif self.algorithm == "RSDPG":
            self.cross.c_cross.cross_expand_sk.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM), POINTER(c_uint8)]
        self.cross.c_cross.cross_expand_sk.restype = None

        self.cross.c_cross.cross_fz_dz_norm_n.argtypes = [POINTER(self.FZ_ELEM)]
        self.cross.c_cross.cross_fz_dz_norm_n.restype = None

        self.cross.c_cross.cross_fp_vec_by_restr_vec_scaled.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM), self.FP_ELEM, POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_vec_by_restr_vec_scaled.restype = None

        self.cross.c_cross.cross_expand_digest_to_fixed_weight.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_expand_digest_to_fixed_weight.restype = None

        self.cross.c_cross.cross_pack_fp_syn.argtypes = [POINTER(c_uint8), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_pack_fp_syn.restype = None

        self.cross.c_cross.cross_pack_fz_vec.argtypes = [POINTER(c_uint8), POINTER(self.FZ_ELEM)]
        self.cross.c_cross.cross_pack_fz_vec.restype = None

        if self.algorithm == "RSDP":
            self.cross.c_cross.cross_expand_pk.argtypes = [POINTER(self.FP_ELEM), POINTER(c_uint8)]
        elif self.algorithm == "RSDPG":
            self.cross.c_cross.cross_expand_pk.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM), POINTER(c_uint8)]
        self.cross.c_cross.cross_expand_pk.restype = None

        if self.algorithm == "RSDPG":
            self.cross.c_cross.cross_fz_inf_w_by_fz_matrix.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM)]
            self.cross.c_cross.cross_fz_inf_w_by_fz_matrix.restype = None

            self.cross.c_cross.cross_fz_vec_sub_m.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM)]
            self.cross.c_cross.cross_fz_vec_sub_m.restype = None

            self.cross.c_cross.cross_fz_dz_norm_m.argtypes = [POINTER(self.FZ_ELEM)]
            self.cross.c_cross.cross_fz_dz_norm_m.restype = None

    # ------------------------------------------------------------------------
    #  Functions for internal state calculation
    # ------------------------------------------------------------------------

    def randombytes(self, length: int) -> bytes:
        buffer = (c_uint8 * length)()

        self.cross.c_cross.cross_randombytes(buffer, c_ulonglong(length)) 
        return bytes(buffer)

    def gen_seed_tree(self, root_seed: bytes, salt: bytes) -> bytes:
        if len(root_seed) != self.seed_length_bytes:
            raise ValueError(f"Expected root_seed to have length {self.seed_length_bytes}, got {len(root_seed)}")
        if len(salt) != self.salt_length_bytes:
            raise ValueError(f"Expected salt to have length {self.salt_length_bytes}, got {len(salt)}")

        c_seed_tree   = (c_uint8 * (self.num_nodes_seed_tree * self.seed_length_bytes))()
        c_root_seed = (c_uint8 * (self.seed_length_bytes))(*root_seed)
        c_salt      = (c_uint8 * (self.salt_length_bytes))(*salt)

        self.cross.c_cross.cross_gen_seed_tree(c_seed_tree, c_root_seed, c_salt)
        return bytes(c_seed_tree)

    def seed_leaves(self, seed_tree: bytes) -> bytes:
        size_seed_tree = self.num_nodes_seed_tree * self.seed_length_bytes
        if len(seed_tree) != (size_seed_tree):
            raise ValueError(f"Expected seed_tree to have length {size_seed_tree}, got {len(seed_tree)}")

        c_seed_tree   = (c_uint8 * size_seed_tree)(*seed_tree)
        c_round_seeds = (c_uint8 * (self.t * self.seed_length_bytes))()

        self.cross.c_cross.cross_seed_leaves(c_round_seeds, c_seed_tree)
        return bytes(c_round_seeds)

    def csprng_initialize(self, seed: bytes, dsc: int) -> c_csprng_state:
        # No fixed length check since the seed length varies by CSPRNG use case.
        seed_len_bytes = len(seed)
        c_state = c_csprng_state()
        c_seed  = (c_uint8 * len(seed))(*seed)
        
        self.cross.c_cross.cross_csprng_initialize(c_state, c_seed, seed_len_bytes, dsc)
        return c_state

    def csprng_fz_vec(self, csprng_state: c_csprng_state) -> List[int]:
        if self.algorithm == "RSDPG": raise ValueError("csprng_fz_vec is only available for RSDP")
        c_res = (self.FZ_ELEM * self.n)()

        self.cross.c_cross.cross_csprng_fz_vec(c_res, csprng_state)
        return list(c_res)

    def csprng_fz_inf_w(self, csprng_state: c_csprng_state) -> List[int]:
        if self.algorithm == "RSDP": raise ValueError("csprng_fz_inf_w is only available for RSDPG")
        c_res = (self.FZ_ELEM * self.m)()

        self.cross.c_cross.cross_csprng_fz_inf_w(c_res, csprng_state)
        return list(c_res)

    def csprng_fp_vec(self, csprng_state: c_csprng_state) -> List[int]:
        c_res = (self.FP_ELEM * self.n)()
        
        self.cross.c_cross.cross_csprng_fp_vec(c_res, csprng_state)
        return list(c_res)

    def fp_dz_norm_synd(self, v: List[int]) -> List[int]:
        if len(v) != (self.n - self.k):
            raise ValueError(f"Expected v to have length {(self.n -  self.k)}, got {len(v)}")
        c_v = (self.FP_ELEM * (self.n - self.k))(*v)

        self.cross.c_cross.cross_fp_dz_norm_synd(c_v)
        return list(c_v)

    def hash(self, m: bytes, dsc: int) -> bytes:
        c_digest = (c_uint8 * self.hash_digest_length)()
        c_m      = (c_uint8 * len(m))(*m)  

        self.cross.c_cross.cross_hash(c_digest, c_m, len(m), dsc)
        return bytes(c_digest)

    def tree_root(self, leaves: list[int]) -> tuple[bytes, bytes]:
        matrix_size = self.t * self.hash_digest_length
        if len(leaves) != matrix_size:
            raise ValueError(f"Expected leaves to have length {matrix_size}, got {len(leaves)}")

        c_root   = (c_uint8 * self.hash_digest_length)()
        c_tree   = (c_uint8 * (self.num_nodes_merkle_tree * self.hash_digest_length))()
        c_leaves = (c_uint8 * matrix_size)(*leaves)

        self.cross.c_cross.cross_tree_root(c_root, c_tree, c_leaves)
        return bytes(c_root), bytes(c_tree)

    def csprng_fp_vec_chall_1(self, csprng_state: c_csprng_state) -> List[int]:
        c_res = (self.FP_ELEM * self.t)()

        self.cross.c_cross.cross_csprng_fp_vec_chall_1(c_res, csprng_state)
        return list(c_res)

    def fp_dz_norm(self, v: List[int]) -> List[int]:
        if len(v) != self.n:
            raise ValueError(f"Expected v to have length {self.n}, got {len(v)}")

        c_v = (self.FP_ELEM * self.n)(*v)
        self.cross.c_cross.cross_fp_dz_norm(c_v)
        return list(c_v)

    def pack_fp_vec(self, inp: List[int]) -> bytes:
        if len(inp) != self.n:
            raise ValueError(f"Expected inp to have length {self.n}, got {len(inp)}")

        c_out = (c_uint8 * self.densely_packed_fp_vec_size)()
        c_inp = (self.FP_ELEM * self.n)(*inp)

        self.cross.c_cross.cross_pack_fp_vec(c_out, c_inp)
        return bytes(c_out)

    def tree_proof(self, tree: List[int], leaves_to_reveal: List[int]) -> tuple[int, bytes]:
        tree_size = self.num_nodes_merkle_tree * self.hash_digest_length
        if len(tree) != tree_size:
            raise ValueError(f"Expected tree to have length {tree_size}, got {len(tree)}")
        if len(leaves_to_reveal) != self.t:
            raise ValueError(f"Expected leaves_to_reveal to have length {self.t}, got {len(leaves_to_reveal)}")

        c_mtp              = (c_uint8 * (self.hash_digest_length * self.tree_nodes_to_store))()
        c_tree             = (c_uint8 * tree_size)(*tree)
        c_leaves_to_reveal = (c_uint8 * self.t)(*leaves_to_reveal)

        res = self.cross.c_cross.cross_tree_proof(c_mtp, c_tree, c_leaves_to_reveal)
        return res, bytes(c_mtp)

    def seed_path(self, seed_tree: List[int], indices_to_publish: List[int]) -> tuple[int, bytes]:
        seed_tree_size = self.num_nodes_seed_tree * self.seed_length_bytes
        if len(seed_tree) != seed_tree_size:
            raise ValueError(f"Expected seed_tree to have length {seed_tree_size}, got {len(seed_tree)}")
        if len(indices_to_publish) != self.t:
            raise ValueError(f"Expected indices_to_publish to have length {self.t}, got {len(indices_to_publish)}")

        # A published parent represents all seeds below it -> in the worst case, we store all leaves -> T seeds.
        c_seed_storage       = (c_uint8 * (self.t * self.seed_length_bytes))()
        c_seed_tree          = (c_uint8 * seed_tree_size)(*seed_tree)
        c_indices_to_publish = (c_uint8 * self.t)(*indices_to_publish)

        res = self.cross.c_cross.cross_seed_path(c_seed_storage, c_seed_tree, c_indices_to_publish)
        # res is the number of published seeds, but the signature uses a fixed-size path field.
        # Any unused bytes in the path field must remain zero.
        return res, bytes(c_seed_storage[:self.tree_nodes_to_store * self.seed_length_bytes])

    def csprng_randombytes(self, xlen: int, csprng_state: c_csprng_state) -> bytes:
        c_x = (c_uint8 * xlen)()
        self.cross.c_cross.cross_csprng_randombytes(c_x, xlen, csprng_state)
        return bytes(c_x)
        
        
    # ------------------------------------------------------------------------
    #  Firmware Subroutines
    # ------------------------------------------------------------------------

    def pack_fz_rsdp_g_vec(self, inp: List[int]) -> bytes:
        if self.algorithm == "RSDP":
            raise ValueError("pack_fz_rsdp_g_vec is only available for RSDPG")
        if len(inp) != self.m:
            raise ValueError(f"Expected inp to have length {self.m}, got {len(inp)}")

        c_out = (c_uint8 * self.densely_packed_fz_rsdp_g_vec_size)()
        c_inp = (self.FZ_ELEM * self.m)(*inp)

        self.cross.c_cross.cross_pack_fz_rsdp_g_vec(c_out, c_inp)
        return bytes(c_out)
        
    def convert_restr_vec_to_fp(self, inp: List[int]) -> List[int]:
        if len(inp) != self.n:
            raise ValueError(f"Expected inp to have length {self.n}, got {len(inp)}")

        c_inp = (self.FZ_ELEM * self.n)(*inp)
        c_res = (self.FP_ELEM * self.n)()

        self.cross.c_cross.cross_convert_restr_vec_to_fp(c_res, c_inp)

        return list(c_res)
    
    def restr_vec_by_fp_matrix(self, e: List[int], V_tr: List[int]) -> List[int]:
        if len(e) != self.n:
            raise ValueError(f"Expected e to have length {self.n}, got {len(e)}")
        matrix_size = self.k * (self.n - self.k)
        if len(V_tr) != matrix_size:
            raise ValueError(f"Expected V_tr to have size {matrix_size}, got {len(V_tr)}")

        c_res = (self.FP_ELEM * (self.n - self.k))()
        c_e = (self.FZ_ELEM * self.n)(*e)
        c_V_tr = (self.FP_ELEM * matrix_size)(*V_tr)

        self.cross.c_cross.cross_restr_vec_by_fp_matrix(c_res, c_e, c_V_tr)
        return list(c_res)

    def fp_vec_by_fp_vec_pointwise(self, in1: List[int], in2: List[int]) -> List[int]:
        if len(in1) != self.n:
            raise ValueError(f"Expected in1 to have length {self.n}, got {len(in1)}")
        if len(in2) != self.n:
            raise ValueError(f"Expected in2 to have length {self.n}, got {len(in2)}")
    
        c_res = (self.FP_ELEM * self.n)()
        c_in1 = (self.FP_ELEM * self.n)(*in1)
        c_in2 = (self.FP_ELEM * self.n)(*in2)
    
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise(c_res, c_in1, c_in2)
        return list(c_res)
    
    def fp_vec_by_fp_matrix(self, e: List[int], V_tr: List[int]) -> List[int]:
        if len(e) != self.n:
            raise ValueError(f"Expected e to have length {self.n}, got {len(e)}")
        matrix_size = self.k * (self.n - self.k)
        if len(V_tr) != matrix_size:
            raise ValueError(f"Expected V_tr to have length {matrix_size}, got {len(V_tr)}")

        c_res = (self.FP_ELEM * (self.n - self.k))()
        c_e = (self.FP_ELEM * self.n)(*e)
        c_V_tr = (self.FP_ELEM * matrix_size)(*V_tr)

        self.cross.c_cross.cross_fp_vec_by_fp_matrix(c_res, c_e, c_V_tr)

        return list(c_res)

    def fz_vec_sub_n(self, a: List[int], b: List [int]) -> List[int]:
        if len(a) != self.n: 
            raise ValueError(f"Expected a to have length {self.n}, got {len(a)}")
        if len(b) != self.n:
            raise ValueError(f"Expected b to have length {self.n}, got {len(b)}")
    
        c_res = (self.FZ_ELEM * self.n)()
        c_a   = (self.FZ_ELEM * self.n)(*a)
        c_b   = (self.FZ_ELEM * self.n)(*b)
    
        self.cross.c_cross.cross_fz_vec_sub_n(c_res, c_a, c_b)
        return list(c_res)

    def expand_sk(self, seed_sk: bytes) -> Tuple[List[int], List[int]] | Tuple[List[int], List[int], List[int], List[int]]:
        """Returns e_bar and V_tr. RSDPG additionally returns e_G_bar and W_mat."""
        if len(seed_sk) != self.keypair_seed_length_bytes: 
            raise ValueError(f"Expected seed_sk to have length {self.keypair_seed_length_bytes}, got {len(seed_sk)}")

        c_seed_sk = (c_uint8 * self.keypair_seed_length_bytes)(*seed_sk)
        c_e_bar   = (self.FZ_ELEM * self.n)()
        c_V_tr    = (self.FP_ELEM * (self.k * (self.n - self.k)))()

        if self.algorithm == "RSDP":
            self.cross.c_cross.cross_expand_sk(c_e_bar, c_V_tr, c_seed_sk)
            return list(c_e_bar), list(c_V_tr)

        elif self.algorithm == "RSDPG":
            c_e_G_bar = (self.FZ_ELEM * self.m)()
            c_W_mat   = (self.FZ_ELEM * (self.m * (self.n - self.m)))()
            self.cross.c_cross.cross_expand_sk(c_e_bar, c_e_G_bar, c_V_tr, c_W_mat, c_seed_sk)
            return list(c_e_bar), list(c_e_G_bar), list(c_V_tr), list(c_W_mat)
    
    def fz_dz_norm_n(self, v: List[int]) -> List[int]:
        if len(v) != self.n:
            raise ValueError(f"Expected v to have length {self.n}, got {len(v)}")
        
        c_v = (self.FZ_ELEM * self.n)(*v)

        self.cross.c_cross.cross_fz_dz_norm_n(c_v)
        return list(c_v)
    
    def fp_vec_by_restr_vec_scaled(self, e: List[int], chall_1: int, u_prime: List[int]) -> List[int]:
        if len(e) != self.n:
            raise ValueError(f"Expected e to have length {self.n}, got {len(e)}")
        if len(u_prime) != self.n:
            raise ValueError(f"Expected u_prime to have length {self.n}, got {len(u_prime)}")
        
        c_res = (self.FP_ELEM * self.n)()
        c_e = (self.FZ_ELEM * self.n)(*e)
        c_u_prime = (self.FP_ELEM * self.n)(*u_prime)
        
        self.cross.c_cross.cross_fp_vec_by_restr_vec_scaled(c_res, c_e, self.FP_ELEM(chall_1), c_u_prime)
        return list(c_res)
    
    def expand_digest_to_fixed_weight(self, digest: bytes) -> List[int]:
        if len(digest) != self.hash_digest_length:
            raise ValueError(f"Expected digest to have length {self.hash_digest_length}, got {len(digest)}")

        c_fixed_weight_string = (c_uint8 * self.t)()
        c_digest = (c_uint8 * self.hash_digest_length)(*digest)
        
        self.cross.c_cross.cross_expand_digest_to_fixed_weight(c_fixed_weight_string, c_digest)
        return list(c_fixed_weight_string)
    
    def pack_fp_syn(self, inp: List[int]) -> bytes:
        expected_len = self.n - self.k
        if len(inp) != expected_len:
            raise ValueError(f"Expected inp to have length {expected_len}, got {len(inp)}")
            
        c_out = (c_uint8 * self.densely_packed_fp_syn_size)()
        c_inp = (self.FP_ELEM * expected_len)(*inp)
        
        self.cross.c_cross.cross_pack_fp_syn(c_out, c_inp)
        return bytes(c_out)

    def pack_fz_vec(self, inp: List[int]) -> bytes:
        if len(inp) != self.n:
            raise ValueError(f"Expected inp to have length {self.n}, got {len(inp)}")
            
        c_out = (c_uint8 * self.densely_packed_fz_vec_size)()
        c_inp = (self.FZ_ELEM * self.n)(*inp)
        
        self.cross.c_cross.cross_pack_fz_vec(c_out, c_inp)
        return bytes(c_out)

    def expand_pk(self, seed_pk: bytes) -> List[int] | Tuple[List[int], List[int]]:
        """Returns V_tr. RSDPG additionally returns W_mat."""
        if len(seed_pk) != self.keypair_seed_length_bytes:
            raise ValueError(f"Expected seed_pk to have length {self.keypair_seed_length_bytes}, got {len(seed_pk)}")
            
        c_V_tr = (self.FP_ELEM * (self.k * (self.n - self.k)))()
        c_seed_pk = (c_uint8 * self.keypair_seed_length_bytes)(*seed_pk)

        if self.algorithm == "RSDP":
            self.cross.c_cross.cross_expand_pk(c_V_tr, c_seed_pk)
            return list(c_V_tr)
        elif self.algorithm == "RSDPG":
            c_W_mat = (self.FZ_ELEM * (self.m * (self.n - self.m)))()
            
            self.cross.c_cross.cross_expand_pk(c_V_tr, c_W_mat, c_seed_pk)
            return list(c_V_tr), list(c_W_mat)

    def fz_inf_w_by_fz_matrix(self, e: List[int], W_mat: List[int]) -> List[int]:
        if self.algorithm == "RSDP":
            raise ValueError("fz_inf_w_by_fz_matrix is only available for RSDPG")
        
        matrix_size = self.m * (self.n - self.m)
        if len(e) != self.m: 
            raise ValueError(f"Expected e to have length {self.m}, got {len(e)}")
        if len(W_mat) != matrix_size:
            raise ValueError(f"Expected W_mat to have length {matrix_size}, got {len(W_mat)}")

        c_res = (self.FZ_ELEM * self.n)()
        c_e = (self.FZ_ELEM * self.m)(*e)
        c_W_mat = (self.FZ_ELEM * matrix_size)(*W_mat)
        
        self.cross.c_cross.cross_fz_inf_w_by_fz_matrix(c_res, c_e, c_W_mat)
        return list(c_res)

    def fz_vec_sub_m(self, a: List[int], b: List[int]) -> List[int]:
        if self.algorithm == "RSDP":
            raise ValueError("fz_vec_sub_m is only available for RSDPG")
        
        if len(a) != self.m:  
            raise ValueError(f"Expected a to have length {self.m}, got {len(a)}")
        if len(b) != self.m:
            raise ValueError(f"Expected b to have length {self.m}, got {len(b)}")

        c_res = (self.FZ_ELEM * self.m)()
        c_a   = (self.FZ_ELEM * self.m)(*a)
        c_b   = (self.FZ_ELEM * self.m)(*b)
        
        self.cross.c_cross.cross_fz_vec_sub_m(c_res, c_a, c_b)
        return list(c_res)

    def fz_dz_norm_m(self, v: List[int]) -> List[int]:
        if self.algorithm == "RSDP":
            raise ValueError("fz_dz_norm_m is only available for RSDPG")
        
        if len(v) != self.m:
            raise ValueError(f"Expected v to have length {self.m}, got {len(v)}")
            
        c_v = (self.FZ_ELEM * self.m)(*v)
        self.cross.c_cross.cross_fz_dz_norm_m(c_v)
        return list(c_v)



