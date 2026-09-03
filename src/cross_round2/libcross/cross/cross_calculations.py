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

    def e_bar(self, seed_sk):
        e_bar, _ = self.subfunctions.expand_sk(seed_sk)
        return e_bar

    def v_tr(self, seed_sk):
        _, v_tr = self.subfunctions.expand_sk(seed_sk)
        return v_tr

    def seed_tree(self, root_seed, salt):
        return self.subfunctions.gen_seed_tree(root_seed, salt)

    def round_seeds(self, seed_tree):
        return self.subfunctions.seed_leaves(seed_tree)

    def round_seed(self, round_seeds, i):
        start = i * self.seed_length_bytes
        end = start + self.seed_length_bytes
        return round_seeds[start:end]
    
    # def csprng_input(self, round_seed, salt):
    #     return round_seed + salt

    # def domain_sep_csprng(self, i):
    #     return self.params.csprng_domain_sep_const + i + (2 * self.t-1)

    def e_bar_prime_i(self, round_seed, salt, i):
        csprng_input = round_seed + salt
        dsc = self.params.csprng_domain_sep_const + i + (2 * self.t-1)

        state = self.subfunctions.csprng_initialize(csprng_input, len(csprng_input), dsc)
        return self.subfunctions.csprng_fz_vec(state)

    def v_bar_i(self, seed_sk, root_seed, salt, i):
        e_bar = self.e_bar(seed_sk)

        seed_tree   = self.seed_tree(root_seed, salt)
        round_seeds = self.round_seeds(seed_tree)
        round_seed  = self.round_seed(round_seeds, i)

        e_bar_prime_i = self.e_bar_prime_i(round_seed, salt, i)

        return self.subfunctions.fz_vec_sub_n(e_bar, e_bar_prime_i)
        
        