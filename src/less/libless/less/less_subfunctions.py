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
        self.num_keypairs = self.params.num_keypairs
        self.seed_length_bytes = self.params.seed_length_bytes
        self.private_key_seed_length_bytes = self.params.private_key_seed_length_bytes

        self.generator_values_count = self.params.generator_values_count

        self.row_values_count = self.n - self.k
        self.rref_values_count = self.k * self.row_values_count
        self.private_monomial_seeds_count = (
            self.num_keypairs - 1
        ) * self.private_key_seed_length_bytes

    def load_dll(self) -> None:
        """Declare native libless argument and return types."""

        self.less.c_less.less_expand_private_key_seeds.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint8),
        ]
        self.less.c_less.less_expand_private_key_seeds.restype = None

        self.less.c_less.less_generator_rref_expand.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint8),
            POINTER(c_uint16),
        ]
        self.less.c_less.less_generator_rref_expand.restype = None

        self.less.c_less.less_monomial_inv.argtypes = [
            POINTER(c_uint8),
            POINTER(c_uint16),
            POINTER(c_uint8),
            POINTER(c_uint16),
        ]
        self.less.c_less.less_monomial_inv.restype = None

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

    def expand_private_key_seeds(
        self,
        compressed_sk: Sequence[int] | bytes | bytearray,
    ) -> Tuple[bytes, List[bytes]]:
        """Derive the generator seed and private monomial seeds
        from the compressed secret-key seed."""
        compressed_sk = bytes(compressed_sk)
        if len(compressed_sk) != self.private_key_seed_length_bytes:
            raise ValueError(
                f"Expected {self.private_key_seed_length_bytes} secret-key "
                f"bytes, got {len(compressed_sk)}"
            )

        g0_type = c_uint8 * self.seed_length_bytes
        seeds_type = c_uint8 * self.private_monomial_seeds_count
        sk_type = c_uint8 * self.private_key_seed_length_bytes

        c_g0_seed = g0_type()
        c_private_seeds = seeds_type()
        c_sk = sk_type.from_buffer_copy(compressed_sk)

        self.less.c_less.less_expand_private_key_seeds(
            c_g0_seed,
            c_private_seeds,
            c_sk,
        )

        private_seeds = bytes(c_private_seeds)
        seed_size = self.private_key_seed_length_bytes
        return bytes(c_g0_seed), [
            private_seeds[offset : offset + seed_size]
            for offset in range(0, len(private_seeds), seed_size)
        ]

    def generator_rref_expand(
        self,
        compact_values: List[int],
        column_pos: List[int],
    ) -> List[int]:
        """Expand compact RREF values and column positions
        into a full LESS generator matrix."""
        if len(compact_values) != self.rref_values_count:
            raise ValueError(
                f"Expected {self.rref_values_count} compact entries, "
                f"got {len(compact_values)}"
            )
        if len(column_pos) != self.row_values_count:
            raise ValueError(
                f"Expected {self.row_values_count} column positions, "
                f"got {len(column_pos)}"
            )

        full_type = c_uint8 * self.generator_values_count
        compact_type = c_uint8 * self.rref_values_count
        positions_type = c_uint16 * self.row_values_count

        c_full = full_type()
        c_compact = compact_type(*compact_values)
        c_positions = positions_type(*column_pos)

        self.less.c_less.less_generator_rref_expand(
            c_full,
            c_compact,
            c_positions,
        )
        return list(c_full)

    def monomial_inv(
        self,
        coefficients: List[int],
        permutation: List[int],
    ) -> Tuple[List[int], List[int]]:
        """Compute the inverse monomial transformation
        and return its coefficients and permutation."""
        if len(coefficients) != self.n or len(permutation) != self.n:
            raise ValueError(f"Expected {self.n} monomial entries")

        coefficients_type = c_uint8 * self.n
        permutation_type = c_uint16 * self.n

        c_res_coefficients = coefficients_type()
        c_res_permutation = permutation_type()
        c_coefficients = coefficients_type(*coefficients)
        c_permutation = permutation_type(*permutation)

        self.less.c_less.less_monomial_inv(
            c_res_coefficients,
            c_res_permutation,
            c_coefficients,
            c_permutation,
        )

        return list(c_res_coefficients), list(c_res_permutation)

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
                f"Expected {self.n} monomial coefficients, " f"got {len(coefficients)}"
            )

        if len(permutation) != self.n:
            raise ValueError(
                f"Expected {self.n} permutation entries, " f"got {len(permutation)}"
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

    def fq_inv(
        self,
        value: int,
    ) -> int:
        """Return the LESS reference inverse of one field element."""

        if not isinstance(value, int):
            raise TypeError("Field element must be an integer")

        if value < 0 or value >= self.q:
            raise ValueError(f"Field element must be in [0, {self.q - 1}]")

        return int(self.less.c_less.less_fq_inv(value))

    def row_mul3(
        self,
        in1: List[int],
        in2: List[int],
    ) -> List[int]:
        """Multiply two LESS rows component-wise."""

        if len(in1) != self.row_values_count:
            raise ValueError(
                f"Expected {self.row_values_count} entries in in1, " f"got {len(in1)}"
            )

        if len(in2) != self.row_values_count:
            raise ValueError(
                f"Expected {self.row_values_count} entries in in2, " f"got {len(in2)}"
            )

        if any(value < 0 or value >= self.q for value in in1):
            raise ValueError(f"in1 entries must be in [0, {self.q - 1}]")

        if any(value < 0 or value >= self.q for value in in2):
            raise ValueError(f"in2 entries must be in [0, {self.q - 1}]")

        row_type = c_uint8 * self.row_values_count

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
            raise TypeError("Seed must be bytes or a sequence of byte values") from exc

        if len(seed_bytes) != self.seed_length_bytes:
            raise ValueError(
                f"Expected {self.seed_length_bytes} seed bytes, "
                f"got {len(seed_bytes)}"
            )

        values_type = c_uint8 * self.rref_values_count

        positions_type = c_uint16 * self.row_values_count

        seed_type = c_uint8 * self.seed_length_bytes

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
            raise TypeError("Seed must be bytes or a sequence of byte values") from exc

        if len(seed_bytes) != self.private_key_seed_length_bytes:
            raise ValueError(
                f"Expected {self.private_key_seed_length_bytes} seed bytes, "
                f"got {len(seed_bytes)}"
            )

        coefficients_type = c_uint8 * self.n

        permutation_type = c_uint16 * self.n

        seed_type = c_uint8 * self.private_key_seed_length_bytes

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