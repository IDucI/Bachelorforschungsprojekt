from less import Less


# category=None and target=None select the official toy parameter set.
less = Less(path="build")

n = less.params.n
k = less.params.k
q = less.params.q

# K x N toy generator matrix in row-major order.
generator = [(row * n + col) % q for row in range(k) for col in range(n)]

# Valid non-zero coefficients and a simple reverse permutation.
coefficients = [(index % (q - 1)) + 1 for index in range(n)]
permutation = list(reversed(range(n)))

result = less.subfunctions.generator_monomial_mul(
    generator,
    coefficients,
    permutation,
)

print("variant         :", less.params.version)
print("input first row :", generator[:n])
print("result first row:", result[:n])
