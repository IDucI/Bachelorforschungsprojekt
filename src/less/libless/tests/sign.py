import json
import subprocess
import sys

from less import Less


variants = [
    (1, 192),
    (1, 68),
    (1, 45),
    (3, 220),
    (3, 102),
    (5, 345),
    (5, 137),
]

if len(sys.argv) == 3:
    category = int(sys.argv[1])
    target = int(sys.argv[2])

    less = Less(
        path="build",
        category=category,
        target=target,
    )

    sk, pk = less.keygen()
    message = list(b"Hello LESS")
    signature = less.sign(sk, message)

    data = {
        "category": category,
        "target": target,
        "public_key": pk,
        "message": message,
        "signature": signature,
    }

    with open("transfer.json", "w") as file:
        json.dump(data, file)

    result = subprocess.run([sys.executable, "-m", "tests.verify"])
    raise SystemExit(result.returncode)

for category, target in variants:
    result = subprocess.run([
        sys.executable,
        "-m",
        "tests.sign",
        str(category),
        str(target),
    ])

    if result.returncode == 0:
        print(f"Category {category} target {target}: PASS")
    else:
        print(f"Category {category} target {target}: FAIL")
