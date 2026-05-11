import ctypes
from typing import List, Tuple
import logging
from ctypes import *

from .kyber_datastructures import *


class Kem_subfunctions:
    def __init__(self, kyber) -> None:
        self.kyber = kyber
        self.kyber_version = None

        self.msgtype = None
        # self.kem_symbytestype = None

    def load_dll(self):
        try:
            self.kyber_version = c_char_p.in_dll(
                self.kyber.c_kyber, "kyber_version").value.decode("utf-8")
            self.kem_symbytes = c_int.in_dll(
                self.kyber.c_kyber, "kyber_symbytes").value
            self.msgtype = ctypes.c_ubyte * self.kem_symbytes
            # self.msgtype = c_uint8 * self.kyber.pke_msgbytes
            # self._ntt_zetas = POINTER(c_int16).in_dll(
            #     self.kyber.c_kyber, 'ntt_zetas')
            # self.ntt_zetas = [self._ntt_zetas[i] for i in range(128)]
            # try:
            #     self._ntt_zetas_inv = POINTER(c_int16).in_dll(
            #         self.kyber.c_kyber, 'ntt_zetas_inv')
            #     self.ntt_zetas_inv = [self._ntt_zetas_inv[i]
            #                           for i in range(128)]
            # except ValueError:
            #     logging.warn("Unable to load ntt_zetas_inv", stacklevel=2)
        except ValueError:
            logging.warn("Exception in reading the data values", stacklevel=2)

    def kem_enc_m(self, m, public_key):
        if len(public_key) > self.kyber.kem_publickeybytes:
            public_key = public_key[:self.kyber.kem_publickeybytes]
            logging.warn("public key was cut of, it was too large")
        if len(m) > self.kem_symbytes:
            m = m[:self.kem_symbytes]
            logging.warn("message was cut of, it was too large")
        ct = self.kyber._kem_cttype()
        ss = self.kyber._kem_sstype()
        m = self.msgtype(*m)
        pk = self.kyber._kem_pktype(*public_key)

        self.kyber.c_kyber.kem_enc_m(ct, ss, m, pk)
        return {'ct': list(ct), 'ss': list(ss)}
