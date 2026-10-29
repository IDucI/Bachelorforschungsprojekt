import sys
import subprocess
import random
from pathlib import Path
import chipwhisperer as cw

# =============================================================================
# Path setup
# =============================================================================

base_dir = Path(__file__).resolve().parent
libcross_dir = base_dir.parent.parent.parent / "libcross"
build_dir = libcross_dir / "build"

if str(libcross_dir) not in sys.path:
    sys.path.insert(0, str(libcross_dir))

from cross import Cross
from cross.cross_calculations import SignCalculationResult, KeygenCalculationResult

# =============================================================================
# Parameter setup and other important declarations
# =============================================================================

PARAMETER_SETS = [
    ("RSDP", 1, "fast"),
    ("RSDP", 1, "balanced"),
    ("RSDP", 1, "small"),
    ("RSDP", 3, "fast"),
    ("RSDP", 3, "balanced"),
    ("RSDP", 3, "small"),
    ("RSDP", 5, "fast"),
    ("RSDP", 5, "balanced"),
    ("RSDP", 5, "small"),
    ("RSDPG", 1, "fast"),
    ("RSDPG", 1, "balanced"),
    ("RSDPG", 1, "small"),
    ("RSDPG", 3, "fast"),
    ("RSDPG", 3, "balanced"),
    ("RSDPG", 3, "small"),
    ("RSDPG", 5, "fast"),
    ("RSDPG", 5, "balanced"),
    ("RSDPG", 5, "small"),
]

baudrate = 230400

# Input chunks are fixed because firmware set_value() accepts 160-byte normal data packets.
input_chunk_size = 160

# SimpleSerial data packets are limited to 160 bytes.
# Outputs larger than 160 bytes are therefore requested in 160-byte chunks.
output_chunk_size = 160

# Generate a new random base seed for every test run.
random_seed = random.SystemRandom().randint(0, 2**32 - 1)
print(f"Random seed: {random_seed}")

# SUBROUTINE IDS
subroutine_convert_restr_vec_to_fp          = 0x03
subroutine_restr_vec_by_fp_matrix           = 0x04 
subroutine_pack_fz_vec                      = 0x05
subroutine_pack_fz_rsdp_g_vec               = 0x05
subroutine_pack_fp_syn                      = 0x06
subroutine_fz_vec_sub_n                     = 0x07
subroutine_fp_vec_by_fp_matrix              = 0x08
subroutine_fp_vec_by_fp_vec_pointwise       = 0x09
subroutine_fz_vec_sub_m                     = 0x10
subroutine_fz_inf_w_by_fz_matrix            = 0x11
subroutine_fp_vec_by_restr_vec_scaled       = 0x12
subroutine_fz_dz_norm_n                     = 0x13
subroutine_fz_dz_norm_m                     = 0x14
subroutine_fp_dz_norm_synd                  = 0x15



# =============================================================================
# USB / Chipwhisperer
# =============================================================================

def release_cdc_acm() -> None:
    """
    Release Linux CDC-ACM driver under WSL.
    """
    subprocess.run(["sudo", "modprobe", "-r", "cdc_acm"], check=False)

# =============================================================================
# Buffer Logic
# =============================================================================

def board_write_buffer(target, data: bytes) -> None:
    """
    Write input data to the STM32 buffer in 160-byte chunks.
    """
    data = bytes(data)

    if not data:
        raise ValueError("Can't write empty buffer.")

    number_of_chunks = (len(data) + input_chunk_size - 1) // input_chunk_size

    if number_of_chunks > 128:
        raise ValueError("More than 128 input chunks are not supported.")

    for chunk_index, offset in enumerate(range(0, len(data), input_chunk_size)):
        # Split input into firmware-compatible chunks.
        chunk = data[offset:offset + input_chunk_size]

        # Pad the final chunk to the required 160-byte size.
        if len(chunk) < input_chunk_size:
            chunk += bytes(input_chunk_size - len(chunk))

        # Send the input chunk using the ChipWhisperer SimpleSerial2 library.
        target.send_cmd(ord("s"), chunk_index, chunk)

        response = target.read_cmd(timeout=2000)

        if response is None:
            raise TimeoutError("Timeout while waiting for ACK from STM32")

        cmd = response[1]
        ack_data = response[3:-2]

        if cmd != ord("e"):
            raise RuntimeError(f"Expected ACK 'e', got 0x{cmd:02X}")

        if len(ack_data) != 1 or ack_data[0] != 0:
            raise RuntimeError(f"STM32 returned error: {ack_data!r}")


