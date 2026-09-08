from .cross_subfunctions import CrossSubfunctions
from .cross_params import CrossParams

class Calculations:
    def __init__(self, subfunctions: CrossSubfunctions):
        self.subfunctions = subfunctions
        self.params: CrossParams = subfunctions.params
        self.algorithm = self.params.algorithm

        self.n = self.params.n
        self.k = self.params.k
        self.m = self.params.m
        self.t = self.params.t
        self.w = self.params.w

        self.seed_length_bytes = self.params.seed_length_bytes
        self.keypair_seed_length_bytes = self.params.keypair_seed_length_bytes
        self.salt_length_bytes = self.params.salt_length_bytes
        self.num_nodes_seed_tree = self.params.num_nodes_seed_tree
        self.densely_packed_fp_syn_size = self.params.densely_packed_fp_syn_size
        self.densely_packed_fz_vec_size = self.params.densely_packed_fz_vec_size

    # def expand_sk(self, seed_sk):
    #     if self.algorithm == "RSDP":
    #         e_bar, _ = self.subfunctions.expand_sk(seed_sk)
    #     elif self.algorithm == "RSDPG":
    #         raise NotImplementedError("RSDPG handling is not implemented yet")
    #     return e_bar

    # def v_tr(self, seed_sk):
    #     _, v_tr = self.subfunctions.expand_sk(seed_sk)
    #     return v_tr

    # def seed_tree(self, root_seed, salt):
    #     return self.subfunctions.gen_seed_tree(root_seed, salt)

    # def round_seeds(self, seed_tree):
    #     return self.subfunctions.seed_leaves(seed_tree)

    # def round_seed(self, round_seeds, i):
    #     start = i * self.seed_length_bytes
    #     end = start + self.seed_length_bytes
    #     return round_seeds[start:end]
    
    # # def csprng_input(self, round_seed, salt):
    # #     return round_seed + salt

    # # def domain_sep_csprng(self, i):
    # #     return self.params.csprng_domain_sep_const + i + (2 * self.t-1)

    # def e_bar_prime_i(self, round_seed, salt, i):
    #     csprng_input = round_seed + salt
    #     dsc = self.params.csprng_domain_sep_const + i + (2 * self.t-1)

    #     state = self.subfunctions.csprng_initialize(csprng_input, len(csprng_input), dsc)
    #     if self.algorithm == "RSDP":
    #         return self.subfunctions.csprng_fz_vec(state)
    #     elif self.algorithm == "RSDPG":
    #          raise NotImplementedError("RSDPG handling is not implemented yet")
    
    # v_bar: output vector for each round i before normalization,
    # used as input for convert_restr_vec_to_fp.
    def v_bar_pre_norm(self, seed_sk, root_seed, salt):
        v_bar = []

        if self.algorithm == "RSDP":
            e_bar, V_tr = self.subfunctions.expand_sk(seed_sk)
        elif self.algorithm == "RSDPG":
            e_bar, e_G_bar, V_tr, W_mat = self.subfunctions.expand_sk(seed_sk)
        
        seed_tree   = self.subfunctions.gen_seed_tree(root_seed, salt)
        round_seeds = self.subfunctions.seed_leaves(seed_tree)

        for i in range(self.params.t):
            round_seed = round_seeds[i * self.seed_length_bytes : (i+1) * self.seed_length_bytes]
            csprng_input = round_seed + salt
            dsc = self.params.csprng_domain_sep_const + i + (2 * self.t-1)

            csprng_state = self.subfunctions.csprng_initialize(csprng_input, len(csprng_input), dsc)

            if self.algorithm == "RSDP":
                e_bar_prime_i = self.subfunctions.csprng_fz_vec(csprng_state)
            elif self.algorithm == "RSDPG":
                e_G_bar_prime = self.subfunctions.csprng_fz_inf_w(csprng_state)
                e_bar_prime_i = self.subfunctions.fz_inf_w_by_fz_matrix(e_G_bar_prime, W_mat)
                e_bar_prime_i = self.subfunctions.fz_dz_norm_n(e_bar_prime_i)

            v_bar_i = self.subfunctions.fz_vec_sub_n(e_bar, e_bar_prime_i)
            v_bar.append(v_bar_i)

        return v_bar

    def v_bar_post_norm(self, v_bar_pre_norm):
        v_bar = []
        for i in range(self.params.t):
            v_bar[i] = self.subfunctions.fz_dz_norm_n(v_bar_pre_norm[i])
        
        