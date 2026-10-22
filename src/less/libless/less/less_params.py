from dataclasses import dataclass
from typing import Optional


VALID_CATEGORIES = {1, 3, 5}
VALID_TARGETS = {
    1: {192, 68, 45},
    3: {220, 102},
    5: {345, 137},
}


@dataclass(frozen=True)
class LessParams:
    """Parameters of one official LESS reference parameter set."""

    category: Optional[int]
    target: Optional[int]

    q: int
    n: int
    k: int
    seed_length_bytes: int
    num_keypairs: int
    t: int
    w: int

    @property
    def version(self) -> str:
        if self.category is None:
            return "toy"
        return f"cat{self.category}_{self.target}"

    @property
    def n_pad(self) -> int:
        # The ISO-C reference implementation uses N_pad == N.
        return self.n

    @property
    def generator_values_count(self) -> int:
        return self.k * self.n_pad

    @property
    def private_key_seed_length_bytes(self) -> int:
        return 2 * self.seed_length_bytes


def get_params(
    category: Optional[int] = None,
    target: Optional[int] = None,
) -> LessParams:
    """Return the selected LESS parameters.

    ``category=None, target=None`` selects the official toy parameter set.
    A real parameter set requires both a NIST category and its TARGET value.
    """
    if category is None and target is None:
        values = PARAMETER_SETS[(None, None)]
        return LessParams(category=None, target=None, **values)

    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unsupported LESS category '{category}'")
    if target not in VALID_TARGETS[category]:
        supported = ", ".join(str(value) for value in sorted(VALID_TARGETS[category]))
        raise ValueError(
            f"Unsupported TARGET '{target}' for category {category}; "
            f"supported values are: {supported}"
        )

    values = PARAMETER_SETS[(category, target)]
    return LessParams(category=category, target=target, **values)


# Values copied from the official Round-2 Reference_Implementation/parameters.h.
PARAMETER_SETS = {
    (None, None): dict(
        q=127,
        n=16,
        k=8,
        seed_length_bytes=16,
        num_keypairs=3,
        t=106,
        w=57,
    ),
    (1, 192): dict(
        q=127,
        n=252,
        k=126,
        seed_length_bytes=16,
        num_keypairs=2,
        t=192,
        w=36,
    ),
    (1, 68): dict(
        q=127,
        n=252,
        k=126,
        seed_length_bytes=16,
        num_keypairs=4,
        t=68,
        w=42,
    ),
    (1, 45): dict(
        q=127,
        n=252,
        k=126,
        seed_length_bytes=16,
        num_keypairs=8,
        t=45,
        w=34,
    ),
    (3, 220): dict(
        q=127,
        n=400,
        k=200,
        seed_length_bytes=24,
        num_keypairs=2,
        t=220,
        w=68,
    ),
    (3, 102): dict(
        q=127,
        n=400,
        k=200,
        seed_length_bytes=24,
        num_keypairs=4,
        t=102,
        w=61,
    ),
    (5, 345): dict(
        q=127,
        n=548,
        k=274,
        seed_length_bytes=32,
        num_keypairs=2,
        t=345,
        w=75,
    ),
    (5, 137): dict(
        q=127,
        n=548,
        k=274,
        seed_length_bytes=32,
        num_keypairs=4,
        t=137,
        w=79,
    ),
}
