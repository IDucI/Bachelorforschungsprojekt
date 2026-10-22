import json

from less import Less


with open(
    "transfer.json",
    "r",
) as file:
    data = json.load(
        file
    )

less = Less(
    path="build",
    category=data["category"],
    target=data["target"],
)

message = data[
    "message"
]

modified_message = list(
    message
)

modified_message[0] ^= 1

positive = less.verify(
    data["public_key"],
    message,
    data["signature"],
)

wrong_message = less.verify(
    data["public_key"],
    modified_message,
    data["signature"],
)

wrong_signature = less.verify(
    data["public_key"],
    message,
    data["different_signature"],
)

wrong_public_key = less.verify(
    data["wrong_public_key"],
    message,
    data["signature"],
)

passed = (
    positive == 1
    and wrong_message == 0
    and wrong_signature == 0
    and wrong_public_key == 0
)

print(
    f'Category '
    f'{data["category"]} '
    f'target '
    f'{data["target"]}: '
    f'positive={positive}, '
    f'wrong_message='
    f'{wrong_message}, '
    f'wrong_signature='
    f'{wrong_signature}, '
    f'wrong_public_key='
    f'{wrong_public_key}'
)

raise SystemExit(
    0 if passed else 1
)