import ctypes
from mimetypes import init
from typing import List, Optional

from warnings import warn

# def get_POLYVEC_struct(data, kyber_k, kyber_n):

#     class POLYVEC(ctypes.Structure):
#         _fields_ = [("vec", get_POLY_struct(kyber_n) * kyber_k)]

#         def __init__(self, data):
#             self.vec = data

#     return POLYVEC(data)


class Poly:
    def __init__(self, kyber_n=256, initial: List[int] = None) -> None:
        self.coeffs = []
        if initial is None:
            self.coeffs = [0] * kyber_n
        else:
            if kyber_n != len(initial):
                warn("initial value doesn't match the lenght of kyber_n")
                raise ValueError
            self.coeffs = initial[:]
        self.kyber_n = kyber_n

    def __str__(self):
        return '{coeffs: ' + str(self.coeffs) + '}'
        # return str(self.coeffs)

    # def __list__(self):
    #     return list(self.coeffs)

    def from_c_type(self, cdata):
        self.coeffs = list(cdata.coeffs)
        return self

    def to_c_type(self):
        return self.get_POLY_struct(self)

    def get_POLY_struct(self, outer):
        class POLY(ctypes.Structure):
            _fields_ = [("coeffs", (ctypes.c_int16 * outer.kyber_n))]

            def __init__(self, data):
                self.cdatatype = (ctypes.c_int16 * outer.kyber_n)
                self.coeffs = self.cdatatype(*data)
        return POLY(outer.coeffs)

    def __getstate__(self):
        return {'coeffs': list(self.coeffs)}

    def __eq__(self, other):
        return self.coeffs == other.coeffs


class PolyVec:
    def __init__(self, kyber_k, kyber_n=256, initial: List[Poly] = None) -> None:
        self.vec = []
        if initial is None:
            self.vec = [Poly(kyber_n) for i in range(kyber_k)]
        else:
            if len(initial) != kyber_k:
                warn("initial value doesn't match the lenght of kyber_n")
                raise ValueError
            self.vec = initial
        self.kyber_k = kyber_k
        self.kyber_n = kyber_n

    def __str__(self):
        st = '{vec: [\n'
        for i in range(self.kyber_k):
            st = st + '\t' + str(self.vec[i]) + '\n'
        st = st + ']}'
        return st

    def from_c_type(self, cdata):
        for i in range(self.kyber_k):
            self.vec[i] = Poly(self.kyber_n).from_c_type(cdata.vec[i])
        return self

    def to_c_type(self):
        return self.get_POLYVEC_struct(self)

    def get_POLYVEC_struct(self, outer):
        class POLY(ctypes.Structure):
            _fields_ = [("coeffs", (ctypes.c_int16 * outer.kyber_n))]

            def __init__(self, data):
                self.cdatatype = (ctypes.c_int16 * outer.kyber_n)
                self.coeffs = self.cdatatype(*data)

        class POLYVEC(ctypes.Structure):
            _fields_ = [("vec", (POLY * outer.kyber_k))]

            def __init__(self, data):
                self.cdatatype = (POLY * outer.kyber_k)
                for i in range(outer.kyber_k):
                    self.vec[i].coeffs = data[i].to_c_type().coeffs

        return POLYVEC(outer.vec)

    def __getstate__(self):
        return {'vec': [x.__getstate__() for x in self.vec]}

    def __eq__(self, other):
        return self.vec == other.vec


"""
import kyber
poly = kyber.kyber_datastructures.Poly(256)
poly.to_c_type()
poly.coeffs[0] =1
list(poly.to_c_type().coeffs)
"""
