import ctypes
from ctypes import *
from pathlib import Path
import logging
from platform import release

from .kyber_subfunctions import Kyber_subfunctions
from .kyber_datastructures import Poly  # , PolyVec

print(__name__)


def platform_release_string():
    return '_'+(release().split('-')[0])


class Kyber:
    """Provides interface to a kyber implementation

    Function name defintion is in pattern <kem/pke>_<keypair/dec/enc/>

    Exports the following size definitions for variables:
        * kem_secretkeybytes    | secrety key
        * kem_publickeybytes    | public key
        * kem_ciphertextbytes   | ciphertext
        * kem_ssbytes           | coins (randomness)

        * pke_secretkeybytes    | secrety key
        * pke_publickeybytes    | public key
        * pke_ciphertextbytes   | ciphertext
        * pke_msgbytes          | message
        * pke_symbytes          | coins (randomness)
    """

    def __init__(self, path=None, name=None, version=None, release=platform_release_string()):
        """
        path | path of the kyber library to load
        name | full name of the library
        version | specific list of libraries kyber[512, 768, 1024]
        """
        self.logger = logging.getLogger(__name__)

        self.c_kyber = None

        self.kyber_n = None
        self.kyber_k = None

        self.kyber_version = None
        self.kem_secretkeybytes = None
        self.kem_publickeybytes = None
        self.kem_ciphertextbytes = None
        self.kem_ssbytes = None
        self._kem_sktype = None
        self._kem_pktype = None
        self._kem_cttype = None
        self._kem_sstype = None

        self._kem_entropy_input_type = None
        self._kem_personalization_string_type = None
        self._kem_security_strength_type = None

        self.pke_secretkeybytes = None
        self.pke_publickeybytes = None
        self.pke_ciphertextbytes = None
        self.pke_msgbytes = None
        self.pke_symbytes = None
        self._pke_sktype = None
        self._pke_pktype = None
        self._pke_cttype = None
        self._pke_msgtype = None
        self._pke_coinstype = None

        self.polybytes = None
        self.polybytes_type = None
        self.polyvecbytes = None
        self.polyvecbytes_type = None

        self.polycompressedbytes = None
        self.polycompressedbytes_type = None
        self.polyveccompressedbytes = None
        self.polyveccompressedbytes_type = None

        self.subfunctions = Kyber_subfunctions(self)

        self._release = release
        self.default_lib_prefix = 'libkyber'
        self.default_lib_path = Path().home() / '.local/lib/'

        self.select_lib(path, name, version, release)

        self.load_dll()

    def select_lib(self, path, name=None, version=None, release=None):
        self.logger.debug('__entry__ select_lib')
        self.logger.debug(f'path: {path}')
        self.logger.debug(f'name: {name}')
        self.logger.debug(f'version: {version}')
        if version in [512, 768, 1024] and name == None:
            self.logger.debug('version is in list')
            self.lib_name = self.default_lib_prefix + \
                str(version) + str(release)
        elif name != None:
            self.logger.debug('name used')
            self.lib_name = name
        else:
            self.logger.debug('default 512 configuration used')
            self.lib_name = self.default_lib_prefix + '512' + str(release)
        self.logger.debug(f'self.lib_name = {self.lib_name}')

        self.logger.debug(f'path!=None: {path!=None}')
        if path != None:
            self.lib_path = Path(path)
        else:
            self.lib_path = self.default_lib_path
        self.logger.debug(f'self.lib_path = {self.lib_path}')

        return self.lib_path, self.lib_name

    def load_dll(self):
        try:
            self.logger.debug(
                f'loading CDLL file in: {self.lib_path / self.lib_name}')
            self.c_kyber = CDLL(self.lib_path / self.lib_name)
        except OSError as e:
            self.logger.error(
                f'\033[0;31mFailed to load lib: {self.lib_path / self.lib_name}\033[0m')
            self.logger.error(f'\033[0;31m{e}\033[0m')
            return
        try:
            self.kyber_n = c_int.in_dll(self.c_kyber, "kyber_n").value
            self.kyber_k = c_int.in_dll(self.c_kyber, "kyber_k").value
            self.kyber_q = c_int.in_dll(self.c_kyber, "kyber_q").value

            self.kyber_version = c_char_p.in_dll(
                self.c_kyber, "kyber_version").value.decode("utf-8")
            self.kem_secretkeybytes = c_int.in_dll(
                self.c_kyber, "kyber_kem_secretkeybytes").value
            self.kem_publickeybytes = c_int.in_dll(
                self.c_kyber, "kyber_kem_publickeybytes").value
            self.kem_ciphertextbytes = c_int.in_dll(
                self.c_kyber, "kyber_kem_ciphertextbytes").value
            self.kem_ssbytes = c_int.in_dll(
                self.c_kyber, "kyber_ssbytes").value
            self._kem_sktype = ctypes.c_ubyte * self.kem_secretkeybytes
            self._kem_pktype = ctypes.c_ubyte * self.kem_publickeybytes
            self._kem_cttype = ctypes.c_ubyte * self.kem_ciphertextbytes
            self._kem_sstype = ctypes.c_ubyte * self.kem_ssbytes

            self._kem_entropy_input_type = ctypes.c_ubyte * 48
            self._kem_personalization_string_type = ctypes.c_ubyte * 48
            self._kem_security_strength_type = ctypes.c_int

            self.pke_secretkeybytes = c_int.in_dll(
                self.c_kyber, "kyber_pke_secretkeybytes").value
            self.pke_publickeybytes = c_int.in_dll(
                self.c_kyber, "kyber_pke_publickeybytes").value
            self.pke_ciphertextbytes = c_int.in_dll(
                self.c_kyber, "kyber_pke_ciphertextbytes").value
            self.pke_msgbytes = c_int.in_dll(
                self.c_kyber, "kyber_pke_msgbytes").value
            self.pke_symbytes = c_int.in_dll(
                self.c_kyber, "kyber_symbytes").value
            self._pke_sktype = ctypes.c_ubyte * self.pke_secretkeybytes
            self._pke_pktype = ctypes.c_ubyte * self.pke_publickeybytes
            self._pke_cttype = ctypes.c_ubyte * self.pke_ciphertextbytes
            self._pke_msgtype = ctypes.c_ubyte * self.pke_msgbytes
            self._pke_coinstype = ctypes.c_ubyte * self.pke_symbytes

            self.polybytes = c_int.in_dll(
                self.c_kyber, "kyber_polybytes").value
            self.polybytes_type = ctypes.c_ubyte * self.polybytes
            self.polyvecbytes = c_int.in_dll(
                self.c_kyber, "kyber_polyvecbytes").value
            self.polyvecbytes_type = ctypes.c_ubyte * self.polyvecbytes

            self.polycompressedbytes = c_int.in_dll(
                self.c_kyber, "kyber_polycompressedbytes").value
            self.polycompressedbytes_type = ctypes.c_ubyte * self.polycompressedbytes
            self.polyveccompressedbytes = c_int.in_dll(
                self.c_kyber, "kyber_polyveccompressedbytes").value
            self.polyveccompressedbytes_type = ctypes.c_ubyte * self.polyveccompressedbytes
        except ValueError as e:
            self.logger.warn(e)
            self.logger.warn(
                "Exception in reading the data values", stacklevel=2)

        self.subfunctions.load_dll()

    def kem_randombytes_init(self, entropy_input, personalization_string=None, security_strength=256):

        entropy_input = self._kem_entropy_input_type(*entropy_input)
        if personalization_string:
            personalization_string = self._kem_personalization_string_type(
                *personalization_string)
        security_strength = self._kem_security_strength_type(security_strength)

        self.c_kyber.kem_randombytes_init(entropy_input,
                                          personalization_string,
                                          security_strength)

    def kem_keypair(self):
        pk = self._kem_pktype()
        sk = self._kem_sktype()
        self.c_kyber.kem_keypair(pk, sk)
        return {'pk': list(pk), 'sk': list(sk)}

    def kem_enc(self, public_key):
        if len(public_key) > self.kem_publickeybytes:
            public_key = public_key[:self.kem_publickeybytes]
            self.logger.warn("public key was cut of, it was too large")
        ct = self._kem_cttype()
        ss = self._kem_sstype()
        pk = self._kem_pktype(*public_key)

        self.c_kyber.kem_enc(ct, ss, pk)
        return {'ct': list(ct), 'ss': list(ss)}

    def kem_dec(self, ciphertext, secret_key):
        # """
        #     kem_dec(ciphertext, secret_key)
        # """
        if len(ciphertext) > self.kem_ciphertextbytes:
            ciphertext = ciphertext[:self.kem_ciphertextbytes]
            self.logger.warn("ciphertext was cut of, it was too large")
        if len(secret_key) > self.kem_secretkeybytes:
            secret_key = secret_key[:self.kem_secretkeybytes]
            self.logger.warn("secret key was cut of, it was too large")

        ss = self._kem_sstype()
        ct = self._kem_cttype(*ciphertext)
        sk = self._kem_sktype(*secret_key)
        self.c_kyber.kem_dec(ss, ct, sk)
        return list(ss)

    def pke_keypair(self):
        pk = self._pke_pktype()
        sk = self._pke_sktype()
        self.c_kyber.pke_keypair(pk, sk)
        return {'pk': list(pk), 'sk': list(sk)}

    def pke_enc(self, msg, public_key, coins=None):
        if len(msg) > self.pke_msgbytes:
            msg = msg[:self.pke_msgbytes]
            self.logger.warn("message was cut of, it was too large")
        if len(public_key) > self.pke_publickeybytes:
            public_key = public_key[:self.pke_publickeybytes]
            self.logger.warn("public key was cut of, it was too large")
        if coins is not None and len(coins) > self.pke_symbytes:
            coins = coins[:self.pke_symbytes]
            self.logger.warn("coins was cut of, it was too large")
        if coins is None:
            import os
            coins = list(os.urandom(self.pke_symbytes))

        ct = self._pke_cttype()
        m = self._pke_msgtype(*msg)
        pk = self._pke_pktype(*public_key)
        coin = self._pke_coinstype(*coins)
        self.c_kyber.pke_enc(ct, m, pk, coin)
        return list(ct)

    def pke_dec(self, ciphertext, secret_key):
        if len(ciphertext) > self.pke_ciphertextbytes:
            ciphertext = ciphertext[:self.pke_ciphertextbytes]
            self.logger.warn("ciphertext was cut of, it was too large")
        if len(secret_key) > self.pke_secretkeybytes:
            secret_key = secret_key[:self.pke_secretkeybytes]
            self.logger.warn("secret key was cut of, it was too large")
        m = self._pke_msgtype()
        ct = self._pke_cttype(*ciphertext)
        sk = self._pke_sktype(*secret_key)
        self.c_kyber.pke_dec(m, ct, sk)
        return list(m)

    def available_implementations(self):
        import glob
        import os
        lst = glob.glob(self.lib_folder+"libkyber*")
        return [os.path.basename(x) for x in lst]
