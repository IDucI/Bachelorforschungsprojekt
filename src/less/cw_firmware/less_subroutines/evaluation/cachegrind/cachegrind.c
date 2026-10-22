#include <stdint.h>
#include <stdio.h>

#include "parameters.h"
#include "fq_arith.h"
#include "codes.h"
#include "monomial_mat.h"
#include "rng.h"

#define ITERATIONS 1000

static volatile uint64_t benchmark_sink;

static void consume(const void *data, size_t length) {
    const uint8_t *bytes = data;
    uint64_t sum = 0;
    for (size_t i = 0; i < length; i++) sum += bytes[i];
    benchmark_sink += sum;
}

static void fill_seed(unsigned char *seed, size_t length) {
    for (size_t i = 0; i < length; i++) seed[i] = (unsigned char)(i * 17u + 31u);
}

#if defined(BENCH_FQ_INV)
static void benchmark(void) {
    volatile FQ_ELEM input = 1;
    for (int i = 0; i < ITERATIONS; i++) {
        input = (FQ_ELEM)(i % (Q - 1) + 1);
        benchmark_sink += fq_inv(input);
    }
}
#elif defined(BENCH_ROW_MUL3)
static void benchmark(void) {
    FQ_ELEM a[N-K], b[N-K], output[N-K];
    for (size_t i = 0; i < N-K; i++) {
        a[i] = (FQ_ELEM)(i % Q);
        b[i] = (FQ_ELEM)((i * 3u + 1u) % Q);
    }
    void (*volatile operation)(FQ_ELEM *, const FQ_ELEM *, const FQ_ELEM *) = row_mul3;
    for (int i = 0; i < ITERATIONS; i++) operation(output, a, b);
    consume(output, sizeof(output));
}
#elif defined(BENCH_GENERATOR_SAMPLE)
static void benchmark(void) {
    unsigned char seed[SEED_LENGTH_BYTES];
    static rref_generator_mat_t output;
    fill_seed(seed, sizeof(seed));
    for (int i = 0; i < ITERATIONS; i++) generator_sample(&output, seed);
    consume(&output, sizeof(output));
}
#elif defined(BENCH_MONOMIAL_SAMPLE_PRIKEY)
static void benchmark(void) {
    unsigned char seed[PRIVATE_KEY_SEED_LENGTH_BYTES];
    static monomial_t output;
    fill_seed(seed, sizeof(seed));
    for (int i = 0; i < ITERATIONS; i++) monomial_sample_prikey(&output, seed);
    consume(&output, sizeof(output));
}
#elif defined(BENCH_GENERATOR_MONOMIAL_MUL)
static void benchmark(void) {
    static generator_mat_t input, output;
    static monomial_t monomial;
    for (size_t i = 0; i < K; i++) {
        for (size_t j = 0; j < N; j++) input.values[i][j] = (FQ_ELEM)((i + j) % Q);
    }
    for (size_t i = 0; i < N; i++) {
        monomial.coefficients[i] = (FQ_ELEM)(i % (Q - 1) + 1);
        monomial.permutation[i] = (POSITION_T)(N - i - 1);
    }
    for (int i = 0; i < ITERATIONS; i++) generator_monomial_mul(&output, &input, &monomial);
    consume(&output, sizeof(output));
}
#else
#error "Select one supported BENCH_* definition"
#endif

int main(void) {
    unsigned char seed[48];
    fill_seed(seed, sizeof(seed));
    initialize_csprng(&platform_csprng_state, seed, sizeof(seed));
    benchmark();
    printf("benchmark_sink=%llu\n", (unsigned long long)benchmark_sink);
    return 0;
}