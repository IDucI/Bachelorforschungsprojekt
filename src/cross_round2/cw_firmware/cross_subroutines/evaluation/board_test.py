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

# Number of independent random inputs tested for each subroutine.
rounds_per_subroutine = 5

# Generate a new random base seed for every test run.
random_seed = random.SystemRandom().randint(0, 2**32 - 1)
print(f"Random seed: {random_seed}")

# SUBROUTINE IDS
subroutine_convert_restr_vec_to_fp          = 0x03
subroutine_restr_vec_by_fp_matrix           = 0x04 
subroutine_pack_fz_vec                      = 0x05
subroutine_pack_fp_syn                      = 0x06
subroutine_unpack_fz_vec                    = 0x07
subroutine_fz_vec_sub_n                     = 0x08
subroutine_fp_vec_by_fp_matrix              = 0x09
subroutine_fp_vec_by_fp_vec_pointwise       = 0x10
subroutine_fz_vec_sub_m                     = 0x11
subroutine_fz_inf_w_by_fz_matrix            = 0x12
subroutine_fp_vec_by_restr_vec_scaled       = 0x13
subroutine_expand_digest_to_fixed_weight    = 0x14
subroutine_fz_dz_norm_n                     = 0x15
subroutine_fz_dz_norm_m                     = 0x16
subroutine_expand_pk                        = 0x17
subroutine_expand_sk                        = 0x18

# =============================================================================
# USB / Chipwhisperer
# =============================================================================

def release_cdc_acm() -> None:
    """
    Release Linux CDC-ACM driver under WSL.
    """
    subprocess.run(["sudo", "modprobe", "-r", "cdc_acm"], check=False)


# =============================================================================
# BUFFER & BOARD COMMUNICATIONS
# =============================================================================

def reset_serial_communication(target) -> None:
    """
    Reset/flush SimpleSerial2 communication. This removes stale bytes before the real test.
    """
    try:
        # SimpleSerial2 provides this helper.
        target.reset_comms()
        print("        Communication reset done.")

    except Exception as err:
        print("        WARNING: reset_comms() failed:", err)
        try:
            target.flush()
            print("        Fallback flush done.")
        except Exception as flush_err:
            print("        WARNING: flush() failed:", flush_err)


def board_write_buffer(target, data: bytes) -> None:
    """
    Write input data to the STM32 buffer in 160-byte chunks.
    """
    data = bytes(data)

    if not data:
        raise ValueError("Can't write empty buffer.")

    for chunk_index, offset in enumerate(range(0, len(data), input_chunk_size)):
        # Split input into firmware-compatible chunks.
        chunk = data[offset:offset + input_chunk_size]

        # Pad the final chunk to the required 160-byte size.
        if len(chunk) < input_chunk_size:
            chunk += bytes(input_chunk_size - len(chunk))

        # Send the input chunk using the ChipWhisperer SimpleSerial2 library.
        target.send_cmd(ord("s"), chunk_index, chunk)

        # Read and validate the firmware acknowledgement.
        cmd, ack_data = target.read_cmd(timeout=2000)

        if cmd != ord("e"):
            raise RuntimeError(f"Expected ACK 'e', got 0x{cmd:02X}")

        if len(ack_data) != 1 or ack_data[0] != 0:
            raise RuntimeError(f"STM32 returned error: {ack_data!r}")


def board_run_subroutine(
    target,
    subroutine_id: int,
    input_data: bytes,
    output_len: int,
    timeout_ms: int = 5000
) -> bytes:
    """
    Execute one firmware subroutine and return its output.
    """
    # Write the complete input to the STM32 buffer.
    board_write_buffer(target, input_data)

    # Trigger the selected subroutine.
    target.send_cmd(ord("b"), subroutine_id, b"")

    # Read the subroutine result.
    cmd, data = target.read_cmd(timeout=timeout_ms)

    if cmd != ord("r"):
        raise RuntimeError(f"Expected result command 'r', got 0x{cmd:02X}")

    # Verify that the firmware returned the expected output size.
    if len(data) != output_len:
        raise RuntimeError(
            f"Wrong board output length: "
            f"expected {output_len}, got {len(data)}"
        )

    # Read and validate the final acknowledgement.
    ack_cmd, ack_data = target.read_cmd(timeout=timeout_ms)

    if ack_cmd != ord("e"):
        raise RuntimeError(f"Expected ACK 'e', got 0x{ack_cmd:02X}")

    if len(ack_data) != 1 or ack_data[0] != 0:
        raise RuntimeError(f"STM32 returned error: {ack_data!r}")

    return bytes(data)