def board_run_chunked_subroutine(
    target,
    subroutine_id,
    input_data,
    output_len,
    chunk_size,
    timeout_ms = 5000
):
    """
    Execute a subroutine whose output must be requested in multiple chunks.
    """
    # Calculate the number of required output requests.
    number_of_chunks = (output_len + chunk_size - 1) // chunk_size

    if number_of_chunks > 256:
        raise ValueError("More than 256 output chunks are not supported.")

    # The complete input is written before requesting output chunks.
    board_write_buffer(target, bytes(input_data))
    
    output = bytearray()

    for chunk_index in range(number_of_chunks):
        # Request the current output chunk from the firmware.
        request = bytes([chunk_index, 0, 0])

        target.send_cmd(ord("b"), subroutine_id, request)

        while True:
            response = target.read_cmd(timeout=timeout_ms)

            if response is None:
                raise TimeoutError("Timeout while waiting for subroutine response")

            cmd = response[1]
            data = response[3:-2]

            # 'd' indicates an intermediate data/status message.
            if cmd == ord("d"):
                continue

            # 'e' indicates a firmware error.
            if cmd == ord("e"):
                error = data[0] if len(data) == 1 else None

                raise RuntimeError(
                    f"Subroutine 0x{subroutine_id:02X}, output chunk "
                    f"{chunk_index}: firmware error {error!r}"
                )

            if cmd != ord("r"):
                raise RuntimeError(
                    f"Subroutine 0x{subroutine_id:02X}, output chunk "
                    f"{chunk_index}: expected 'r', got 0x{cmd:02X}"
                )
            break

        # The final chunk may contain fewer bytes than the normal chunk size.
        expected_len = min(chunk_size, output_len - chunk_index * chunk_size)

        if len(data) != expected_len:
            raise RuntimeError(
                f"Subroutine 0x{subroutine_id:02X}, output chunk "
                f"{chunk_index}: expected {expected_len} bytes, "
                f"got {len(data)}"
            )

        # Append the received chunk to the complete output.
        output.extend(data)

        response = target.read_cmd(timeout=timeout_ms)

        if response is None:
            raise TimeoutError("Timeout while waiting for subroutine response")

        ack_cmd = response[1]
        ack_data = response[3:-2]

        if ack_cmd != ord("e"):
            raise RuntimeError(f"Expected ACK 'e', got 0x{ack_cmd:02X}")

        if len(ack_data) != 1 or ack_data[0] != 0:
            raise RuntimeError(f"STM32 returned error: {ack_data!r}")

    return bytes(output)

# =============================================================================
# Test case helper function
# =============================================================================

def random_bytes(rng, length): 
    """
    Generate a sequence of random bytes using the test RNG.
    """
    return bytes(rng.randrange(256) for _ in range(length)) 

def intermediate_results(c: Cross, rng):
        """
        Generate the reference intermediate values used by the board tests.

        A key-generation result and a signing result are created so that the
        corresponding intermediate values can be used by the individual tests.
        """
        keygen = c.calculation.keygen()
        
        message = random_bytes(rng, 32)

        sign = c.calculation.sign(message)

        return keygen, sign

# Convert Python integer lists to the byte representation expected by the firmware interface.
# The required element width depends on whether the values represent FZ_ELEM or FP_ELEM.
def fz_to_bytes(values):
    # FZ_ELEM is uint8_t for both RSDP and RSDPG.
    return bytes(values)


