import unittest
from pathlib import Path

from less import Less


VARIANTS = (
    (None, None),
    (1, 192),
    (1, 68),
    (1, 45),
    (3, 220),
    (3, 102),
    (5, 345),
    (5, 137),
)


class IntermediateTests(unittest.TestCase):
    def test_keygen_inputs(self):
        build = Path(__file__).resolve().parents[1] / "build"

        for category, target in VARIANTS:
            with self.subTest(category=category, target=target):
                less = Less(
                    path=build,
                    category=category,
                    target=target,
                )

                sub = less.subfunctions
                seed = bytes(
                    range(sub.private_key_seed_length_bytes)
                )

                keygen = less.calculation.keygen(seed)

                self.assertEqual(
                    sub.fq_inv(keygen.fq_inv.value),
                    keygen.fq_inv.inverse,
                )

                sample = keygen.generator_sample

                self.assertEqual(
                    sub.generator_sample(sample.seed),
                    (
                        list(sample.values),
                        list(sample.positions),
                    ),
                )

                monomial = keygen.monomial_sample_prikey

                self.assertEqual(
                    sub.monomial_sample_prikey(monomial.seed),
                    (
                        list(monomial.coefficients),
                        list(monomial.permutation),
                    ),
                )

                product = keygen.generator_monomial_mul

                self.assertEqual(
                    sub.generator_monomial_mul(
                        product.generator,
                        product.coefficients,
                        product.permutation,
                    ),
                    list(product.result),
                )

                self.assertEqual(
                    less.calculation.keygen_generator_monomial_mul(seed),
                    list(product.result),
                )


if __name__ == "__main__":
    unittest.main()