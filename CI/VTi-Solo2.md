# VTi 15.0.04 / VU+ Solo2 port preparation

This branch prepares Python 2.7 persistence and native option handling. It does
not produce or claim a working VTi MIPS package yet. OpenPLi ARM binaries are
not transferable to Solo2.

## Receiver facts supplied 2026-10-13

* `/etc/issue`: `vuplus 3.0.0` (this banner alone does not identify the VTi build).
* `uname -m`: `mips`; accepted packages include `mips32el`, `vusolo2`, `mipsel`.
* Python 2.7.9, `python-core` 2.7.9-r1-vuplus1.
* glibc 2.21-r0, libgcc1 4.9.2-r0, libsigc-1.2-5 1.2.5-r2.
* libavcodec57, libavformat57, libavutil55: VTi001.3.4.1-r14.
* Enigma2, installed ServiceApp/player, libstdc++, OpenSSL and development
  headers remain unconfirmed. The original grep expression contained embedded
  newlines and did not reliably match all requested package names.

The SF8008 player uses libavcodec58/libavformat58/libavutil56 and glibc >=2.33;
that package cannot satisfy this receiver's confirmed ABI requirements.

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
