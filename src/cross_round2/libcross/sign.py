import json
import subprocess
import sys
from cross import Cross

algorithms = ["RSDP", "RSDPG"]
categories = [1, 3, 5]
optimizations = ["fast", "balanced", "small"]



if len(sys.argv) == 4:
    algorithm = sys.argv[1]
    category = int(sys.argv[2])
    optimization = sys.argv[3]

    c = Cross(
        path="build",
        algorithm=algorithm,
        category=category,
        optimization=optimization,
    )

    sk, pk = c.keygen()

    message = list(b"Hello CROSS")
    signature = c.sign(sk, message)

    data = {
        "algorithm": algorithm,
        "category": category,
        "optimization": optimization,
        "public_key": pk,
        "message": message,
        "signature": signature,
    }

    with open("transfer.json", "w") as f:
        json.dump(data, f)

    result = subprocess.run(["python3", "verify.py"])

    raise SystemExit(result.returncode)


for algorithm in algorithms:
    for category in categories:
        for optimization in optimizations:

            result = subprocess.run([
                sys.executable,
                __file__,
                algorithm,
                str(category),
                optimization
            ])

            if result.returncode == 0:
                print(f"{algorithm} {category} {optimization}: PASS")
            else:
                print(f"{algorithm} {category} {optimization}: FAIL")