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

# Generate a new random base seed for every test run.
random_seed = random.SystemRandom().randint(0, 2**32 - 1)
print(f"Random seed: {random_seed}")

# SUBROUTINE IDS
subroutine_convert_restr_vec_to_fp          = 0x03
subroutine_restr_vec_by_fp_matrix           = 0x04 
subroutine_pack_fz_vec                      = 0x05
subroutine_pack_fp_syn                      = 0x06
subroutine_fz_vec_sub_n                     = 0x07
subroutine_fp_vec_by_fp_matrix              = 0x08
subroutine_fp_vec_by_fp_vec_pointwise       = 0x09
subroutine_fz_vec_sub_m                     = 0x10
subroutine_fz_inf_w_by_fz_matrix            = 0x11
subroutine_fp_vec_by_restr_vec_scaled       = 0x12
subroutine_expand_digest_to_fixed_weight    = 0x13
subroutine_fz_dz_norm_n                     = 0x14
subroutine_fz_dz_norm_m                     = 0x15
subroutine_expand_pk                        = 0x16
subroutine_expand_sk                        = 0x17

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
        # Send the reference input to the STM32 and execute the selected firmware subroutine.
        # The output may be larger than one SimpleSerial packet, therefore it is received in multiple chunks.
        actual = board_run_chunked_subroutine(
            target,
            subroutine_id,
            bytes(inp),
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

def test_intermediate_convert_restr_vec_to_fp(target, c, rng):
    """
    Test `convert_restr_vec_to_fp` using an intermediate value from the CROSS key-generation procedure.
    The input is the restricted vector e_bar produced during key generation.
    The expected output is the corresponding vector s after conversion to FP.
    """
    # Generate the secret-key seed used for the reference execution.
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)

    # Execute CROSS key generation with the Python reference implementation.
    keygen_result = c.calculation.keygen(seed_sk)

    # e_bar is the actual input used by the reference implementation.
    # s is the resulting output after the relevant key-generation step.
    inputs = [keygen_result.fz_dz_norm_n.e_bar_in]
    outputs = [keygen_result.restr_vec_by_fp_matrix.s]

    # Send the reference input to the board and compare its output against the reference result.
    test_intermediate_values(
        target,
        subroutine_convert_restr_vec_to_fp,
        "convert_restr_vec_to_fp",
        inputs,
        outputs
    )


def test_intermediate_restr_vec_by_fp_matrix(target, c, rng):
    """
    Test `restr_vec_by_fp_matrix` with the actual intermediate values generated during CROSS key generation.
    The subroutine receives: restricted vector e_bar, converted to FP representation, the public/secret matrix V_tr
    and produces the syndrome vector s.
    """
    # Generate a fresh secret-key seed for the reference execution.
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)

    # Run key generation in the Python reference implementation.
    keygen_result = c.calculation.keygen(seed_sk)

    # The reference subroutine receives e_bar and V_tr.
    inputs = [(keygen_result.fz_dz_norm_n.e_bar_in, keygen_result.restr_vec_by_fp_matrix.V_tr)]

    # s is the expected result of the matrix operation.
    outputs = [keygen_result.restr_vec_by_fp_matrix.s]

    converted_inputs = []

    for e_bar, V_tr in inputs:
        # The board interface works with raw bytes.
        # e_bar itself is an FZ vector, but the firmware subroutine expects the converted FP representation.
        # V_tr is already an FP matrix and therefore also needs the FP-specific byte representation.
        converted_inputs.append(
            fp_to_bytes(c.subfunctions.convert_restr_vec_to_fp(e_bar), c)
            + fp_to_bytes(V_tr, c)
        )

    test_intermediate_values(
        target,
        subroutine_restr_vec_by_fp_matrix,
        "restr_vec_by_fp_matrix",
        converted_inputs,
        [fp_to_bytes(x, c) for x in outputs]
    )


def test_intermediate_pack_fz_vec(target, c, rng):
    """
    Test `pack_fz_vec` using the vector that occurs during CROSS signing.
    The subroutine converts an FZ vector into the compact byte representation used inside the signature.
    """
    # Generate the input data required for a real signing execution.
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    # Key generation is required because signing needs the public key.
    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )

    inputs = [result.pack_fz_vec.v_bar_in]
    outputs = [result.pack_fz_vec.v_bar_out]

    test_intermediate_values(
        target,
        subroutine_pack_fz_vec,
        "pack_fz_vec",
        [bytes(x) for x in inputs],
        outputs
    )


