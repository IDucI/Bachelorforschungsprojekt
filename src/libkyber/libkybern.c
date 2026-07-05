#include "libkybern.h"

#ifdef __cplusplus
extern "C" {
#endif

// #include "api.h"
// #include "indcpa.h"
#include "reduce.h"
#include "symmetric.h"

#include <string.h>

#ifndef KYBER_SSBYTES
#define KYBER_SSBYTES 32 /* size in bytes of shared key */
#endif
#ifndef CRYPTO_SECRETKEYBYTES
#define CRYPTO_SECRETKEYBYTES KYBER_SECRETKEYBYTES
#endif
#ifndef CRYPTO_PUBLICKEYBYTES
#define CRYPTO_PUBLICKEYBYTES KYBER_PUBLICKEYBYTES
#endif
#ifndef CRYPTO_CIPHERTEXTBYTES
#define CRYPTO_CIPHERTEXTBYTES KYBER_CIPHERTEXTBYTES
#endif
#ifndef CRYPTO_BYTES
#define CRYPTO_BYTES KYBER_SSBYTES
#endif

// #ifdef KYBER_NAMESPACE
// #if KYBER_NAMESPACE == pqcrystals_kyber512_ref_
// #error "FAILED"
// #endif
// #endif
// const int _KYBER_INDCPA_BYTES = KYBER_INDCPA_BYTES;
// const int _KYBER_INDCPA_SECRETKEYBYTES = KYBER_INDCPA_SECRETKEYBYTES;
// const int _KYBER_INDCPA_MSGBYTES = KYBER_INDCPA_MSGBYTES;

const char *kyber_version = ALG_VERSION;

const uint32_t kyber_k = KYBER_K;
const uint32_t kyber_n = KYBER_N;
const uint32_t kyber_q = KYBER_Q;

const uint32_t kyber_symbytes = KYBER_SYMBYTES;
const uint32_t kyber_ssbytes = KYBER_SSBYTES;

const uint32_t kyber_polybytes = KYBER_POLYBYTES;
const uint32_t kyber_polyvecbytes = KYBER_POLYVECBYTES;
//
// const uint32_t kyber_eta1 = KYBER_ETA1;
const uint32_t kyber_polycompressedbytes = KYBER_POLYCOMPRESSEDBYTES;
const uint32_t kyber_polyveccompressedbytes = KYBER_POLYVECCOMPRESSEDBYTES;
//
// const uint32_t kyber_eta2 = KYBER_ETA2;

const uint32_t kyber_pke_msgbytes = KYBER_INDCPA_MSGBYTES;
const uint32_t kyber_pke_publickeybytes = KYBER_INDCPA_PUBLICKEYBYTES;
const uint32_t kyber_pke_secretkeybytes = KYBER_INDCPA_SECRETKEYBYTES;
const uint32_t kyber_pke_ciphertextbytes = KYBER_INDCPA_BYTES;

const uint32_t kyber_kem_publickeybytes = KYBER_PUBLICKEYBYTES;
const uint32_t kyber_kem_secretkeybytes = KYBER_SECRETKEYBYTES;
const uint32_t kyber_kem_ciphertextbytes = KYBER_CIPHERTEXTBYTES;

const uint32_t kyber_MONT = MONT;
const uint32_t kyber_QINV = QINV;

extern void (*c_randombytes_init)(unsigned char *entropy_input,
                                  unsigned char *personalization_string,
                                  int security_strength);
void kem_randombytes_init(unsigned char *entropy_input,
                          unsigned char *personalization_string,
                          int security_strength) {
  c_randombytes_init(entropy_input, personalization_string, security_strength);
}

/**
 * pk: input public key
 * ct: output ciphertext
 * returns 0 on success
 */

int kem_keypair(uint8_t pk[CRYPTO_PUBLICKEYBYTES],
                uint8_t sk[CRYPTO_SECRETKEYBYTES]) {
  return crypto_kem_keypair(pk, sk);
}

/**
 * ct: output ciphertext
 * ss: output shared secret
 * pk: input public key
 * returns 0 on success
 */
int kem_enc(uint8_t ct[CRYPTO_CIPHERTEXTBYTES], uint8_t ss[CRYPTO_BYTES],
            const uint8_t pk[CRYPTO_PUBLICKEYBYTES]) {
  return crypto_kem_enc(ct, ss, pk);
}
/**
 * ss: output shared secret
 * ct: input ciphertext
 * pk: input secret key
 * returns 0 on success
 */
int kem_dec(uint8_t ss[CRYPTO_BYTES], const uint8_t ct[CRYPTO_CIPHERTEXTBYTES],
            const uint8_t sk[CRYPTO_SECRETKEYBYTES]) {
  return crypto_kem_dec(ss, ct, sk);
}

// void pke_gen_matrix(a, seed, trasposed)
// void gen_matrix(polyvec *a, const uint8_t seed[KYBER_SYMBYTES], int
// transposed);
/**
 * sk: output secret_key
 * pk: output public_key
 */
void pke_keypair(uint8_t pk[KYBER_INDCPA_PUBLICKEYBYTES],
                 uint8_t sk[KYBER_INDCPA_SECRETKEYBYTES]) {
  indcpa_keypair(pk, sk);
}

/**
 * ct: output ciphertext
 * m: input message
 * pk: input public_key
 * coins: input coins
 */
void pke_enc(uint8_t c[KYBER_INDCPA_BYTES],
             const uint8_t m[KYBER_INDCPA_MSGBYTES],
             const uint8_t pk[KYBER_INDCPA_PUBLICKEYBYTES],
             const uint8_t coins[KYBER_SYMBYTES]) {
  indcpa_enc(c, m, pk, coins);
}
/**
 * m: output message
 * ct: input ciphertext
 * pk: input secret_key
 */
void pke_dec(uint8_t m[KYBER_INDCPA_MSGBYTES],
             const uint8_t c[KYBER_INDCPA_BYTES],
             const uint8_t sk[KYBER_INDCPA_SECRETKEYBYTES]) {
  indcpa_dec(m, c, sk);
}

// void pke_polyvec_reduce(polyvec *r){
//   polyvec_reduce(r);
// }

// decryption
// unpack_ciphertext
// unpack_sk
extern void (*c_pack_ciphertext)(uint8_t r[KYBER_INDCPA_BYTES], polyvec *b,
                                 poly *v);
extern void (*c_unpack_ciphertext)(polyvec *b, poly *v,
                                   const uint8_t c[KYBER_INDCPA_BYTES]);
extern void (*c_unpack_sk)(polyvec *sk,
                           const uint8_t packedsk[KYBER_INDCPA_SECRETKEYBYTES]);
extern void (*c_polyvec_ntt)(polyvec *r);
extern void (*c_polyvec_pointwise_acc_montgomery)(poly *r, const polyvec *a,
                                                  const polyvec *b);
extern void (*c_basemul)(int16_t r[2], const int16_t a[2], const int16_t b[2],
                         int16_t zeta);

extern void (*c_poly_compress)(uint8_t r[KYBER_POLYCOMPRESSEDBYTES],
                               const poly *a);
extern void (*c_poly_decompress)(const poly *r,
                                 uint8_t a[KYBER_POLYCOMPRESSEDBYTES]);
extern void (*c_poly_tobytes)(uint8_t r[KYBER_POLYBYTES], const poly *a);
extern void (*c_poly_frombytes)(poly *r, const uint8_t a[KYBER_POLYBYTES]);
extern void (*c_poly_frommsg)(poly *r,
                              const uint8_t msg[KYBER_INDCPA_MSGBYTES]);
extern void (*c_poly_tomsg)(uint8_t msg[KYBER_INDCPA_MSGBYTES], const poly *r);
extern void (*c_poly_basemul_montgomery)(poly *r, const poly *a, const poly *b);
extern void (*c_poly_add)(poly *r, const poly *a, const poly *b);
extern void (*c_poly_reduce)(poly *r);
extern void (*c_poly_invntt_tomont)(poly *r);
extern void (*c_poly_sub)(poly *r, const poly *a, const poly *b);

extern int16_t (*c_ntt_fqmul)(int16_t a, int16_t b);
extern int16_t (*c_montgomery_reduce)(int32_t a);
extern int16_t (*c_barrett_reduce)(int16_t a);

void pke_pack_ciphertext(uint8_t r[KYBER_INDCPA_BYTES], polyvec *b, poly *v) {
  c_pack_ciphertext(r, b, v);
}
void pke_unpack_ciphertext(polyvec *b, poly *v,
                           const uint8_t c[KYBER_INDCPA_BYTES]) {
  c_unpack_ciphertext(b, v, c);
}
void pke_unpack_sk(polyvec *sk,
                   const uint8_t packedsk[KYBER_INDCPA_SECRETKEYBYTES]) {
  c_unpack_sk(sk, packedsk);
}

void pke_polyvec_ntt(polyvec *r) { c_polyvec_ntt(r); }
void pke_polyvec_pointwise_acc_montgomery(poly *r, const polyvec *a,
                                          const polyvec *b) {
  c_polyvec_pointwise_acc_montgomery(r, a, b);
}
void pke_basemul(int16_t r[2], const int16_t a[2], const int16_t b[2],
                 int16_t zeta) {
  c_basemul(r, a, b, zeta);
}

void pke_poly_compress(uint8_t msg[KYBER_POLYCOMPRESSEDBYTES], const poly *r) {
  c_poly_compress(msg, r);
}
void pke_poly_decompress(const poly *r,
                         uint8_t msg[KYBER_POLYCOMPRESSEDBYTES]) {
  c_poly_decompress(r, msg);
}
void pke_poly_tobytes(uint8_t r[KYBER_POLYBYTES], const poly *a) {
  c_poly_tobytes(r, a);
  // void poly_tobytes(uint8_t r[KYBER_POLYBYTES], const poly *a)
}
void pke_poly_frombytes(poly *r, const uint8_t a[KYBER_POLYBYTES]) {
  c_poly_frombytes(r, a);
  // void poly_frombytes(poly *r, const uint8_t a[KYBER_POLYBYTES])
}
void pke_poly_frommsg(poly *r, const uint8_t msg[KYBER_INDCPA_MSGBYTES]) {
  c_poly_frommsg(r, msg);
  // void poly_frommsg(poly *r, const uint8_t msg[KYBER_INDCPA_MSGBYTES])
}
void pke_poly_tomsg(uint8_t msg[KYBER_INDCPA_MSGBYTES], const poly *r) {
  c_poly_tomsg(msg, r);
}
void pke_poly_basemul_montgomery(poly *r, const poly *a, const poly *b) {
  c_poly_basemul_montgomery(r, a, b);
}
void pke_poly_add(poly *r, const poly *a, const poly *b) {
  c_poly_add(r, a, b);
}
void pke_poly_reduce(poly *r) { c_poly_reduce(r); }

void pke_poly_invntt_tomont(poly *r) { c_poly_invntt_tomont(r); }
void pke_poly_sub(poly *r, const poly *a, const poly *b) {
  c_poly_sub(r, a, b);
}

int16_t pke_ntt_fqmul(int16_t a, int16_t b) { return c_ntt_fqmul(a, b); }

int16_t pke_montgomery_reduce(int32_t a) { return c_montgomery_reduce(a); }

int16_t pke_barrett_reduce(int16_t a) { return c_barrett_reduce(a); }

int kem_enc_m(unsigned char *ct, unsigned char *ss, const unsigned char *m,
              const unsigned char *pk) {
  uint8_t buf[2 * KYBER_SYMBYTES];
  /* Will contain key, coins */
  uint8_t kr[2 * KYBER_SYMBYTES];

  // randombytes(buf, KYBER_SYMBYTES);
  /* instead of randomly generating the message, we use a defined message */
  memcpy(buf, m, KYBER_SYMBYTES);

  /* Don't release system RNG output */
  hash_h(buf, buf, KYBER_SYMBYTES);

  /* Multitarget countermeasure for coins + contributory KEM */
  hash_h(buf + KYBER_SYMBYTES, pk, KYBER_PUBLICKEYBYTES);
  hash_g(kr, buf, 2 * KYBER_SYMBYTES);

  /* coins are in kr+KYBER_SYMBYTES */
  indcpa_enc(ct, buf, pk, kr + KYBER_SYMBYTES);

  /* overwrite coins in kr with H(c) */
  hash_h(kr + KYBER_SYMBYTES, ct, KYBER_CIPHERTEXTBYTES);
  /* hash concatenation of pre-k and H(c) to k */
  kdf(ss, kr, 2 * KYBER_SYMBYTES);
  return 0;
}

#ifdef __cplusplus
}
#endif