def board_run_chunked_subroutine(
    target,
    subroutine_id,
    input_data,
    output_len,
    chunk_size,
    timeout_ms=5000
):
    """
    Execute a subroutine whose output must be requested in multiple chunks.
    """
    # The complete input is written before requesting output chunks.
    board_write_buffer(target, bytes(input_data))

    output = bytearray()

    # Calculate the number of required output requests.
    number_of_chunks = (output_len + chunk_size - 1) // chunk_size

    for chunk_index in range(number_of_chunks):
        if chunk_index > 0x7F:
            raise ValueError("More than 128 output chunks are not supported.")

        # Request the current output chunk from the firmware.
        request = bytes([chunk_index, 0, 0])

        target.send_cmd(ord("b"), subroutine_id, request)

        while True:
            cmd, data = target.read_cmd(timeout=timeout_ms)

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

        # Read and validate the acknowledgement for this chunk.
        ack_cmd, ack_data = target.read_cmd(timeout=timeout_ms)

        if ack_cmd != ord("e"):
            raise RuntimeError(f"Expected ACK 'e', got 0x{ack_cmd:02X}")

        if len(ack_data) != 1 or ack_data[0] != 0:
            raise RuntimeError(f"STM32 returned error: {ack_data!r}")

    return bytes(output)

# =============================================================================
# Test case helper function
# =============================================================================

def random_fz(rng, c, length):
    """
    Generate a random vector over the field Z. Values are sampled uniformly from [0, z).
    """
    return [rng.randrange(c.params.z) for _ in range(length)]


def random_fp(rng, c, length):
    """
    Generate a random vector over the field F_p. Values are sampled uniformly from [0, p)
    """
    return [rng.randrange(c.params.p) for _ in range(length)]


def random_bytes(rng, length): 
    """
    Generate a sequence of random bytes using the test RNG.
    """
    return bytes(rng.randrange(256) for _ in range(length)) 


def fp_to_bytes(values, c):
    """
    Convert field elements to the byte representation used by the firmware.
    RSDP uses one byte per field element, while RSDP-(G) uses two little-endian bytes per field element.
    """
    if c.params.algorithm == "RSDPG":
        out = bytearray()
        for value in values:
            out.extend(int(value).to_bytes(2, "little"))
        return bytes(out)
    return bytes(int(value) & 0xFF for value in values)


def fp_from_bytes(data, cross):
    """
    Convert firmware byte output back into field elements. 
    RSDP-(G) uses two byte little-endian field elements. RSDP uses one byte per field element. 
    """
    if cross.params.algorithm == "RSDPG":
        if len(data) % 2:
            raise RuntimeError(f"RSDPG FP output has odd length: {len(data)}")
        return [
            int.from_bytes(data[index:index + 2], "little")
            for index in range(0, len(data), 2)
        ]
    return list(data)


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

def test_convert_restr_vec_to_fp(target, c, rng):
    """
    Test convert_restr_vec_to_fp using a random restricted vector.
    """
    inp = random_fz(rng, c, c.params.n)
    expected = c.subfunctions.convert_restr_vec_to_fp(inp)
    output_len = c.params.n * ( 2 if c.params.algorithm == "RSDPG" else 1)
    actual = board_run_chunked_subroutine(
        target, 
        subroutine_convert_restr_vec_to_fp, 
        bytes(inp), 
        output_len, 
        chunk_size = output_chunk_size
    )
    compare("convert_restr_vec_to_fp", expected, fp_from_bytes(actual, c))


def test_restr_vec_by_fp_matrix(target, c, rng):
    """
    Test multiplication of a restricted vector by an F_p matrix.
    """
    e = random_fz(rng, c, c.params.n)
    matrix = random_fp(rng, c, c.params.k * (c.params.n - c.params.k))
    expected = c.subfunctions.restr_vec_by_fp_matrix(e, matrix)
    input_data = bytes(e) + fp_to_bytes(matrix, c)
    actual = board_run_subroutine(
        target,
        subroutine_restr_vec_by_fp_matrix,
        input_data,
        (c.params.n - c.params.k) 
        * (2 if c.params.algorithm == "RSDPG" else 1)
    )
    compare("restr_vec_by_fp_matrix", expected,fp_from_bytes(actual, c))


