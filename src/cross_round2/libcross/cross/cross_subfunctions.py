import ctypes
from ctypes import c_uint8, POINTER
from typing import List


class CrossSubfunctions:
    def __init__(self, cross) -> None:
        self.cross = cross
        self.n = 127

    def load_dll(self):
        """Loads the native CROSS shared library (.so) via ctypes and declares the argument types (argtypes) and return types (restype) 
        of the C functions.This ensures type safety when passing Python lists (converted into ctypes arrays) to the raw C pointers of 
        the reference implementation. 
        """

        self.cross.c_cross.cross_convert_restr_vec_to_fp.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]
        self.cross.c_cross.cross_convert_restr_vec_to_fp.restype = None

        self.cross.c_cross.cross_restr_vec_by_fp_matrix.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]
        self.cross.c_cross.cross_restr_vec_by_fp_matrix.argtypes = None

        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.argtypes = [
            POINTER(c_uint8),  
            POINTER(c_uint8),  
            POINTER(c_uint8),  
        ]
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise.restype = None

        self.cross.c_cross.cross_fp_vec_by_fp_matrix.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]
        self.cross.c_cross.cross_fp_vec_by_fp_matrix.restype = None 

        self.cross.c_cross.cross_fz_vec_sub_n.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]
        self.cross.c_cross.cross_fz_vec_sub_n.restype = None

        self.cross.c_cross.cross_expand_sk.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  
            ctypes.POINTER(ctypes.c_uint8),  
            ctypes.POINTER(ctypes.c_uint8)  
        ]
        self.cross.c_cross.cross_expand_sk.restype = None

        

    def convert_restr_vec_to_fp(self, input_vector: List[int]) -> List[int]:
        if len(input_vector) != self.n:
            raise ValueError(f"Expected input length {self.n}, got {len(input_vector)}")

        input_type = c_uint8 * self.n
        output_type = c_uint8 * self.n

        c_input = input_type(*input_vector)
        c_output = output_type()

        self.cross.c_cross.cross_convert_restr_vec_to_fp(c_output, c_input)

        return list(c_output)
    
    def restr_vec_by_fp_matrix(self, vector: List[int], matrix: List[int]) -> List[int]:
        if len(vector) != self.n:
            raise ValueError(f"Expected vector length {self.n}, got {len(vector)}")
        # M is a flat list of size K * (N-K)
        matrix_size = self.k * (self.n - self.k)
        if len(matrix) != matrix_size:
            raise ValueError(f"Expected matrix size {matrix_size}, got {len(matrix)}")

        c_vector = (c_uint8 * self.n)(*vector)
        c_matrix = (c_uint8 * matrix_size)(*matrix)
        c_result = (c_uint8 * (self.n - self.k))()

        self.cross.c_cross.cross_restr_vec_by_fp_matrix(c_result, c_vector, c_matrix)
        return list(c_result)

    def fp_vec_by_fp_vec_pointwise(self, in1: List[int], in2: List[int]) -> List[int]:
        # Validierung: Both Entry vector must have the length N (self.n) 
        if len(in1) != self.n or len(in2) != self.n:
            raise ValueError(f"Expected both inputs to have length {self.n}")
    
        # ctypes-Arrays for C preparing (Size N)
        FP_ELEM_ARRAY_N = ctypes.c_uint8 * self.n  # If FP_ELEM = 1 Byte 
    
        c_res = FP_ELEM_ARRAY_N()
        c_in1 = FP_ELEM_ARRAY_N(*in1)
        c_in2 = FP_ELEM_ARRAY_N(*in2)
    
        # The call of the C-Function
        self.cross.c_cross.cross_fp_vec_by_fp_vec_pointwise(c_res, c_in1, c_in2)
        return list(c_res)
    
    def fp_vec_by_fp_matrix(self, vector: List[int], matrix: List[int]) -> List[int]:
        if len(vector) != self.n:
            raise ValueError(f"Expected vector length {self.n}, got {len(vector)}")
        matrix_size = self.k * (self.n - self.k)
        if len(matrix) != matrix_size:
            raise ValueError(f"Expected matrix size {matrix_size}, got {len(matrix)}")
        
        # The mathematical result length of such a vector-matrix multiplication
        # (vector of length K times matrix K x (N-K) gives a vector of length N-K)
        output_size = self.n - self.k

        vector_type = c_uint8 * self.n
        matrix_type = c_uint8 * matrix_size
        output_type = c_uint8 * output_size

        c_vector = vector_type(*vector)
        c_matrix = matrix_type(*matrix)
        c_output = output_type()  

        # C-Function call up 
        self.cross.c_cross.cross_fp_vec_by_fp_matrix(c_output, c_vector, c_matrix)

        return list(c_output)

    def fz_vec_sub_n(self, vector_a : List[int], vector_b : List [int]) -> List[int]:
        if len(vector_a) != self.n or len(vector_b) != self.n:
            raise ValueError(f"Expected both inputs to have length {self.n}")
        
        # ctypes-Arrays for C preparing (Size N)
        FZ_ELEM_ARRAY_N = ctypes.c_uint8 * self.n  
    
        res_c = FZ_ELEM_ARRAY_N()
        c_vector_a = FZ_ELEM_ARRAY_N(*vector_a)
        c_vector_b = FZ_ELEM_ARRAY_N(*vector_b)
    
        self.cross.c_cross.cross_fz_vec_sub_n(res_c, c_vector_a, c_vector_b)
        return list(res_c)

    def expand_sk(self, seed_sk: bytes) -> List [List[int], List[int]]:
        # Security check for the seed length (usually 32 bytes at level 1)
        # Replace 'self.seed_length' with your variable or the fixed value (e.g., 32)
        if len(seed_sk) != 32: 
            raise ValueError(f"Expected seed length 32, got {len(seed_sk)}")

        # Dimension
        matrix_size = self.k * (self.n - self.k)

        # ctypes-Types defintion
        E_BAR_TYPE = ctypes.c_uint8 * self.n
        V_TR_TYPE = ctypes.c_uint8 * matrix_size
        SEED_TYPE = ctypes.c_uint8 * 32
        
        c_e_bar = E_BAR_TYPE()
        c_V_tr = V_TR_TYPE()
        c_seed = SEED_TYPE(*seed_sk)

        self.cross.c_cross.cross_expand_sk(c_e_bar, c_V_tr, c_seed)

        return list(c_e_bar), list(c_V_tr)



