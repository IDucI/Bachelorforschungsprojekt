import ctypes
from ctypes import c_uint8, POINTER
from typing import List


class CrossSubfunctions:
    def __init__(self, cross) -> None:
        self.cross = cross
        self.n = 127

    def load_dll(self):
        self.cross.c_cross.cross_convert_restr_vec_to_fp.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]
        self.cross.c_cross.cross_convert_restr_vec_to_fp.restype = None

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

    def fp_vec_by_fp_vec_pointwise():
        pass

    def fp_vec_by_fp_matrix():
        pass

    def fz_vec_sub_n():
        pass

    def expand_sk():
        pass