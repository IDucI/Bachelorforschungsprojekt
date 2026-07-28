import time
from pathlib import Path

import chipwhisperer as cw


HERE = Path(__file__).resolve().parent

HEX_BINARY = str(
    HERE / "less_fq_inv-PINATA.hex"
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

# Store the field element 5 and request a readback.
target.send_cmd(
    "s",
    0x80,
    bytes([5]),
)

response = target.simpleserial_read(
    "r",
    1,
)

print("readback:", response)

if response is not None and list(response) == [5]:
    print("OK: SimpleSerial readback works.")
else:
    print("ERROR: unexpected readback response.")

target.dis()
scope.dis()