def fp_to_bytes(values, c):
    # FP_ELEM is uint8_t for RSDP and uint16_t for RSDPG.
    byte_length = 2 if c.params.algorithm == "RSDPG" else 1

    return b"".join(
        int(value).to_bytes(byte_length, "little")
        for value in values
    )


def test_intermediate_values(
    target,
    subroutine_id,
    name,
    inputs,
    outputs
):
    """
    Test a subroutine using intermediate values generated by the Python reference implementation.
    inputs: Actual inputs used by the Python reference execution.
    outputs: Expected outputs produced by the Python reference execution.
    """
    if len(inputs) != len(outputs):
        raise RuntimeError(
            f"{name}: number of inputs and outputs differs "
            f"({len(inputs)} != {len(outputs)})"
        )
    # Test every reference input/output pair.
    for round_index, (inp, expected) in enumerate(zip(inputs, outputs)):
        if not isinstance(inp, bytes):
            raise TypeError(f"{name}: input must be serialized to bytes")
        
        if not isinstance(expected, bytes):
            raise TypeError(f"{name}: output must be serialized to bytes")

        # Send the reference input to the STM32 and execute the selected firmware subroutine.
        # The output may be larger than one SimpleSerial packet, therefore it is received in multiple chunks.
        actual = board_run_chunked_subroutine(
            target,
            subroutine_id,
            inp,
            len(expected),
            output_chunk_size
        )
        # Compare the result produced by the STM32 with the output produced by the Python CROSS reference implementation.
        compare(
            f"{name} round {round_index}",
            expected,
            actual
        )


def compare(name, expected, actual):
    """
    Compare reference output with board output.
    If a mismatch occurs, report the first differing index and a small surrounding window to make debugging easier.
    """
    expected = list(expected)
    actual = list(actual)

    if expected == actual:
        return

    limit = min(len(expected), len(actual))
    first = None

    # Find the first differing element.
    for index in range(limit):
        if expected[index] != actual[index]:
            first = index
            break

    # No differing element means that only the lengths are different.
    if first is None:
        raise AssertionError(f"{name}: length mismatch: expected {len(expected)}, actual {len(actual)}")

    # Show a small region around the first mismatch.
    start = max(0, first - 4)
    end = min(limit, first + 5)

    raise AssertionError(
        f"{name}: first mismatch at index {first}: "
        f"expected={expected[first]}, actual={actual[first]}\n"
        f"expected[{start}:{end}]={expected[start:end]}\n"
        f"actual[{start}:{end}]={actual[start:end]}"
    )

# =============================================================================
# Subroutine test cases
# =============================================================================

