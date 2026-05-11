import ctypes
# from distutils.log import warn
from typing import List, Tuple
# import logging
from ctypes import *
import numpy as np

from .kyber_datastructures import *


class Pke_subfunctions:
    def __init__(self, kyber) -> None:
        self.kyber = kyber
        self.kyber_version = None
        # self.msgtype = None

    def load_dll(self):
        try:
            self.kyber_version = c_char_p.in_dll(
                self.kyber.c_kyber, "kyber_version").value.decode("utf-8")
            # self.msgtype = c_uint8 * self.kyber.pke_msgbytes
            self._ntt_zetas = POINTER(c_int16).in_dll(
                self.kyber.c_kyber, 'ntt_zetas')
            self.ntt_zetas = [self._ntt_zetas[i] for i in range(128)]
            self.MONT = c_int.in_dll(
                self.kyber.c_kyber, "kyber_MONT").value
            self.QINV = c_int.in_dll(
                self.kyber.c_kyber, "kyber_QINV").value

            try:
                self._ntt_zetas_inv = POINTER(c_int16).in_dll(
                    self.kyber.c_kyber, 'ntt_zetas_inv')
                self.ntt_zetas_inv = [self._ntt_zetas_inv[i]
                                      for i in range(128)]
            except ValueError:
                self.kyber.logger.warn(
                    "Unable to load ntt_zetas_inv", stacklevel=2)
        except ValueError:
            self.kyber.logger.warn(
                "Exception in reading the data values", stacklevel=2)

    def pack_ciphertext(self, b: PolyVec, v: Poly) -> List:
        cb = b.to_c_type()
        cv = v.to_c_type()
        cc = (c_uint8 * self.kyber.pke_ciphertextbytes)()
        self.kyber.c_kyber.pke_pack_ciphertext(byref(cc), byref(cb), byref(cv))

        return list(cc)

    def unpack_ciphertext(self, c: List[int]):  # -> Tuple(PolyVec, Poly):
        if len(c) != self.kyber.pke_ciphertextbytes:
            self.kyber.logger.warn('packed ciphertext was not right length. Expected: {}, not: {}'.format(
                self.kyber.pke_ciphertextbytes, len(c)))
            raise ValueError

        cb = PolyVec(self.kyber.kyber_k, self.kyber.kyber_n).to_c_type()
        cv = Poly(self.kyber.kyber_n).to_c_type()
        cc = (c_uint8 * self.kyber.pke_ciphertextbytes)(*c)
        self.kyber.c_kyber.pke_unpack_ciphertext(
            byref(cb), byref(cv), byref(cc))
        return PolyVec(self.kyber.kyber_k, self.kyber.kyber_n).from_c_type(cb), Poly(self.kyber.kyber_n).from_c_type(cv)

    def unpack_sk(self, packedsk: List[int]) -> PolyVec:
        if len(packedsk) != self.kyber.pke_secretkeybytes:
            self.kyber.logger.warn('packed key was not right length. Expected: {}, not: {}'.format(
                len(packedsk), self.kyber.pke_secretkeybytes))
            raise ValueError

        csk = PolyVec(self.kyber.kyber_k, self.kyber.kyber_n).to_c_type()
        cpackedsk = (c_uint8 * self.kyber.pke_secretkeybytes)(*packedsk)
        self.kyber.c_kyber.pke_unpack_sk(byref(csk), byref(cpackedsk))

        return PolyVec(self.kyber.kyber_k, self.kyber.kyber_n).from_c_type(csk)

    def polyvec_ntt(self, r: PolyVec) -> PolyVec:
        cpv = r.to_c_type()
        self.kyber.c_kyber.pke_polyvec_ntt(byref(cpv))
        return PolyVec(self.kyber.kyber_k, self.kyber.kyber_n).from_c_type(cpv)

    def polyvec_pointwise_acc_montgomery(self, a: PolyVec, b: PolyVec) -> Poly:
        cr = Poly(self.kyber.kyber_n).to_c_type()
        ca = a.to_c_type()
        cb = b.to_c_type()
        self.kyber.c_kyber.pke_polyvec_pointwise_acc_montgomery(
            byref(cr), byref(ca), byref(cb))
        return Poly(self.kyber.kyber_n).from_c_type(cr)

    def basemul(self, a: List[int], b: List[int], zeta: int) -> List[int]:
        if len(a) != 2:
            self.kyber.logger.warn('a parameter must be lenth 2')
            raise ValueError
        if len(b) != 2:
            self.kyber.logger.warn('b parameter must be lenth 2')
            raise ValueError
        cr = (c_uint16 * 2)()
        ca = (c_int16 * 2)(*a)
        cb = (c_int16 * 2)(*b)
        czeta = c_int16(zeta)
        self.kyber.c_kyber.pke_basemul(byref(cr), byref(ca), byref(cb), czeta)
        return list(cr)

    def poly_compress(self, a: Poly) -> list:
        cpoly = a.to_c_type()
        compressedpoly = self.kyber.polycompressedbytes_type()
        self.kyber.c_kyber.pke_poly_compress(
            byref(compressedpoly), byref(cpoly))
        return list(compressedpoly)

    def poly_decompress(self, r: list) -> Poly:
        # void poly_decompress(poly *r, const uint8_t a[KYBER_POLYCOMPRESSEDBYTES])
        cpoly = Poly(self.kyber.kyber_n).to_c_type()
        cr = self.kyber.polycompressedbytes_type(*r)
        self.kyber.c_kyber.pke_poly_decompress(byref(cpoly), byref(cr))
        return Poly(self.kyber.kyber_n).from_c_type(cpoly)

    def poly_tobytes(self, a: Poly) -> list:
        cpoly = a.to_c_type()
        compressedpoly = self.kyber.polycompressedbytes_type()
        self.kyber.c_kyber.pke_poly_tobytes(
            byref(compressedpoly), byref(cpoly))
        return list(compressedpoly)

    def poly_frombytes(self, a: list) -> Poly:
        if len(a) != self.kyber.polybytes:
            self.kyber.logger.warn('packed msg was not right length. Expected: {}, not: {}'.format(
                len(a), self.kyber.polybytes))
            raise ValueError
        cpoly = Poly(self.kyber.kyber_n).to_c_type()
        ca = self.kyber.polybytes_type(*(a))
        self.kyber.c_kyber.pke_poly_frombytes(byref(cpoly), byref(ca))
        return Poly(self.kyber.kyber_n).from_c_type(cpoly)

    def poly_tomsg(self, poly: Poly) -> List:
        cpoly = poly.to_c_type()
        cmsg = self.kyber._pke_msgtype()
        self.kyber.c_kyber.pke_poly_tomsg(byref(cmsg), byref(cpoly))
        return list(cmsg)

    def poly_frommsg(self, msg: list) -> Poly:
        if len(msg) != self.kyber.pke_msgbytes:
            self.kyber.logger.warn('packed msg was not right length. Expected: {}, not: {}'.format(
                len(msg), self.kyber.pke_msgbytes))
            raise ValueError

        cpoly = Poly(self.kyber.kyber_n).to_c_type()
        cmsg = self.kyber._pke_msgtype(*msg)
        self.kyber.c_kyber.pke_poly_frommsg(byref(cpoly), byref(cmsg))
        return Poly(self.kyber.kyber_n).from_c_type(cpoly)
        return None

    def poly_basemul_montgomery(self, a: Poly, b: Poly) -> Poly:
        cr = Poly(self.kyber.kyber_n).to_c_type()
        ca = a.to_c_type()
        cb = b.to_c_type()
        self.kyber.c_kyber.pke_poly_basemul_montgomery(
            byref(cr), byref(ca), byref(cb))
        return Poly(self.kyber.kyber_n).from_c_type(cr)

    def poly_add(self, a: Poly, b: Poly) -> Poly:
        cr = Poly(self.kyber.kyber_n).to_c_type()
        ca = a.to_c_type()
        cb = b.to_c_type()
        self.kyber.c_kyber.pke_poly_add(byref(cr), byref(ca), byref(cb))
        return Poly(self.kyber.kyber_n).from_c_type(cr)

    def poly_reduce(self, poly: Poly) -> Poly:
        cdata = poly.to_c_type()
        self.kyber.c_kyber.pke_poly_reduce(byref(cdata))
        return Poly(self.kyber.kyber_n).from_c_type(cdata)

    def poly_sub(self, a: Poly, b: Poly) -> Poly:
        cr = Poly(self.kyber.kyber_n).to_c_type()
        ca = a.to_c_type()
        cb = b.to_c_type()
        self.kyber.c_kyber.pke_poly_sub(byref(cr), byref(ca), byref(cb))
        return Poly(self.kyber.kyber_n).from_c_type(cr)

    def poly_invntt_tomont(self, r: Poly) -> Poly:
        cr = r.to_c_type()
        self.kyber.c_kyber.pke_poly_invntt_tomont(byref(cr))
        return Poly(self.kyber.kyber_n).from_c_type(cr)

    def ntt_fqmul(self, a, b) -> np.int16:
        self.kyber.c_kyber.pke_ntt_fqmul.restype = c_int16
        self.kyber.c_kyber.pke_ntt_fqmul.argtype = [c_int16, c_int16]

        if isinstance(a, np.generic):
            a = a.item()
        if isinstance(b, np.generic):
            b = b.item()

        ca = c_int16(a)
        cb = c_int16(b)

        return np.int16(self.kyber.c_kyber.pke_ntt_fqmul(a, b))

    def montgomery_reduce(self, a) -> np.int16:
        self.kyber.c_kyber.pke_montgomery_reduce.restype = c_int16
        ca = c_int32(a)
        return np.int16(self.kyber.c_kyber.pke_montgomery_reduce(ca))
        # return  int16_t (int32_t)

    """
    I need the following for encryption:

        unpack_pk
        poly_frommsg
        gen_at
        poly_getnoise_eta1
        poly_getnoise_eta2
        polyvec_ntt
        polyvect_pointwise_acc_montgomery
        polyvec_invntt_tomont
        polyvec_add
        poly_add
        polyvec_reduce
        pack_ciphertext


    And for decryption:

        # unpack_ciphertext
        # unpack_sk
        # polyvec_ntt
        # polyvec_pointwise_acc_montgomery
            # poly_basemul_montgomery
                # basemul
            # poly_add
            # poly_reduce
        # poly_invntt_tomont
        # poly_sub
        # poly_reduce
        # poly_tomsg
    """
