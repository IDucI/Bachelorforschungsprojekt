#include "parameters.h"
#include "CROSS.h"
#include "csprng_hash.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "seedtree.h"
#include "pack_unpack.h"
#include <string.h>
#include <stdio.h>
#include <stdbool.h>

// expand_sk is not exposed in a header, so we declared it here.
#if defined(RSDP)
void expand_sk(FZ_ELEM e_bar[N],
	FP_ELEM V_tr[K][N - K],
	const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
#elif defined(RSDPG)
void expand_sk(FZ_ELEM e_bar[N],
	FZ_ELEM e_G_bar[M],
	FP_ELEM V_tr[K][N - K],
	FZ_ELEM W_mat[M][N - M],
	const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]);
#endif

// Write comma between JSON fields if needed.
static void json_separator(FILE* json, bool last) {
	if (!last) {
		fprintf(json, ",\n");
	}
	else {
		fprintf(json, "\n");
	}
}

/*
 * Write byte array as hexadecimal JSON string.
 * Example: "seed_sk":"12ab"
 * If last is false, append a comma after the JSON field.
 */
static void write_hex(
	FILE* json,
	const char* name,
	const uint8_t* array,
	size_t length,
	bool last) {

	fprintf(json, "\"%s\":\"", name);
	for (size_t i = 0; i < length; i++) {
		fprintf(json, "%02x", array[i]);
	}
	fprintf(json, "\"");
	json_separator(json, last);
}

/*
 * Write FP_ELEM matrix as JSON array.
 * Example: "matrix":[[1,2],[2,1]]
 * If last is false, append a comma after the JSON field.
 */
