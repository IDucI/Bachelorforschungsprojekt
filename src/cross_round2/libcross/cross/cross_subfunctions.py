import ctypes
from ctypes import c_uint8, POINTER
from typing import List, Tuple
from .cross_params import get_params


class CrossSubfunctions:
    def __init__(self, cross) -> None:
        self.cross = cross
        self.params = cross.params

        self.n = self.params.n
        self.k = self.params.k
        self.m = self.params.m
        self.t = self.params.t
        self.w = self.params.w

        self.keypair_seed_length_bytes = self.params.keypair_seed_length_bytes
        self.densely_packed_fp_syn_size = self.params.densely_packed_fp_syn_size
        self.densely_packed_fz_vec_size = self.params.densely_packed_fz_vec_size

    def load_dll(self):
        """Loads the native CROSS shared library (.so) via ctypes and declares the argument types (argtypes) and return types (restype) 
        of the C functions.This ensures type safety when passing Python lists (converted into ctypes arrays) to the raw C pointers of 
        the reference implementation. 
        """

        # Vector conversion
        self.cross.c_cross.cross_convert_restr_vec_to_fp.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_convert_restr_vec_to_fp.restype = None

        # Vector-Matrix arithmetic
        self.cross.c_cross.cross_restr_vec_by_fp_matrix.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_restr_vec_by_fp_matrix.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_matrix.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_fp_vec_by_fp_matrix.restype = None 

        self.cross.c_cross.cross_fz_vec_sub_n.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_fz_vec_sub_n.restype = None

        # Key generation and expansion (Key Generation)
        #self.cross.c_cross.cross_expand_sk.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8)]
        #self.cross.c_cross.cross_expand_sk.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8)  ]
        #self.cross.c_cross.cross_expand_sk.restype = None

        # Protocol core validation & scaling
        #self.cross.c_cross.cross_fz_dz_norm_n.argtypes = [POINTER(c_uint8)]
        #self.cross.c_cross.cross_fz_dz_norm_n.restype = None

        self.cross.c_cross.cross_fp_vec_by_restr_vec_scaled.argtypes = [POINTER(c_uint8), POINTER(c_uint8), c_uint8, POINTER(c_uint8)]
        self.cross.c_cross.cross_fp_vec_by_restr_vec_scaled.restype = None

        self.cross.c_cross.cross_expand_digest_to_fixed_weight.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_expand_digest_to_fixed_weight.restype = None

        self.cross.c_cross.cross_pack_fp_syn.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_pack_fp_syn.restype = None

        self.cross.c_cross.cross_pack_fz_vec.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_pack_fz_vec.restype = None

        self.cross.c_cross.cross_unpack_fz_vec.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
        self.cross.c_cross.cross_unpack_fz_vec.restype = c_uint8  # Returns 1 on success

        if hasattr(self.cross.c_cross, "cross_expand_pk"):
            # Since the C function has 2 or 3 parameters depending on the variant, we check for type safety
            # whether the RSDPG group functions are available to choose the appropriate signature.
            if hasattr(self.cross.c_cross, "cross_fz_inf_w_by_fz_matrix"):
                # RSDPG: cross_expand_pk(V_tr, W_mat, seed_pk)
                self.cross.c_cross.cross_expand_pk.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
            else:
                # RSDP: cross_expand_pk(V_tr, seed_pk)
                self.cross.c_cross.cross_expand_pk.argtypes = [POINTER(c_uint8), POINTER(c_uint8)]
            self.cross.c_cross.cross_expand_pk.restype = None

        # DYNAMIC PROTECTION FOR RSDP(G), because its currently working with only variant RSDP without the subgroup G
        # Catches errors if the library was built for pure RSDP without the subgroup G
        if hasattr(self.cross.c_cross, "cross_fz_inf_w_by_fz_matrix"):
            self.cross.c_cross.cross_fz_inf_w_by_fz_matrix.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
            self.cross.c_cross.cross_fz_inf_w_by_fz_matrix.restype = None

            self.cross.c_cross.cross_fz_vec_sub_m.argtypes = [POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8)]
            self.cross.c_cross.cross_fz_vec_sub_m.restype = None

            self.cross.c_cross.cross_fz_dz_norm_m.argtypes = [POINTER(c_uint8)]
            self.cross.c_cross.cross_fz_dz_norm_m.restype = None

    def convert_restr_vec_to_fp(self, restr_vector: List[int]) -> List[int]:
        """Maps a vector from the restricted subgroup (FZ) to the full field (FP) of length N."""
        if len(restr_vector) != self.n:
            raise ValueError(f"Expected input length {self.n}, got {len(restr_vector)}")

        input_type = c_uint8 * self.n
        output_type = c_uint8 * self.n

        c_restr_input= input_type(*restr_vector)
        c_fp_output = output_type()

        self.cross.c_cross.cross_convert_restr_vec_to_fp(c_fp_output, c_restr_input)

        return list(c_fp_output)
    
    def restr_vec_by_fp_matrix(self, restr_vector: List[int], public_matrix_V_tr: List[int]) -> List[int]:
        """Multiplies a restricted vector (length N) by a flat FP matrix of size K x (N-K)."""
        if len(restr_vector) != self.n:
            raise ValueError(f"Expected vector length {self.n}, got {len(restr_vector)}")
        # M is a flat list of size K * (N-K)
        matrix_size = self.k * (self.n - self.k)
        if len(public_matrix_V_tr) != matrix_size:
            raise ValueError(f"Expected matrix size {matrix_size}, got {len(public_matrix_V_tr)}")

        c_restr_vector = (c_uint8 * self.n)(*restr_vector)
        c_matrix_V_tr = (c_uint8 * matrix_size)(*public_matrix_V_tr)
        c_synd_result = (c_uint8 * (self.n - self.k))()

        self.cross.c_cross.cross_restr_vec_by_fp_matrix(c_synd_result, c_restr_vector, c_matrix_V_tr)
        return list(c_synd_result)

    def fp_vec_by_fp_vec_pointwise(self, fp_vector_1: List[int], fp_vector_2: List[int]) -> List[int]:
        """Performs a coordinate-wise multiplication of two FP vectors of length N."""
        # Validation: Both Entry vector must have the length N (self.n) 
        if len(fp_vector_1) != self.n or len(fp_vector_2) != self.n:
            raise ValueError(f"Expected both inputs to have length {self.n}")
    
        # ctypes-Arrays for C preparing (Size N)
        FP_ELEM_ARRAY_N = ctypes.c_uint8 * self.n  # If FP_ELEM = 1 Byte 
    
        c_res_vector = FP_ELEM_ARRAY_N()
        c_fp_input_1 = FP_ELEM_ARRAY_N(*fp_vector_1)
        c_fp_input_2 = FP_ELEM_ARRAY_N(*fp_vector_2)
    
        # The call of the C-Function
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise(c_res_vector, c_fp_input_1, c_fp_input_2)
        return list(c_res_vector)
    
    def fp_vec_by_fp_matrix(self, fp_vector: List[int], public_matrix_V_tr: List[int]) -> List[int]:
        """Multiplies an FP vector by a flat FP matrix yielding a result of length N-K."""
        if len(fp_vector) != self.n:
            raise ValueError(f"Expected vector length {self.n}, got {len(fp_vector)}")
        matrix_size = self.k * (self.n - self.k)
        if len(public_matrix_V_tr) != matrix_size:
            raise ValueError(f"Expected matrix size {matrix_size}, got {len(public_matrix_V_tr)}")
        
        # The mathematical result length of such a vector-matrix multiplication
        # (vector of length K times matrix K x (N-K) gives a vector of length N-K)
        output_size = self.n - self.k

        vector_type = c_uint8 * self.n
        matrix_type = c_uint8 * matrix_size
        output_type = c_uint8 * output_size

        c_fp_vector = vector_type(*fp_vector)
        c_matrix_V_tr = matrix_type(*public_matrix_V_tr)
        c_output_synd = output_type()  

        # C-Function call up 
        self.cross.c_cross.cross_fp_vec_by_fp_matrix(c_output_synd, c_fp_vector, c_matrix_V_tr)

        return list(c_output_synd)

    def fz_vec_sub_n(self, restr_vec_a : List[int], restr_vec_b : List [int]) -> List[int]:
        """Subtracts two restricted vectors coordinate-wise over the space N."""
        if len(restr_vec_a) != self.n or len(restr_vec_b) != self.n:
            raise ValueError(f"Expected both inputs to have length {self.n}")
        
        # ctypes-Arrays for C preparing (Size N)
        FZ_ELEM_ARRAY_N = ctypes.c_uint8 * self.n  
    
        c_diff_result = FZ_ELEM_ARRAY_N()
        c_restr_vec_a = FZ_ELEM_ARRAY_N(*restr_vec_a)
        c_restr_vec_b = FZ_ELEM_ARRAY_N(*restr_vec_b)
    
        self.cross.c_cross.cross_fz_vec_sub_n(c_diff_result, c_restr_vec_a, c_restr_vec_b)
        return list(c_diff_result)

    def expand_sk(self, seed_sk: bytes) -> Tuple [List[int], List[int]]:
        """Expands the secret key seed into the error vector e_bar (N) and public matrix V_tr (K x N-K)."""
        # Security check for the seed length (usually 32 bytes at level 1)
        # Replace 'self.seed_length' with your variable or the fixed value (e.g., 32)
        if len(seed_sk) != self.keypair_seed_length_bytes: 
            raise ValueError(f"Expected seed length {self.keypair_seed_length_bytes}, got {len(seed_sk)}")

        # Dimension
        matrix_size = self.k * (self.n - self.k)

        # ctypes-Types defintion
        E_BAR_TYPE = ctypes.c_uint8 * self.n
        V_TR_TYPE = ctypes.c_uint8 * matrix_size
        SEED_TYPE = ctypes.c_uint8 * self.keypair_seed_length_bytes
        
        c_error_vec_e_bar = E_BAR_TYPE()
        c_public_matrix_V_tr = V_TR_TYPE()
        c_seed_sk = SEED_TYPE(*seed_sk)

        self.cross.c_cross.cross_expand_sk(c_error_vec_e_bar, c_public_matrix_V_tr, c_seed_sk)

        return list(c_error_vec_e_bar), list(c_public_matrix_V_tr)
    
    def fz_dz_norm_n(self, restr_vector: List[int]) -> List[int]:
        """Normalizes a restricted vector of length N in place (internally) and returns the normalized list."""
        if len(restr_vector) != self.n:
            raise ValueError(f"Expected input length {self.n}, got {len(restr_vector)}")
        
        c_restr_vector = (c_uint8 * self.n)(*restr_vector)

        self.cross.c_cross.cross_fz_dz_norm_n(c_restr_vector)
        return list(c_restr_vector)
    
    def fp_vec_by_restr_vec_scaled(self, restr_error_vector: List[int], chall_1: int, fp_vec_u_prime: List[int]) -> List[int]:
        """Computes the scaled addition of a restricted vector and an FP vector scaled by challenge_1."""
        if len(restr_error_vector) != self.n or len(fp_vec_u_prime) != self.n:
            raise ValueError(f"Expected vectors of length {self.n}")
        
        c_scaled_res = (c_uint8 * self.n)()
        c_restr_error = (c_uint8 * self.n)(*restr_error_vector)
        c_fp_u_prime = (c_uint8 * self.n)(*fp_vec_u_prime)
        
        self.cross.c_cross.cross_fp_vec_by_restr_vec_scaled(c_scaled_res, c_restr_error, c_uint8(chall_1), c_fp_u_prime)
        return list(c_scaled_res)
    
    def expand_digest_to_fixed_weight(self, digest_chall_2: bytes) -> List[int]:
        """Expands a seed/digest string into a challenge string of fixed weight T."""
        # T-size for fixed_weight_string (selft.t)
        c_weight_res = (c_uint8 * self.t)()
        c_digest_input = (c_uint8 * len(digest_chall_2))(*digest_chall_2)
        
        self.cross.c_cross.cross_expand_digest_to_fixed_weight(c_weight_res, c_digest_input)
        return list(c_weight_res)
    
    def pack_fp_syn(self, fp_synd: List[int]) -> bytes:
        """Packs a syndrome vector over FP (length N-K) into a densely packed byte string."""
        expected_len = self.n - self.k
        if len(fp_synd) != expected_len:
            raise ValueError(f"Expected syndrome length {expected_len}, got {len(fp_synd)}")
            
        c_packed_bytes = (c_uint8 * self.densely_packed_fp_syn_size)()
        c_synd_input = (c_uint8 * expected_len)(*fp_synd)
        
        self.cross.c_cross.cross_pack_fp_syn(c_packed_bytes, c_synd_input)
        return bytes(c_packed_bytes)

    def pack_fz_vec(self, restr_vector: List[int]) -> bytes:
        """Packs a restricted vector over FZ (length N) into a densely packed byte string."""
        if len(restr_vector) != self.n:
            raise ValueError(f"Expected vector length {self.n}, got {len(restr_vector)}")
            
        c_packed_bytes = (c_uint8 * self.densely_packed_fz_vec_size)()
        c_vec_input = (c_uint8 * self.n)(*restr_vector)
        
        self.cross.c_cross.cross_pack_fz_vec(c_packed_bytes, c_vec_input)
        return bytes(c_packed_bytes)

    def unpack_fz_vec(self, packed_bytes: bytes) -> List[int]:
        """Unpacks a densely packed byte string back into a restricted vector over FZ of length N."""
        if len(packed_bytes) != self.densely_packed_fz_vec_size:
            raise ValueError(f"Expected packed size {self.densely_packed_fz_vec_size}, got {len(packed_bytes)}")
            
        c_unpacked_vec = (c_uint8 * self.n)()
        c_packed_input = (c_uint8 * self.densely_packed_fz_vec_size)(*packed_bytes)
        
        success_flag = self.cross.c_cross.cross_unpack_fz_vec(c_unpacked_vec, c_packed_input)
        if success_flag != 1:
            raise RuntimeError("Unpacking the FZ vector failed in native library.")
            
        return list(c_unpacked_vec)

    def expand_pk(self, seed_pk: bytes) -> Tuple[List[int], List[int]]:
        """Expands the public key seed into the public matrix V_tr (K x N-K) and optional RSDPG group matrix W_mat."""
        if len(seed_pk) != self.keypair_seed_length_bytes:
            raise ValueError(f"Expected seed length {self.keypair_seed_length_bytes}, got {len(seed_pk)}")
            
        v_tr_size = self.k * (self.n - self.k)
        c_public_matrix_V_tr = (c_uint8 * v_tr_size)()
        c_seed_pk = (c_uint8 * self.keypair_seed_length_bytes)(*seed_pk)
        
        # Dynamic case distinction, whether we are in RSDP or RSDPG mode
        if hasattr(self.cross.c_cross, "cross_fz_inf_w_by_fz_matrix"):
            # RSDPG variant: Requires the additional allocation/buffering of W_mat
            w_mat_size = self.m * (self.n - self.m)
            c_group_matrix_W_mat = (c_uint8 * w_mat_size)()
            
            self.cross.c_cross.cross_expand_pk(c_public_matrix_V_tr, c_group_matrix_W_mat, c_seed_pk)
            return list(c_public_matrix_V_tr), list(c_group_matrix_W_mat)
        else:
            # Standard RSDP variant: Only V_tr is expanded
            self.cross.c_cross.cross_expand_pk(c_public_matrix_V_tr, c_seed_pk)
            return list(c_public_matrix_V_tr), []

    # RSDP(G) METHODS (Catch errors if the library was built without G) otherwise they will work normally
    def fz_inf_w_by_fz_matrix(self, subgroup_vec: List[int], group_matrix_W_mat: List[int]) -> List[int]:
        """RSDP(G) only: Multiplies a subgroup vector (M) by a flat FZ matrix of size M x (N-M)."""
        if not hasattr(self.cross.c_cross, "cross_fz_inf_w_by_fz_matrix"):
            raise NotImplementedError("This compiled .so file does not support RSDP(G) functions.")
        
        matrix_size = self.m * (self.n - self.m)
        if len(subgroup_vec) != self.m or len(group_matrix_W_mat) != matrix_size:
            raise ValueError(f"Dimensions error for RSDPG matrix arithmetic.")
            
        c_extended_res = (c_uint8 * self.n)()
        c_subgroup_input = (c_uint8 * self.m)(*subgroup_vec)
        c_matrix_W_mat = (c_uint8 * matrix_size)(*group_matrix_W_mat)
        
        self.cross.c_cross.cross_fz_inf_w_by_fz_matrix(c_extended_res, c_subgroup_input, c_matrix_W_mat)
        return list(c_extended_res)

    def fz_vec_sub_m(self, subgroup_vec_a: List[int], subgroup_vec_b: List[int]) -> List[int]:
        """RSDP(G) only: Subtracts two subgroup vectors coordinate-wise over the space M."""
        if not hasattr(self.cross.c_cross, "cross_fz_vec_sub_m"):
            raise NotImplementedError("This compiled .so file does not support RSDP(G) functions.")
        
        if len(subgroup_vec_a) != self.m or len(subgroup_vec_b) != self.m:
            raise ValueError(f"Expected both inputs to have length {self.m}")
        
        FZ_ELEM_ARRAY_M = c_uint8 * self.m
        c_difference_res = FZ_ELEM_ARRAY_M()
        c_subgroup_a = FZ_ELEM_ARRAY_M(*subgroup_vec_a)
        c_subgroup_b = FZ_ELEM_ARRAY_M(*subgroup_vec_b)
        
        self.cross.c_cross.cross_fz_vec_sub_m(c_difference_res, c_subgroup_a, c_subgroup_b)
        return list(c_difference_res)

    def fz_dz_norm_m(self, subgroup_vec: List[int]) -> List[int]:
        """RSDP(G) only: Normalizes a subgroup vector of length M to its canonical representation."""
        if not hasattr(self.cross.c_cross, "cross_fz_dz_norm_m"):
            raise NotImplementedError("This compiled .so file does not support RSDP(G) functions.")
        
        if len(subgroup_vec) != self.m:
            raise ValueError(f"Expected input length {self.m}, got {len(subgroup_vec)}")
            
        c_subgroup_vec = (c_uint8 * self.m)(*subgroup_vec)
        self.cross.c_cross.cross_fz_dz_norm_m(c_subgroup_vec)
        return list(c_subgroup_vec)



