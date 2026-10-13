/* Build-only CPython 2.7 configuration for the verified VTi UCS2 runtime.
 * Debian's same-version Python headers otherwise select UCS4. CPython's
 * unicodeobject.h derives API names and Py_UNICODE from these configuration
 * macros. This changes the actual Unicode type, not just a linker symbol.
 */
#ifndef SERVICEAPP_VTI_PYTHON_CONFIG
#define SERVICEAPP_VTI_PYTHON_CONFIG
#include <pyconfig.h>
#undef Py_UNICODE_SIZE
#define Py_UNICODE_SIZE 2
#undef PY_UNICODE_TYPE
#define PY_UNICODE_TYPE unsigned short
#undef Py_UNICODE_WIDE
#undef HAVE_USABLE_WCHAR_T
#endif
