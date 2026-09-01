#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define RSDP
#define CATEGORY_1
#define SIG_SIZE

#include "parameters.h"
#include "csprng_hash.h"
#include "fp_arith.h"
#include "restr_arith.h"
#include "seedtree.h"

void expand_sk(
	FZ_ELEM e_bar[N],
	FP_ELEM V_tr[K][N - K],
	const uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES]
);

int main(void)
{
	uint8_t seed_sk[KEYPAIR_SEED_LENGTH_BYTES];
	uint8_t root_seed[SEED_LENGTH_BYTES];
	uint8_t salt[SALT_LENGTH_BYTES];

	for (size_t j = 0; j < KEYPAIR_SEED_LENGTH_BYTES; j++) {
		seed_sk[j] = (uint8_t)j;
	}

	for (size_t j = 0; j < SEED_LENGTH_BYTES; j++) {
		root_seed[j] = (uint8_t)(0x40 + j);
	}

	for (size_t j = 0; j < SALT_LENGTH_BYTES; j++) {
		salt[j] = (uint8_t)(0x80 + j);
	}

	FZ_ELEM e_bar[N];
	FP_ELEM V_tr[K][N - K];

	expand_sk(e_bar, V_tr, seed_sk);

	uint8_t seed_tree[
		NUM_NODES_SEED_TREE * SEED_LENGTH_BYTES
	] = { 0 };

		gen_seed_tree(
			seed_tree,
			root_seed,
			salt
		);

		uint8_t round_seeds[
			T * SEED_LENGTH_BYTES
		] = { 0 };

			seed_leaves(
				round_seeds,
				seed_tree
			);

			const uint16_t i = 0;

			uint8_t csprng_input[
				SEED_LENGTH_BYTES + SALT_LENGTH_BYTES
			];

			memcpy(
				csprng_input,
				round_seeds + (SEED_LENGTH_BYTES * i),
				SEED_LENGTH_BYTES
			);

			memcpy(
				csprng_input + SEED_LENGTH_BYTES,
				salt,
				SALT_LENGTH_BYTES
			);

			const uint16_t domain_sep_csprng =
				CSPRNG_DOMAIN_SEP_CONST
				+ i
				+ (2 * T - 1);

			CSPRNG_STATE_T csprng_state;

			csprng_initialize(
				&csprng_state,
				csprng_input,
				SEED_LENGTH_BYTES + SALT_LENGTH_BYTES,
				domain_sep_csprng
			);

			FZ_ELEM e_bar_prime[N];

			csprng_fz_vec(
				e_bar_prime,
				&csprng_state
			);

			FZ_ELEM v_bar[N];

			fz_vec_sub_n(
				v_bar,
				e_bar,
				e_bar_prime
			);

			printf("v_bar[0] = [");

			for (size_t j = 0; j < N; j++) {
				printf("%u", (unsigned int)v_bar[j]);

				if (j + 1 < N) {
					printf(", ");
				}
			}

			printf("]\n");

			return 0;
}