static void write_fp_matrix(
	FILE* json,
	const char* name,
	size_t rows,
	size_t cols,
	const FP_ELEM array[rows][cols],
	bool comma) {

	fprintf(json, "\"%s\":", name);
	fprintf(json, "[");
	for (size_t i = 0; i < rows; i++) {
		fprintf(json, "[");

		for (size_t j = 0; j < cols; j++) {
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
	json_separator(json, comma);
}

/*
 * Write FZ_ELEM matrix as JSON array.
 * Example: "matrix":[[1,2],[2,1]]
 * If last is false, append a comma after the JSON field.
 */
static void write_fz_matrix(
	FILE* json,
	const char* name,
	size_t rows,
	size_t cols,
	const FZ_ELEM array[rows][cols],
	bool comma) {

	fprintf(json, "\"%s\":", name);
	fprintf(json, "[");
	for (size_t i = 0; i < rows; i++) {
		fprintf(json, "[");

		for (size_t j = 0; j < cols; j++) {
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
	json_separator(json, comma);
}

/*
 * Write FP_ELEM vector as JSON array.
 * Example: "vector":[1,2,3]
 * If last is false, append a comma after the JSON field.
 */
static void write_fp_vector(
	FILE* json,
	const char* name,
	size_t length,
	const FP_ELEM array[length],
	bool comma) {

	fprintf(json, "\"%s\":", name);
	fprintf(json, "[");
	for (size_t i = 0; i < length; i++) {
		fprintf(json, "%u", (unsigned int)array[i]);
		if (i + 1 < length) {
			fprintf(json, ", ");
		}
	}
	fprintf(json, "]");
	json_separator(json, comma);
}

/*
 * Write FZ_ELEM vector as JSON array.
 * Example: "vector":[1,2,3]
 * If last is false, append a comma after the JSON field.
 */
static void write_fz_vector(
	FILE* json,
	const char* name,
	size_t length,
	const FZ_ELEM array[length],
	bool comma) {

	fprintf(json, "\"%s\":", name);
	fprintf(json, "[");
	for (size_t i = 0; i < length; i++) {
		fprintf(json, "%u", (unsigned int)array[i]);
		if (i + 1 < length) {
			fprintf(json, ", ");
		}
	}
	fprintf(json, "]");
	json_separator(json, comma);
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
	FZ_ELEM e_bar[N];
	FP_ELEM V_tr[K][N - K];

#if defined(RSDP)
	expand_sk(e_bar, V_tr, SK.seed_sk);
#elif defined(RSDPG)
	FZ_ELEM e_G_bar[M];
	FZ_ELEM W_mat[M][N - M];
	expand_sk(e_bar, e_G_bar, V_tr, W_mat, SK.seed_sk);
#endif

	uint8_t seed_tree[SEED_LENGTH_BYTES * NUM_NODES_SEED_TREE] = { 0 };
	unsigned char round_seeds[T * SEED_LENGTH_BYTES] = { 0 };
	gen_seed_tree(seed_tree, root_seed, salt);
	seed_leaves(round_seeds, seed_tree);

	FZ_ELEM e_bar_prime[T][N];
	FZ_ELEM v_bar[T][N];
	FZ_ELEM v_bar_pre_norm[T][N];
	FP_ELEM u_prime[T][N];
	FP_ELEM s_prime[T][N - K];

	FP_ELEM v[T][N];
	FP_ELEM u[T][N];

#if defined(RSDP)
	uint8_t cmt_0_i_input[DENSELY_PACKED_FP_SYN_SIZE +
		DENSELY_PACKED_FZ_VEC_SIZE +
		SALT_LENGTH_BYTES];
	const int offset_salt = DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_VEC_SIZE;
#elif defined(RSDPG)
	uint8_t cmt_0_i_input[DENSELY_PACKED_FP_SYN_SIZE +
		DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE +
		SALT_LENGTH_BYTES];
	const int offset_salt = DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE;
#endif

	memcpy(cmt_0_i_input + offset_salt, salt, SALT_LENGTH_BYTES);

#if defined(RSDPG)
	FZ_ELEM e_G_bar_prime[M];
#endif

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
		fz_inf_w_by_fz_matrix(e_bar_prime[i], e_G_bar_prime, W_mat);
		fz_dz_norm_n(e_bar_prime[i]);
#endif
		fz_vec_sub_n(v_bar[i], e_bar, e_bar_prime[i]);
		fz_vec_sub_n(v_bar_pre_norm[i], e_bar, e_bar_prime[i]);

		// FP_ELEM v[N] is declared above as FP_ELEM v[T][N] for testing, so we use v[i].
		convert_restr_vec_to_fp(v[i], v_bar[i]);
		fz_dz_norm_n(v_bar[i]);
		csprng_fp_vec(u_prime[i], &csprng_state);

		// FP_ELEM u[N] is declared above as FP_ELEM u[T][N] for testing, so we use u[i].
		fp_vec_by_fp_vec_pointwise(u[i], v[i], u_prime[i]);
		// FP_ELEM s_prime[N-K] is declared above as FP_ELEM s_prime[T][N - K] for testing, so we use s_prime[i].
		fp_vec_by_fp_matrix(s_prime[i], u[i], V_tr);
		fp_dz_norm_synd(s_prime[i]);
		pack_fp_syn(cmt_0_i_input, s_prime[i]);
	}

	fprintf(json, "{\n");

	write_hex(json, "seed_sk", SK.seed_sk, KEYPAIR_SEED_LENGTH_BYTES, false);
	write_hex(json, "root_seed", root_seed, SEED_LENGTH_BYTES, false);
	write_hex(json, "salt", salt, SALT_LENGTH_BYTES, false);

	write_fz_matrix(json, "v_bar_pre_norm", T, N, v_bar_pre_norm, false);
	write_fz_vector(json, "e_bar", N, e_bar, false);
	write_fp_matrix(json, "V_tr", K, (N - K), V_tr, false);
	write_fz_matrix(json, "v_bar", T, N, v_bar, false);

#if defined(RSDPG)
	write_fz_vector(json, "e_G_bar", M, e_G_bar, false);
	write_fz_matrix(json, "W_mat", M, (N - M), W_mat, false);
#endif

	write_fz_matrix(json, "e_bar_prime", T, N, e_bar_prime, false);
	write_fp_matrix(json, "v", T, N, v, false);
	write_fp_matrix(json, "u_prime", T, N, u_prime, false);
	write_fp_matrix(json, "u", T, N, u, false);
	write_fp_matrix(json, "s_prime", T, (N - K), s_prime, true);

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