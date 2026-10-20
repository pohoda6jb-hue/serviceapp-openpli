# VU+ Duo4K / OpenPLi 9.2 test build

Target facts already supplied by the user: OpenPLi 9.2 release, ARMv7,
Python 3.9.9, package architecture `vuduo4k` with `armv7ahf-neon` supported.
The original player listing contained `exteplayer3 - 181`.

The OpenEmbedded build uses `MACHINE=vuduo4k` and the pinned OpenPLi 9.2
revision in `build.sh`. It produces ServiceApp and `exteplayer3-serviceapp`.
The latter installs `/usr/bin/exteplayer3-serviceapp`, allowing the separately
installed `/usr/bin/exteplayer3` to remain available to other plugins.
The Duo4K ServiceApp build selects its companion executable through
`SERVICEAPP_BUNDLED_EXTEPLAYER3`; the on-screen player choice remains
`exteplayer3`. The ServiceApp IPK requires the companion package.

The companion uses the previously audited OpenPLi player source series 69
at `e258b47863fae1d74dbd1d707c948ae4232fea64` and the read-error/explicit-options
patch. It is not presented as a modification of the user's unverified version
181 source. No FFmpeg or image upgrade is included. Other builds retain the
original `exteplayer3` executable name.

Each CI run builds one selected receiver. Push builds select Duo4K; manual
runs offer Duo4K or SF8008. The policy tests execute both executable-name
variants before the target cross-build starts. The IPK audit checks the
receiver/package architecture, native ARM ELF files, exact companion install
path and its ServiceApp dependency, and verifies the companion name is present
in the compiled module before creating the ZIP and checksums.

Receiver playback is still untested. Recovery remains opt-in and finite;
it handles an exited player, not an indefinitely frozen process. Follow the
bundled `CTI-NEJDRIV.txt` and `TESTING.md` for TS/HLS, VOD and cancellation tests.
