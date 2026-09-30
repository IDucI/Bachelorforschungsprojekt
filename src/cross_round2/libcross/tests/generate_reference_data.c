#include "parameters.h"
#include "CROSS.h"
#include "csprng_hash.h"
#include "fp_arith.h"
#include "merkle_tree.h"
#include "restr_arith.h"
#include "seedtree.h"
#include "pack_unpack.h"
#include <string.h>
#include <stdio.h>
#include <stdbool.h>
#include <assert.h>

uint8_t root_seed_json[SEED_LENGTH_BYTES];
uint8_t salt_json[SALT_LENGTH_BYTES];

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

void sign(const sk_t* SK,
	const char* const m,
	const uint64_t mlen,
	CROSS_sig_t* sig) {
	/* Wipe any residual information in the sig structure allocated by the
	 * caller */
	memset(sig, 0, sizeof(CROSS_sig_t));
	/* Key material expansion */
	FP_ELEM V_tr[K][N - K];
	FZ_ELEM e_bar[N];
#if defined(RSDP)
	expand_sk(e_bar, V_tr, SK->seed_sk);
#elif defined(RSDPG)
	FZ_ELEM e_G_bar[M];
	FZ_ELEM W_mat[M][N - M];
	expand_sk(e_bar, e_G_bar, V_tr, W_mat, SK->seed_sk);
#endif

	uint8_t root_seed[SEED_LENGTH_BYTES];
	randombytes(root_seed, SEED_LENGTH_BYTES);
	randombytes(sig->salt, SALT_LENGTH_BYTES);
	memcpy(root_seed_json, root_seed, SEED_LENGTH_BYTES);
	memcpy(salt_json, sig->salt, SALT_LENGTH_BYTES);
#if defined(NO_TREES)
	unsigned char round_seeds[T * SEED_LENGTH_BYTES] = { 0 };
	seed_leaves(round_seeds, root_seed, sig->salt);
#else
	uint8_t seed_tree[SEED_LENGTH_BYTES * NUM_NODES_SEED_TREE] = { 0 };
	gen_seed_tree(seed_tree, root_seed, sig->salt);
	unsigned char round_seeds[T * SEED_LENGTH_BYTES] = { 0 };
	seed_leaves(round_seeds, seed_tree);
#endif

	FZ_ELEM e_bar_prime[T][N];
	FZ_ELEM v_bar[T][N];
	FP_ELEM u_prime[T][N];
	FP_ELEM s_prime[N - K];

#if defined(RSDP)
	uint8_t cmt_0_i_input[DENSELY_PACKED_FP_SYN_SIZE +
		DENSELY_PACKED_FZ_VEC_SIZE +
		SALT_LENGTH_BYTES];
	const int offset_salt = DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_VEC_SIZE;
#elif defined(RSDPG)
	FZ_ELEM e_G_bar_prime[M];
	FZ_ELEM v_G_bar[T][M];
	uint8_t cmt_0_i_input[DENSELY_PACKED_FP_SYN_SIZE +
		DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE +
		SALT_LENGTH_BYTES];
	const int offset_salt = DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE;
#endif
	/* cmt_0_i_input is syndrome || v_bar resp. v_G_bar || salt ; place salt at the end */
	memcpy(cmt_0_i_input + offset_salt, sig->salt, SALT_LENGTH_BYTES);

	uint8_t cmt_1_i_input[SEED_LENGTH_BYTES +
		SALT_LENGTH_BYTES];
	/* cmt_1_i_input is concat(seed,salt,round index + 2T-1) */
	memcpy(cmt_1_i_input + SEED_LENGTH_BYTES, sig->salt, SALT_LENGTH_BYTES);

	uint8_t cmt_0[T][HASH_DIGEST_LENGTH] = { 0 };
	uint8_t cmt_1[T * HASH_DIGEST_LENGTH] = { 0 };

	CSPRNG_STATE_T csprng_state;
	for (uint16_t i = 0; i < T; i++) {
		/* CSPRNG is fed with concat(seed,salt,round index) represented
		 * as a 2 bytes little endian unsigned integer */
		uint8_t csprng_input[SEED_LENGTH_BYTES + SALT_LENGTH_BYTES];
		memcpy(csprng_input, round_seeds + SEED_LENGTH_BYTES * i, SEED_LENGTH_BYTES);
		memcpy(csprng_input + SEED_LENGTH_BYTES, sig->salt, SALT_LENGTH_BYTES);

		uint16_t domain_sep_csprng = CSPRNG_DOMAIN_SEP_CONST + i + (2 * T - 1);
		/* expand seed[i] into seed_e and seed_u */
		csprng_initialize(&csprng_state,
			csprng_input,
			SEED_LENGTH_BYTES + SALT_LENGTH_BYTES,
			domain_sep_csprng);
		/* expand e_bar_prime */
#if defined(RSDP)
		csprng_fz_vec(e_bar_prime[i], &csprng_state);
#elif defined(RSDPG)
		csprng_fz_inf_w(e_G_bar_prime, &csprng_state);
		fz_vec_sub_m(v_G_bar[i], e_G_bar, e_G_bar_prime);
		fz_dz_norm_m(v_G_bar[i]);
		fz_inf_w_by_fz_matrix(e_bar_prime[i], e_G_bar_prime, W_mat);

		fz_dz_norm_n(e_bar_prime[i]);
#endif
		fz_vec_sub_n(v_bar[i], e_bar, e_bar_prime[i]);

		FP_ELEM v[N];
		convert_restr_vec_to_fp(v, v_bar[i]);

		fz_dz_norm_n(v_bar[i]);
		/* expand u_prime */
		csprng_fp_vec(u_prime[i], &csprng_state);

		FP_ELEM u[N];
		fp_vec_by_fp_vec_pointwise(u, v, u_prime[i]);
		fp_vec_by_fp_matrix(s_prime, u, V_tr);
		fp_dz_norm_synd(s_prime);

		/* cmt_0_i_input contains s_prime || v_bar resp. v_G_bar || salt */
		pack_fp_syn(cmt_0_i_input, s_prime);

#if defined(RSDP)
		pack_fz_vec(cmt_0_i_input + DENSELY_PACKED_FP_SYN_SIZE, v_bar[i]);
#elif defined(RSDPG)
		pack_fz_rsdp_g_vec(cmt_0_i_input + DENSELY_PACKED_FP_SYN_SIZE, v_G_bar[i]);
#endif

		/* Fixed endianness marshalling of round counter */
		uint16_t domain_sep_hash = HASH_DOMAIN_SEP_CONST + i + (2 * T - 1);

		hash(cmt_0[i], cmt_0_i_input, sizeof(cmt_0_i_input), domain_sep_hash);
		memcpy(cmt_1_i_input,
			round_seeds + SEED_LENGTH_BYTES * i,
			SEED_LENGTH_BYTES);

		hash(&cmt_1[i * HASH_DIGEST_LENGTH], cmt_1_i_input, sizeof(cmt_1_i_input), domain_sep_hash);
	}

	/* vector containing d_0 and d_1 from spec */
	uint8_t digest_cmt0_cmt1[2 * HASH_DIGEST_LENGTH];

#if defined(NO_TREES)
	tree_root(digest_cmt0_cmt1, cmt_0);
#else
	uint8_t merkle_tree_0[NUM_NODES_MERKLE_TREE * HASH_DIGEST_LENGTH];
	tree_root(digest_cmt0_cmt1, merkle_tree_0, cmt_0);
#endif
	hash(digest_cmt0_cmt1 + HASH_DIGEST_LENGTH, cmt_1, sizeof(cmt_1), HASH_DOMAIN_SEP_CONST);
	hash(sig->digest_cmt, digest_cmt0_cmt1, sizeof(digest_cmt0_cmt1), HASH_DOMAIN_SEP_CONST);

	/* first challenge extraction */
	uint8_t digest_msg_cmt_salt[2 * HASH_DIGEST_LENGTH + SALT_LENGTH_BYTES];

	/* place digest_msg at the beginning of the input of the hash generating digest_chall_1 */
	hash(digest_msg_cmt_salt, (uint8_t*)m, mlen, HASH_DOMAIN_SEP_CONST);
	memcpy(digest_msg_cmt_salt + HASH_DIGEST_LENGTH, sig->digest_cmt, HASH_DIGEST_LENGTH);
	memcpy(digest_msg_cmt_salt + 2 * HASH_DIGEST_LENGTH, sig->salt, SALT_LENGTH_BYTES);

	uint8_t digest_chall_1[HASH_DIGEST_LENGTH];
	hash(digest_chall_1, digest_msg_cmt_salt, sizeof(digest_msg_cmt_salt), HASH_DOMAIN_SEP_CONST);

	// Domain separation unique for expanding chall_1
	const uint16_t dsc_csprng_chall_1 = CSPRNG_DOMAIN_SEP_CONST + (3 * T - 1);

	FP_ELEM chall_1[T];
	csprng_initialize(&csprng_state, digest_chall_1, sizeof(digest_chall_1), dsc_csprng_chall_1);
	csprng_fp_vec_chall_1(chall_1, &csprng_state);

	/* Computation of the first round of responses */
	FP_ELEM y[T][N];
	for (int i = 0; i < T; i++) {
		fp_vec_by_restr_vec_scaled(y[i],
			e_bar_prime[i],
			chall_1[i],
			u_prime[i]);
		fp_dz_norm(y[i]);
	}
	/* y vectors are packed before being hashed */
	uint8_t y_digest_chall_1[T * DENSELY_PACKED_FP_VEC_SIZE + HASH_DIGEST_LENGTH];

	for (int x = 0; x < T; x++) {
		pack_fp_vec(y_digest_chall_1 + (x * DENSELY_PACKED_FP_VEC_SIZE), y[x]);
	}
	/* Second challenge extraction */
	memcpy(y_digest_chall_1 + T * DENSELY_PACKED_FP_VEC_SIZE, digest_chall_1, HASH_DIGEST_LENGTH);

	hash(sig->digest_chall_2, y_digest_chall_1, sizeof(y_digest_chall_1), HASH_DOMAIN_SEP_CONST);

	uint8_t chall_2[T] = { 0 };
	expand_digest_to_fixed_weight(chall_2, sig->digest_chall_2);

	/* Computation of the second round of responses */
#if defined(NO_TREES)
	tree_proof(sig->proof, cmt_0, chall_2);
	seed_path(sig->path, round_seeds, chall_2);
#else
	tree_proof(sig->proof, merkle_tree_0, chall_2);
	seed_path(sig->path, seed_tree, chall_2);
#endif

	int published_rsps = 0;
	for (int i = 0; i < T; i++) {
		if (chall_2[i] == 0) {
			assert(published_rsps < T - W);
			pack_fp_vec(sig->resp_0[published_rsps].y, y[i]);
#if defined(RSDP)
			pack_fz_vec(sig->resp_0[published_rsps].v_bar, v_bar[i]);
#elif defined(RSDPG)
			pack_fz_rsdp_g_vec(sig->resp_0[published_rsps].v_G_bar, v_G_bar[i]);
#endif
			memcpy(sig->resp_1[published_rsps], &cmt_1[i * HASH_DIGEST_LENGTH], HASH_DIGEST_LENGTH);
			published_rsps++;
		}
	}
}

