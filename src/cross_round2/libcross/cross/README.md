# Python Interface

## Overview

The `cross` package provides the Python interface to the native libcross
libraries.

The `Cross` class is the main entry point and provides high-level key generation,
signing, and verification, as well as access to the wrapped CROSS subfunctions.

The `calculation` API reproduces CROSS key generation and signing while recording
the inputs and outputs of selected subroutines used by the firmware.

## Creating a Cross Instance

Import `Cross` and create an instance for the desired CROSS configuration:

```
from cross import Cross

cross = Cross(
    algorithm="RSDP",
    category=1,
    optimization="fast",
)
```

The configuration is selected using:

- `algorithm`: `RSDP` or `RSDPG`
- `category`: `1`, `3`, or `5`
- `optimization`: `fast`, `balanced`, or `small`

If no configuration is specified, `Cross()` uses `RSDP`, category `1`, and the
`fast` optimization corner by default.

## High-Level API

The high-level API provides the standard CROSS operations for key generation,
signing, and verification.

```
from cross import Cross

cross = Cross()

seed_sk, pk = cross.keygen()

message = b"Hello CROSS"
signature = cross.sign(seed_sk, message)

is_valid = cross.verify(pk, message, signature)
```

`verify()` returns `1` for a valid signature and `0` for an invalid.

## Subfunction API

The subfunction API provides direct access to the wrapped C routines used during
CROSS key generation and signing.

The subfunctions are available through `cross.subfunctions`:

```
from cross import Cross

cross = Cross()

seed_sk, _ = cross.keygen()
e_bar, V_tr = cross.subfunctions.expand_sk(seed_sk)
```

## Calculation API

The calculation API runs CROSS key generation and signing through the
subfunction wrappers and collects the intermediate values required by the
corresponding firmware subroutines in result objects. These values are taken
directly from a complete key generation or signing run and therefore correspond
to the actual state of the algorithm at that point.

This makes it convenient to obtain coherent reference values for the
corresponding firmware subroutines without manually reproducing all preceding
steps of the algorithm.

### Running Calculations

Key generation and signing return result objects containing the generated
outputs together with the recorded intermediate values:

The calculation methods can either generate the required values automatically or
accept predefined values as optional arguments. The values used during the run
are also stored in the returned result object, allowing generated key material,
seeds, and other inputs to be accessed and reused afterwards.

For example, values generated during one calculation can be accessed through
the returned result object and reused in later calculations:

```
from cross import Cross

cross = Cross()

keygen_result = cross.calculation.keygen()

seed_sk = keygen_result.seed_sk
pk = keygen_result.pk

sign_result = cross.calculation.sign(
    b"Hello CROSS",
    seed_sk=seed_sk,
    pk=pk,
)

signature = sign_result.signature
root_seed = sign_result.root_seed
salt = sign_result.salt
```

If none of the optional values are provided, `sign()` generates the required `seed_sk`, `pk`, `root_seed`, and `salt` automatically.

### Accessing Recorded Values

Recorded subroutine values are grouped by subroutine in the result object and
can be accessed using:

```
result.<subroutine>.<value>
```

For subroutines that are called repeatedly during signing, the recorded inputs
and outputs are stored as sequences and can be accessed using an index such as
`i`:

```
result.<subroutine>.<value>[i]
```

For example:

```
s_prime_in = sign_result.pack_fp_syn.s_prime_in[i]
```

## Parameters

The parameters of the selected CROSS configuration are available through
`cross.params`.

In addition to the selected algorithm, category, and optimization corner,
`cross.params` provides the corresponding CROSS parameters and derived sizes
used for arrays, buffers, keys, and signatures.