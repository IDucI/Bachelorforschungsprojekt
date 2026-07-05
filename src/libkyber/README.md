# Installing libkyber

Compile the library for all kyber variants. If you are only working with kyberHLS then it is sufficient to remove all other variants.
```
make
```
Or if you have multi core:
```
make -j 4
```

Now we can install the library. The default install path is `$HOME/.local/lib`. The library will be suffixed with the local kernel version: `libHLS_6.2.0`. This is done because of the shared home directory of the ralab machines. This will also add the python library to the current `python3` installation.
```
make install
```

To see if everything is installed correctly you can use
```
make installed
```
and you should see something like:

> make[1]: Entering directory '\<repo directory\>'
> 
> libHLS is installed
> 
> libHLS.so is installed
> 
> libHLS.a is installed
> 
> HLS headers are installed
> 
> make[1]: Leaving directory '\<repo directory\>'
>
> kyber is installed for Python 3.10.12


Now it is possible to open libkyber in python.
To test if it works you can run this script in `python3`:
```
import kyber as k
kyber = k.Kyber() # this loads the default kyber version: libkyber512, if you only install kyberHLS this won't work
kyber.pke_keypair() # should output a dict with {'pk': [...], 'sk': [...]}

# if you want to open a specific kyber version you do:
kyber = k.Kyber(name='libHLS'+k.platform_release_string())
# this will give a message "Unable to load ntt_zetas_inv", this is correct, there are no inverse zetas in that implementation.

kyber.pke_keypair() # should output a dict with {'pk': [...], 'sk': [...]}
```


## Adding a new kyber impl to libkyber

Create a `function_linkage.c` file with function pointers to all functions that are used in the kyber subfunctions classes.

Make sure all functions referenced are not declared as static

`pack_ciphertext`, `unpack_ciphertext`, `unpack_sk`, `fqmul` needs to be made unstatic

`c_randombytes_init` needs to be set


## What is that makefile in the `variants/kyber*` folder?

That is the makefile provided by the original implementation. We do not use it, I left it because that's the original submission package content.