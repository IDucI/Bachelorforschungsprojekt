from dataclasses import dataclass
from typing import Optional


VALID_ALGORITHMS = {"RSDP", "RSDPG"}
VALID_CATEGORIES = {1, 3, 5}
VALID_OPTIMIZATIONS = {"fast", "balanced", "small"}


@dataclass(frozen=True)
class CrossParams:
    algorithm: str 
    category: int
    optimization: str 

    # ============================== RSDP(G) Parameters ==============================

    p: int # Field size of Fp
    z: int # Field size of Fz
    n: int # Length of vectors in the full code space (N)
    k: int # Dimension of the code (K); defines parity-check sizes
    m: Optional[int] # Dimension of the subgroup G (Only used in RSDPG variants)

    t: int # Number of protocol rounds
    w: int # Weight of the second challenge

    @property
    def version(self) -> str:
        algorithm_part = "rsdp" if self.algorithm == "RSDP" else "rsdpg"
        return f"{algorithm_part}_{self.category}_{self.optimization}"

    @property
    def sec_margin_lambda(self) -> int:
        return {
            1: 128,
            3: 192,
            5: 256,
            }[self.category]

    # ========================= Derived parameter helpers =========================

    @property
    def seed_length_bytes(self) -> int:
        return self.sec_margin_lambda//8

    @property
    def keypair_seed_length_bytes(self) -> int:
        # Seedsk and Seedpk are 2 * lambda bits long
        return 2 * (self.sec_margin_lambda // 8) 

    @property
    def hash_digest_length(self) -> int:
        return 2 * (self.sec_margin_lambda // 8) 

    @property
    def salt_length_bytes(self) -> int:
        return 2 * (self.sec_margin_lambda // 8) 

    @property
    def num_leaves_seed_tree(self) -> int:
        return self.t

    @property
    def num_nodes_seed_tree(self) -> int:
        return 2 * self.num_leaves_seed_tree - 1

    @property 
    def densely_packed_fp_syn_size(self) -> int:
        return ((self.n - self.k) * (self.p - 1).bit_length() + 7) // 8

    @property
    def densely_packed_fz_vec_size(self) -> int:
        return (self.n * (self.z - 1).bit_length() + 7) // 8

    @property
    def csprng_domain_sep_const(self) -> int:
        return 0

# ==================== Input normalization and validation ====================

def normalize_algorithm(algorithm: str) -> str:
    normalized = algorithm.upper().replace("-", "").replace("(", "").replace(")", "")
    if normalized not in VALID_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm '{algorithm}'")
    return normalized

def validate_category(category: int) -> int:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unsupported category '{category}'")
    return category

def normalize_optimization(optimization: str) -> str:
    normalized = optimization.lower()
    if normalized not in VALID_OPTIMIZATIONS:
        raise ValueError(f"Unsupported optimization '{optimization}'")
    return normalized


def get_params(
    algorithm: str, 
    category: int,
    optimization: str,
) -> CrossParams:
    algorithm = normalize_algorithm(algorithm)
    category = validate_category(category)
    optimization = normalize_optimization(optimization)
    params = PARAMETER_SETS[(algorithm, category, optimization)]
    return CrossParams(
        algorithm=algorithm,
        category=category,
        optimization=optimization,
        **params,)

PARAMETER_SETS = {
    ("RSDP", 1, "fast"): dict(p=127, z=7, n=127, k=76, m=None, t=157, w=82),
    ("RSDP", 1, "balanced"): dict(p=127, z=7, n=127, k=76, m=None, t=256, w=215),
    ("RSDP", 1, "small"): dict(p=127, z=7, n=127, k=76, m=None, t=520, w=488),

    ("RSDP", 3, "fast"): dict(p=127, z=7, n=187, k=111, m=None, t=239, w=125),
    ("RSDP", 3, "balanced"): dict(p=127, z=7, n=187, k=111, m=None, t=384, w=321),
    ("RSDP", 3, "small"): dict(p=127, z=7, n=187, k=111, m=None, t=580, w=527),

    ("RSDP", 5, "fast"): dict(p=127, z=7, n=251, k=150, m=None, t=321, w=167),
    ("RSDP", 5, "balanced"): dict(p=127, z=7, n=251, k=150, m=None, t=512, w=427),
    ("RSDP", 5, "small"): dict(p=127, z=7, n=251, k=150, m=None, t=832, w=762),

    ("RSDPG", 1, "fast"): dict(p=509, z=127, n=55, k=36, m=25, t=147, w=76),
    ("RSDPG", 1, "balanced"): dict(p=509, z=127, n=55, k=36, m=25, t=256, w=220),
    ("RSDPG", 1, "small"): dict(p=509, z=127, n=55, k=36, m=25, t=512, w=484),

    ("RSDPG", 3, "fast"): dict(p=509, z=127, n=79, k=48, m=40, t=224, w=119),
    ("RSDPG", 3, "balanced"): dict(p=509, z=127, n=79, k=48, m=40, t=268, w=196),
    ("RSDPG", 3, "small"): dict(p=509, z=127, n=79, k=48, m=40, t=512, w=463),

    ("RSDPG", 5, "fast"): dict(p=509, z=127, n=106, k=69, m=48, t=300, w=153),
    ("RSDPG", 5, "balanced"): dict(p=509, z=127, n=106, k=69, m=48, t=356, w=258),
    ("RSDPG", 5, "small"): dict(p=509, z=127, n=106, k=69, m=48, t=642, w=575),
}
