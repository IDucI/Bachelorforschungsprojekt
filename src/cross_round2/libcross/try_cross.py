from cross import Cross


c = Cross(
    path="build",
    algorithm="RSDP",
    category=1,
    optimization="small",
)

#inp = [i % c.params.z for i in range(c.params.n)]
#out = c.subfunctions.convert_restr_vec_to_fp(inp)

#print(out[:16])

print("SIG size:", c.sig_size)

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

