from cross import Cross


c = Cross(
    path="build",
    algorithm="RSDPG",
    category=3,
    optimization="fast",
)

inp = [i % c.params.z for i in range(c.params.n)]
out = c.subfunctions.convert_restr_vec_to_fp(inp)

print(out[:16])

sk, pk = c.keygen()

print("SK length:", len(sk))
print("PK length", len(pk))

message = list(b"Hello Cross")
signature = c.sign(sk, message)
result = c.verify(pk, message, signature)

print ("Verify:", result)

c = Cross(
    path="build",
    algorithm="RSDP",
    category=1,
    optimization="balanced",
)

