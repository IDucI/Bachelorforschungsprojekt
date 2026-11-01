from dataclasses import dataclass

"""Intermediate values for the selected LESS subroutines."""


@dataclass
class FqInvData:
    value: int
    inverse: int


@dataclass
class GeneratorSampleData:
    seed: bytes
    values: bytes
    positions: tuple[int, ...]


@dataclass
class MonomialSamplePrikeyData:
    seed: bytes
    coefficients: bytes
    permutation: tuple[int, ...]


@dataclass
class GeneratorMonomialMulData:
    generator: bytes
    coefficients: bytes
    permutation: tuple[int, ...]
    result: bytes


@dataclass
class KeygenCalculationResult:
    compressed_sk: bytes
    fq_inv: FqInvData
    generator_sample: GeneratorSampleData
    monomial_sample_prikey: MonomialSamplePrikeyData
    generator_monomial_mul: GeneratorMonomialMulData
