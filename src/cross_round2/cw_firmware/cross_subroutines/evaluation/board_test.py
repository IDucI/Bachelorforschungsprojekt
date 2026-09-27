import sys
import subprocess
import time
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
# Simpleserial V2.1
# =============================================================================

def ss_crc(data: bytes) -> int:
    """
    Calculate the SimpleSerial V2.1 crc.
    The crc implementation follows the crc calculation used by the reference implementation in simpleserial.c.
    SimpleSerial V2.1 uses polynomial 0x4D. The crc is calculated over the complete packet excluding the crc byte itself.
    """
    crc = 0x00

    # Process every byte of the packet.
    for byte in data:
        crc = crc ^ byte

        # Process all eight bits of the current byte.
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x4D) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def cobs_encode(data: bytes) -> bytes:
    """
    COBS-encode one SimpleSerial V2.1 packet.
    SimpleSerial V2.1 uses Consistent Overhead Byte Stuffing (COBS) before transmission. The encoded frame is terminated with 0x00.
    This is required because 0x00 is used as the frame delimiter in the SimpleSerial V2.1 protocol.
    """
    data = bytes(data)
    output = bytearray()

    # Index of the COBS code byte that describes the following data block.
    code_index = 0

    # Reserve the first byte for the initial COBS code.
    output.append(0)
    code = 1

    for byte in data:

        # A zero byte terminates the current COBS block.
        if byte == 0:
            output[code_index] = code
            # Start a new COBS block.
            code_index = len(output)
            output.append(0)
            code = 1
        else:
            output.append(byte)
            code = code + 1
            # COBS blocks can contain at most 254 data bytes.
            if code == 0xFF:
                output[code_index] = code
                code_index = len(output)
                output.append(0)
                code = 1

    # Write the code byte of the final block.
    output[code_index] = code

    # 0x00 marks the end of the SimpleSerial frame.
    output.append(0)

    return bytes(output)

def cobs_decode(frame: bytes) -> bytes:
    """
    Decode one COBS-encoded SimpleSerial V2.1 frame.
    The function reverses the transformation performed by cobs_encode() and restores the original packet 
    containing command, length, data and CRC.
    """
    frame = bytes(frame)

    # A valid frame must contain the 0x00 frame delimiter.
    if not frame:
        raise ValueError("Empty COBS frame.")
    
    if frame[-1] != 0x00:
        raise ValueError("Frame does not end with 0x00.")

     # Remove the frame delimiter before decoding.
    encoded = frame[:-1]

    if not encoded:
        raise ValueError("Empty COBS payload.")

    decoded = bytearray()
    index = 0

    while index < len(encoded):

        # Each COBS block starts with a code byte.
        code = encoded[index]

        if code == 0:
            raise ValueError("Invalid COBS packet.")

        index = index + 1

        # The code byte specifies how many bytes belong to this block.
        end = index + code - 1

        if end > len(encoded):
            raise ValueError("Invalid COBS code.")

        # Copy the block's data into the decoded packet.
        decoded.extend(encoded[index:end])

        index = end

        # A code smaller than 0xFF indicates that a zero byte was removed
        # between this block and the next block during encoding.
        if code < 0xFF and index < len(encoded):
            decoded.append(0)

    return bytes(decoded)


def ss_write_raw(target, packet: bytes) -> None:
    """
    Send already encoded SimpleSerial bytes to the target.
    No additional protocol processing is performed here. The packet is written directly to the serial interface.
    """
    target.ser.write(packet)


