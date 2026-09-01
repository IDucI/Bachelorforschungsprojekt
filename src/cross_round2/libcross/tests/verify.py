import json
from cross import Cross

with open("transfer.json") as f:
    data = json.load(f)

c = Cross(
    path="build",
    algorithm=data["algorithm"],
    category=data["category"],
    optimization=data["optimization"],
)

result = c.verify(
    data["public_key"],
    data["message"],
    data["signature"],
)

print(
    f'{data["algorithm"]} '
    f'{data["category"]} '
    f'{data["optimization"]}: '
    f'Verify = {result}'
)

raise SystemExit(0 if result else 1)