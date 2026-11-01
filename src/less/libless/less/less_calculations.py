from .less_subfunctions import LessSubfunctions
import secrets

from .less_calculation_result import (
    FqInvData,
    GeneratorSampleData,
    MonomialSamplePrikeyData,
    GeneratorMonomialMulData,
    KeygenCalculationResult,
)


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

    def keygen(self, compressed_sk=None, keypair_index=0):
        """Collect intermediate values from LESS key generation."""

        sub = self.subfunctions

        if compressed_sk is None:
            compressed_sk = secrets.token_bytes(sub.private_key_seed_length_bytes)

        compressed_sk = bytes(compressed_sk)

        g0_seed, private_seeds = sub.expand_private_key_seeds(compressed_sk)

        if keypair_index < 0 or keypair_index >= len(private_seeds):
            raise ValueError(f"keypair_index must be in [0, {len(private_seeds) - 1}]")

        compact, positions = sub.generator_sample(g0_seed)
        generator = sub.generator_rref_expand(compact, positions)

        private_seed = private_seeds[keypair_index]
        inverse_coefficients, inverse_permutation = sub.monomial_sample_prikey(
            private_seed
        )

        coefficients, permutation = sub.monomial_inv(
            inverse_coefficients,
            inverse_permutation,
        )

        product = sub.generator_monomial_mul(
            generator,
            coefficients,
            permutation,
        )

        value = inverse_coefficients[0]
        inverse = coefficients[inverse_permutation[0]]

        return KeygenCalculationResult(
            compressed_sk=compressed_sk,
            fq_inv=FqInvData(value, inverse),
            generator_sample=GeneratorSampleData(
                bytes(g0_seed),
                bytes(compact),
                tuple(positions),
            ),
            monomial_sample_prikey=MonomialSamplePrikeyData(
                bytes(private_seed),
                bytes(inverse_coefficients),
                tuple(inverse_permutation),
            ),
            generator_monomial_mul=GeneratorMonomialMulData(
                bytes(generator),
                bytes(coefficients),
                tuple(permutation),
                bytes(product),
            ),
        )
