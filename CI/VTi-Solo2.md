# VTi 15.0.04 / VU+ Solo2 port preparation

This branch prepares Python 2.7 persistence and native option handling. It does
not produce or claim a working VTi MIPS package yet. OpenPLi ARM binaries are
not transferable to Solo2.

Required before a receiver package can be validated:

* exact architecture priorities and installed Enigma2/Python/player versions;
* target glibc, libstdc++, OpenSSL, libsigc++ and FFmpeg ABI;
* matching Enigma2 headers and target libraries/sysroot, or a reproducible SDK;
* VTi-specific service virtual interfaces and event numbering;
* Solo2 MIPS hardware output and actual outage/zapping/VOD tests.

Reference inspected (not executed or blindly incorporated):
https://github.com/boingbasti/e2-serviceapp-vti

Its README requires a target sysroot which is absent from the repository.
Its MIPS build uses Python 2.7, libsigc++ 1.2 and explicit C++/glibc ABI
compatibility settings. These must be checked against the intended receiver.
The reference includes FFmpeg 6.1.1 changes; upgrading VTi FFmpeg is not implied
or authorized merely by adapting ServiceApp.

CI checks real Python 2.7 execution and Python C-API syntax, as well as the
existing Python 3 regressions. Those checks do not substitute for a VTi SDK
build or hardware verification.
