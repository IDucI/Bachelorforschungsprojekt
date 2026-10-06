"""Tests the CROSS Python implementation using C-generated test data.

Key generation and signing are reconstructed step by step to validate the
intermediate values stored by the calculation API. Additional tests generate
Python signatures and check that they are accepted by the C implementation's
CROSS_verify().
"""

import json
from pathlib import Path
from cross import Cross
import secrets

algorithms = ["RSDP", "RSDPG"]
categories = [1, 3, 5]
optimizations = ["fast", "balanced", "small"]

test_dir = Path(__file__).parent
build_dir = test_dir.parent / "build"

sign_success_count = 0
keygen_success_count = 0


def keygen_test(c: Cross, data):
    """Reconstruct key generation from C-generated test data and validate the stored intermediate values and public key."""
    global keygen_success_count

    seed_sk   = bytes.fromhex(data["seed_sk"])
    pk   = bytes.fromhex(data["public_key"])

    result = c.calculation.keygen(seed_sk)
    
    # Expansion of sk->seed, explicit domain separation for CSPRNG
    dsc_csprng_seed_sk = c.params.csprng_domain_sep_const + (3 * c.params.t + 1)

    csprng_state = c.subfunctions.csprng_initialize(seed_sk, dsc_csprng_seed_sk)
    seed_e_seed_pk = c.subfunctions.csprng_randombytes(2*c.params.keypair_seed_length_bytes, csprng_state)
    seed_pk = seed_e_seed_pk[c.params.keypair_seed_length_bytes : 2 * c.params.keypair_seed_length_bytes]

    # expansion of matrix/matrices
    if c.params.algorithm == "RSDP":
        assert result.expand_pk.seed_pk == seed_pk
        V_tr = c.subfunctions.expand_pk(seed_pk)
        assert result.expand_pk.V_tr == V_tr
    elif c.params.algorithm == "RSDPG":
        assert result.expand_pk.seed_pk == seed_pk
        V_tr, W_mat = c.subfunctions.expand_pk(seed_pk)
        assert result.expand_pk.V_tr == V_tr
        assert result.expand_pk.W_mat == W_mat
        
    # expansion of secret key material 
    # Expansion of seede, explicit domain separation for CSPRNG
    dsc_csprng_seed_e = c.params.csprng_domain_sep_const + (3 * c.params.t + 3)

    csprng_state_e_bar = c.subfunctions.csprng_initialize(seed_e_seed_pk[: c.params.keypair_seed_length_bytes], dsc_csprng_seed_e)

    if c.params.algorithm == "RSDP":
        e_bar = c.subfunctions.csprng_fz_vec(csprng_state_e_bar)
    elif c.params.algorithm == "RSDPG":
        e_G_bar = c.subfunctions.csprng_fz_inf_w(csprng_state_e_bar)
        assert result.fz_inf_w_by_fz_matrix.W_mat == W_mat
        e_bar = c.subfunctions.fz_inf_w_by_fz_matrix(e_G_bar, W_mat)
        assert result.fz_inf_w_by_fz_matrix.e_bar == e_bar
        assert result.fz_inf_w_by_fz_matrix.e_G_bar == e_G_bar
            
        assert result.fz_dz_norm_n.e_bar_in == e_bar
        e_bar = c.subfunctions.fz_dz_norm_n(e_bar)
        assert result.fz_dz_norm_n.e_bar_out == e_bar

    assert result.restr_vec_by_fp_matrix.e_bar == e_bar
    assert result.restr_vec_by_fp_matrix.V_tr == V_tr
    s = c.subfunctions.restr_vec_by_fp_matrix(e_bar, V_tr)
    assert result.restr_vec_by_fp_matrix.s == s
    s = c.subfunctions.fp_dz_norm_synd(s)
    assert result.pack_fp_syn.s_in == s
    s = c.subfunctions.pack_fp_syn(s)
    assert result.pack_fp_syn.s_out == s

    # Build public key as seed_pk || s
    public_key = seed_pk + s 
    assert result.pk == pk == public_key # compare calculation, C reference, and reconstructed public keys

    keygen_success_count += 1
    