def test_intermediate_pack_fp_syn(target, c, rng):
    """
    Test `pack_fp_syn` with the syndrome generated during signing.
    The input is an FP syndrome vector and the output is its densely packed byte representation.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    # Generate the public key required for signing.
    keygen_result = c.calculation.keygen(seed_sk)

    # Run the reference signing procedure.
    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )

    # s_prime is the FP syndrome that is passed to the packing routine.
    inputs = [result.pack_fp_syn.s_prime_in]

    # s_prime_out is the expected packed representation.
    outputs = [result.pack_fp_syn.s_prime_out]

    test_intermediate_values(
        target,
        subroutine_pack_fp_syn,
        "pack_fp_syn",
        [fp_to_bytes(x, c) for x in inputs],
        outputs
    )


def test_intermediate_fz_vec_sub_n(target, c, rng):
    """
    Test `fz_vec_sub_n`. This operation corresponds to the subtraction e_bar - y, inside CROSS_sign.
    Both operands are N-dimensional restricted vectors.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    # Generate the public key and execute the reference signing procedure.
    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )

    # e_bar comes from the secret-key expansion.
    # y is the vector generated by fp_vec_by_restr_vec_scaled.
    # The reference implementation stores the result of e_bar - y
    e_bar = result.expand_sk.e_bar
    y = result.fp_vec_by_restr_vec_scaled.y

    expected = result.fz_vec_sub_n.e_bar_prime

    inputs = [bytes(e_bar) + bytes(y)]

    outputs = [bytes(expected)]

    test_intermediate_values(
        target,
        subroutine_fz_vec_sub_n,
        "fz_vec_sub_n",
        inputs,
        outputs
    )


def test_intermediate_fp_vec_by_fp_matrix(target, c, rng):
    """
    Test `fp_vec_by_fp_matrix` using the intermediate values generated during CROSS signing.
    The operation takes: an FP vector, the matrix V_tr and produces the FP vector s_prime.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )
    # Both u and V_tr are intermediate values of the real signing execution.
    inputs = [
        fp_to_bytes(result.fp_vec_by_fp_matrix.u, c)
        + fp_to_bytes(result.fp_vec_by_fp_matrix.V_tr, c)
    ]
    # s_prime is the expected matrix-operation result.
    outputs = [fp_to_bytes(result.fp_vec_by_fp_matrix.s_prime, c)]

    test_intermediate_values(
        target,
        subroutine_fp_vec_by_fp_matrix,
        "fp_vec_by_fp_matrix",
        inputs,
        outputs
    )


def test_intermediate_fp_vec_by_fp_vec_pointwise(target, c, rng):
    """
    Test `fp_vec_by_fp_vec_pointwise`. The operation performs a coordinate-wise multiplication of
    two FP vectors: u = u_prime * v. 
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )

    inputs = [
        fp_to_bytes(result.fp_vec_by_fp_vec_pointwise.u_prime, c)
        + fp_to_bytes(result.fp_vec_by_fp_vec_pointwise.v, c)
    ]

    outputs = [fp_to_bytes(result.fp_vec_by_fp_vec_pointwise.u, c)]

    test_intermediate_values(
        target,
        subroutine_fp_vec_by_fp_vec_pointwise,
        "fp_vec_by_fp_vec_pointwise",
        inputs,
        outputs
    )


def test_intermediate_fp_vec_by_restr_vec_scaled(target, c, rng):
    """
    Test `fp_vec_by_restr_vec_scaled`. This is the operation that produces y during CROSS signing.
    The board receives: e_bar_prime, challenge_1, u_prime and must reproduce the reference vector y.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )
     # Build the exact input expected by the firmware.
    inputs = [
        bytes(result.fp_vec_by_restr_vec_scaled.e_bar_prime)
        + bytes([result.fp_vec_by_restr_vec_scaled.chall_1])
        + fp_to_bytes(result.fp_vec_by_restr_vec_scaled.u_prime, c)
    ]
    # y is the expected result of the scaled vector operation.
    outputs = [fp_to_bytes(result.fp_vec_by_restr_vec_scaled.y, c)]

    test_intermediate_values(
        target,
        subroutine_fp_vec_by_restr_vec_scaled,
        "fp_vec_by_restr_vec_scaled",
        inputs,
        outputs
    )


def test_intermediate_expand_digest_to_fixed_weight(target, c, rng):
    """
    Test `expand_digest_to_fixed_weight`. The input is the digest used to derive challenge_2.
    The output is the fixed-weight challenge vector.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = keygen_result.pk,
        root_seed = root_seed,
        salt = salt
    )
    # The digest is the actual input used by the reference implementation
    inputs = [result.expand_digest_to_fixed_weight.digest_chall_2]

    # chall_2 is the resulting fixed-weight challenge vector.
    outputs = [bytes(result.expand_digest_to_fixed_weight.chall_2)]

    test_intermediate_values(
        target,
        subroutine_expand_digest_to_fixed_weight,
        "expand_digest_to_fixed_weight",
        inputs,
        outputs
    )


