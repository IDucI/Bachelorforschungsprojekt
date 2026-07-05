import ctypes
from ctypes import *
from pathlib import Path
import logging
from platform import release

from .cross_subfunctions import CrossSubfunctions


def platform_release_string():
    return '_'+(release().split('-')[0])


class Cross:
    """Provides a Python interface to a CROSS implementation."""

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

    def __init__(self, path=None, name=None, version="r_sdp_1_fast", release=platform_release_string()):
        """
        path    | path of the CROSS library to load
        name    | full name of the library
        version | CROSS variant, e.g. r_sdp_1_fast
        """
        self.logger = logging.getLogger(__name__)

        self.c_cross = None
        self.cross_n = None

        self.subfunctions = CrossSubfunctions(self)

        self._release = release
        self.default_lib_prefix = "libcross_"
        self.default_lib_path = Path().home() / ".local/lib/"

        self.select_lib(path, name, version, release)

        self.load_dll()

    def select_lib(self, path, name=None, version=None, release=None):
        self.logger.debug("__entry__ select_lib")
        self.logger.debug(f"path: {path}")
        self.logger.debug(f"name: {name}")
        self.logger.debug(f"version: {version}")

        if name is not None:
            self.logger.debug("name used")
            self.lib_name = name
        elif version is not None:
            self.logger.debug("version used")
            self.lib_name = self.default_lib_prefix + str(version) + str(release)
        else:
            self.logger.debug("default CROSS configuration used")
            self.lib_name = self.default_lib_prefix + "r_sdp_1_fast" + str(release)

        self.logger.debug(f"self.lib_name = {self.lib_name}")

        if path is not None:
            self.lib_path = Path(path)
        else:
            self.lib_path = self.default_lib_path

        self.logger.debug(f"self.lib_path = {self.lib_path}")

        return self.lib_path, self.lib_name

    def load_dll(self):
        try:
            self.logger.debug(f"loading CDLL file in: {self.lib_path / self.lib_name}")
            self.c_cross = CDLL(str(self.lib_path / self.lib_name))
        except OSError as e:
            self.logger.error(f"Failed to load lib: {self.lib_path / self.lib_name}")
            self.logger.error(e)
            raise

        self.subfunctions.load_dll()
