import time
from pathlib import Path

import chipwhisperer as cw


HERE = Path(__file__).resolve().parent

HEX_BINARY = str(
    HERE / "less_row_mul3-PINATA.hex"
)

BAUDRATE = 230400


scope = cw.scope()
scope.default_setup()

scope.io.clkout = 15e6

print("clkout:", scope.io.clkout)

time.sleep(0.5)

cw.program_target(
    scope,
    cw.programmers.STM32FProgrammer,
    HEX_BINARY,
    baud=BAUDRATE,
)

target = cw.target(
    scope,
    cw.targets.SimpleSerial2,
)

target.baud = BAUDRATE
target.flush()

payload = bytes(range(1, 17))

target.send_cmd(
    "s",
    0x80,
    payload,
)

response = target.simpleserial_read(
    "r",
    len(payload),
)

print("readback:", response)

if (
    response is not None
    and bytes(response) == payload
):
    print("OK: SimpleSerial readback works.")
else:
    print("ERROR: unexpected readback response.")

target.dis()
scope.dis()