def test_intermediate_convert_restr_vec_to_fp(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `convert_restr_vec_to_fp` using an intermediate value from the CROSS signing procedure.
    The input is the restricted vector v_bar.
    The expected output is the corresponding vector v after conversion to FP.
    """
    c_v_bar = result.convert_restr_vec_to_fp.v_bar[i]
    c_v = result.convert_restr_vec_to_fp.v[i]

    # Input: FZ_ELEM v_bar[N]
    inputs = [fz_to_bytes(c_v_bar)]

    # Output: FP_ELEM v[N]
    outputs = [fp_to_bytes(c_v, c)]
    
    test_intermediate_values(
        target,
        subroutine_convert_restr_vec_to_fp,
        "convert_restr_vec_to_fp",
        inputs,
        outputs
    )


def test_intermediate_restr_vec_by_fp_matrix(target, c: Cross, result: KeygenCalculationResult):
    """
    Test `restr_vec_by_fp_matrix` with the actual intermediate values
    generated during CROSS key generation.
    
    The subroutine receives the restricted vector e_bar and the matrix V_tr
    and produces the syndrome vector s.
    """
    c_e_bar = result.restr_vec_by_fp_matrix.e_bar
    c_V_tr = result.restr_vec_by_fp_matrix.V_tr
    c_s = result.restr_vec_by_fp_matrix.s

    # Input: FZ_ELEM e_bar[N] || FP_ELEM V_tr[K][N-K]
    inputs = [fz_to_bytes(c_e_bar) + fp_to_bytes(c_V_tr, c)]

    # Output: FP_ELEM s[N-K].
    outputs = [fp_to_bytes(c_s, c)]

    test_intermediate_values(
        target,
        subroutine_restr_vec_by_fp_matrix,
        "restr_vec_by_fp_matrix",
        inputs,
        outputs
    )


def test_intermediate_pack_fp_syn(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `pack_fp_syn` using an intermediate value from the CROSS signing procedure.
    The input is the FP syndrome vector s_prime.
    The expected output is its densely packed byte representation.
    """
    c_s_prime_in = result.pack_fp_syn.s_prime_in[i]
    c_s_prime_out = result.pack_fp_syn.s_prime_out[i]

    # Input: FP_ELEM s_prime[N-K]
    inputs = [fp_to_bytes(c_s_prime_in, c)]

    # Output: uint8_t out[DENSELY_PACKED_FP_SYN_SIZE]
    outputs = [bytes(c_s_prime_out)]

    test_intermediate_values(
        target,
        subroutine_pack_fp_syn,
        "pack_fp_syn",
        inputs,
        outputs
    )


def test_intermediate_fz_vec_sub_n(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fz_vec_sub_n` using intermediate values from the CROSS signing procedure.
    The inputs are the restricted vectors e_bar and e_bar_prime.
    The expected output is the resulting restricted vector v_bar.
    """
    c_e_bar = result.fz_vec_sub_n.e_bar
    c_e_bar_prime = result.fz_vec_sub_n.e_bar_prime[i]
    c_v_bar = result.fz_vec_sub_n.v_bar[i]

    # Input: FZ_ELEM e_bar[N] || FZ_ELEM e_bar_prime[N]
    inputs = [fz_to_bytes(c_e_bar) + fz_to_bytes(c_e_bar_prime)]

    # Output: FZ_ELEM v_bar[N]
    outputs = [fz_to_bytes(c_v_bar)]

    test_intermediate_values(
        target,
        subroutine_fz_vec_sub_n,
        "fz_vec_sub_n",
        inputs,
        outputs
    )


def test_intermediate_fp_vec_by_fp_matrix(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fp_vec_by_fp_matrix` using intermediate values from the CROSS signing procedure.
    The inputs are the FP vector u and the matrix V_tr.
    The expected output is the resulting FP syndrome vector s_prime.
    """
    c_u = result.fp_vec_by_fp_matrix.u[i]
    c_V_tr = result.fp_vec_by_fp_matrix.V_tr
    c_s_prime = result.fp_vec_by_fp_matrix.s_prime[i]

    # Input: FP_ELEM u[N] || FP_ELEM V_tr[K][N-K]
    inputs = [fp_to_bytes(c_u, c) + fp_to_bytes(c_V_tr, c)]

    # Output: FP_ELEM s_prime[N-K]
    outputs = [fp_to_bytes(c_s_prime, c)]

    test_intermediate_values(
        target,
        subroutine_fp_vec_by_fp_matrix,
        "fp_vec_by_fp_matrix",
        inputs,
        outputs
    )


def test_intermediate_fp_vec_by_fp_vec_pointwise(target, c:Cross, result: SignCalculationResult, i):
    """
    Test `fp_vec_by_fp_vec_pointwise` using intermediate values from the CROSS signing procedure.
    The inputs are the FP vectors u_prime and v.
    The expected output is the resulting FP vector u.
    """
    c_u_prime = result.fp_vec_by_fp_vec_pointwise.u_prime[i]
    c_v = result.fp_vec_by_fp_vec_pointwise.v[i]
    c_u = result.fp_vec_by_fp_vec_pointwise.u[i]
    # Input: FP_ELEM u_prime[N] || FP_ELEM v[N]
    inputs = [fp_to_bytes(c_u_prime, c) + fp_to_bytes(c_v, c)]

    # Output: FP_ELEM u[N]
    outputs = [fp_to_bytes(c_u, c)]

    test_intermediate_values(
        target,
        subroutine_fp_vec_by_fp_vec_pointwise,
        "fp_vec_by_fp_vec_pointwise",
        inputs,
        outputs
    )


def test_intermediate_fp_vec_by_restr_vec_scaled(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fp_vec_by_restr_vec_scaled` using intermediate values from the CROSS signing procedure.
    The inputs are the restricted vector e_bar_prime, the challenge value chall_1
    and the FP vector u_prime.
    The expected output is the resulting FP vector y.
    """
    c_e_bar_prime = result.fp_vec_by_restr_vec_scaled.e_bar_prime[i]
    c_chall_1 = result.fp_vec_by_restr_vec_scaled.chall_1[i]
    c_u_prime = result.fp_vec_by_restr_vec_scaled.u_prime[i]
    c_y = result.fp_vec_by_restr_vec_scaled.y[i]

    # Input: FZ_ELEM e_bar_prime[N] || FP_ELEM chall_1 || FP_ELEM u_prime[N]
    inputs = [fz_to_bytes(c_e_bar_prime) + fp_to_bytes([c_chall_1] ,c) + fp_to_bytes(c_u_prime, c)]

    # Output: FP_ELEM y[N]
    outputs = [fp_to_bytes(c_y, c)]

    test_intermediate_values(
        target,
        subroutine_fp_vec_by_restr_vec_scaled,
        "fp_vec_by_restr_vec_scaled",
        inputs,
        outputs
    )


def test_intermediate_fz_dz_norm_n(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fz_dz_norm_n` using intermediate values from the CROSS signing procedure.
    The input is the restricted vector v_bar before normalization.
    The expected output is the resulting normalized restricted vector v_bar.
    """
    c_v_bar_in = result.fz_dz_norm_n.v_bar_in[i]
    c_v_bar_out = result.fz_dz_norm_n.v_bar_out[i]

    # Input: FZ_ELEM v_bar_in[N]
    inputs = [fz_to_bytes(c_v_bar_in)]

    # Output: FZ_ELEM v_bar_out[N]
    outputs = [fz_to_bytes(c_v_bar_out)]
    test_intermediate_values(
        target,
        subroutine_fz_dz_norm_n,
        "fz_dz_norm_n",
        inputs,
        outputs
    )

# =============================================================================
# RSDP only subroutine tests
# =============================================================================

def test_intermediate_pack_fz_vec(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `pack_fz_vec` using intermediate values from signing round i.

    The subroutine packs the FZ vector v_bar into its compact byte
    representation used by the CROSS signing procedure.
    """
    c_v_bar_in = result.pack_fz_vec.v_bar_in[i]
    c_v_bar_out = result.pack_fz_vec.v_bar_out[i]

    # Input: FZ_ELEM v_bar[N]
    inputs = [fz_to_bytes(c_v_bar_in)]

    # Output: packed byte representation of v_bar
    outputs = [c_v_bar_out]

    test_intermediate_values(
        target,
        subroutine_pack_fz_vec,
        "pack_fz_vec",
        inputs,
        outputs
    )


def test_intermediate_fz_vec_sub_m(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fz_vec_sub_m` using intermediate values from the CROSS signing procedure.
    The inputs are the restricted vectors e_G_bar and e_G_bar_prime.
    The expected output is the resulting restricted vector v_G_bar.
    """
    c_e_G_bar = result.fz_vec_sub_m.e_G_bar
    c_e_G_bar_prime = result.fz_vec_sub_m.e_G_bar_prime[i]
    c_v_G_bar = result.fz_vec_sub_m.v_G_bar[i]

    # Input: FZ_ELEM e_G_bar[M] || FZ_ELEM e_G_bar_prime[M]
    inputs = [fz_to_bytes(c_e_G_bar) + fz_to_bytes(c_e_G_bar_prime)]

    # Output: FZ_ELEM v_G_bar[M]
    outputs = [fz_to_bytes(c_v_G_bar)]

    test_intermediate_values(
        target,
        subroutine_fz_vec_sub_m,
        "fz_vec_sub_m",
        inputs,
        outputs
    )


def test_intermediate_fz_inf_w_by_fz_matrix(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fz_inf_w_by_fz_matrix` using intermediate values from the CROSS signing procedure.
    The inputs are the restricted vector e_G_bar_prime and the matrix W_mat.
    The expected output is the resulting restricted vector e_bar_prime.
    """
    c_e_bar_prime = result.fz_inf_w_by_fz_matrix.e_bar_prime[i]
    c_e_G_bar_prime = result.fz_inf_w_by_fz_matrix.e_G_bar_prime[i]
    c_W_mat = result.fz_inf_w_by_fz_matrix.W_mat

    # Input: FZ_ELEM e_G_bar_prime[M] || FZ_ELEM W_mat[M][N-M]
    inputs = [fz_to_bytes(c_e_G_bar_prime) + fz_to_bytes(c_W_mat)]

    # Output: FZ_ELEM e_bar_prime[N]
    outputs = [fz_to_bytes(c_e_bar_prime)]

    test_intermediate_values(
        target,
        subroutine_fz_inf_w_by_fz_matrix,
        "fz_inf_w_by_fz_matrix",
        inputs,
        outputs
    )


def test_intermediate_fz_dz_norm_m(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fz_dz_norm_m` using intermediate values from the CROSS signing procedure.
    The input is the restricted vector v_G_bar before normalization.
    The expected output is the resulting normalized restricted vector v_G_bar.
    """
    c_v_G_bar_in = result.fz_dz_norm_m.v_G_bar_in[i]
    c_v_G_bar_out = result.fz_dz_norm_m.v_G_bar_out[i]

    # Input: FZ_ELEM v_G_bar_in[M]
    inputs = [fz_to_bytes(c_v_G_bar_in)]

    # Output: FZ_ELEM v_G_bar_out[M]
    outputs = [fz_to_bytes(c_v_G_bar_out)]

    test_intermediate_values(
        target,
        subroutine_fz_dz_norm_m,
        "fz_dz_norm_m",
        inputs,
        outputs
    )

def test_intermediate_pack_fz_rsdp_g_vec(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `pack_fz_rsdp_g_vec` using intermediate values from the CROSS signing procedure.
    The input is the restricted vector v_G_bar.
    The expected output is the resulting packed representation v_G_bar_out.
    """
    c_v_G_bar_in = result.pack_fz_rsdp_g_vec.v_G_bar_in[i]
    c_v_G_bar_out = result.pack_fz_rsdp_g_vec.v_G_bar_out[i]

    # Input: FZ_ELEM v_G_bar_in[M]
    inputs = [fz_to_bytes(c_v_G_bar_in)]

    # Output: uint8_t v_G_bar_out[DENSELY_PACKED_FZ_RSDP_G_VEC_SIZE]
    outputs = [c_v_G_bar_out]

    test_intermediate_values(
            target,
            subroutine_pack_fz_rsdp_g_vec,
            "pack_fz_rsdp_g_vec",
            inputs,
            outputs
        )

def test_intermediate_fp_dz_norm_synd(target, c: Cross, result: SignCalculationResult, i):
    """
    Test `fp_dz_norm_synd` using intermediate values from the CROSS signing procedure.
    The input is the syndrome vector s_prime before normalization.
    The expected output is the normalized syndrome vector.
    """
    c_s_prime_in = result.fp_dz_norm_synd.s_prime_in[i]
    c_s_prime_out = result.fp_dz_norm_synd.s_prime_out[i]

    # Input: FP_ELEM s_prime[N-K]
    inputs = [fp_to_bytes(c_s_prime_in, c)]

    # Output: FP_ELEM s_prime[N-K]
    outputs = [fp_to_bytes(c_s_prime_out, c)]

    test_intermediate_values(
        target,
        subroutine_fp_dz_norm_synd,
        "fp_dz_norm_synd",
        inputs,
        outputs
    )

# =============================================================================
# Intermediate subroutine test suite
# =============================================================================

# Each entry: (name, test function, source, round_specific)
# source: "sign" or "keygen"
# round_specific: True  = multiple calls per signature (test one random round)
#                 False = single call (no round selection)
COMMON_INTERMEDIATE_TESTS = [
    ("convert_restr_vec_to_fp", test_intermediate_convert_restr_vec_to_fp, "sign", True),
    ("restr_vec_by_fp_matrix", test_intermediate_restr_vec_by_fp_matrix, "keygen", False),
    ("pack_fp_syn", test_intermediate_pack_fp_syn, "sign", True),
    ("fz_vec_sub_n", test_intermediate_fz_vec_sub_n, "sign", True),
    ("fp_vec_by_fp_matrix", test_intermediate_fp_vec_by_fp_matrix, "sign", True),
    ("fp_vec_by_fp_vec_pointwise", test_intermediate_fp_vec_by_fp_vec_pointwise, "sign", True),
    ("fp_vec_by_restr_vec_scaled", test_intermediate_fp_vec_by_restr_vec_scaled, "sign", True),
    ("fz_dz_norm_n", test_intermediate_fz_dz_norm_n, "sign", True),
    ("fp_dz_norm_synd", test_intermediate_fp_dz_norm_synd, "sign", True),
]

RSDP_INTERMEDIATE_TESTS = [
    ("pack_fz_vec", test_intermediate_pack_fz_vec, "sign", True),
]

RSDPG_INTERMEDIATE_TESTS = [
    ("fz_vec_sub_m", test_intermediate_fz_vec_sub_m, "sign", True),
    ("fz_inf_w_by_fz_matrix", test_intermediate_fz_inf_w_by_fz_matrix, "sign", True),
    ("fz_dz_norm_m", test_intermediate_fz_dz_norm_m, "sign", True),
    ("pack_fz_rsdp_g_vec", test_intermediate_pack_fz_rsdp_g_vec, "sign", True),
]

def run_intermediate_tests(target, c: Cross):
    """
    Run tests using intermediate values generated by the reference implementation.
    """
    tests = list(COMMON_INTERMEDIATE_TESTS)

    if c.params.algorithm == "RSDP":
        tests.extend(RSDP_INTERMEDIATE_TESTS)
    elif c.params.algorithm == "RSDPG":
        tests.extend(RSDPG_INTERMEDIATE_TESTS)

    rng = random.Random(
        random_seed
        + 500000
        + c.params.category * 100000
        + (1000000 if c.params.algorithm == "RSDPG" else 0)
    )

    keygen, sign = intermediate_results(c, rng)

    print()
    print("============================================================")
    print(" Intermediate-value tests")
    print("============================================================")
    print()

    for name, test_function, source, round_specific in tests:
        print(f"{name:<38}", end = "", flush = True)

        result = sign if source == "sign" else keygen

        try:
            # Execute the selected test.
            if round_specific:
                # Select a random signing round for this subroutine test.
                i = rng.randrange(c.params.t)
                test_function(target, c, result, i)
            else:
                test_function(target, c, result)

        except Exception as exc:
            import traceback

            print(" Fail")
            traceback.print_exc()
            print()
            print("============================================================")
            print("INTERMEDIATE TEST FAILURE")
            print("============================================================")
            print(f"Subroutine : {name}")
            print(f"Exception  : {type(exc).__name__}: {exc}")
            print("============================================================")
            return False, f"{name} intermediate test failed"

        print(" Pass")

    print()
    print("============================================================")
    print(f" {len(tests)}/{len(tests)} intermediate tests passed.")
    print("============================================================")

    return True, ""

# =============================================================================
# Single variant
# =============================================================================

def run_single_variant(target, family: str, category: int, variant: str):
    """
    Run the intermediate subroutine test suite for one firmware variant.
    """
    print()
    print("============================================================")
    print(f" Variant: {family} Cat-{category} {variant}")
    print("============================================================")

    print()
    print("Creating host-side CROSS instance...")

    # Create the Python reference implementation for exactly the same
    # algorithm/category/optimization combination as the firmware.
    c = Cross(
        path = str(build_dir),
        algorithm = family,
        category = category,
        optimization = variant
    )

    print("CROSS instance created.")
    print()
    print(
        f"Parameters: p={c.params.p}, z={c.params.z}, "
        f"n={c.params.n}, k={c.params.k}, m={c.params.m}, "
        f"t={c.params.t}"
    )

    # Run all intermediate-value tests for this parameter set.
    return run_intermediate_tests(target, c)

# =============================================================================
# Main
# =============================================================================

def main():
    """
    Connect to the board, execute the selected tests and report the result.
    """
    print()
    print("============================================================")
    print(" CROSS Board Reference Test")
    print("============================================================")

    # Read parameter set from the command line.
    if len(sys.argv) == 4:

        family = sys.argv[1]
        category = int(sys.argv[2])
        variant = sys.argv[3]

        parameter_set = (family, category, variant)

        if parameter_set not in PARAMETER_SETS:
            print(f"Invalid parameter set: {family} {category} {variant}")
            return 1

        parameter_sets = [parameter_set]

    elif len(sys.argv) == 1:

        parameter_sets = PARAMETER_SETS
    else:
        print("Usage:")
        print("  python3 board_test.py")
        print("  python3 board_test.py RSDP 1 fast")
        return 1

    print(f"Variants: {len(parameter_sets)}")

    print()

    # Release USB serial driver, to avoid an error.
    release_cdc_acm()

    scope = None
    target = None

    try:
        # ChipWhisperer
        print("Connecting to ChipWhisperer...")

        scope = cw.scope()

        scope.default_setup()

        scope.io.clkout = 16e6

        target = cw.target(scope, cw.targets.SimpleSerial2)

        target.baud = baudrate

        print(f"Target type: {type(target).__name__}")

        print(f"Target baudrate: {target.baud}")

        # Initial communication reset after connecting to the target.
        target.reset_comms()
        print("        Communication reset done.")

        print()
        print("ChipWhisperer connection successful.")

        # Test each selected variant
        overall_passed = True

        for family, category, variant in parameter_sets:

            print()
            print("=" * 60)
            print(f" Testing: {family} Cat-{category} {variant} ")
            print("=" * 60)

            # Reset SimpleSerial2 communication before each variant.
            target.reset_comms()
            print("        Communication reset done.")

            try:
                passed, error = run_single_variant(target, family, category, variant)
                if passed:
                    print()
                    print(f"Pass: {family} Cat-{category} {variant}")
                else:
                    print()
                    print(f"Fail: {family} Cat-{category} {variant}")
                    print(f"    Error: {error}")

                    overall_passed = False

            except Exception as err:
                print()
                print(f"Exception: {family} Cat-{category} {variant}")
                print(f"    {type(err).__name__}: {err}")

                overall_passed = False

        # Final result
        print()
        print("=" * 60)
        print(" Final Result")
        print("=" * 60)

        if overall_passed:
            print("Pass")
            return 0
        else:
            print("Fail")
            return 1
    except Exception as err:
        print()
        print("=" * 60)
        print(" Exception")
        print("=" * 60)

        print(f"{type(err).__name__}: {err}")

        return 1

if __name__ == "__main__":
    sys.exit(main())