def ss_send_cmd(target, cmd: int, scmd: int, data: bytes = b"") -> None:
    """
    Construct and send one SimpleSerial V2.1 command.
    The packet structure follows the format used by the reference
    SimpleSerial V2.1 implementation:
        [cmd, scmd, data_length, data, CRC]
    After constructing the packet, the CRC is appended and the complete packet is COBS-encoded before transmission.
    """
    data = bytes(data)

    #the SimpleSerial package in its original structure, before COBS encoding happens
    raw_packet = bytearray()

    # Command identifier.
    raw_packet.append(cmd & 0xFF)

    # Sub-command identifier.
    raw_packet.append(scmd & 0xFF)

    # Length of the payload in bytes.
    raw_packet.append(len(data))

    # Actual command payload.
    raw_packet.extend(data)

    # Calculate the CRC over all packet fields except the CRC itself.
    crc = ss_crc(raw_packet)

    # Append the calculated CRC to the packet.
    raw_packet.append(crc)

    # COBS-encode the complete packet and add the frame delimiter.
    encoded_packet = cobs_encode(bytes(raw_packet))

    # Send the encoded frame to the STM32.
    ss_write_raw(target, encoded_packet)


def ss_read_raw(target, timeout_ms: int = 2000) -> bytes:
    """
    Read exactly one complete SimpleSerial V2.1 COBS frame.
    Reception continues until the 0x00 frame delimiter is received. A timeout prevents the test program from waiting 
    indefinitely if the target does not respond.
    """
    start_time = time.monotonic()

    received = bytearray()

    while True:
        # Check the overall timeout.
        elapsed_ms = (time.monotonic() - start_time) * 1000

        if elapsed_ms > timeout_ms:
            raise TimeoutError("Timeout waiting for SimpleSerial response.")
        # Read one byte from the serial interface.
        try:
            chunk = target.ser.read(1, timeout=10)
        except TypeError:
            chunk = target.ser.read(1)

        if chunk is None:
            continue

        if isinstance(chunk, str):
            chunk = chunk.encode("latin-1")

        chunk = bytes(chunk)

        if not chunk:
            continue

        received.extend(chunk)

        # SimpleSerial V2.1 frames are terminated by 0x00.
        if received[-1] == 0x00:
            return bytes(received)


def ss_parse_packet(frame: bytes):
    """
    Decode and validate one SimpleSerial V2.1 response.
    A response packet has the following structure:
        [cmd, data_length, data, CRC]
    The function:
      -COBS-decodes the received frame.
      -Checks the packet length.
      -Extracts the command and payload.
      -Recalculates and verifies the CRC.
    """
    # Restore the original SimpleSerial packet.
    decoded = cobs_decode(frame)

    # Minimum packet: command + length + CRC
    if len(decoded) < 3:
        raise RuntimeError("Response too short.")

    # Extract command and payload length.
    cmd = decoded[0]
    data_len = decoded[1]

    # Expected packet size:
    #   1 byte command
    # + 1 byte length
    # + N bytes data
    # + 1 byte CRC
    expected_length = 2 + data_len + 1

    if len(decoded) != expected_length:
        raise RuntimeError(f"Invalid packet length: expected {expected_length}, got {len(decoded)}")

    # Extract the payload.
    data = decoded[2:2 + data_len]

    # The final byte contains the CRC sent by the STM32.
    received_crc = decoded[-1]

    # Calculate the CRC over all fields except the received CRC.
    calculated_crc = ss_crc(decoded[:-1])

    # Verify integrity of the received packet.
    if received_crc != calculated_crc:
        raise RuntimeError("CRC mismatch.")

    return cmd, bytes(data)


def ss_read_packet(target, timeout_ms: int = 2000):
    """
    Receive, decode and validate one SimpleSerial V2.1 response.
    This combines the raw frame reception and packet parsing steps.
    """
    frame = ss_read_raw(target, timeout_ms=timeout_ms)

    return ss_parse_packet(frame)