def test_pack_fz_vec(target, c, rng):
    """
    Test packing of an F_z vector.
    """
    if c.params.algorithm == "RSDP":
        inp = random_fz(rng, c, c.params.n)
        expected = c.subfunctions.pack_fz_vec(inp)
    else:
        inp = random_fz(rng, c, c.params.m)
        expected = c.subfunctions.pack_fz_rsdp_g_vec(inp)
    actual = board_run_subroutine(
        target,
        subroutine_pack_fz_vec,
        bytes(inp),
        len(expected)
    )
    compare("pack_fz_vec", expected, actual)


def test_pack_fp_syn(target, c, rng):
    """
    Test packing of an F_p syndrome vector.
    """
    inp = random_fp(rng, c, c.params.n - c.params.k)
    expected = c.subfunctions.pack_fp_syn(inp)
    actual = board_run_subroutine(
        target,
        subroutine_pack_fp_syn,
        fp_to_bytes(inp, c),
        len(expected)
    )
    compare("pack_fp_syn", expected, actual)


def test_unpack_fz_vec(target, c, rng):
    """
    Test unpacking of a packed F_z vector.
    """
    original = random_fz(rng, c, c.params.n)
    packed = c.subfunctions.pack_fz_vec(original)
    expected = c.subfunctions.unpack_fz_vec(packed)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_unpack_fz_vec,
        packed,
        c.params.n,
        chunk_size = output_chunk_size
    )
    compare("unpack_fz_vec", expected, actual)


def test_fz_vec_sub_n(target, c, rng):
    """
    Test subtraction of two F_z vectors of length n.
    """
    a = random_fz(rng, c, c.params.n)
    b = random_fz(rng, c, c.params.n)
    expected = c.subfunctions.fz_vec_sub_n(a, b)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_fz_vec_sub_n,
        bytes(a) + bytes(b),
        c.params.n,
        chunk_size = output_chunk_size
    )
    compare("fz_vec_sub_n", expected, actual)


def test_fp_vec_by_fp_matrix(target, c, rng):
    """
    Test multiplication of an F_p vector by an F_p matrix.
    """
    e = random_fp(rng, c, c.params.n)
    matrix = random_fp(rng, c, c.params.k * (c.params.n - c.params.k))
    expected = c.subfunctions.fp_vec_by_fp_matrix(e, matrix)
    actual = board_run_subroutine(
        target,
        subroutine_fp_vec_by_fp_matrix,
        fp_to_bytes(e, c) + fp_to_bytes(matrix, c),
        (c.params.n - c.params.k) 
        * (2 if c.params.algorithm == "RSDPG" else 1)
    )
    compare("fp_vec_by_fp_matrix", expected, fp_from_bytes(actual, c))


def test_fp_vec_by_fp_vec_pointwise(target, c, rng):
    """
    Test pointwise multiplication of two F_p vectors.
    """
    a = random_fp(rng, c, c.params.n)
    b = random_fp(rng, c, c.params.n)
    expected = c.subfunctions.fp_vec_by_fp_vec_pointwise(a, b)
    output_len = c.params.n * (2 if c.params.algorithm == "RSDPG" else 1)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_fp_vec_by_fp_vec_pointwise,
        fp_to_bytes(a, c) + fp_to_bytes(b, c),
        output_len,
        chunk_size = output_chunk_size
    )
    compare("fp_vec_by_fp_vec_pointwise", expected, fp_from_bytes(actual, c))


def test_fz_vec_sub_m(target, c, rng):
    """
    Test subtraction of two F_z vectors of length m for RSDPG.
    """
    if c.params.algorithm != "RSDPG":
        return
    a = random_fz(rng, c, c.params.m)
    b = random_fz(rng, c, c.params.m)
    expected = c.subfunctions.fz_vec_sub_m(a, b)
    actual = board_run_subroutine(
        target,
        subroutine_fz_vec_sub_m,
        bytes(a) + bytes(b),
        c.params.m,
    )
    compare("fz_vec_sub_m", expected, actual)


