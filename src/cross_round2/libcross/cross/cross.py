import ctypes
from ctypes import *
from pathlib import Path
import logging
from platform import release

from .cross_subfunctions import CrossSubfunctions
from .cross_params import get_params


def platform_release_string():
    version = release().split("-")[0]
    version = ".".join(version.split(".")[:3])
    return f"_{version}.so"


class Cross:
    """Provides a Python interface to a CROSS implementation.
    
    The implementation is selected through:
        * algorithm: RSDP or RSDPG
        * category: NIST security category 1, 3, or 5
        * optimization: fast, balanced, or small

    The active CROSS parameter set is stored in self.params.
    """

    def __init__(self, path=None, name=None, algorithm="RSDP", category=1, optimization="fast", release=platform_release_string()):
        """
        path         | path of the CROSS library to load
        name         | full name of the library
        algorithm    | CROSS variant: RSDP or RSDPG
        category     | NIST security category: 1, 3, or 5
        optimization | optimization corner: fast, balanced, or small
        """
        self.logger = logging.getLogger(__name__)

        self.c_cross = None
        self.cross_n = None

        self.params = get_params(algorithm, category, optimization)
        self.subfunctions = CrossSubfunctions(self)

        self._release = release
        self.default_lib_prefix = "libcross_"
        self.default_lib_path = Path().home() / ".local/lib/"

        self.select_lib(path, name, self.params.version, release)

        self.load_dll()

    def select_lib(self, path, name=None, version=None, release=None):
        self.logger.debug("__entry__ select_lib")
        self.logger.debug(f"path: {path}")
        self.logger.debug(f"name: {name}")
        self.logger.debug(f"version: {version}")

        if name is not None:
            self.logger.debug("name used")
            self.lib_name = name
        else:
            self.logger.debug("version used")
            self.lib_name = self.default_lib_prefix + str(version) + str(release)

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
