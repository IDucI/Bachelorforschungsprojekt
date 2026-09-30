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
#include <assert.h>
#include <stdlib.h>

#define GREEN "\033[0;32m"
#define RED   "\033[0;31m"
#define RESET "\033[0m"

static uint8_t* read_hex(const char **start, const char* name, size_t* out_len ){
	const char* field = strstr(*start, name);

	const char* hex = strchr(field, ':');
	hex = strchr(hex, '"') + 1;

	const char* end = strchr(hex, '"');

	*out_len = (size_t)(end - hex) / 2;

	uint8_t* bytes = malloc(*out_len);

	for (size_t i = 0; i < *out_len; i++){
		unsigned int byte;
		sscanf(hex + 2 * i, "%2x", &byte);
		bytes[i] = (uint8_t)byte;
	}

	*start = end + 1;
	return bytes;
}

int main(void) {
	FILE* json = fopen("c_verify_py.json", "r");

	if (json == NULL) {
		perror("Could not open JSON file");
		return 1;
	}

	fseek(json, 0, SEEK_END);
	long file_size = ftell(json);
	rewind(json);

	char* json_data = malloc((size_t)file_size + 1);
	
	fread(json_data, 1, (size_t)file_size, json);
	json_data[file_size] = '\0';

	fclose(json);

	const char* start = strstr(json_data, ALG_VERSION);

	start = strstr(start, "\"high_level_api\"");

	for (size_t i = 0; i < 1; i++){
		size_t message_len;
		size_t public_key_len;
		size_t signature_len;

		uint8_t* message = read_hex(&start, "\"message\"", &message_len);
		uint8_t* public_key = read_hex(&start, "\"public_key\"", &public_key_len);
		uint8_t* signature = read_hex(&start, "\"signature\"", &signature_len);

		pk_t pk;
		CROSS_sig_t sig;

		memcpy(&pk, public_key, sizeof(pk));
		memcpy(&sig, signature, sizeof(sig));

		int success = CROSS_verify(&pk, (const char*)message, message_len, &sig);
		if (success == 1) {
			printf(GREEN "High-level API: PASS\n" RESET);
		}
		else {
			printf(RED "High-level API: FAIL\n" RESET);
			return 1;
		}

		free(message);
		free(public_key);
		free(signature);
	}

	start = strstr(start, "\"calculation_api\"");

	for (size_t i = 0; i < 1; i++) {
		size_t message_len;
		size_t public_key_len;
		size_t signature_len;

		uint8_t* message = read_hex(&start, "\"message\"", &message_len);
		uint8_t* public_key = read_hex(&start, "\"public_key\"", &public_key_len);
		uint8_t* signature = read_hex(&start, "\"signature\"", &signature_len);

		pk_t pk;
		CROSS_sig_t sig;

		assert(public_key_len == sizeof(pk));
		assert(signature_len == sizeof(sig));

		memcpy(&pk, public_key, sizeof(pk));
		memcpy(&sig, signature, sizeof(sig));

		int success = CROSS_verify(&pk, (const char*)message, message_len, &sig);
		if (success == 1) {
			printf(GREEN "Calculation API: PASS\n" RESET);
		}
		else {
			printf(RED "Calculation API: FAIL\n" RESET);
			return 1;
		}

		free(message);
		free(public_key);
		free(signature);
	}

	free(json_data);
	return 0;
}