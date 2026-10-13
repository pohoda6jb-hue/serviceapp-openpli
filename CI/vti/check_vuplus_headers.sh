#!/bin/sh
# Native-host syntax check of production code against pinned public Vu+ headers.
# This is deliberately separate from a target MIPS link/receiver test.
set -eu
root=$(pwd)
sdk="$root/work/vti-headers"
mkdir -p "$sdk"
cd "$sdk"
curl -fL --retry 2 --max-time 60 \
  https://download.gnome.org/sources/libsigc++/1.2/libsigc++-1.2.5.tar.gz \
  -o libsigc.tar.gz
printf '%s\n' 'dcd6d3ea9a2c185b5286f80eefe9ac1402036b8fa21cfc742442d99579bd2b3e  libsigc.tar.gz' | sha256sum -c -
tar xzf libsigc.tar.gz
cd libsigc++-1.2.5
./configure --disable-dependency-tracking > "$sdk/sigc-configure.log" 2>&1
# This release generates slot.h/signal.h with m4 during make, not configure.
make -C sigc++ slot.h signal.h bind.h bind_return.h object_slot.h \
  retype_return.h class_slot.h hide.h retype.h method_slot.h \
  > "$sdk/sigc-make.log" 2>&1
cd "$sdk"
curl -fL --retry 2 --max-time 60 \
  https://mirror.metanet.ch/BLFS/conglomeration/uchardet/uchardet-0.0.6.tar.xz \
  -o uchardet.tar.xz
# Upstream release checksum also published in Stremio's source build manifest.
printf '%s\n' '8351328cdfbcb2432e63938721dd781eb8c11ebc56e3a89d0f84576b96002c61  uchardet.tar.xz' | sha256sum -c -
tar xJf uchardet.tar.xz
mkdir -p "$sdk/uchar-include/uchardet"
cp uchardet-0.0.6/src/uchardet.h "$sdk/uchar-include/uchardet/"
git init -q vuplus
git -C vuplus fetch --depth 1 https://github.com/OpenVuPlus/dvbapp.git \
  847b84273e9696223fd0f50d1957309cfee2caec
git -C vuplus checkout -q --detach FETCH_HEAD
git init -q dvbsi
git -C dvbsi fetch --depth 1 https://github.com/jack2015/libdvbsi.git \
  ff57e585c47fd62b484d0a8f96fe4f020f5840e3
git -C dvbsi checkout -q --detach FETCH_HEAD
cd "$root"
# The old header recognizes GCC 3/4 only. Newer GCC still uses __gnu_cxx::slist.
sed -i 's/__GNUC__ == 4 )/__GNUC__ >= 4 )/' "$sdk/vuplus/lib/dvb/idvb.h"
# VTi exports the newer subtitle methods (confirmed by the pinned binary),
# while public Vu+ still declares the older eWidget/Python-list interface.
patch -p1 -d "$sdk/vuplus" < CI/vti/vuplus-subtitle-interface.patch
# GCC 4.9 checks constructor exception cleanup against the inherited delete.
# Expose only that inline forwarding function in the build SDK; keep the
# destructor protected and preserve all fields, virtual methods and layout.
python - "$sdk/vuplus/lib/base/object.h" <<'PY'
import io
import sys
path = sys.argv[1]
old = 'protected:\n\tvoid operator delete(void *p) { ::operator delete(p); }\n'
with io.open(path, encoding='utf-8') as source:
    text = source.read()
assert text.count(old) == 1
with io.open(path, 'w', encoding='utf-8') as destination:
    destination.write(text.replace(old, 'public:\n\tvoid operator delete(void *p) { ::operator delete(p); }\nprotected:\n'))
PY
if [ "${SERVICEAPP_PREPARE_ONLY:-0}" = 1 ]; then exit 0; fi
cat > "$sdk/check.cpp" <<'EOF'
#include "serviceapp.h"
#include <type_traits>
static_assert(!std::is_abstract<eServiceApp>::value,
              "ServiceApp must implement every public Vu+ service method");
static_assert(std::is_same<decltype(&iPlayableService::setTarget),
                          RESULT (iPlayableService::*)(int)>::value,
              "Unexpected Vu+ setTarget prototype");
static_assert(std::is_same<decltype(&iStreamedService::getBufferCharge),
                          PyObject* (iStreamedService::*)()>::value,
              "Unexpected Vu+ streamed-buffer prototype");
EOF
status=0
for source in "$sdk/check.cpp" src/serviceapp/serviceapp.cpp \
  src/serviceapp/extplayer.cpp src/serviceapp/myconsole.cpp \
  src/serviceapp/scriptrun.cpp src/serviceapp/exteplayer3.cpp \
  src/serviceapp/gstplayer.cpp src/serviceapp/common.cpp \
  src/serviceapp/wrappers.cpp src/serviceapp/m3u8.cpp \
  src/serviceapp/subtitles/subtitles.cpp src/serviceapp/subtitles/subrip.cpp; do
  echo "Checking $source against public Vu+ / Python 2.7 / libsigc++ 1.2.5"
  if ! g++ -std=gnu++11 -fsyntax-only -DSERVICEAPP_VTI15 -DHAVE_EPG -D_GLIBCXX_USE_CXX11_ABI=0 \
    -include Python.h -I /usr/local/include/python2.7 -I "$sdk/uchar-include" \
    -I "$sdk/vuplus" -I "$sdk/vuplus/include" -I "$sdk/dvbsi/include" \
    -I /usr/include/freetype2 \
    -I "$sdk/libsigc++-1.2.5" -I "$sdk/libsigc++-1.2.5/sigc++/config" \
    -I src/serviceapp "$source"; then
    status=1
  fi
done
exit "$status"
