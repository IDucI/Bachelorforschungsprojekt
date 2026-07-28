from hashlib import shake_256
from os import urandom

from less import Less


less = Less(path="build")

n = less.params.n
k = less.params.k
q = less.params.q

seed_length = less.params.seed_length_bytes
private_key_seed_length = (
    less.params.private_key_seed_length_bytes
)

row_length = n - k


class ShakeReader:
    """Sequential reader over Python's SHAKE256 output stream."""

    def __init__(
        self,
        seed: bytes,
    ) -> None:
        self._shake = shake_256(seed)
        self._offset = 0

    def read(
        self,
        length: int,
    ) -> bytes:
        end = self._offset + length

        data = self._shake.digest(end)[
            self._offset:end
        ]

        self._offset = end

        return data


def generator_monomial_mul_python(
    generator_values: list[int],
    coefficients: list[int],
    permutation: list[int],
) -> list[int]:
    result = [0] * (k * n)

    for source_column in range(n):
        destination_column = (
            permutation[source_column]
        )

        coefficient = (
            coefficients[source_column]
        )

        for row in range(k):
            source_index = (
                row * n + source_column
            )

            destination_index = (
                row * n + destination_column
            )

            result[destination_index] = (
                generator_values[source_index]
                * coefficient
            ) % q

    return result


def generator_sample_python(
    seed: bytes,
) -> tuple[list[int], list[int]]:
    if len(seed) != seed_length:
        raise ValueError(
            f"Expected {seed_length} seed bytes, "
            f"got {len(seed)}"
        )

    reader = ShakeReader(seed)
    values: list[int] = []

    for _ in range(k):
        row: list[int] = []

        while len(row) < row_length:
            word = int.from_bytes(
                reader.read(8),
                byteorder="little",
            )

            for _ in range(64 // 7):
                candidate = word & 0x7F

                if candidate <= q - 1:
                    row.append(candidate)

                    if len(row) == row_length:
                        break

                word >>= 7

        values.extend(row)

    return (
        values,
        list(range(k, n)),
    )


def monomial_sample_prikey_python(
    seed: bytes,
) -> tuple[list[int], list[int]]:
    if len(seed) != private_key_seed_length:
        raise ValueError(
            f"Expected {private_key_seed_length} seed bytes, "
            f"got {len(seed)}"
        )

    reader = ShakeReader(seed)
    coefficients: list[int] = []

    while len(coefficients) < n:
        word = int.from_bytes(
            reader.read(8),
            byteorder="little",
        )

        for _ in range(64 // 7):
            candidate = word & 0x7F

            if candidate <= q - 2:
                coefficients.append(
                    candidate + 1
                )

                if len(coefficients) == n:
                    break

            word >>= 7

    permutation = list(range(n))

    position_bits = (
        n - 1
    ).bit_length()

    position_mask = (
        1 << position_bits
    ) - 1

    random_word = int.from_bytes(
        reader.read(8),
        byteorder="little",
    )

    consumed_candidates = 0

    for index in range(n):
        while True:
            if consumed_candidates == (
                64 // position_bits
            ) - 1:
                random_word = int.from_bytes(
                    reader.read(8),
                    byteorder="little",
                )

                consumed_candidates = 0

            destination = (
                random_word
                & position_mask
            )

            random_word >>= position_bits
            consumed_candidates += 1

            if destination < n:
                break

        permutation[index], permutation[destination] = (
            permutation[destination],
            permutation[index],
        )

    return (
        coefficients,
        permutation,
    )


# ---------------------------------------------------------------------------
# generator_monomial_mul
# ---------------------------------------------------------------------------

generator = [
    (row * n + column) % q
    for row in range(k)
    for column in range(n)
]

coefficients = [
    (index % (q - 1)) + 1
    for index in range(n)
]

permutation = list(
    reversed(range(n))
)

expected_generator = (
    generator_monomial_mul_python(
        generator,
        coefficients,
        permutation,
    )
)

actual_generator = (
    less.subfunctions.generator_monomial_mul(
        generator,
        coefficients,
        permutation,
    )
)

assert actual_generator == expected_generator

print(
    "generator_monomial_mul: passed"
)


# ---------------------------------------------------------------------------
# fq_inv
# ---------------------------------------------------------------------------

for value in range(q):
    expected = (
        0
        if value == 0
        else pow(value, -1, q)
    )

    actual = less.subfunctions.fq_inv(
        value
    )

    assert actual == expected, (
        value,
        expected,
        actual,
    )

print(
    f"fq_inv: all {q} field elements passed"
)


# ---------------------------------------------------------------------------
# row_mul3
# ---------------------------------------------------------------------------

row1 = [
    index + 1
    for index in range(row_length)
]

row2 = list(
    reversed(row1)
)

expected_row = [
    (left * right) % q
    for left, right in zip(
        row1,
        row2,
    )
]

actual_row = less.subfunctions.row_mul3(
    row1,
    row2,
)

assert actual_row == expected_row

print(
    "row_mul3: passed"
)


# ---------------------------------------------------------------------------
# generator_sample
# ---------------------------------------------------------------------------

generator_sample_seeds = [
    bytes(seed_length),
    bytes(range(seed_length)),
    bytes([255]) * seed_length,
]

generator_sample_seeds.extend(
    urandom(seed_length)
    for _ in range(1000)
)

for seed in generator_sample_seeds:
    expected = generator_sample_python(
        seed
    )

    actual = less.subfunctions.generator_sample(
        seed
    )

    assert actual == expected, (
        seed.hex(),
        expected,
        actual,
    )

sample_values, sample_positions = (
    less.subfunctions.generator_sample(
        bytes(range(seed_length))
    )
)

print(
    "generator_sample first row:",
    sample_values[:row_length],
)

print(
    "generator_sample positions:",
    sample_positions,
)

print(
    f"generator_sample: "
    f"{len(generator_sample_seeds)} seeds passed"
)


# ---------------------------------------------------------------------------
# monomial_sample_prikey
# ---------------------------------------------------------------------------

private_key_seeds = [
    bytes(private_key_seed_length),
    bytes(range(private_key_seed_length)),
    bytes([255]) * private_key_seed_length,
]

private_key_seeds.extend(
    urandom(private_key_seed_length)
    for _ in range(1000)
)

for seed in private_key_seeds:
    expected = (
        monomial_sample_prikey_python(
            seed
        )
    )

    actual = (
        less.subfunctions.monomial_sample_prikey(
            seed
        )
    )

    assert actual == expected, (
        seed.hex(),
        expected,
        actual,
    )

sample_coefficients, sample_permutation = (
    less.subfunctions.monomial_sample_prikey(
        bytes(range(private_key_seed_length))
    )
)

print(
    "monomial_sample_prikey coefficients:",
    sample_coefficients,
)

print(
    "monomial_sample_prikey permutation:",
    sample_permutation,
)

print(
    f"monomial_sample_prikey: "
    f"{len(private_key_seeds)} seeds passed"
)