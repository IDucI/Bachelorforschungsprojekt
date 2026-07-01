# libcross

`libcross` provides a Python <-> C interface for selected CROSS reference implementation subroutines.

The structure is based on the existing `libkyber` interface, but adapted for CROSS.


## Current status

Currently supported variant:

- `cross_r_sdp_1_fast`

Currently exposed subroutine:

- `cross_convert_restr_vec_to_fp`
- `restr_vec_by_fp_matrix` 
- `fp_vec_by_fp_vec_pointwise`
- `fp_vec_by_fp_matrix`
- `fz_vec_sub_n`
- `expand_sk`
- `csprng_fz_inf_w`
- `fz_inf_w_by_fz_matrix`
- `fz_dz_norm_n`
- `fz_vec_sub_m` Ist useless wahrscheinlich wegen RSDP(G)

### Important files

libcross/
├─ Makefile                         (selects variants)
├─ lib_Makefile                     (compiles one variant)
├─ libcross.h                       (declares exported C API)
├─ libcross.c                       (implements C API wrappers)
├─ cross/                           
│  ├─ __init__.py                   (package exports)
│  ├─ cross.py                      (loads shared library)
│  └─ cross_subfunctions.py         (ctypes calls to libcross.h)
├─ variants/
│  └─ Reference_Implementation/     (original CROSS code)
│     ├─ function_linkage.c         (links wrappers to CROSS functions)
│     ├─ include/                   (CROSS headers)
│     └─ lib/                       (CROSS C sources)
└─ build/                           (generated libraries)


### Interface flow

Python calls the exported functions from the shared library. These functions are declared in libcross.h, implemented in libcross.c, forwarded through function_linkage.c, and finally execute the original CROSS code.


### Adding a new subroutine

To expose a new CROSS subroutine, connect it in function_linkage.c, declare and wrap it in libcross.h/libcross.c, and finally add the Python call in cross/cross_subfunctions.py.


## Quick Python check

A small Python script can be used to check whether the Python interface can load the shared library and call an exposed subroutine.

Run it from WSL/Linux in the `libcross` directory:

python3 try_cross.py