def test_fz_inf_w_by_fz_matrix(target, c, rng):
    """
    Test F_z matrix multiplication used by the RSDPG variant.
    """
    if c.params.algorithm != "RSDPG":
        return
    e = random_fz(rng, c, c.params.m)
    matrix = random_fz(rng, c, c.params.m * (c.params.n - c.params.m))
    expected = c.subfunctions.fz_inf_w_by_fz_matrix(e, matrix)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_fz_inf_w_by_fz_matrix,
        bytes(e) + bytes(matrix),
        c.params.n,
        chunk_size = output_chunk_size
    )
    compare("fz_inf_w_by_fz_matrix", expected, actual)


def test_fp_vec_by_restr_vec_scaled(target, c, rng):
    """
    Test scaled multiplication of an F_p vector by a restricted vector.
    """
    e = random_fz(rng, c, c.params.n)
    chall_1 = rng.randrange(c.params.p)
    u_prime = random_fp(rng, c, c.params.n)
    expected = c.subfunctions.fp_vec_by_restr_vec_scaled(e, chall_1, u_prime)
    input_data = (bytes(e) + fp_to_bytes([chall_1], c) + fp_to_bytes(u_prime, c))
    output_len = c.params.n * (2 if c.params.algorithm == "RSDPG" else 1)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_fp_vec_by_restr_vec_scaled,
        input_data,
        output_len,
        chunk_size = output_chunk_size
    )
    compare("fp_vec_by_restr_vec_scaled", expected, fp_from_bytes(actual, c))


def test_expand_digest_to_fixed_weight(target, c, rng):
    """
    Test expansion of a digest into a fixed-weight vector.
    """
    digest = random_bytes(rng, c.params.hash_digest_length)
    expected = c.subfunctions.expand_digest_to_fixed_weight(digest)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_expand_digest_to_fixed_weight,
        digest,
        len(expected),
        output_chunk_size
    )
    compare("expand_digest_to_fixed_weight", expected, actual)


def test_fz_dz_norm_n_random(target, c, rng):
    """
    Test the F_z norm function for vectors of length n.
    """
    inp = random_fz(rng, c, c.params.n)
    expected = c.subfunctions.fz_dz_norm_n(inp)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_fz_dz_norm_n,
        bytes(inp),
        len(expected),
        output_chunk_size
    )
    compare("fz_dz_norm_n", expected, actual)


def test_fz_dz_norm_m(target, c, rng):
    """
    Test the F_z norm function for vectors of length m in RSDPG.
    """
    if c.params.algorithm != "RSDPG":
        return
    inp = random_fz(rng, c, c.params.m)
    expected = c.subfunctions.fz_dz_norm_m(inp)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_fz_dz_norm_m,
        bytes(inp),
        len(expected),
        chunk_size = output_chunk_size
    )
    compare("fz_dz_norm_m", expected, actual)


def test_expand_pk(target, c, rng):
    """
    Test expansion of a public-key seed.
    """
    seed_pk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    result = c.subfunctions.expand_pk(seed_pk)
    expected = result if c.params.algorithm == "RSDP" else result[0]
    expected_len = len(expected) * (2 if c.params.algorithm == "RSDPG" else 1)
    actual = board_run_chunked_subroutine(
        target,
        subroutine_expand_pk,
        seed_pk,
        expected_len,
        output_chunk_size,
        timeout_ms=30000
    )
    compare("expand_pk", expected, fp_from_bytes(actual, c))


