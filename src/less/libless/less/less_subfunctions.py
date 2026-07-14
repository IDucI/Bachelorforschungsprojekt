from ctypes import POINTER, c_uint8, c_uint16
from typing import List


class LessSubfunctions:
    """ctypes bindings for selected LESS reference subroutines."""

    def __init__(self, less) -> None:
        self.less = less
        self.params = less.params

        self.q = self.params.q
        self.n = self.params.n
        self.k = self.params.k
        self.n_pad = self.params.n_pad
        self.generator_values_count = self.params.generator_values_count

    def load_dll(self):
        """Declare native libless argument and return types."""
        self.less.c_less.less_generator_monomial_mul.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint16),
        ]
        self.less.c_less.less_generator_monomial_mul.restype = None

    def generator_monomial_mul(
        self,
        generator_values: List[int],
        coefficients: List[int],
        permutation: List[int],
    ) -> List[int]:
        """Apply a LESS monomial map to a generator matrix.

        ``generator_values`` is a row-major flat K x N_pad matrix.
        ``coefficients`` contains N non-zero field elements.
        ``permutation`` contains each position from 0 to N-1 exactly once.
        """
        if len(generator_values) != self.generator_values_count:
            raise ValueError(
                f"Expected {self.generator_values_count} generator entries, "
                f"got {len(generator_values)}"
            )
        if len(coefficients) != self.n:
            raise ValueError(
                f"Expected {self.n} monomial coefficients, got {len(coefficients)}"
            )
        if len(permutation) != self.n:
            raise ValueError(
                f"Expected {self.n} permutation entries, got {len(permutation)}"
            )

        if any(value < 0 or value >= self.q for value in generator_values):
            raise ValueError(f"Generator entries must be in [0, {self.q - 1}]")
        if any(value <= 0 or value >= self.q for value in coefficients):
            raise ValueError(f"Coefficients must be in [1, {self.q - 1}]")
        if sorted(permutation) != list(range(self.n)):
            raise ValueError("Permutation must contain each index from 0 to N-1")

        generator_type = c_uint8 * self.generator_values_count
        coefficient_type = c_uint8 * self.n
        permutation_type = c_uint16 * self.n

        c_result = generator_type()
        c_generator = generator_type(*generator_values)
        c_coefficients = coefficient_type(*coefficients)
        c_permutation = permutation_type(*permutation)

        self.less.c_less.less_generator_monomial_mul(
            c_result,
            c_generator,
            c_coefficients,
            c_permutation,
        )

        return list(c_result)
