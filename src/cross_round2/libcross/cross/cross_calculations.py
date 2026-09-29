from typing import TYPE_CHECKING
from .cross_calculation_result import CalculationResult, KeygenCalculationResult, SignCalculationResult
import ctypes

if TYPE_CHECKING:
    from .cross import Cross

class Calculations:

    def __init__(self, cross: "Cross"):
        self.cross = cross
        self.subfunctions = cross.subfunctions
        
    def keygen(self, seed_sk: bytes | None = None):
        c = self.cross

        if seed_sk == None:
            seed_sk = c.subfunctions.randombytes(c.params.keypair_seed_length_bytes)

        result = KeygenCalculationResult(seed_sk = seed_sk)

        #/* Expansion of sk->seed, explicit domain separation for CSPRNG */
        dsc_csprng_seed_sk = c.params.csprng_domain_sep_const + (3 * c.params.t + 1)

        csprng_state = c.subfunctions.csprng_initialize(seed_sk, dsc_csprng_seed_sk)
        seed_e_seed_pk = c.subfunctions.csprng_randombytes(2*c.params.keypair_seed_length_bytes, csprng_state)
        seed_pk = seed_e_seed_pk[c.params.keypair_seed_length_bytes : 2 * c.params.keypair_seed_length_bytes]

        # /* expansion of matrix/matrices */
        if c.params.algorithm == "RSDP":
            V_tr = c.subfunctions.expand_pk(seed_pk)
            result.expand_pk.V_tr = V_tr
            result.expand_pk.seed_pk = seed_pk
        elif c.params.algorithm == "RSDPG":
            V_tr, W_mat = c.subfunctions.expand_pk(seed_pk)
            result.expand_pk.V_tr = V_tr
            result.expand_pk.W_mat = W_mat
            result.expand_pk.seed_pk = seed_pk
        
        # /* expansion of secret key material */ 
        # /* Expansion of seede, explicit domain separation for CSPRNG */
        dsc_csprng_seed_e = c.params.csprng_domain_sep_const + (3 * c.params.t + 3)

        csprng_state_e_bar = c.subfunctions.csprng_initialize(seed_e_seed_pk[: c.params.keypair_seed_length_bytes], dsc_csprng_seed_e)

        if c.params.algorithm == "RSDP":
            e_bar = c.subfunctions.csprng_fz_vec(csprng_state_e_bar)
        elif c.params.algorithm == "RSDPG":
            e_G_bar = c.subfunctions.csprng_fz_inf_w(csprng_state_e_bar)
            e_bar = c.subfunctions.fz_inf_w_by_fz_matrix(e_G_bar, W_mat)
            result.fz_inf_w_by_fz_matrix.e_bar = e_bar.copy
            result.fz_inf_w_by_fz_matrix.e_G_bar = e_G_bar
            
            e_bar = c.subfunctions.fz_dz_norm_n(e_bar)
            result.fz_dz_norm_n.e_bar_out = e_bar

        s = c.subfunctions.restr_vec_by_fp_matrix(e_bar, V_tr)
        result.restr_vec_by_fp_matrix.s = s.copy
        s = c.subfunctions.fp_dz_norm_synd(s)
        s = c.subfunctions.pack_fp_syn(s)

        # Build public key as seed_pk || s
        result.pk.extend(seed_pk)
        result.pk.extend(s)

        return result


    def sign(self, 
             m: bytes, 
             *, 
             seed_sk: bytes | None = None,
             seed_pk: bytes | None = None,
             root_seed: bytes | None = None,
             salt: bytes | None = None
             ):
        c = self.cross

        values = (seed_sk, seed_pk, root_seed, salt)
        
        if all(value is None for value in values):
            seed_sk, seed_pk = c.keygen
            root_seed = c.subfunctions.randombytes(c.params.seed_length_bytes)
            salt = c.subfunctions.randombytes(c.params.salt_length_bytes)

        elif any(value is None for value in values):
            raise ValueError("Either provide seed_sk, seed_pk, root_seed, salt, or provide none of them.")
           
        mlen = len(m)
        #sig  = c._sig_type

        result = SignCalculationResult(
            seed_sk = seed_sk,
            seed_pk = seed_pk,
            root_seed = root_seed,
            salt = salt,
        )

        # Intermediate values required for signature generation
        cmt_0 = []
        cmt_1 = bytearray()

        # Per-round values that must be preserved for response computation
        e_bar_prime_replay = []
        u_prime_replay = []
        v_bar_replay = []
        v_G_bar_replay = []

        # ------------------------------------------------------------------------
        #  Cross sign
        # ------------------------------------------------------------------------
            
        # Key material expansion, these values remain unchanged
        # expand_sk
        if c.params.algorithm == "RSDP":
            e_bar, V_tr = c.subfunctions.expand_sk(seed_sk)
            result.expand_sk.e_bar[:] = e_bar
            result.expand_sk.V_tr[:] = V_tr
        elif c.params.algorithm == "RSDPG":
            e_bar, e_G_bar, V_tr, W_mat = c.subfunctions.expand_sk(seed_sk)
            result.expand_sk.e_bar[:] = e_bar
            result.expand_sk.e_G_bar[:] = e_G_bar
            result.expand_sk.V_tr[:] = V_tr
            result.expand_sk.W_mat[:] = W_mat

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

        #cmt_0_i_input is syndrome || v_bar resp. v_G_bar || salt ; place salt at the end
        #write salt in cmt_0_i_input start: offset_salt end: ofset_salt+salt length_bytes
        cmt_0_i_input[offset_salt : offset_salt + c.params.salt_length_bytes] = salt

        cmt_1_i_input = bytearray(c.params.seed_length_bytes + 
                                    c.params.salt_length_bytes)

        # cmt_1_i_input is concat(seed,salt,round index + 2T-1)
        cmt_1_i_input[c.params.seed_length_bytes : 
                        c.params.seed_length_bytes + 
                        c.params.salt_length_bytes] = salt

        for i in range(c.params.t):
            #/* CSPRNG is fed with concat(seed,salt,round index) represented
            # * as a 2 bytes little endian unsigned integer */
            csprng_input = bytearray(c.params.seed_length_bytes +
                                        c.params.salt_length_bytes)
            csprng_input[0 : c.params.seed_length_bytes] = round_seeds[c.params.seed_length_bytes * i : 
                                                                        c.params.seed_length_bytes * (i + 1)]
            csprng_input[c.params.seed_length_bytes : 
                            c.params.seed_length_bytes + 
                            c.params.salt_length_bytes] = salt

            domain_sep_csprng = c.params.csprng_domain_sep_const + i + (2 * c.params.t -1)
            # /* expand seed[i] into seed_e and seed_u */
            csprng_state = c.subfunctions.csprng_initialize(csprng_input, domain_sep_csprng)
     
            #/* expand e_bar_prime */
            if c.params.algorithm == "RSDP":
                e_bar_prime_i = c.subfunctions.csprng_fz_vec(csprng_state)
                e_bar_prime_replay.append(e_bar_prime_i)
            elif c.params.algorithm == "RSDPG":
                e_G_bar_prime = c.subfunctions.csprng_fz_inf_w(csprng_state)
                # fz_vec_sub_m
                v_G_bar_i = c.subfunctions.fz_vec_sub_m(e_G_bar, e_G_bar_prime)
                result.fz_vec_sub_m.e_G_bar_prime.append(e_G_bar_prime)
                result.fz_vec_sub_m.v_G_bar.append(v_G_bar_i)
                # fz_dz_norm_m
                v_G_bar_i = c.subfunctions.fz_dz_norm_m(v_G_bar_i)
                result.fz_dz_norm_m.v_G_bar_out.append(v_G_bar_i)
                v_G_bar_replay.append(v_G_bar_i)
                # fz_inf_w_by_fz_matrix
                e_bar_prime_i = c.subfunctions.fz_inf_w_by_fz_matrix(e_G_bar_prime, W_mat)
                result.fz_inf_w_by_fz_matrix.e_bar_prime.append(e_bar_prime_i)
                # fz_dz_norm_n
                e_bar_prime_i = c.subfunctions.fz_dz_norm_n(e_bar_prime_i)
                result.fz_dz_norm_n.e_bar_prime_out.append(e_bar_prime_i)
                e_bar_prime_replay.append(e_bar_prime_i)
                
            # fz_vec_sub_n
            v_bar_i = c.subfunctions.fz_vec_sub_n(e_bar, e_bar_prime_i)
            result.fz_vec_sub_n.e_bar_prime.append(e_bar_prime_i)
            result.fz_vec_sub_n.v_bar.append(v_bar_i)

            # convert_restr_vec_to_fp
            v = c.subfunctions.convert_restr_vec_to_fp(v_bar_i)
            result.convert_restr_vec_to_fp.v.append(v)
            #fz_dz_norm_n
            v_bar_i = c.subfunctions.fz_dz_norm_n(v_bar_i)
            result.fz_dz_norm_n.v_bar_out.append(v_bar_i)
            v_bar_replay.append(v_bar_i) 

            #/* expand u_prime */
            u_prime_i = c.subfunctions.csprng_fp_vec(csprng_state)
            u_prime_replay.append(u_prime_i)

            # fp_vec_by_fp_vec_pointwise
            u = c.subfunctions.fp_vec_by_fp_vec_pointwise(v, u_prime_i)
            result.fp_vec_by_fp_vec_pointwise.u.append(u)
            result.fp_vec_by_fp_vec_pointwise.u_prime.append(u_prime_i)
            #fp_vec_by_fp_matrix
            s_prime = c.subfunctions.fp_vec_by_fp_matrix(u, V_tr)
            result.fp_vec_by_fp_matrix.s_prime.append(s_prime)

            s_prime = c.subfunctions.fp_dz_norm_synd(s_prime)

            # pack_fp_syn
            packed_s_prime = c.subfunctions.pack_fp_syn(s_prime)
            # /* cmt_0_i_input contains s_prime || v_bar resp. v_G_bar || salt */
            cmt_0_i_input[0 : c.params.densely_packed_fp_syn_size] = packed_s_prime
            result.pack_fp_syn.s_prime_in.append(s_prime)
            result.pack_fp_syn.s_prime_out.append(packed_s_prime)

            if c.params.algorithm == "RSDP":
                # pack_fz_vec
                packed_v_bar_i = c.subfunctions.pack_fz_vec(v_bar_i)# wieder umgeschrieben lol
                result.pack_fz_vec.v_bar_out.append(packed_v_bar_i)
                # cmt_0_i_input looks like DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_VEC_SIZE+ SALT_LENGTH_BYTES
                #                          s_prime || v_bar or v_G_bar || salt
                cmt_0_i_input[c.params.densely_packed_fp_syn_size : c.params.densely_packed_fp_syn_size + c.params.densely_packed_fz_vec_size] = packed_v_bar_i
            elif c.params.algorithm == "RSDPG":
                #pack_fz_rsdp_g_vec
                packed_v_G_bar = c.subfunctions.pack_fz_rsdp_g_vec(v_G_bar_i)
                result.pack_fz_rsdp_g_vec.v_G_bar_out.append(packed_v_G_bar)
                # cmt_0_i_input looks like DENSELY_PACKED_FP_SYN_SIZE + DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE+ SALT_LENGTH_BYTES
                #                          s_prime || v_bar or v_G_bar || salt
                cmt_0_i_input[c.params.densely_packed_fp_syn_size : c.params.densely_packed_fp_syn_size + c.params.densely_packed_fz_rsdp_g_vec_size] = packed_v_G_bar
            #/* Fixed endianness marshalling of round counter */
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

        #/* first challenge extraction */
        digest_msg_cmt_salt = bytearray()
        #/* place digest_msg at the beginning of the input of the hash generating digest_chall_1 */
        digest_msg_cmt_salt.extend(c.subfunctions.hash(m, c.params.hash_domain_sep_const))
        digest_msg_cmt_salt.extend(digest_cmt)
        digest_msg_cmt_salt.extend(salt)

        digest_chall_1 = c.subfunctions.hash(digest_msg_cmt_salt, c.params.hash_domain_sep_const)

        #// Domain separation unique for expanding chall_1
        dsc_csprng_chall_1 = c.params.csprng_domain_sep_const + (3 * c.params.t -1)
            
        csprng_state = c.subfunctions.csprng_initialize(digest_chall_1, dsc_csprng_chall_1)
        chall_1 = c.subfunctions.csprng_fp_vec_chall_1(csprng_state)

        #/* Computation of the first round of responses */
        # fp_vec_by_restr_vec_scaled
        result.fp_vec_by_restr_vec_scaled.chall_1 = chall_1
        y =[]
        for i in range(c.params.t):
            y_i = c.subfunctions.fp_vec_by_restr_vec_scaled(e_bar_prime_replay[i], chall_1[i], u_prime_replay[i])
            result.fp_vec_by_restr_vec_scaled.y.append(y_i) 

            y.append(c.subfunctions.fp_dz_norm(y_i))
                
        # /* y vectors are packed before being hashed */
        y_digest_chall_1 = bytearray()
            
        for i in range(c.params.t):
            y_digest_chall_1.extend(c.subfunctions.pack_fp_vec(y[i]))

        # /* Second challenge extraction */
        y_digest_chall_1.extend(digest_chall_1)

        digest_chall_2 = c.subfunctions.hash(y_digest_chall_1, c.params.hash_domain_sep_const)

        # expand_digest_to_fixed_weight
        result.expand_digest_to_fixed_weight.digest_chall_2 = digest_chall_2
        chall_2 = c.subfunctions.expand_digest_to_fixed_weight(digest_chall_2)
        result.expand_digest_to_fixed_weight.chall_2 = chall_2

        #/* Computation of the second round of responses */
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
                    # v_G_bar_fz_dz_norm_n_out style bad refactor!
                    resp_0.extend(c.subfunctions.pack_fp_vec(y[i]))
                    resp_0.extend(c.subfunctions.pack_fz_rsdp_g_vec(v_G_bar_replay[i]))
                resp_1.extend(cmt_1[i * c.params.hash_digest_length : (i + 1) * c.params.hash_digest_length])   
                published_rsps += 1

        # ------------------------------------------------------------------------
        #  Cross sign end
        # ------------------------------------------------------------------------

        # calculate offsets for signature 
        # expected: salt || digest_cmt || digest_chall_2 || path || proof || resp_1 || resp_0
        salt_offset           = 0
        digest_cmt_offset     = salt_offset + len(salt)
        digest_chall_2_offset = digest_cmt_offset + len(digest_cmt)
        path_offset           = digest_chall_2_offset + len(digest_chall_2)
        proof_offset          = path_offset + len(path)
        resp_1_offset         = proof_offset + len(proof)
        resp_0_offset         = resp_1_offset + len(resp_1)

        # build signature from calculated inputs
        sig_bytes = bytearray(c.params.sig_size)

        sig_bytes[salt_offset : salt_offset + len(salt)] = salt
        sig_bytes[digest_cmt_offset : digest_cmt_offset + len(digest_cmt)] = digest_cmt
        sig_bytes[digest_chall_2_offset : digest_chall_2_offset + len(digest_chall_2)] = digest_chall_2
        # path may be smaller than the fixed-size field, remaining bytes stay zero
        sig_bytes[path_offset : path_offset +  len(path)] = path
        sig_bytes[proof_offset : proof_offset + len(proof)] = proof
        sig_bytes[resp_1_offset : resp_1_offset + len(resp_1)] = resp_1
        sig_bytes[resp_0_offset : resp_0_offset + len(resp_0)] = resp_0

        result.signature = sig_bytes
        
        return result