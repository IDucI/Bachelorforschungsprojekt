from cross import Cross

c = Cross(path="build", name="libcross_r_sdp_1_fast_6.6.114.so")

inp = [i % 8 for i in range(127)]
out = c.subfunctions.convert_restr_vec_to_fp(inp)

print(out[:16])
