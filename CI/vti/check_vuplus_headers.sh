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
git init -q vuplus
git -C vuplus fetch --depth 1 https://github.com/OpenVuPlus/dvbapp.git \
  847b84273e9696223fd0f50d1957309cfee2caec
git -C vuplus checkout -q --detach FETCH_HEAD
git init -q dvbsi
git -C dvbsi fetch --depth 1 https://github.com/jack2015/libdvbsi.git \
  ff57e585c47fd62b484d0a8f96fe4f020f5840e3
git -C dvbsi checkout -q --detach FETCH_HEAD
cd "$root"
# VTi exports the newer subtitle methods (confirmed by the pinned binary),
# while public Vu+ still declares the older eWidget/Python-list interface.
patch -p1 -d "$sdk/vuplus" < CI/vti/vuplus-subtitle-interface.patch
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
for source in "$sdk/check.cpp" src/serviceapp/serviceapp.cpp \
  src/serviceapp/extplayer.cpp src/serviceapp/myconsole.cpp \
  src/serviceapp/scriptrun.cpp src/serviceapp/exteplayer3.cpp \
  src/serviceapp/gstplayer.cpp src/serviceapp/common.cpp; do
  echo "Checking $source against public Vu+ / Python 2.7 / libsigc++ 1.2.5"
  g++ -std=gnu++11 -fsyntax-only -DSERVICEAPP_VTI15 -D_GLIBCXX_USE_CXX11_ABI=0 \
    -DNO_UCHARDET -include Python.h -I /usr/local/include/python2.7 \
    -I "$sdk/vuplus" -I "$sdk/vuplus/include" -I "$sdk/dvbsi/include" \
    -I /usr/include/freetype2 \
    -I "$sdk/libsigc++-1.2.5" -I "$sdk/libsigc++-1.2.5/sigc++/config" \
    -I src/serviceapp "$source"
done