def test_intermediate_fz_dz_norm_n(target, c, rng):
    """
    Test `fz_dz_norm_n`. The input and expected output are taken directly from the signing reference execution.
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)

    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)

    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    pk = keygen_result.pk

    result = c.calculation.sign(
        message,
        seed_sk = seed_sk,
        pk = pk,
        root_seed = root_seed,
        salt = salt
    )

    # v_bar_in is the vector before normalization.
    # v_bar_out is the canonical/normalized representation produced by the reference implementation.
    inputs = result.fz_dz_norm_n.v_bar_in
    outputs = result.fz_dz_norm_n.v_bar_out

    test_intermediate_values(
        target,
        subroutine_fz_dz_norm_n,
        "fz_dz_norm_n",
        inputs,
        outputs
    )


def test_intermediate_expand_pk(target, c, rng):
    """
    Test `expand_pk`. expand_pk reconstructs the public matrix/matrices from seed_pk.
    RSDP: seed_pk -> V_tr
    RSDPG: seed_pk -> V_tr + W_mat
    """
    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)

    # Run key generation to obtain the actual seed_pk and the expanded reference values.
    keygen_result = c.calculation.keygen(seed_sk)

    seed_pk = keygen_result.expand_pk.seed_pk
    V_tr = keygen_result.expand_pk.V_tr

    if c.params.algorithm == "RSDP":
        # Standard RSDP only has V_tr.
        inputs = [seed_pk]
        outputs = [fp_to_bytes(V_tr, c)]
    else:
        # RSDPG additionally contains the subgroup matrix W_mat.
        W_mat = keygen_result.expand_pk.W_mat

        inputs = [seed_pk]
        outputs = [
            fp_to_bytes(V_tr, c)
            + bytes(W_mat)
        ]

    test_intermediate_values(
        target,
        subroutine_expand_pk,
        "expand_pk",
        inputs,
        outputs
    )


def test_intermediate_expand_sk(target, c, rng):
    """
    Test `expand_sk`. expand_sk derives the secret-key-dependent intermediate values from seed_sk.
    RSDP: seed_sk -> e_bar + V_tr
    RSDPG: seed_sk -> e_bar + e_G_bar + V_tr + W_mat
    """
    seed_sk = random_bytes(
        rng,
        c.params.keypair_seed_length_bytes
    )

    keygen_result = c.calculation.keygen(seed_sk)

    e_bar = keygen_result.fz_inf_w_by_fz_matrix.e_bar
    V_tr = keygen_result.restr_vec_by_fp_matrix.V_tr

    if c.params.algorithm == "RSDP":
        # RSDP only requires the normal secret vector and V_tr.
        inputs = [seed_sk]

        outputs = [bytes(e_bar) + fp_to_bytes(V_tr, c)]
    else:
        # RSDPG has two additional intermediate values: e_G_bar and W_mat.
        e_G_bar = keygen_result.fz_inf_w_by_fz_matrix.e_G_bar
        W_mat = keygen_result.fz_inf_w_by_fz_matrix.W_mat

        inputs = [seed_sk]

        outputs = [
            bytes(e_bar)
            + bytes(e_G_bar)
            + fp_to_bytes(V_tr, c)
            + bytes(W_mat)
        ]

    test_intermediate_values(
        target,
        subroutine_expand_sk,
        "expand_sk",
        inputs,
        outputs
    )


# =============================================================================
# RSDP-(G) only subroutine tests
# =============================================================================

def test_intermediate_fz_vec_sub_m(target, c, rng):
    """
    Test `fz_vec_sub_m`. This is the RSDPG-only equivalent of `fz_vec_sub_n`, but operates on M-dimensional subgroup vectors.
    The operation is: e_G_bar - v_G_bar
    """
    if c.params.algorithm != "RSDPG":
        return

    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk=seed_sk,
        pk=keygen_result.pk,
        root_seed=root_seed,
        salt=salt
    )

    # Both operands are M-dimensional restricted vectors.
    e_G_bar = result.expand_sk.e_G_bar
    v_G_bar = result.fz_vec_sub_m.v_G_bar

    inputs = [bytes(e_G_bar) + bytes(v_G_bar)]

    # The reference result is e_G_bar_prime.
    outputs = [bytes(result.fz_vec_sub_m.e_G_bar_prime)]

    test_intermediate_values(
        target,
        subroutine_fz_vec_sub_m,
        "fz_vec_sub_m",
        inputs,
        outputs
    )


def test_intermediate_fz_inf_w_by_fz_matrix(target, c, rng):
    """
    Test `fz_inf_w_by_fz_matrix`. This subroutine is only present in RSDPG.
    It takes: e_G_bar_prime, W_mat and produces the N-dimensional vector used later in the signing flow.
    """
    if c.params.algorithm != "RSDPG":
        return

    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk=seed_sk,
        pk=keygen_result.pk,
        root_seed=root_seed,
        salt=salt
    )
    # e_G_bar_prime is the M-dimensional input vector.
    # W_mat is the FZ matrix generated during secret-key expansion.
    inputs = [bytes(result.fz_vec_sub_m.e_G_bar_prime) + bytes(result.expand_sk.W_mat)]

    # The resulting N-dimensional vector is stored in the reference
    # implementation as e_G_bar_prime of the following calculation step.
    outputs = [bytes(result.fz_inf_w_by_fz_matrix.e_G_bar_prime)]

    test_intermediate_values(
        target,
        subroutine_fz_inf_w_by_fz_matrix,
        "fz_inf_w_by_fz_matrix",
        inputs,
        outputs
    )


def test_intermediate_fz_dz_norm_m(target, c, rng):
    """
    Test `fz_dz_norm_m`. This is the RSDPG-only normalization routine for M-dimensional subgroup vectors.
    """
    if c.params.algorithm != "RSDPG":
        return

    seed_sk = random_bytes(rng, c.params.keypair_seed_length_bytes)
    message = random_bytes(rng, 32)

    root_seed = random_bytes(rng, c.params.seed_length_bytes)
    salt = random_bytes(rng, c.params.salt_length_bytes)

    keygen_result = c.calculation.keygen(seed_sk)

    result = c.calculation.sign(
        message,
        seed_sk=seed_sk,
        pk=keygen_result.pk,
        root_seed=root_seed,
        salt=salt
    )
    # v_G_bar_in is the vector before normalization.
    # v_G_bar_out is the normalized reference result.
    inputs = [result.fz_dz_norm_m.v_G_bar_in]

    outputs = [result.fz_dz_norm_m.v_G_bar_out]

    test_intermediate_values(
        target,
        subroutine_fz_dz_norm_m,
        "fz_dz_norm_m",
        [bytes(x) for x in inputs],
        [bytes(x) for x in outputs]
    )

# =============================================================================
# Intermediate subroutine test suite
# =============================================================================

COMMON_INTERMEDIATE_TESTS = [
    ("convert_restr_vec_to_fp", test_intermediate_convert_restr_vec_to_fp),
    ("restr_vec_by_fp_matrix", test_intermediate_restr_vec_by_fp_matrix),
    ("pack_fz_vec", test_intermediate_pack_fz_vec),
    ("pack_fp_syn", test_intermediate_pack_fp_syn),
    ("fz_vec_sub_n", test_intermediate_fz_vec_sub_n),
    ("fp_vec_by_fp_matrix", test_intermediate_fp_vec_by_fp_matrix),
    ("fp_vec_by_fp_vec_pointwise", test_intermediate_fp_vec_by_fp_vec_pointwise),
    ("fp_vec_by_restr_vec_scaled", test_intermediate_fp_vec_by_restr_vec_scaled),
    ("expand_digest_to_fixed_weight", test_intermediate_expand_digest_to_fixed_weight),
    ("fz_dz_norm_n", test_intermediate_fz_dz_norm_n),
    ("expand_pk", test_intermediate_expand_pk),
    ("expand_sk", test_intermediate_expand_sk),
]

RSDPG_INTERMEDIATE_TESTS = [
    ("fz_vec_sub_m", test_intermediate_fz_vec_sub_m),
    ("fz_inf_w_by_fz_matrix", test_intermediate_fz_inf_w_by_fz_matrix),
    ("fz_dz_norm_m", test_intermediate_fz_dz_norm_m),
]

def run_intermediate_tests(target, c):
    """
    Run tests using intermediate values generated by the reference implementation.
    """
    tests = list(COMMON_INTERMEDIATE_TESTS)
    if c.params.algorithm == "RSDPG":
        tests.extend(RSDPG_INTERMEDIATE_TESTS)

    print()
    print("============================================================")
    print(" Intermediate-value tests")
    print("============================================================")
    print()

    for name, test_function in tests:
        print(f"{name:<38}", end="", flush = True)

        # Use the same deterministic seed for all tests of this parameter set.
        # This makes a failing test reproducible while still separating: categories and RSDP vs. RSDP-(G)
        # The actual seed is derived from the globally generated random_seed.
        rng = random.Random(
            random_seed
            + 500000
            + c.params.category * 100000
            + (1000000 if c.params.algorithm == "RSDPG" else 0)
        )

        try:
            # Execute the selected test.
            test_function(target, c, rng)
        except Exception as exc:
            print(" Fail")
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
        path=str(build_dir),
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
    # Remove any stale SimpleSerial data before starting the tests.
    reset_serial_communication(target)

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