from ctypes import POINTER, c_uint8, c_uint16
from typing import List, Sequence, Tuple


class LessSubfunctions:
    """ctypes bindings for selected LESS reference subroutines."""

    def __init__(self, less) -> None:
        self.less = less
        self.params = less.params

        self.q = self.params.q
        self.n = self.params.n
        self.k = self.params.k
        self.n_pad = self.params.n_pad
        self.seed_length_bytes = self.params.seed_length_bytes
        self.private_key_seed_length_bytes = (
            self.params.private_key_seed_length_bytes
        )

        self.generator_values_count = (
            self.params.generator_values_count
        )

        self.row_values_count = self.n - self.k
        self.rref_values_count = (
            self.k * self.row_values_count
        )

    def load_dll(self) -> None:
        """Declare native libless argument and return types."""

        self.less.c_less.less_generator_monomial_mul.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint16),
        ]

        self.less.c_less.less_generator_monomial_mul.restype = None

        self.less.c_less.less_fq_inv.argtypes = [
            c_uint8,
        ]

        self.less.c_less.less_fq_inv.restype = c_uint8

        self.less.c_less.less_row_mul3.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]

        self.less.c_less.less_row_mul3.restype = None

        self.less.c_less.less_generator_sample.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint16),
            POINTER(c_uint8),
        ]

        self.less.c_less.less_generator_sample.restype = None

        self.less.c_less.less_monomial_sample_prikey.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint16),
            POINTER(c_uint8),
        ]

        self.less.c_less.less_monomial_sample_prikey.restype = None

    def generator_monomial_mul(
        self,
        generator_values: List[int],
        coefficients: List[int],
        permutation: List[int],
    ) -> List[int]:
        """Apply a LESS monomial map to a generator matrix."""

        if len(generator_values) != self.generator_values_count:
            raise ValueError(
                f"Expected {self.generator_values_count} generator entries, "
                f"got {len(generator_values)}"
            )

        if len(coefficients) != self.n:
            raise ValueError(
                f"Expected {self.n} monomial coefficients, "
                f"got {len(coefficients)}"
            )

        if len(permutation) != self.n:
            raise ValueError(
                f"Expected {self.n} permutation entries, "
                f"got {len(permutation)}"
            )

        if any(
            value < 0 or value >= self.q
            for value in generator_values
        ):
            raise ValueError(
                f"Generator entries must be in [0, {self.q - 1}]"
            )

        if any(
            value <= 0 or value >= self.q
            for value in coefficients
        ):
            raise ValueError(
                f"Coefficients must be in [1, {self.q - 1}]"
            )

        if sorted(permutation) != list(range(self.n)):
            raise ValueError(
                "Permutation must contain each index from 0 to N-1"
            )

        generator_type = (
            c_uint8 * self.generator_values_count
        )

        coefficient_type = (
            c_uint8 * self.n
        )

        permutation_type = (
            c_uint16 * self.n
        )

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

    def fq_inv(
        self,
        value: int,
    ) -> int:
        """Return the LESS reference inverse of one field element."""

        if not isinstance(value, int):
            raise TypeError(
                "Field element must be an integer"
            )

        if value < 0 or value >= self.q:
            raise ValueError(
                f"Field element must be in [0, {self.q - 1}]"
            )

        return int(
            self.less.c_less.less_fq_inv(value)
        )

    def row_mul3(
        self,
        in1: List[int],
        in2: List[int],
    ) -> List[int]:
        """Multiply two LESS rows component-wise."""

        if len(in1) != self.row_values_count:
            raise ValueError(
                f"Expected {self.row_values_count} entries in in1, "
                f"got {len(in1)}"
            )

        if len(in2) != self.row_values_count:
            raise ValueError(
                f"Expected {self.row_values_count} entries in in2, "
                f"got {len(in2)}"
            )

        if any(
            value < 0 or value >= self.q
            for value in in1
        ):
            raise ValueError(
                f"in1 entries must be in [0, {self.q - 1}]"
            )

        if any(
            value < 0 or value >= self.q
            for value in in2
        ):
            raise ValueError(
                f"in2 entries must be in [0, {self.q - 1}]"
            )

        row_type = (
            c_uint8 * self.row_values_count
        )

        c_out = row_type()
        c_in1 = row_type(*in1)
        c_in2 = row_type(*in2)

        self.less.c_less.less_row_mul3(
            c_out,
            c_in1,
            c_in2,
        )

        return list(c_out)

    def generator_sample(
        self,
        seed: Sequence[int] | bytes | bytearray,
    ) -> Tuple[List[int], List[int]]:
        """Expand a seed with the official LESS generator_sample function."""

        try:
            seed_bytes = bytes(seed)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                "Seed must be bytes or a sequence of byte values"
            ) from exc

        if len(seed_bytes) != self.seed_length_bytes:
            raise ValueError(
                f"Expected {self.seed_length_bytes} seed bytes, "
                f"got {len(seed_bytes)}"
            )

        values_type = (
            c_uint8 * self.rref_values_count
        )

        positions_type = (
            c_uint16 * self.row_values_count
        )

        seed_type = (
            c_uint8 * self.seed_length_bytes
        )

        c_values = values_type()
        c_positions = positions_type()
        c_seed = seed_type.from_buffer_copy(seed_bytes)

        self.less.c_less.less_generator_sample(
            c_values,
            c_positions,
            c_seed,
        )

        return (
            list(c_values),
            list(c_positions),
        )

    def monomial_sample_prikey(
        self,
        seed: Sequence[int] | bytes | bytearray,
    ) -> Tuple[List[int], List[int]]:
        """Expand a private-key seed into a LESS monomial matrix."""

        try:
            seed_bytes = bytes(seed)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                "Seed must be bytes or a sequence of byte values"
            ) from exc

        if len(seed_bytes) != self.private_key_seed_length_bytes:
            raise ValueError(
                f"Expected {self.private_key_seed_length_bytes} seed bytes, "
                f"got {len(seed_bytes)}"
            )

        coefficients_type = (
            c_uint8 * self.n
        )

        permutation_type = (
            c_uint16 * self.n
        )

        seed_type = (
            c_uint8 * self.private_key_seed_length_bytes
        )

        c_coefficients = coefficients_type()
        c_permutation = permutation_type()
        c_seed = seed_type.from_buffer_copy(seed_bytes)

        self.less.c_less.less_monomial_sample_prikey(
            c_coefficients,
            c_permutation,
            c_seed,
        )

        return (
            list(c_coefficients),
            list(c_permutation),
        )