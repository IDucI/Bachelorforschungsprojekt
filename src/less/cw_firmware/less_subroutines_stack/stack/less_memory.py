import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libless" / "less"))

from less_params import get_params, PARAMETER_SETS


MAX_PUBLISHED_SEEDS = {
    (1, 192): 87,
    (1, 68): 26,
    (1, 45): 11,
    (3, 220): 119,
    (3, 102): 41,
    (5, 345): 169,
    (5, 137): 58,
}


with open(Path(__file__).with_name("less_memory.csv"), "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Variant", "Subroutine", "CCMRAM_Bytes", "SRAM_Bytes", "Stack_Buffer_Bytes", "Total_Bytes"])

    for category, target in PARAMETER_SETS:
        params = get_params(category, target)

        fq_size = 1
        position_size = 2
        row_size = (params.n - params.k) * fq_size
        monomial_size = params.n * (fq_size + position_size)
        generator_size = ((params.k * params.n_pad * fq_size + 31) // 32) * 32

        fq_inv = (fq_size, fq_size, 0)
        row_mul3 = (2 * row_size, row_size, 0)
        generator_sample = (params.seed_length_bytes, params.k * row_size + (params.n - params.k) * position_size, params.seed_length_bytes)
        monomial_sample_prikey = (params.private_key_seed_length_bytes, monomial_size, params.private_key_seed_length_bytes)
        generator_monomial_mul = (params.k * params.n_pad * fq_size + monomial_size, 2 * generator_size, monomial_size)

        memory = {
            "fq_inv": fq_inv,
            "row_mul3": row_mul3,
            "generator_sample": generator_sample,
            "monomial_sample_prikey": monomial_sample_prikey,
        }

        if category in (None, 1):
            memory["generator_monomial_mul"] = generator_monomial_mul

        if category is not None:
            rref_packed = (params.q.bit_length() * (params.n - params.k) * params.k + 7) // 8 + (params.n + 7) // 8
            secret_key = params.private_key_seed_length_bytes
            public_key = params.seed_length_bytes + (params.num_keypairs - 1) * rref_packed
            signature = 4 * params.seed_length_bytes + params.w * ((params.n + 7) // 8) + MAX_PUBLISHED_SEEDS[(category, target)] * params.seed_length_bytes + 1

            memory["keygen"] = (secret_key + public_key, 0, 0)
            memory["sign"] = (secret_key + signature, 0, 0)
            memory["verify"] = (public_key + signature, 0, 0)

        for name, (ccmram, sram, stack) in memory.items():
            writer.writerow([params.version, name, ccmram, sram, stack, ccmram + sram + stack])
