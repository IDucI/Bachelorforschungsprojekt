from ctypes import CDLL
from ctypes import POINTER, c_int, c_size_t, c_uint8, c_uint32, c_uint64
import logging
from pathlib import Path
from platform import release
import secrets
from typing import Optional

from .less_params import get_params
from .less_subfunctions import LessSubfunctions


def platform_release_string() -> str:
    version = release().split("-")[0]
    version = ".".join(version.split(".")[:3])
    return f"_{version}.so"


class Less:
    """Provides a Python interface to selected LESS subroutines."""

    def __init__(
        self,
        path=None,
        name=None,
        category: Optional[int] = None,
        target: Optional[int] = None,
        release_suffix=platform_release_string(),
    ):
        """
        path           | directory containing the LESS shared library
        name           | complete shared-library filename
        category       | NIST category 1, 3, or 5; None selects toy parameters
        target         | TARGET value from parameters.h; None for toy parameters
        release_suffix | platform suffix used by the project Makefile
        """
        self.logger = logging.getLogger(__name__)
        self.c_less = None

        self.params = get_params(category, target)
        self.subfunctions = LessSubfunctions(self)

        self._release = release_suffix
        self.default_lib_prefix = "libless_"
        self.default_lib_path = Path.home() / ".local/lib"

        self.select_lib(path, name, self.params.version, release_suffix)
        self.load_dll()

    def select_lib(self, path, name=None, version=None, release_suffix=None):
        self.logger.debug("__entry__ select_lib")
        self.logger.debug("path: %s", path)
        self.logger.debug("name: %s", name)
        self.logger.debug("version: %s", version)

        if name is not None:
            self.lib_name = name
        else:
            self.lib_name = (
                self.default_lib_prefix + str(version) + str(release_suffix)
            )

        self.lib_path = Path(path) if path is not None else self.default_lib_path
        return self.lib_path, self.lib_name

    def load_dll(self):
        library_file = self.lib_path / self.lib_name
        try:
            self.logger.debug("loading CDLL file: %s", library_file)
            self.c_less = CDLL(str(library_file))
        except OSError as exc:
            self.logger.error("Failed to load lib: %s", library_file)
            self.logger.error(exc)
            raise

        self.c_less.less_initialize_randombytes.argtypes = [
            POINTER(c_uint8),
            c_uint32,
        ]
        self.c_less.less_initialize_randombytes.restype = None

        self._has_high_level = hasattr(self.c_less, "less_keygen")
        if self._has_high_level:
            self.sk_size = c_size_t.in_dll(
                self.c_less,
                "less_skbytes",
            ).value
            self.pk_size = c_size_t.in_dll(
                self.c_less,
                "less_pkbytes",
            ).value
            self.sig_size = c_size_t.in_dll(
                self.c_less,
                "less_sigbytes",
            ).value

            self._sk_type = c_uint8 * self.sk_size
            self._pk_type = c_uint8 * self.pk_size
            self._sig_type = c_uint8 * self.sig_size

            self.c_less.less_keygen.argtypes = [
                POINTER(c_uint8),
                POINTER(c_uint8),
            ]
            self.c_less.less_keygen.restype = None

            self.c_less.less_sign.argtypes = [
                POINTER(c_uint8),
                POINTER(c_uint8),
                c_uint64,
                POINTER(c_uint8),
            ]
            self.c_less.less_sign.restype = None

            self.c_less.less_verify.argtypes = [
                POINTER(c_uint8),
                POINTER(c_uint8),
                c_uint64,
                POINTER(c_uint8),
            ]
            self.c_less.less_verify.restype = c_int

        self.subfunctions.load_dll()

    def _require_high_level(self):
        if not self._has_high_level:
            raise RuntimeError(
                "LESS keygen/sign/verify are available for official "
                "parameter sets, not the toy build"
            )

    def _initialize_randombytes(self):
        seed = secrets.token_bytes(48)
        c_seed = (c_uint8 * len(seed)).from_buffer_copy(seed)
        self.c_less.less_initialize_randombytes(
            c_seed,
            len(seed),
        )

    def keygen(self):
        self._require_high_level()
        self._initialize_randombytes()

        sk = self._sk_type()
        pk = self._pk_type()
        self.c_less.less_keygen(sk, pk)
        return list(sk), list(pk)

    def sign(self, secret_key, message):
        self._require_high_level()
        self._initialize_randombytes()

        sk = self._sk_type(*secret_key)
        c_message = (c_uint8 * len(message))(*message)
        signature = self._sig_type()

        self.c_less.less_sign(
            sk,
            c_message,
            len(message),
            signature,
        )
        return list(signature)

    def verify(self, public_key, message, signature):
        self._require_high_level()

        pk = self._pk_type(*public_key)
        c_message = (c_uint8 * len(message))(*message)
        c_signature = self._sig_type(*signature)

        return self.c_less.less_verify(
            pk,
            c_message,
            len(message),
            c_signature,
        )
