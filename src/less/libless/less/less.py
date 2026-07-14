from ctypes import CDLL
import logging
from pathlib import Path
from platform import release
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

        self.subfunctions.load_dll()
