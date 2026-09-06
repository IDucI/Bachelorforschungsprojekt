import json

from less import Less


with open("transfer.json", "r") as file:
    data = json.load(file)

less = Less(
    path="build",
    category=data["category"],
    target=data["target"],
)

result = less.verify(
    data["public_key"],
    data["message"],
    data["signature"],
)

print(
    f'Category {data["category"]} target {data["target"]}: '
    f'Verify = {result}'
)

raise SystemExit(0 if result else 1)