int main(void) {
	// Create JSON output file for current variant
	char filename[100];
	snprintf(filename, sizeof(filename), "%s.json", ALG_VERSION);
	FILE* json = fopen(filename, "w");

	if (json == NULL) {
		perror("Could not open output file");
		return 1;
	}

	// Generate random root seed and salt for both C and Python calculations.
	sk_t SK;
	pk_t PK;
	CROSS_keygen(&SK, &PK);

	uint8_t m[100];
	const uint64_t mlen = sizeof(m);
	randombytes(m, mlen);
	CROSS_sig_t sig;

	sign(&SK, (const char *)m, mlen, &sig);

	int valid = CROSS_verify(&PK, (const char*)m, mlen, &sig);
	printf("verify: %s\n", valid ? "OK" : "FAILED");
	if (!valid) {
		return 1;
	}

	fprintf(json, "{\n");
	write_hex(json, "m", m, sizeof(m), false);
	write_hex(json, "seed_sk", SK.seed_sk, KEYPAIR_SEED_LENGTH_BYTES, false);
	write_hex(json, "public_key", (const uint8_t*)&PK, sizeof(PK), false);
	write_hex(json, "root_seed", root_seed_json, SEED_LENGTH_BYTES, false);
	write_hex(json, "salt", salt_json, SALT_LENGTH_BYTES, false);
	write_fz_vector(json, "signature", sizeof(sig), (const uint8_t*)&sig, true);

	fprintf(json, "}\n");
	fclose(json);
	return 0;
}