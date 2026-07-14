import time
from pathlib import Path

import chipwhisperer as cw


HERE = Path(__file__).resolve().parent
HEX_BINARY = str(HERE / "fz_vec_sub_m-PINATA.hex")
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

target = cw.target(scope, cw.targets.SimpleSerial2)
target.baud = BAUDRATE
target.flush()

target.send_cmd("s", 0x80, bytes([1, 2, 3]))
resp = target.simpleserial_read("r", 3)

print("readback:", resp)

if resp is not None and list(resp) == [1, 2, 3]:
    print("OK: SimpleSerial readback works.")
else:
    print("ERROR: unexpected readback response.")

target.dis()
scope.dis()
