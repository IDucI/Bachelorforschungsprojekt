#include "parameters.h"
#include "CROSS.h"
#include "csprng_hash.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "seedtree.h"
#include "pack_unpack.h"
#include <string.h>
#include <stdio.h>

#if defined(RSDP)
void expand_sk(FZ_ELEM e_bar[N],
	FP_ELEM V_tr[K][N - K],
	const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
#elif defined(RSDPG)
#error "RSDPG not implemented yet"
#endif

// Write byte array as hexadecimal string
static void write_hex(
	FILE* json,
	const uint8_t* array,
	size_t length) {

	for (size_t i = 0; i < length; i++) {
		fprintf(json, "%02x", array[i]);
	}
}

// Write FZ_ELEM array as JSON array
static void write_fz_2d_array(
	FILE* json,
	size_t rows,
	size_t cols,
	const FZ_ELEM array[rows][cols]) {

	fprintf(json, "[");

	for (size_t i = 0; i < rows; i++){
		fprintf(json, "[");

		for (size_t j = 0; j < cols; j++){
			fprintf(json, "%u", (unsigned int)array[i][j]);
			if (j + 1 < cols) {
				fprintf(json, ", ");
			}
		}

		fprintf(json, "]");
		if (i + 1 < rows) { 
			fprintf(json, ", "); 
		}
	}

	fprintf(json, "]");
}

// v_bar: output v_bar vector for each round i
static void calculate_v_bar(
	FZ_ELEM v_bar[T][N],
	const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES],
	const uint8_t root_seed[SEED_LENGTH_BYTES],
	const uint8_t salt[SALT_LENGTH_BYTES]) {

	FZ_ELEM e_bar[N];
	FP_ELEM V_tr[K][N - K];
	expand_sk(e_bar, V_tr, seed_sk);

	uint8_t seed_tree[SEED_LENGTH_BYTES * NUM_NODES_SEED_TREE] = { 0 };
	unsigned char round_seeds[T * SEED_LENGTH_BYTES] = { 0 };
	gen_seed_tree(seed_tree, root_seed, salt);
	seed_leaves(round_seeds, seed_tree);

	FZ_ELEM e_bar_prime[T][N];

	CSPRNG_STATE_T csprng_state;
	for (uint16_t i = 0; i < T; i++) {
		uint8_t csprng_input[SEED_LENGTH_BYTES + SALT_LENGTH_BYTES];
		memcpy(csprng_input, round_seeds + SEED_LENGTH_BYTES * i, SEED_LENGTH_BYTES);
		memcpy(csprng_input + SEED_LENGTH_BYTES, salt, SALT_LENGTH_BYTES);

		uint16_t domain_sep_csprng = CSPRNG_DOMAIN_SEP_CONST + i + (2 * T - 1);

		csprng_initialize(&csprng_state,
			csprng_input,
			SEED_LENGTH_BYTES + SALT_LENGTH_BYTES,
			domain_sep_csprng);

#if defined(RSDP)
		csprng_fz_vec(e_bar_prime[i], &csprng_state);
#elif defined(RSDPG)
		csprng_fz_inf_w(e_G_bar_prime, &csprng_state);
#endif
		fz_vec_sub_n(v_bar[i], e_bar, e_bar_prime[i]);
	}
}

int main(void) {
	// Create JSON output file for current variant
	char filename[100];
	snprintf(filename, sizeof(filename), "%s.json", ALG_VERSION);
	FILE* json = fopen(filename, "w");

	// Generate random root seed and salt for both C and Python calculations.
	sk_t SK;
	pk_t PK;
	CROSS_keygen(&SK, &PK);

	uint8_t root_seed[SEED_LENGTH_BYTES];
	uint8_t salt[SALT_LENGTH_BYTES];
	randombytes(root_seed, SEED_LENGTH_BYTES);
	randombytes(salt, SALT_LENGTH_BYTES);

	// Calculate v_bar for comparison with the Python implementation.
	FZ_ELEM v_bar[T][N];
	calculate_v_bar(v_bar, SK.seed_sk, root_seed, salt);
	fprintf(json, "{\n");

	fprintf(json, "\"seed_sk\":\"");
	write_hex(json, SK.seed_sk, KEYPAIR_SEED_LENGTH_BYTES);
	fprintf(json, "\",\n");

	fprintf(json, "\"root_seed\":\"");
	write_hex(json, root_seed, SEED_LENGTH_BYTES);
	fprintf(json, "\",\n");

	fprintf(json, "\"salt\":\"");
	write_hex(json, salt, SALT_LENGTH_BYTES);
	fprintf(json, "\",\n");

	fprintf(json, "\"v_bar\":");
	write_fz_2d_array(json, T, N, v_bar);
	fprintf(json, "\n");

	fprintf(json, "}\n");
	fclose(json);

	for (size_t j = 0; j < N; j++) {
		printf("%u", (unsigned int)v_bar[0][j]);

		if (j + 1 < N) {
			printf(", ");
		}
	}
	printf("]\033[0m\n");
	return 0;
}