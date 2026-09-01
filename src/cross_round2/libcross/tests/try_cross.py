from cross import Cross, Calculations

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

calc = Calculations(c.subfunctions)

seed_sk = bytes(
    j for j in range(c.params.keypair_seed_length_bytes)
)

root_seed = bytes(
    0x40 + j for j in range(c.params.seed_length_bytes)
)

salt = bytes(
    0x80 + j for j in range(c.params.salt_length_bytes)
)

v_bar_0 = calc.v_bar_i(
    seed_sk,
    root_seed,
    salt,
    0
)

print("v_bar[0] =", v_bar_0)