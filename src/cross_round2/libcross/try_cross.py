from cross import Cross


c = Cross(
    path="build",
    algorithm="RSDP",
    category=1,
    optimization="fast",
)

inp = [i % c.params.z for i in range(c.params.n)]
out = c.subfunctions.convert_restr_vec_to_fp(inp)

print(out[:16])