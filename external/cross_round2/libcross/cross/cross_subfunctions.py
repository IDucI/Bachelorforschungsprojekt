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