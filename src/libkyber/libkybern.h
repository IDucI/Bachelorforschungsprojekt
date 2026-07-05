#include <stdint.h>

#include "api.h"
#include "indcpa.h"
#include "kem.h"

#ifdef __cplusplus
extern "C" {
#endif

// polyvec;
// poly;

// extern const int _KYBER_INDCPA_BYTES;
// extern const int _KYBER_INDCPA_SECRETKEYBYTES;
// extern const int _KYBER_INDCPA_MSGBYTES;

extern const char *kyber_version;

extern const uint32_t kyber_k;
extern const uint32_t kyber_n;
// extern const uint32_t kyber_q;

extern const uint32_t kyber_symbytes;
extern const uint32_t kyber_ssbytes;

// extern const uint32_t kyber_polybytes;
// extern const uint32_t kyber_polyvecbytes;

// extern const uint32_t kyber_eta1;
// extern const uint32_t kyber_polycompressedbytes;
// extern const uint32_t kyber_polyveccompressedbytes;

// extern const uint32_t kyber_eta2;

extern const uint32_t kyber_pke_msgbytes;
extern const uint32_t kyber_pke_publickeybytes;
extern const uint32_t kyber_pke_secretkeybytes;
extern const uint32_t kyber_pke_ciphertextbytes;

extern const uint32_t kyber_kem_publickeybytes;
extern const uint32_t kyber_kem_secretkeybytes;
extern const uint32_t kyber_kem_ciphertextbytes;

void kem_randombytes_init(unsigned char *entropy_input,
                          unsigned char *personalization_string,
                          int security_strength);

/**
 * pk: input public key
 * ct: output ciphertext
 * returns 0 on success
 */

// int kem_keypair(uint8_t pk[kyber_kem_publickeybytes],
//                 uint8_t sk[kyber_kem_secretkeybytes]);
int kem_keypair(uint8_t *pk, uint8_t *sk);

/**
 * ct: output ciphertext
 * ss: output shared secret
 * pk: input public key
 * returns 0 on success
 */
// int kem_enc(uint8_t ct[kyber_kem_ciphertextbytes], uint8_t ss[kyber_ssbytes],
//             const uint8_t pk[kyber_kem_publickeybytes]);
int kem_enc(uint8_t *ct, uint8_t *ss, const uint8_t *pk);

int kem_enc_m(unsigned char *ct, unsigned char *ss, const unsigned char *m,
              const unsigned char *pk);

/**
 * ss: output shared secret
 * ct: input ciphertext
 * pk: input secret key
 * returns 0 on success
 */
// int kem_dec(uint8_t ss[kyber_ssbytes], const uint8_t
// ct[kyber_kem_ciphertextbytes],
//             const uint8_t sk[kyber_kem_secretkeybytes]);
int kem_dec(uint8_t *ss, const uint8_t *ct, const uint8_t *sk);

// void pke_gen_matrix(a, seed, trasposed)
// void gen_matrix(polyvec *a, const uint8_t seed[KYBER_SYMBYTES], int
// transposed);
/**
 * sk: output secret_key
 * pk: output public_key
 */
// void pke_keypair(uint8_t pk[kyber_pke_publickeybytes],
//                  uint8_t sk[kyber_pke_secretkeybytes]);
void pke_keypair(uint8_t *pk, uint8_t *sk);

/**
 * ct: output ciphertext
 * m: input message
 * pk: input public_key
 * coins: input coins
 */
// void pke_enc(uint8_t c[kyber_pke_ciphertextbytes],
//              const uint8_t m[kyber_pke_msgbytes],
//              const uint8_t pk[kyber_pke_publickeybytes],
//              const uint8_t coins[kyber_symbytes]);
void pke_enc(uint8_t *c, const uint8_t *m, const uint8_t *pk,
             const uint8_t *coins);
/**
 * m: output message
 * ct: input ciphertext
 * pk: input secret_key
 */
// void pke_dec(uint8_t m[kyber_pke_msgbytes],
//              const uint8_t c[kyber_pke_ciphertextbytes],
//              const uint8_t sk[kyber_pke_secretkeybytes]);
void pke_dec(uint8_t *m, const uint8_t *c, const uint8_t *sk);

void pke_pack_ciphertext(uint8_t r[], polyvec *b,
                         poly *v); // array param is size of KYBER_INDCPA_BYTES
void pke_unpack_ciphertext(polyvec *b, poly *v,
                           const uint8_t c[]); // array param is size of
                                               // KYBER_INDCPA_BYTES
void pke_unpack_sk(polyvec *sk,
                   const uint8_t packedsk[]); // array param is size of
                                              // KYBER_INDCPA_SECRETKEYBYTES

void pke_polyvec_ntt(polyvec *r);
void pke_polyvec_pointwise_acc_montgomery(poly *r, const polyvec *a,
                                          const polyvec *b);
void pke_basemul(int16_t r[2], const int16_t a[2], const int16_t b[2],
                 int16_t zeta);

void pke_poly_compress(uint8_t msg[KYBER_POLYCOMPRESSEDBYTES], const poly *r);
void pke_poly_basemul_montgomery(poly *r, const poly *a, const poly *b);
void pke_poly_add(poly *r, const poly *a, const poly *b);
void pke_poly_reduce(poly *r);
void pke_poly_invntt_tomont(poly *r);
void pke_poly_sub(poly *r, const poly *a, const poly *b);
void pke_poly_tomsg(uint8_t msg[], const poly *r); // array param is size of
                                                   // KYBER_INDCPA_MSGBYTES

int16_t pke_ntt_fqmul(int16_t a, int16_t b);

int16_t pke_montgomery_reduce(int32_t a);
int16_t pke_barrett_reduce(int16_t a);

void pke_polyvec_test(polyvec *pv);

// ntt.c
extern const int16_t *ntt_zetas;     //[128];
extern const int16_t *ntt_zetas_inv; //[128];

#ifdef __cplusplus
}
#endif
