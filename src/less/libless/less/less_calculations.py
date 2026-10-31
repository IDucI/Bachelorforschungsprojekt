from .less_subfunctions import LessSubfunctions


class Calculations:
    """Reconstruct intermediate matrices from LESS key generation."""

    def __init__(self, subfunctions: LessSubfunctions):
        self.subfunctions = subfunctions

    def keygen_generator_monomial_mul(self, compressed_sk, keypair_index=0):
        """Reproduce the monomial multiplication step of LESS key generation.
        Select one of the derived private monomials using keypair_index.
        Return the transformed generator matrix before RREF reduction."""

        g0_seed, private_seeds = self.subfunctions.expand_private_key_seeds(
            compressed_sk
        )

        if keypair_index < 0 or keypair_index >= len(private_seeds):
            raise ValueError(f"keypair_index must be in [0, {len(private_seeds) - 1}]")

        compact_values, column_pos = self.subfunctions.generator_sample(g0_seed)
        full_g0 = self.subfunctions.generator_rref_expand(
            compact_values,
            column_pos,
        )

        q_inv_coefficients, q_inv_permutation = (
            self.subfunctions.monomial_sample_prikey(private_seeds[keypair_index])
        )
        q_coefficients, q_permutation = self.subfunctions.monomial_inv(
            q_inv_coefficients,
            q_inv_permutation,
        )

        return self.subfunctions.generator_monomial_mul(
            full_g0,
            q_coefficients,
            q_permutation,
        )