def sign_test(c: Cross, data):
    """Reconstruct signing from C-generated test data and validate the stored intermediate values and signature."""
    global sign_success_count

    m         = bytes.fromhex(data["m"])
    seed_sk   = bytes.fromhex(data["seed_sk"])
    pk   = bytes.fromhex(data["public_key"])
    root_seed = bytes.fromhex(data["root_seed"])
    salt      = bytes.fromhex(data["salt"])

    result = c.calculation.sign(m, seed_sk=seed_sk, pk=pk, root_seed=root_seed, salt=salt)
            
    sig = result.signature

     # ------------------------------------------------------------------------
     #  Cross sign
     # ------------------------------------------------------------------------

    # Intermediate values required for signature generation
    cmt_0 = []
    cmt_1 = bytearray()

    # Per-round values that must be preserved for response computation
    e_bar_prime_replay = []
    u_prime_replay = []
    v_bar_replay = []
    v_G_bar_replay = []

    # Key material expansion, these values remain unchanged
    # expand_sk
    assert seed_sk == result.seed_sk

    if c.params.algorithm == "RSDP":
        e_bar, V_tr = c.subfunctions.expand_sk(seed_sk)
        assert e_bar == result.expand_sk.e_bar
        assert V_tr == result.expand_sk.V_tr
    elif c.params.algorithm == "RSDPG":
        e_bar, e_G_bar, V_tr, W_mat = c.subfunctions.expand_sk(seed_sk)
        assert e_bar == result.expand_sk.e_bar
        assert e_G_bar == result.expand_sk.e_G_bar
        assert V_tr == result.expand_sk.V_tr
        assert W_mat == result.expand_sk.W_mat

    seed_tree = c.subfunctions.gen_seed_tree(root_seed, salt)
    round_seeds = c.subfunctions.seed_leaves(seed_tree)

    if c.params.algorithm == "RSDP":
        cmt_0_i_input = bytearray(c.params.densely_packed_fp_syn_size +
                                    c.params.densely_packed_fz_vec_size +
                                    c.params.salt_length_bytes)
        offset_salt = c.params.densely_packed_fp_syn_size + c.params.densely_packed_fz_vec_size
    elif c.params.algorithm == "RSDPG":
        cmt_0_i_input = bytearray(c.params.densely_packed_fp_syn_size +
                                    c.params.densely_packed_fz_rsdp_g_vec_size +
                                    c.params.salt_length_bytes)
        offset_salt = c.params.densely_packed_fp_syn_size + c.params.densely_packed_fz_rsdp_g_vec_size
            
    assert salt == result.salt

    # cmt_0_i_input is syndrome || v_bar resp. v_G_bar || salt
    cmt_0_i_input[offset_salt : offset_salt + c.params.salt_length_bytes] = salt

    cmt_1_i_input = bytearray(c.params.seed_length_bytes + 
                                c.params.salt_length_bytes)

   # cmt_1_i_input = seed || salt
    cmt_1_i_input[c.params.seed_length_bytes : 
                    c.params.seed_length_bytes + 
                    c.params.salt_length_bytes] = salt

    for i in range(c.params.t):
        # csprng_input = seed || salt
        csprng_input = bytearray(c.params.seed_length_bytes +
                                    c.params.salt_length_bytes)
        csprng_input[0 : c.params.seed_length_bytes] = round_seeds[c.params.seed_length_bytes * i : 
                                                                    c.params.seed_length_bytes * (i + 1)]
        csprng_input[c.params.seed_length_bytes : 
                        c.params.seed_length_bytes + 
                        c.params.salt_length_bytes] = salt

        domain_sep_csprng = c.params.csprng_domain_sep_const + i + (2 * c.params.t -1)
        # expand seed[i] into seed_e and seed_u
        csprng_state = c.subfunctions.csprng_initialize(csprng_input, domain_sep_csprng)

        # expand e_bar_prime
        if c.params.algorithm == "RSDP":
            e_bar_prime_i = c.subfunctions.csprng_fz_vec(csprng_state)
            e_bar_prime_replay.append(e_bar_prime_i)
        elif c.params.algorithm == "RSDPG":
            e_G_bar_prime = c.subfunctions.csprng_fz_inf_w(csprng_state)
            # fz_vec_sub_m
            assert e_G_bar == result.fz_vec_sub_m.e_G_bar
            assert e_G_bar_prime == result.fz_vec_sub_m.e_G_bar_prime[i]
            v_G_bar_i = c.subfunctions.fz_vec_sub_m(e_G_bar, e_G_bar_prime)
            assert v_G_bar_i == result.fz_vec_sub_m.v_G_bar[i]

            # fz_dz_norm_m
            assert v_G_bar_i == result.fz_dz_norm_m.v_G_bar_in[i]
            v_G_bar_i = c.subfunctions.fz_dz_norm_m(v_G_bar_i)
            assert v_G_bar_i == result.fz_dz_norm_m.v_G_bar_out[i]
            v_G_bar_replay.append(v_G_bar_i)

            # fz_inf_w_by_fz_matrix
            assert e_G_bar_prime == result.fz_inf_w_by_fz_matrix.e_G_bar_prime[i]
            assert W_mat == result.fz_inf_w_by_fz_matrix.W_mat
            e_bar_prime_i = c.subfunctions.fz_inf_w_by_fz_matrix(e_G_bar_prime, W_mat)
            assert e_bar_prime_i == result.fz_inf_w_by_fz_matrix.e_bar_prime[i]

            # fz_dz_norm_n
            assert e_bar_prime_i == result.fz_dz_norm_n.e_bar_prime_in[i]
            e_bar_prime_i = c.subfunctions.fz_dz_norm_n(e_bar_prime_i)
            assert e_bar_prime_i == result.fz_dz_norm_n.e_bar_prime_out[i]
            e_bar_prime_replay.append(e_bar_prime_i)
                
        # fz_vec_sub_n
        assert e_bar == result.fz_vec_sub_n.e_bar
        assert e_bar_prime_i == result.fz_vec_sub_n.e_bar_prime[i]
        v_bar_i = c.subfunctions.fz_vec_sub_n(e_bar, e_bar_prime_i)
        assert v_bar_i == result.fz_vec_sub_n.v_bar[i]

        # convert_restr_vec_to_fp
        assert v_bar_i == result.convert_restr_vec_to_fp.v_bar[i]
        v = c.subfunctions.convert_restr_vec_to_fp(v_bar_i)
        assert v == result.convert_restr_vec_to_fp.v[i]

        # fz_dz_norm_n
        assert v_bar_i == result.fz_dz_norm_n.v_bar_in[i]
        v_bar_i = c.subfunctions.fz_dz_norm_n(v_bar_i)
        assert v_bar_i == result.fz_dz_norm_n.v_bar_out[i]
        v_bar_replay.append(v_bar_i) 


        # expand u_prime 
        u_prime_i = c.subfunctions.csprng_fp_vec(csprng_state)
        u_prime_replay.append(u_prime_i)

        # fp_vec_by_fp_vec_pointwise
        assert v == result.fp_vec_by_fp_vec_pointwise.v[i]
        assert u_prime_i == result.fp_vec_by_fp_vec_pointwise.u_prime[i]
        u = c.subfunctions.fp_vec_by_fp_vec_pointwise(v, u_prime_i)
        assert u == result.fp_vec_by_fp_vec_pointwise.u[i]

        # fp_vec_by_fp_matrix
        assert u == result.fp_vec_by_fp_matrix.u[i]
        assert V_tr == result.fp_vec_by_fp_matrix.V_tr
        s_prime = c.subfunctions.fp_vec_by_fp_matrix(u, V_tr)
        assert s_prime == result.fp_vec_by_fp_matrix.s_prime[i]

        s_prime = c.subfunctions.fp_dz_norm_synd(s_prime)

        # cmt_0_i_input contains s_prime || v_bar resp. v_G_bar || salt
        # pack_fp_syn
        assert s_prime == result.pack_fp_syn.s_prime_in[i]
        packed_s_prime = c.subfunctions.pack_fp_syn(s_prime)
        assert packed_s_prime == result.pack_fp_syn.s_prime_out[i]

        cmt_0_i_input[0 : c.params.densely_packed_fp_syn_size] = packed_s_prime

        if c.params.algorithm == "RSDP":
            # pack_fz_vec
            assert v_bar_i == result.pack_fz_vec.v_bar_in[i]
            packed_v_bar_i = c.subfunctions.pack_fz_vec(v_bar_i)
            assert packed_v_bar_i == result.pack_fz_vec.v_bar_out[i]
            # cmt_0_i_input looks like DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_VEC_SIZE+ SALT_LENGTH_BYTES
            #                          s_prime || v_bar or v_G_bar || salt
            cmt_0_i_input[c.params.densely_packed_fp_syn_size : c.params.densely_packed_fp_syn_size + c.params.densely_packed_fz_vec_size] = packed_v_bar_i
        elif c.params.algorithm == "RSDPG":
            # pack_fz_rsdp_g_vec
            assert v_G_bar_i == result.pack_fz_rsdp_g_vec.v_G_bar_in[i]
            packed_v_G_bar_i = c.subfunctions.pack_fz_rsdp_g_vec(v_G_bar_i)
            assert packed_v_G_bar_i == result.pack_fz_rsdp_g_vec.v_G_bar_out[i]
            # cmt_0_i_input looks like DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE+ SALT_LENGTH_BYTES
            #                          s_prime || v_bar or v_G_bar || salt
            cmt_0_i_input[c.params.densely_packed_fp_syn_size : c.params.densely_packed_fp_syn_size + c.params.densely_packed_fz_rsdp_g_vec_size] = packed_v_G_bar_i

        domain_sep_hash = c.params.hash_domain_sep_const + i + (2 * c.params.t - 1)

        cmt_0.extend(c.subfunctions.hash(cmt_0_i_input, domain_sep_hash))

        cmt_1_i_input[0 : c.params.seed_length_bytes]= round_seeds[c.params.seed_length_bytes * i : c.params.seed_length_bytes * (i + 1)]

        cmt_1.extend(c.subfunctions.hash(cmt_1_i_input, domain_sep_hash))

    # digest_cmt0_cmt1 contains: root || hash1
    digest_cmt0_cmt1 = bytearray()
    root, merkle_tree_0 = c.subfunctions.tree_root(cmt_0)
    digest_cmt0_cmt1.extend(root)

    hash1 = c.subfunctions.hash(cmt_1, c.params.hash_domain_sep_const)
    digest_cmt0_cmt1.extend(hash1)    
    digest_cmt = c.subfunctions.hash(digest_cmt0_cmt1, c.params.hash_domain_sep_const)

    # first challenge extraction
    digest_msg_cmt_salt = bytearray()

    digest_msg_cmt_salt.extend(c.subfunctions.hash(m, c.params.hash_domain_sep_const))
    digest_msg_cmt_salt.extend(digest_cmt)
    digest_msg_cmt_salt.extend(salt)

    digest_chall_1 = c.subfunctions.hash(digest_msg_cmt_salt, c.params.hash_domain_sep_const)

    # Domain separation unique for expanding chall_1
    dsc_csprng_chall_1 = c.params.csprng_domain_sep_const + (3 * c.params.t -1)
            
    csprng_state = c.subfunctions.csprng_initialize(digest_chall_1, dsc_csprng_chall_1)
    chall_1 = c.subfunctions.csprng_fp_vec_chall_1(csprng_state)

    # Computation of the first round of responses
    y =[]
    for i in range(c.params.t):
        # fp_vec_by_restr_vec_scaled
        assert e_bar_prime_replay[i] == result.fp_vec_by_restr_vec_scaled.e_bar_prime[i]
        assert chall_1[i] == result.fp_vec_by_restr_vec_scaled.chall_1[i]
        assert u_prime_replay[i] == result.fp_vec_by_restr_vec_scaled.u_prime[i]
        y_i = c.subfunctions.fp_vec_by_restr_vec_scaled(e_bar_prime_replay[i], chall_1[i], u_prime_replay[i])
        assert y_i == result.fp_vec_by_restr_vec_scaled.y[i]

        y.append(c.subfunctions.fp_dz_norm(y_i))
                
    # y vectors are packed before being hashed
    y_digest_chall_1 = bytearray()
            
    for i in range(c.params.t):
        y_digest_chall_1.extend(c.subfunctions.pack_fp_vec(y[i]))

    # Second challenge extraction
    y_digest_chall_1.extend(digest_chall_1)

    digest_chall_2 = c.subfunctions.hash(y_digest_chall_1, c.params.hash_domain_sep_const)

    # expand_digest_to_fixed_weight
    assert digest_chall_2 == result.expand_digest_to_fixed_weight.digest_chall_2
    chall_2 = c.subfunctions.expand_digest_to_fixed_weight(digest_chall_2)
    assert chall_2 == result.expand_digest_to_fixed_weight.chall_2

    # Computation of the second round of responses
    _, proof = c.subfunctions.tree_proof(merkle_tree_0, chall_2)
    _, path  = c.subfunctions.seed_path(seed_tree, chall_2)

    resp_0 = bytearray()
    resp_1 = bytearray()
    published_rsps = 0
    for i in range(c.params.t):
        if chall_2[i] == 0:
            assert(published_rsps < c.params.t - c.params.w)
            if c.params.algorithm == "RSDP":
                resp_0.extend(c.subfunctions.pack_fp_vec(y[i]))
                resp_0.extend(c.subfunctions.pack_fz_vec(v_bar_replay[i]))
            if c.params.algorithm == "RSDPG":
                resp_0.extend(c.subfunctions.pack_fp_vec(y[i]))
                resp_0.extend(c.subfunctions.pack_fz_rsdp_g_vec(v_G_bar_replay[i]))
            resp_1.extend(cmt_1[i * c.params.hash_digest_length : (i + 1) * c.params.hash_digest_length])   
            published_rsps += 1

    # ------------------------------------------------------------------------
    #  Cross sign end
    # ------------------------------------------------------------------------

    # Signature: salt || digest_cmt || digest_chall_2 || path || proof || resp_1 || resp_0
    salt_offset           = 0
    digest_cmt_offset     = salt_offset + len(salt)
    digest_chall_2_offset = digest_cmt_offset + len(digest_cmt)
    path_offset           = digest_chall_2_offset + len(digest_chall_2)
    proof_offset          = path_offset + len(path)
    resp_1_offset         = proof_offset + len(proof)
    resp_0_offset         = resp_1_offset + len(resp_1)

    sig_bytes = bytearray(c.params.sig_size)

    sig_bytes[salt_offset : salt_offset + len(salt)] = salt
    sig_bytes[digest_cmt_offset : digest_cmt_offset + len(digest_cmt)] = digest_cmt
    sig_bytes[digest_chall_2_offset : digest_chall_2_offset + len(digest_chall_2)] = digest_chall_2
    # path may be smaller than the fixed-size field, remaining bytes stay zero
    sig_bytes[path_offset : path_offset +  len(path)] = path
    sig_bytes[proof_offset : proof_offset + len(proof)] = proof
    sig_bytes[resp_1_offset : resp_1_offset + len(resp_1)] = resp_1
    sig_bytes[resp_0_offset : resp_0_offset + len(resp_0)] = resp_0

    sig = c._sig_type(*sig_bytes)
    c_sig = bytes(data["signature"])
    assert sig_bytes == c_sig == result.signature # compare reconstructed, C reference, and calculation signatures
    assert c.verify(pk, m, sig)  # verify signature validity
    sign_success_count += 1


