import json
from pathlib import Path

from less import Calculations, Less


variants = [
    (1, 192),
    (1, 68),
    (1, 45),
    (3, 220),
    (3, 102),
    (5, 345),
    (5, 137),
]

test_dir = Path(__file__).parent

for category, target in variants:
    name = f"less_cat{category}_{target}"
    with open(test_dir / f"{name}.json", "r") as file:
        data = json.load(file)

    less = Less(
        path="build",
        category=category,
        target=target,
    )
    calc = Calculations(less.subfunctions)

    compressed_sk = bytes.fromhex(data["compressed_sk"])
    result = calc.keygen_generator_monomial_mul(compressed_sk)
    result_c = [
        value
        for row in data["generator_product"]
        for value in row
    ]

    print(category, target, "MATCH" if result == result_c else "MISMATCH")