def wait_for_ack(target, timeout_ms: int = 2000) -> None:
    """
    Wait for and validate the SimpleSerial V2.1 error/acknowledgement packet.
    According to the SimpleSerial V2.1 protocol, the target sends:
        ['e', 0x01, error_code, CRC]
    The error code 0x00 indicates successful execution. Any non-zero error code indicates an error reported by the STM32.
    """
    cmd, data = ss_read_packet(target, timeout_ms=timeout_ms)

    # The target must respond with the SimpleSerial error command 'e'.
    if cmd != ord("e"):
        raise RuntimeError("Expected ACK 'e', " f"received 0x{cmd:02X}")

    # The error response contains exactly one byte: the error code.
    if len(data) != 1:
        raise RuntimeError("Invalid ACK payload length: "f"{len(data)}")

    error_code = data[0]

    # 0x00 means successful execution.
    if error_code != 0:
        raise RuntimeError("STM32 returned SimpleSerial error: " f"0x{error_code:02X}")

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


def board_write_buffer(target,data: bytes) -> None:
    """
    Write input data into STM32 databuffer.
    Firmware:
        set_value(cmd, scmd, len, x)
    accepts:
        len == 160
        len == 3
    For normal data we therefore send 160-byte chunks.
    """
    data = bytes(data)

    if not data:
        raise ValueError("Can't write empty buffer.")

    # Split the input into firmware compatible chunks.
    for chunk_index, offset in enumerate(range(0, len(data), input_chunk_size)):
        chunk = data[offset: offset + input_chunk_size]

        # Pad the final chunk to the required input size.
        if len(chunk) < input_chunk_size:
            chunk = chunk + bytes(input_chunk_size - len(chunk))

        # 's' writes one chunk into the firmware data buffer.
        ss_send_cmd(target, ord("s"), chunk_index, chunk)

        wait_for_ack(target)


def board_run_subroutine(
        target, 
        subroutine_id: int, 
        input_data: bytes, 
        output_len: int, 
        timeout_ms: int = 5000
) -> bytes:
    """
    Execute one firmware subroutine and return its complete output.
    The input is written to the board buffer first. The selected subroutine is then executed and its result is read back.
    """
    # Write the input data into the board buffer.
    board_write_buffer(target, input_data)

    # Execute selected subroutine
    ss_send_cmd(target, ord("b"), subroutine_id, b"")

    # Read result
    cmd, data = ss_read_packet(target, timeout_ms=timeout_ms)

    if cmd != ord("r"):
        # Report firmware errors explicitly.
        if cmd == ord("e"):

            error_code = data[0] if len(data) == 1 else None

            raise RuntimeError("Board rejected 'b' command. " f"Error code = {error_code!r}")

        raise RuntimeError("Expected result command 'r', " f"received 0x{cmd:02X}")
    # Verify that the firmware returned the expected amount of data.
    if len(data) != output_len:
        raise RuntimeError("Wrong board output length: " f"expected {output_len}, " f"got {len(data)}")

    actual = bytes(data)

    # Final ACK
    wait_for_ack(target, timeout_ms=timeout_ms)

    return actual

def board_run_chunked_subroutine(
    target,
    subroutine_id,
    input_data,
    output_len,
    chunk_size,
    timeout_ms=5000
):
    """
    Execute a subroutine whose output must be requested in chunks.
    The firmware uses x[0] as the output-chunk index. Since normal
    firmware writes are limited to 160 bytes and command payloads
    to 3 bytes, each output request is sent as:
        [chunk_index, 0, 0]
    The firmware uses the chunk index to calculate the output offset.
    """
    # The complete input is written before requesting output chunks.
    board_write_buffer(target, bytes(input_data))

    output = bytearray()

    # Calculate the number of required output requests.
    number_of_chunks = (output_len + chunk_size - 1) // chunk_size

    for chunk_index in range(number_of_chunks):
        if chunk_index > 0x7F:
            raise ValueError("More than 128 output chunks are not supported.")

        # x[0] contains the requested output chunk index.
        request = bytes([chunk_index, 0, 0])

        ss_send_cmd(target, ord("b"), subroutine_id, request)

        while True:
            cmd, data = ss_read_packet(target, timeout_ms=timeout_ms)

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

        output.extend(data)

        # Every chunk is followed by an ack
        wait_for_ack(target, timeout_ms = timeout_ms)

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