c_verify_input = {}  # stores message, public_key, and signature generated through the high-level and calculation APIs for later verification in C

def high_level_api_to_c_test(c: Cross):
    """Generate key and signature data through the high-level API for validation by C CROSS_verify()."""
    seed_sk, pk = c.keygen()

    length = secrets.randbelow(10000) + 1
    m = secrets.token_bytes(length)

    sig = c.sign(seed_sk, m)

    return {
        "message": m.hex(),
        "public_key": pk.hex(),
        "signature": sig.hex(),
    }


def calculation_api_to_c_test(c: Cross):
    """Generate key and signature data through the calculation API for validation by C CROSS_verify()."""
    keygen_result = c.calculation.keygen()
    pk = keygen_result.pk
    seed_sk = keygen_result.seed_sk

    length = secrets.randbelow(10000) + 1
    m = secrets.token_bytes(length)

    sign_result = c.calculation.sign(m, seed_sk=seed_sk, pk=pk)
    sig = sign_result.signature

    return {
        "message": m.hex(),
        "public_key": pk.hex(),
        "signature": sig.hex(),
    }


print("Start testing ...")
for algorithm in algorithms:
    for category in categories:
        for optimization in optimizations:
            json_path = test_dir / f"cross_{algorithm.lower()}_{category}_{optimization}.json"

            with open(json_path, "r") as f:
                data = json.load(f)

            c = Cross(
                path=str(build_dir),
                algorithm=algorithm,
                category=category,
                optimization=optimization,
            )
            print(algorithm, category, optimization) # show the current parameter set for easier debugging
            sign_test(c, data)
            keygen_test(c, data)

            # Generate Python test data for later verification by C CROSS_verify()
            variant = f"cross_{algorithm.lower()}_{category}_{optimization}"
            c_verify_input[variant] = {
                "high_level_api": [],
                "calculation_api": []
            }

            for _ in range(1):
                c_verify_input[variant]["high_level_api"].append(high_level_api_to_c_test(c))
                c_verify_input[variant]["calculation_api"].append(calculation_api_to_c_test(c))

# Store Python-generated test data for the C verification test
with open(test_dir / "c_verify_py.json", "w") as f:
    json.dump(c_verify_input, f, indent=4)

# Report overall test results
if sign_success_count == 18:
    print("\033[92mAll sign tests passed.\033[0m")
else:
    print("\033[91mSome sign tests failed.\033[0m")

if keygen_success_count == 18:
    print("\033[92mAll keygen tests passed.\033[0m")
else:
    print("\033[91mSome keygen tests failed.\033[0m")

if sign_success_count != 18 or keygen_success_count != 18:
    raise SystemExit(1)


            