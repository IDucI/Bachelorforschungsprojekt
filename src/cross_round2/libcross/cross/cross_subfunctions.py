import ctypes
from ctypes import c_uint16, c_uint32, c_uint64, c_uint8, POINTER, c_ulonglong
from pickletools import uint8
from typing import List, Tuple
from .cross_params import get_params


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
        """Loads the native CROSS shared library (.so) via ctypes and declares the argument types (argtypes) and return types (restype) 
        of the C functions.This ensures type safety when passing Python lists (converted into ctypes arrays) to the raw C pointers of 
        the reference implementation. 
        """

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

        self.cross.c_cross.cross_fp_dz_norm_synd.artypes = [POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_dz_norm_synd.restype = None

        self.cross.c_cross.cross_hash.argtypes = [POINTER(c_uint8), POINTER(c_uint8), c_uint64, c_uint16]
        self.cross.c_cross.cross_hash.restype = None

        self.cross.c_cross.cross_tree_root.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_tree_root.restype = None

        self.cross.c_cross.cross_csprng_fp_vec_chall_1.argtypes = [POINTER(self.FP_ELEM), POINTER(c_csprng_state)]
        self.cross.c_cross.cross_csprng_fp_vec_chall_1.restype = None

        self.cross.c_cross.cross_fp_dz_norm.argtypte = [POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_dz_norm.restype = None

        self.cross.c_cross.cross_pack_fp_vec.argtypes = [POINTER(c_uint8), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_pack_fp_vec.restype = None

        self.cross.c_cross.cross_tree_proof.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_tree_proof.restype = c_uint16

        self.cross.c_cross.cross_seed_path.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_seed_path.restype = int

        if self.algorithm == "RSDPG":
            self.cross.c_cross.cross_pack_fz_rsdp_g_vec.argtypes = [POINTER(c_uint8), POINTER(self.FZ_ELEM)]
            self.cross.c_cross.cross_pack_fz_rsdp_g_vec.restype = None
            
        # ------------------------------------------------------------------------
        #  Subroutines
        # ------------------------------------------------------------------------

        # Vector conversion
        self.cross.c_cross.cross_convert_restr_vec_to_fp.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM)]
        self.cross.c_cross.cross_convert_restr_vec_to_fp.restype = None

        # Vector-Matrix arithmetic
        self.cross.c_cross.cross_restr_vec_by_fp_matrix.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_restr_vec_by_fp_matrix.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FP_ELEM), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_matrix.argtypes = [POINTER(self.FP_ELEM), POINTER(self.FP_ELEM), POINTER(self.FP_ELEM)]
        self.cross.c_cross.cross_fp_vec_by_fp_matrix.restype = None 

        self.cross.c_cross.cross_fz_vec_sub_n.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM)]
        self.cross.c_cross.cross_fz_vec_sub_n.restype = None

        # Key generation and expansion (Key Generation)
        if self.algorithm == "RSDP":
            self.cross.c_cross.cross_expand_sk.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FP_ELEM), POINTER(c_uint8)]
        elif self.algorithm == "RSDPG":
            self.cross.c_cross.cross_expand_sk.argtypes = [POINTER(self.FZ_ELEM), POINTER(self.FZ_ELEM), POINTER(self.FP_ELEM), POINTER(self.FZ_ELEM), POINTER(c_uint8)]
        self.cross.c_cross.cross_expand_sk.restype = None

        # Protocol core validation & scaling
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

        self.cross.c_cross.cross_unpack_fz_vec.argtypes = [POINTER(self.FZ_ELEM), POINTER(c_uint8)]
        self.cross.c_cross.cross_unpack_fz_vec.restype = c_uint8  # Returns 1 on success


        # Since the C function has 2 or 3 parameters depending on the variant, we check for type safety
        # whether the RSDPG group functions are available to choose the appropriate signature.
        if self.algorithm == "RSDP":
            # RSDP: cross_expand_pk(V_tr, seed_pk)
            self.cross.c_cross.cross_expand_pk.argtypes = [POINTER(self.FP_ELEM), POINTER(c_uint8)]
        elif self.algorithm == "RSDPG":
            # RSDPG: cross_expand_pk(V_tr, W_mat, seed_pk)
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

    def randombytes (self, length: int) -> bytes:
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
        c_round_seeds = (c_uint8* (self.t * self.seed_length_bytes))()

        self.cross.c_cross.cross_seed_leaves(c_round_seeds, c_seed_tree)
        return bytes(c_round_seeds)

    def csprng_initialize(self, seed: bytes, dsc: int) -> c_csprng_state:
        #seed_len_bytes = self.seed_length_bytes + self.salt_length_bytes
        #if len(seed) != seed_len_bytes:
        #    raise ValueError(f"Expected seed to have length {seed_len_bytes}, got {len(seed)}")
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

    def fp_dz_norm_synd(self, v:List[int]) -> List[int]:
        if len(v) != (self.n - self.k):
            raise ValueError(f"Expected v to have length {(self.n -  self.k)}, got {len(v)}")
        c_v = (self.FP_ELEM * (self.n- self.k))(*v)

        self.cross.c_cross.cross_fp_dz_norm_synd(c_v)
        return list(c_v)

    def hash(self, m: bytes, dsc: int) -> bytes:
        c_digest = (c_uint8 * self.hash_digest_length)()
        c_m      = (c_uint8 *len(m))(*m)  

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
        # The reference returns the number of published seeds in res -> so we only return that written part of seed_storage.
        return res, bytes(c_seed_storage[:self.tree_nodes_to_store * self.seed_length_bytes])

    def pack_fz_rsdp_g_vec (self, inp: List[int]) -> bytes:
        if len(inp) != self.m:
            raise ValueError(f"Expected inp to have length {self.m}, got {len(inp)}")

        c_out = (c_uint8 * self.densely_packed_fz_rsdp_g_vec_size)()
        c_inp = (self.FZ_ELEM * self.m)(*inp)

        self.cross.c_cross.cross_pack_fz_rsdp_g_vec(c_out, c_inp)
        return bytes(c_out)

    # ------------------------------------------------------------------------
    #  Subroutines
    # ------------------------------------------------------------------------
        
    def convert_restr_vec_to_fp(self, inp: List[int]) -> List[int]:
        """Maps a vector from the restricted subgroup (FZ) to the full field (FP) of length N."""
        if len(inp) != self.n:
            raise ValueError(f"Expected inp to have length {self.n}, got {len(inp)}")

        c_inp = (self.FZ_ELEM * self.n)(*inp)
        c_res = (self.FP_ELEM * self.n)()

        self.cross.c_cross.cross_convert_restr_vec_to_fp(c_res, c_inp)

        return list(c_res)
    
    def restr_vec_by_fp_matrix(self, e: List[int], V_tr: List[int]) -> List[int]:
        """Multiplies a restricted vector (length N) by a flat FP matrix of size K x (N-K)."""
        if len(e) != self.n:
            raise ValueError(f"Expected e to have length {self.n}, got {len(e)}")
        # V_tr is a flat list of size K * (N-K)
        matrix_size = self.k * (self.n - self.k)
        if len(V_tr) != matrix_size:
            raise ValueError(f"Expected V_tr to have size {matrix_size}, got {len(V_tr)}")

        c_res = (self.FP_ELEM * (self.n - self.k))()
        c_e = (self.FZ_ELEM * self.n)(*e)
        c_V_tr = (self.FP_ELEM * matrix_size)(*V_tr)

        self.cross.c_cross.cross_restr_vec_by_fp_matrix(c_res, c_e, c_V_tr)
        return list(c_res)

    def fp_vec_by_fp_vec_pointwise(self, in1: List[int], in2: List[int]) -> List[int]:
        """Performs a coordinate-wise multiplication of two FP vectors of length N."""
        # Validation: Both Entry vector must have the length N (self.n) 
        if len(in1) != self.n:
            raise ValueError(f"Expected in1 to have length {self.n}, got {len(in1)}")
        if len(in2) != self.n:
            raise ValueError(f"Expected in2 to have length {self.n}, got {len(in2)}")
    
        c_res = (self.FP_ELEM * self.n)()
        c_in1 = (self.FP_ELEM * self.n)(*in1)
        c_in2 = (self.FP_ELEM * self.n)(*in2)
    
        # The call of the C-Function
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise(c_res, c_in1, c_in2)
        return list(c_res)
    
    def fp_vec_by_fp_matrix(self, e: List[int], V_tr: List[int]) -> List[int]:
        """Multiplies an FP vector by a flat FP matrix yielding a result of length N-K."""
        if len(e) != self.n:
            raise ValueError(f"Expected e to have length {self.n}, got {len(e)}")
        matrix_size = self.k * (self.n - self.k)
        if len(V_tr) != matrix_size:
            raise ValueError(f"Expected V_tr to have length {matrix_size}, got {len(V_tr)}")
        
        # The mathematical result length of such a vector-matrix multiplication
        # (vector of length K times matrix K x (N-K) gives a vector of length N-K)

        c_res = (self.FP_ELEM * (self.n - self.k))()
        c_e = (self.FP_ELEM * self.n)(*e)
        c_V_tr = (self.FP_ELEM * matrix_size)(*V_tr)

        # C-Function call up 
        self.cross.c_cross.cross_fp_vec_by_fp_matrix(c_res, c_e, c_V_tr)

        return list(c_res)

    def fz_vec_sub_n(self, a : List[int], b : List [int]) -> List[int]:
        """Subtracts two restricted vectors coordinate-wise over the space N."""
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
        """Expands seed_sk into e_bar and V_tr, RSDPG additionally returns e_G_bar and W_mat."""
        # Security check for the seed length (usually 32 bytes at level 1)
        # Replace 'self.seed_length' with your variable or the fixed value (e.g., 32)
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
        """Normalizes a restricted vector of length N in place (internally) and returns the normalized list."""
        if len(v) != self.n:
            raise ValueError(f"Expected v to have length {self.n}, got {len(v)}")
        
        c_v = (self.FZ_ELEM * self.n)(*v)

        self.cross.c_cross.cross_fz_dz_norm_n(c_v)
        return list(c_v)
    
    def fp_vec_by_restr_vec_scaled(self, e: List[int], chall_1: int, u_prime: List[int]) -> List[int]:
        """Computes the scaled addition of a restricted vector and an FP vector scaled by challenge_1."""
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
        """Expands a seed/digest string into a challenge string of fixed weight T."""
        # T-size for fixed_weight_string (selft.t)
        if len(digest) != self.hash_digest_length:
            raise ValueError(f"Expected digest to have length {self.hash_digest_length}, got {len(digest)}")

        c_fixed_weight_string = (c_uint8 * self.t)()
        c_digest = (c_uint8 * self.hash_digest_length)(*digest)
        
        self.cross.c_cross.cross_expand_digest_to_fixed_weight(c_fixed_weight_string, c_digest)
        return list(c_fixed_weight_string)
    
    def pack_fp_syn(self, inp: List[int]) -> bytes:
        """Packs a syndrome vector over FP (length N-K) into a densely packed byte string."""
        expected_len = self.n - self.k
        if len(inp) != expected_len:
            raise ValueError(f"Expected inp to have length {expected_len}, got {len(inp)}")
            
        c_out = (c_uint8 * self.densely_packed_fp_syn_size)()
        c_inp = (self.FP_ELEM * expected_len)(*inp)
        
        self.cross.c_cross.cross_pack_fp_syn(c_out, c_inp)
        return bytes(c_out)

    def pack_fz_vec(self, inp: List[int]) -> bytes:
        """Packs a restricted vector over FZ (length N) into a densely packed byte string."""
        if len(inp) != self.n:
            raise ValueError(f"Expected inp to have length {self.n}, got {len(inp)}")
            
        c_out = (c_uint8 * self.densely_packed_fz_vec_size)()
        c_inp = (self.FZ_ELEM * self.n)(*inp)
        
        self.cross.c_cross.cross_pack_fz_vec(c_out, c_inp)
        return bytes(c_out)

    def unpack_fz_vec(self, inp: bytes) -> List[int]:
        """Unpacks a densely packed byte string back into a restricted vector over FZ of length N."""
        if len(inp) != self.densely_packed_fz_vec_size:
            raise ValueError(f"Expected inp to have length {self.densely_packed_fz_vec_size}, got {len(inp)}")
            
        c_out = (self.FZ_ELEM * self.n)()
        c_inp = (c_uint8 * self.densely_packed_fz_vec_size)(*inp)
        
        success_flag = self.cross.c_cross.cross_unpack_fz_vec(c_out, c_inp)
        if success_flag != 1:
            raise RuntimeError("Unpacking the FZ vector failed in native library.")
            
        return list(c_out)

    def expand_pk(self, seed_pk: bytes) -> List[int] | Tuple[List[int], List[int]]:
        """Expands the public key seed into the public matrix V_tr (K x N-K) and optional RSDPG group matrix W_mat."""
        if len(seed_pk) != self.keypair_seed_length_bytes:
            raise ValueError(f"Expected seed_pk to have length {self.keypair_seed_length_bytes}, got {len(seed_pk)}")
            
        c_V_tr = (self.FP_ELEM * (self.k * (self.n - self.k)))()
        c_seed_pk = (c_uint8 * self.keypair_seed_length_bytes)(*seed_pk)

        if self.algorithm == "RSDP":
            # Standard RSDP variant: Only V_tr is expanded
            self.cross.c_cross.cross_expand_pk(c_V_tr, c_seed_pk)
            return list(c_V_tr)
        elif self.algorithm == "RSDPG":
            # RSDPG variant: Requires the additional allocation/buffering of W_mat
            c_W_mat = (self.FZ_ELEM * (self.m * (self.n - self.m)))()
            
            self.cross.c_cross.cross_expand_pk(c_V_tr, c_W_mat, c_seed_pk)
            return list(c_V_tr), list(c_W_mat)

    def fz_inf_w_by_fz_matrix(self, e: List[int], W_mat: List[int]) -> List[int]:
        """RSDP(G) only: Multiplies a subgroup vector (M) by a flat FZ matrix of size M x (N-M)."""
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
        """RSDP(G) only: Subtracts two subgroup vectors coordinate-wise over the space M."""
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
        """RSDP(G) only: Normalizes a subgroup vector of length M to its canonical representation."""
        if self.algorithm == "RSDP":
            raise ValueError("fz_dz_norm_m is only available for RSDPG")
        
        if len(v) != self.m:
            raise ValueError(f"Expected v to have length {self.m}, got {len(v)}")
            
        c_v = (self.FZ_ELEM * self.m)(*v)
        self.cross.c_cross.cross_fz_dz_norm_m(c_v)
        return list(c_v)