def test_expand_sk(target, c, rng):
    """
    Test expansion of a secret-key seed.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    result = c.subfunctions.expand_sk(seed_sk)
    expected = result[0]
    actual = board_run_chunked_subroutine(
        target,
        subroutine_expand_sk,
        seed_sk,
        len(expected),
        chunk_size = output_chunk_size
    )
    compare("expand_sk", expected, actual)

# =============================================================================
# Random subroutine test suite
# =============================================================================

COMMON_RANDOM_TESTS = [
    ("convert_restr_vec_to_fp", test_convert_restr_vec_to_fp),
    ("restr_vec_by_fp_matrix", test_restr_vec_by_fp_matrix),
    ("pack_fz_vec", test_pack_fz_vec),
    ("pack_fp_syn", test_pack_fp_syn),
    ("unpack_fz_vec", test_unpack_fz_vec),
    ("fz_vec_sub_n", test_fz_vec_sub_n),
    ("fp_vec_by_fp_matrix", test_fp_vec_by_fp_matrix),
    ("fp_vec_by_fp_vec_pointwise", test_fp_vec_by_fp_vec_pointwise),
    ("fp_vec_by_restr_vec_scaled", test_fp_vec_by_restr_vec_scaled),
    ("expand_digest_to_fixed_weight", test_expand_digest_to_fixed_weight),
    ("fz_dz_norm_n", test_fz_dz_norm_n_random),
    ("expand_pk", test_expand_pk),
    ("expand_sk", test_expand_sk),
]

RSDPG_RANDOM_TESTS = [
    ("fz_vec_sub_m", test_fz_vec_sub_m),
    ("fz_inf_w_by_fz_matrix", test_fz_inf_w_by_fz_matrix),
    ("fz_dz_norm_m", test_fz_dz_norm_m),
]


def run_random_subroutine_tests(target, c):
    """
    Run all applicable random subroutine tests for one CROSS variant.
    Each subroutine is executed several times with independently generated but reproducible random inputs.
    """
    tests = list(COMMON_RANDOM_TESTS)
    if c.params.algorithm == "RSDPG":
        tests.extend(RSDPG_RANDOM_TESTS)

    total = len(tests) * rounds_per_subroutine
    passed = 0

    print()
    print("============================================================")
    print(" Random subroutine tests")
    print("============================================================")
    print(f"Rounds per subroutine : {rounds_per_subroutine}")
    print(f"Total board tests     : {total}")
    print(f"Random seed           : {random_seed}")
    print()

    for test_number, (name, test_function) in enumerate(tests, start=1):
        print(
            f"[{test_number:02d}/{len(tests):02d}] {name:<38}",
            end="",
            flush=True,
        )

        for round_number in range(1, rounds_per_subroutine + 1):
            # Generate a deterministic but unique seed for this test case.
            seed = (
                random_seed
                + test_number * 1000
                + round_number
                + c.params.category * 100000
                + (1000000 if c.params.algorithm == "RSDPG" else 0)
            )

            rng = random.Random(seed)

            try:
                test_function(target, c, rng)
            except Exception as exc:
                print(" Fail")
                print()
                print("============================================================")
                print("TEST FAILURE")
                print("============================================================")
                print(f"Subroutine : {name}")
                print(f"Round      : {round_number}/{rounds_per_subroutine}")
                print(f"Seed       : {seed}")
                print(f"Exception  : {type(exc).__name__}: {exc}")
                print("============================================================")
                return False, (f"{name} round {round_number} failed (seed={seed})")

            passed = passed + 1

        print(f" Pass ({rounds_per_subroutine}/{rounds_per_subroutine})")

    print()
    print("============================================================")
    print(f" {passed}/{total} random board tests passed.")
    print("============================================================")
    return True, ""

# =============================================================================
# Single variant
# =============================================================================

def run_single_variant(target, family: str, category: int, variant: str):
    """
    Run the random subroutine test suite for one firmware variant.
    """
    print()
    print("============================================================")
    print(f" Variant: {family} Cat-{category} {variant}")
    print("============================================================")

    print()
    print("Creating host-side CROSS instance...")

    c = Cross(path=str(build_dir), 
        algorithm=family, 
        category=category, 
        optimization=variant, 
        release="_6.6.87.so"
    )

    print("CROSS instance created.")
    print()
    print(
        f"Parameters: p={c.params.p}, z={c.params.z}, "
        f"n={c.params.n}, k={c.params.k}, m={c.params.m}, "
        f"t={c.params.t}"
    )

    reset_serial_communication(target)

    return run_random_subroutine_tests(target, c)

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

    print(f"Mode: {rounds_per_subroutine} fresh random tests per subroutine")

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

        scope.io.clkout = 15e6

        target = cw.target(scope, cw.targets.SimpleSerial2)

        target.baud = baudrate

        print(f"Target type: {type(target).__name__}")

        print(f"Target baudrate: {target.baud}")

        # Communication reset
        reset_serial_communication(target)

        print()
        print("ChipWhisperer connection successful.")

        # Test each selected variant
        overall_passed = True

        for family, category, variant in parameter_sets:

            print()
            print("=" * 60)
            print(f" Testing: {family} Cat-{category} {variant} ")
            print("=" * 60)

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

    finally:
         # Always disconnect from the target and scope.
        if target is not None:
            try:
                target.dis()
            except Exception:
                pass
        if scope is not None:
            try:
                scope.dis()
            except Exception:
                pass

        print()
        print("ChipWhisperer disconnected.")

if __name__ == "__main__":
    sys.exit(main())