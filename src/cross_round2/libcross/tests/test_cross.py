import json
from pathlib import Path
from cross import Cross, Calculations

algorithms = ["RSDP", "RSDPG"]
categories = [1, 3, 5]
optimizations = ["fast", "balanced", "small"]

test_dir = Path(__file__).parent

for algorithm in algorithms:
    for category in categories:
        for optimization in optimizations:
            json_path = test_dir / f"cross_{algorithm.lower()}_{category}_{optimization}.json"

            with open(json_path, "r") as f:
                data = json.load(f)

            c = Cross(
                path="build",
                algorithm=algorithm,
                category=category,
                optimization=optimization,
            )

            calc = Calculations(c.subfunctions)

            seed_sk = bytes.fromhex(data["seed_sk"])
            root_seed = bytes.fromhex(data["root_seed"])
            salt = bytes.fromhex(data["salt"])

            print(algorithm, category, optimization)

            v_bar = calc.v_bar(seed_sk, root_seed, salt)

            v_bar_c = data["v_bar"]

            print(v_bar[0][:10])
            print(v_bar_c[0][:10])

            if v_bar == v_bar_c:
                print("MATCH")
            else:
                print("MISMATCH")

