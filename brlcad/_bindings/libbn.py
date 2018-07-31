'''Wrapper for bn.h

Generated with:
setup.py install

Do not modify this file.
'''

__docformat__ =  'restructuredtext'

# Begin preamble

from ctypesgencore.printer_python.preamble import *
from ctypesgencore.printer_python.preamble import _variadic_function

# End preamble

_libs = {}
_libdirs = []

# Begin loader

# ----------------------------------------------------------------------------
# Copyright (c) 2008 David James
# Copyright (c) 2006-2008 Alex Holkner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

import os.path, re, sys, glob
import platform
import ctypes
import ctypes.util

def _environ_path(name):
    if name in os.environ:
        return os.environ[name].split(":")
    else:
        return []

class LibraryLoader(object):
    def __init__(self):
        self.other_dirs=[]

    def load_library(self,libname):
        """Given the name of a library, load it."""
        paths = self.getpaths(libname)

        for path in paths:
            if os.path.exists(path):
                return self.load(path)

        raise ImportError("%s not found." % libname)

    def load(self,path):
        """Given a path to a library, load it."""
        try:
            # Darwin requires dlopen to be called with mode RTLD_GLOBAL instead
            # of the default RTLD_LOCAL.  Without this, you end up with
            # libraries not being loadable, resulting in "Symbol not found"
            # errors
            if sys.platform == 'darwin':
                return ctypes.CDLL(path, ctypes.RTLD_GLOBAL)
            else:
                return ctypes.cdll.LoadLibrary(path)
        except OSError,e:
            raise ImportError(e)

    def getpaths(self,libname):
        """Return a list of paths where the library might be found."""
        if os.path.isabs(libname):
            yield libname
        else:
            # FIXME / TODO return '.' and os.path.dirname(__file__)
            for path in self.getplatformpaths(libname):
                yield path

            path = ctypes.util.find_library(libname)
            if path: yield path

    def getplatformpaths(self, libname):
        return []

# Darwin (Mac OS X)

class DarwinLibraryLoader(LibraryLoader):
    name_formats = ["lib%s.dylib", "lib%s.so", "lib%s.bundle", "%s.dylib",
                "%s.so", "%s.bundle", "%s"]

    def getplatformpaths(self,libname):
        if os.path.pathsep in libname:
            names = [libname]
        else:
            names = [format % libname for format in self.name_formats]

        for dir in self.getdirs(libname):
            for name in names:
                yield os.path.join(dir,name)

    def getdirs(self,libname):
        '''Implements the dylib search as specified in Apple documentation:

        http://developer.apple.com/documentation/DeveloperTools/Conceptual/
            DynamicLibraries/Articles/DynamicLibraryUsageGuidelines.html

        Before commencing the standard search, the method first checks
        the bundle's ``Frameworks`` directory if the application is running
        within a bundle (OS X .app).
        '''

        dyld_fallback_library_path = _environ_path("DYLD_FALLBACK_LIBRARY_PATH")
        if not dyld_fallback_library_path:
            dyld_fallback_library_path = [os.path.expanduser('~/lib'),
                                          '/usr/local/lib', '/usr/lib']

        dirs = []

        if '/' in libname:
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))
        else:
            dirs.extend(_environ_path("LD_LIBRARY_PATH"))
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))

        dirs.extend(self.other_dirs)
        dirs.append(".")
        dirs.append(os.path.dirname(__file__))

        if hasattr(sys, 'frozen') and sys.frozen == 'macosx_app':
            dirs.append(os.path.join(
                os.environ['RESOURCEPATH'],
                '..',
                'Frameworks'))

        dirs.extend(dyld_fallback_library_path)

        return dirs

# Posix

class PosixLibraryLoader(LibraryLoader):
    _ld_so_cache = None

    def _create_ld_so_cache(self):
        # Recreate search path followed by ld.so.  This is going to be
        # slow to build, and incorrect (ld.so uses ld.so.cache, which may
        # not be up-to-date).  Used only as fallback for distros without
        # /sbin/ldconfig.
        #
        # We assume the DT_RPATH and DT_RUNPATH binary sections are omitted.

        directories = []
        for name in ("LD_LIBRARY_PATH",
                     "SHLIB_PATH", # HPUX
                     "LIBPATH", # OS/2, AIX
                     "LIBRARY_PATH", # BE/OS
                    ):
            if name in os.environ:
                directories.extend(os.environ[name].split(os.pathsep))
        directories.extend(self.other_dirs)
        directories.append(".")
        directories.append(os.path.dirname(__file__))

        try: directories.extend([dir.strip() for dir in open('/etc/ld.so.conf')])
        except IOError: pass

        unix_lib_dirs_list = ['/lib', '/usr/lib', '/lib64', '/usr/lib64']
        if sys.platform.startswith('linux'):
            # Try and support multiarch work in Ubuntu
            # https://wiki.ubuntu.com/MultiarchSpec
            bitage = platform.architecture()[0]
            if bitage.startswith('32'):
                # Assume Intel/AMD x86 compat
                unix_lib_dirs_list += ['/lib/i386-linux-gnu', '/usr/lib/i386-linux-gnu']
            elif bitage.startswith('64'):
                # Assume Intel/AMD x86 compat
                unix_lib_dirs_list += ['/lib/x86_64-linux-gnu', '/usr/lib/x86_64-linux-gnu']
            else:
                # guess...
                unix_lib_dirs_list += glob.glob('/lib/*linux-gnu')
        directories.extend(unix_lib_dirs_list)

        cache = {}
        lib_re = re.compile(r'lib(.*)\.s[ol]')
        ext_re = re.compile(r'\.s[ol]$')
        for dir in directories:
            try:
                for path in glob.glob("%s/*.s[ol]*" % dir):
                    file = os.path.basename(path)

                    # Index by filename
                    if file not in cache:
                        cache[file] = path

                    # Index by library name
                    match = lib_re.match(file)
                    if match:
                        library = match.group(1)
                        if library not in cache:
                            cache[library] = path
            except OSError:
                pass

        self._ld_so_cache = cache

    def getplatformpaths(self, libname):
        if self._ld_so_cache is None:
            self._create_ld_so_cache()

        result = self._ld_so_cache.get(libname)
        if result: yield result

        path = ctypes.util.find_library(libname)
        if path: yield os.path.join("/lib",path)

# Windows

class _WindowsLibrary(object):
    def __init__(self, path):
        self.cdll = ctypes.cdll.LoadLibrary(path)
        self.windll = ctypes.windll.LoadLibrary(path)

    def __getattr__(self, name):
        try: return getattr(self.cdll,name)
        except AttributeError:
            try: return getattr(self.windll,name)
            except AttributeError:
                raise

class WindowsLibraryLoader(LibraryLoader):
    name_formats = ["%s.dll", "lib%s.dll", "%slib.dll"]

    def load_library(self, libname):
        try:
            result = LibraryLoader.load_library(self, libname)
        except ImportError:
            result = None
            if os.path.sep not in libname:
                for name in self.name_formats:
                    try:
                        result = getattr(ctypes.cdll, name % libname)
                        if result:
                            break
                    except WindowsError:
                        result = None
            if result is None:
                try:
                    result = getattr(ctypes.cdll, libname)
                except WindowsError:
                    result = None
            if result is None:
                raise ImportError("%s not found." % libname)
        return result

    def load(self, path):
        return _WindowsLibrary(path)

    def getplatformpaths(self, libname):
        if os.path.sep not in libname:
            for name in self.name_formats:
                dll_in_current_dir = os.path.abspath(name % libname)
                if os.path.exists(dll_in_current_dir):
                    yield dll_in_current_dir
                path = ctypes.util.find_library(name % libname)
                if path:
                    yield path

# Platform switching

# If your value of sys.platform does not appear in this dict, please contact
# the Ctypesgen maintainers.

loaderclass = {
    "darwin":   DarwinLibraryLoader,
    "cygwin":   WindowsLibraryLoader,
    "win32":    WindowsLibraryLoader
}

loader = loaderclass.get(sys.platform, PosixLibraryLoader)()

def add_library_search_dirs(other_dirs):
    loader.other_dirs = other_dirs

load_library = loader.load_library

del loaderclass

# End loader

add_library_search_dirs([])

# Begin libraries

_libs["/opt/brlcad/lib/libbn.dylib"] = load_library("/opt/brlcad/lib/libbn.dylib")

# 1 libraries
# End libraries

# Begin modules

from libbu import *

# 1 modules
# End modules

# /usr/include/math.h: 447
if hasattr(_libs['/opt/brlcad/lib/libbn.dylib'], 'sqrt'):
    sqrt = _libs['/opt/brlcad/lib/libbn.dylib'].sqrt
    sqrt.argtypes = [c_double]
    sqrt.restype = c_double

# /usr/include/math.h: 482
if hasattr(_libs['/opt/brlcad/lib/libbn.dylib'], 'rint'):
    rint = _libs['/opt/brlcad/lib/libbn.dylib'].rint
    rint.argtypes = [c_double]
    rint.restype = c_double

fastf_t = c_double # /opt/brlcad/include/brlcad/vmath.h: 330

vect2d_t = fastf_t * 2 # /opt/brlcad/include/brlcad/vmath.h: 333

vect2dp_t = POINTER(fastf_t) # /opt/brlcad/include/brlcad/vmath.h: 336

point2d_t = fastf_t * 2 # /opt/brlcad/include/brlcad/vmath.h: 339

point2dp_t = POINTER(fastf_t) # /opt/brlcad/include/brlcad/vmath.h: 342

vect_t = fastf_t * 3 # /opt/brlcad/include/brlcad/vmath.h: 345

vectp_t = POINTER(fastf_t) # /opt/brlcad/include/brlcad/vmath.h: 348

point_t = fastf_t * 3 # /opt/brlcad/include/brlcad/vmath.h: 351

pointp_t = POINTER(fastf_t) # /opt/brlcad/include/brlcad/vmath.h: 354

hvect_t = fastf_t * 4 # /opt/brlcad/include/brlcad/vmath.h: 357

quat_t = hvect_t # /opt/brlcad/include/brlcad/vmath.h: 360

hpoint_t = fastf_t * 4 # /opt/brlcad/include/brlcad/vmath.h: 363

mat_t = fastf_t * (4 * 4) # /opt/brlcad/include/brlcad/vmath.h: 366

matp_t = POINTER(fastf_t) # /opt/brlcad/include/brlcad/vmath.h: 369

plane_t = fastf_t * 4 # /opt/brlcad/include/brlcad/vmath.h: 393

enum_vmath_vector_component_ = c_int # /opt/brlcad/include/brlcad/vmath.h: 402

X = 0 # /opt/brlcad/include/brlcad/vmath.h: 402

Y = 1 # /opt/brlcad/include/brlcad/vmath.h: 402

Z = 2 # /opt/brlcad/include/brlcad/vmath.h: 402

W = 3 # /opt/brlcad/include/brlcad/vmath.h: 402

H = W # /opt/brlcad/include/brlcad/vmath.h: 402

vmath_vector_component = enum_vmath_vector_component_ # /opt/brlcad/include/brlcad/vmath.h: 402

enum_vmath_matrix_component_ = c_int # /opt/brlcad/include/brlcad/vmath.h: 416

MSX = 0 # /opt/brlcad/include/brlcad/vmath.h: 416

MDX = 3 # /opt/brlcad/include/brlcad/vmath.h: 416

MSY = 5 # /opt/brlcad/include/brlcad/vmath.h: 416

MDY = 7 # /opt/brlcad/include/brlcad/vmath.h: 416

MSZ = 10 # /opt/brlcad/include/brlcad/vmath.h: 416

MDZ = 11 # /opt/brlcad/include/brlcad/vmath.h: 416

MSA = 15 # /opt/brlcad/include/brlcad/vmath.h: 416

vmath_matrix_component = enum_vmath_matrix_component_ # /opt/brlcad/include/brlcad/vmath.h: 416

# <built-in>
try:
    __FLT_EPSILON__ = 1.1920929e-07
except:
    pass

# <built-in>
try:
    __DBL_EPSILON__ = 2.220446049250313e-16
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 109
try:
    _USE_MATH_DEFINES = 1
except:
    pass

# /usr/include/math.h: 63
try:
    HUGE_VALF = 1e+50
except:
    pass

# /usr/include/math.h: 68
try:
    INFINITY = HUGE_VALF
except:
    pass

# /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/9.0.0/include/float.h: 120
try:
    FLT_EPSILON = __FLT_EPSILON__
except:
    pass

# /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/9.0.0/include/float.h: 121
try:
    DBL_EPSILON = __DBL_EPSILON__
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 128
try:
    M_1_2PI = 0.15915494309189535
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 143
try:
    M_EULER = 0.5772156649015329
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 158
try:
    M_LNPI = 1.1447298858494002
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 164
try:
    M_2PI = 6.283185307179586
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 170
try:
    M_PI_3 = 1.0471975511965979
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 182
try:
    M_SQRT3 = 1.7320508075688772
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 185
try:
    M_SQRTPI = 1.772453850905516
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 189
try:
    DEG2RAD = 0.017453292519943295
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 192
try:
    RAD2DEG = 57.29577951308232
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 234
try:
    MAX_FASTF = 1e+73
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 235
try:
    SQRT_MAX_FASTF = 1e+36
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 236
try:
    SMALL_FASTF = 1e-77
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 240
try:
    SQRT_SMALL_FASTF = 1e-39
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 245
try:
    SMALL = SQRT_SMALL_FASTF
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 288
try:
    VDIVIDE_TOL = DBL_EPSILON
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 293
try:
    VUNITIZE_TOL = FLT_EPSILON
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 301
try:
    ELEMENTS_PER_VECT2D = 2
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 304
try:
    ELEMENTS_PER_POINT2D = 2
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 307
try:
    ELEMENTS_PER_VECT = 3
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 310
try:
    ELEMENTS_PER_POINT = 3
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 313
try:
    ELEMENTS_PER_HVECT = 4
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 316
try:
    ELEMENTS_PER_HPOINT = 4
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 319
try:
    ELEMENTS_PER_PLANE = 4
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 322
try:
    ELEMENTS_PER_MAT = (ELEMENTS_PER_PLANE * ELEMENTS_PER_PLANE)
except:
    pass

# /opt/brlcad/include/brlcad/vmath.h: 422
def INVALID(n):
    return (not ((n > (-INFINITY)) and (n < INFINITY)))

# /opt/brlcad/include/brlcad/vmath.h: 428
def VINVALID(v):
    return (((INVALID ((v [X]))) or (INVALID ((v [Y])))) or (INVALID ((v [Z]))))

# /opt/brlcad/include/brlcad/vmath.h: 434
def V2INVALID(v):
    return ((INVALID ((v [X]))) or (INVALID ((v [Y]))))

# /opt/brlcad/include/brlcad/vmath.h: 440
def HINVALID(v):
    return ((((INVALID ((v [X]))) or (INVALID ((v [Y])))) or (INVALID ((v [Z])))) or (INVALID ((v [W]))))

# /opt/brlcad/include/brlcad/vmath.h: 461
def NEAR_ZERO(val, epsilon):
    return ((val > (-epsilon)) and (val < epsilon))

# /opt/brlcad/include/brlcad/vmath.h: 468
def VNEAR_ZERO(v, tol):
    return (((NEAR_ZERO ((v [X]), tol)) and (NEAR_ZERO ((v [Y]), tol))) and (NEAR_ZERO ((v [Z]), tol)))

# /opt/brlcad/include/brlcad/vmath.h: 477
def V2NEAR_ZERO(v, tol):
    return ((NEAR_ZERO ((v [X]), tol)) and (NEAR_ZERO ((v [Y]), tol)))

# /opt/brlcad/include/brlcad/vmath.h: 496
def ZERO(_a):
    return (NEAR_ZERO (_a, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 504
def VZERO(_a):
    return (VNEAR_ZERO (_a, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 512
def V2ZERO(_a):
    return (V2NEAR_ZERO (_a, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 527
def NEAR_EQUAL(_a, _b, _tol):
    return (NEAR_ZERO ((_a - _b), _tol))

# /opt/brlcad/include/brlcad/vmath.h: 533
def VNEAR_EQUAL(_a, _b, _tol):
    return (((NEAR_EQUAL ((_a [X]), (_b [X]), _tol)) and (NEAR_EQUAL ((_a [Y]), (_b [Y]), _tol))) and (NEAR_EQUAL ((_a [Z]), (_b [Z]), _tol)))

# /opt/brlcad/include/brlcad/vmath.h: 542
def V2NEAR_EQUAL(a, b, tol):
    return ((NEAR_EQUAL ((a [X]), (b [X]), tol)) and (NEAR_EQUAL ((a [Y]), (b [Y]), tol)))

# /opt/brlcad/include/brlcad/vmath.h: 550
def HNEAR_EQUAL(_a, _b, _tol):
    return ((((NEAR_EQUAL ((_a [X]), (_b [X]), _tol)) and (NEAR_EQUAL ((_a [Y]), (_b [Y]), _tol))) and (NEAR_EQUAL ((_a [Z]), (_b [Z]), _tol))) and (NEAR_EQUAL ((_a [W]), (_b [W]), _tol)))

# /opt/brlcad/include/brlcad/vmath.h: 562
def EQUAL(_a, _b):
    return (NEAR_EQUAL (_a, _b, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 571
def VEQUAL(_a, _b):
    return (VNEAR_EQUAL (_a, _b, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 577
def V2EQUAL(_a, _b):
    return (V2NEAR_EQUAL (_a, _b, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 583
def HEQUAL(_a, _b):
    return (HNEAR_EQUAL (_a, _b, SMALL_FASTF))

# /opt/brlcad/include/brlcad/vmath.h: 587
def DIST_PT_PLANE(_pt, _pl):
    return (((VDOT (_pt, _pl)).value) - (_pl [W]))

# /opt/brlcad/include/brlcad/vmath.h: 590
def DIST_PT_PT_SQ(_a, _b):
    return (((((_a [X]) - (_b [X])) * ((_a [X]) - (_b [X]))) + (((_a [Y]) - (_b [Y])) * ((_a [Y]) - (_b [Y])))) + (((_a [Z]) - (_b [Z])) * ((_a [Z]) - (_b [Z]))))

# /opt/brlcad/include/brlcad/vmath.h: 594
def DIST_PT_PT(_a, _b):
    return (sqrt ((DIST_PT_PT_SQ (_a, _b))))

# /opt/brlcad/include/brlcad/vmath.h: 597
def DIST_PT2_PT2_SQ(_a, _b):
    return ((((_a [X]) - (_b [X])) * ((_a [X]) - (_b [X]))) + (((_a [Y]) - (_b [Y])) * ((_a [Y]) - (_b [Y]))))

# /opt/brlcad/include/brlcad/vmath.h: 600
def DIST_PT2_PT2(_a, _b):
    return (sqrt ((DIST_PT2_PT2_SQ (_a, _b))))

# /opt/brlcad/include/brlcad/vmath.h: 1431
def MAGSQ(v):
    return ((((v [X]) * (v [X])) + ((v [Y]) * (v [Y]))) + ((v [Z]) * (v [Z])))

# /opt/brlcad/include/brlcad/vmath.h: 1432
def MAG2SQ(v):
    return (((v [X]) * (v [X])) + ((v [Y]) * (v [Y])))

# /opt/brlcad/include/brlcad/vmath.h: 1439
def MAGNITUDE(v):
    return (sqrt ((MAGSQ (v))))

# /opt/brlcad/include/brlcad/vmath.h: 1445
def MAGNITUDE2(v):
    return (sqrt ((MAG2SQ (v))))

# /opt/brlcad/include/brlcad/vmath.h: 1473
def V2CROSS(a, b):
    return (((a [X]) * (b [Y])) - ((a [Y]) * (b [X])))

# /opt/brlcad/include/brlcad/vmath.h: 1482
def VDOT(a, b):
    return ((((a [X]) * (b [X])) + ((a [Y]) * (b [Y]))) + ((a [Z]) * (b [Z])))

# /opt/brlcad/include/brlcad/vmath.h: 1484
def V2DOT(a, b):
    return (((a [X]) * (b [X])) + ((a [Y]) * (b [Y])))

# /opt/brlcad/include/brlcad/vmath.h: 1486
def HDOT(a, b):
    return (((((a [X]) * (b [X])) + ((a [Y]) * (b [Y]))) + ((a [Z]) * (b [Z]))) + ((a [W]) * (b [W])))

# /opt/brlcad/include/brlcad/vmath.h: 1539
def VSUB2DOT(_pt2, _pt, _vec):
    return (((((_pt2 [X]) - (_pt [X])) * (_vec [X])) + (((_pt2 [Y]) - (_pt [Y])) * (_vec [Y]))) + (((_pt2 [Z]) - (_pt [Z])) * (_vec [Z])))

# /opt/brlcad/include/brlcad/vmath.h: 1561
def INTCLAMP(_a):
    return (NEAR_EQUAL (_a, (rint (_a)), VUNITIZE_TOL)) and (rint (_a)) or _a

# /opt/brlcad/include/brlcad/vmath.h: 1936
def QMAGSQ(a):
    return (((((a [X]) * (a [X])) + ((a [Y]) * (a [Y]))) + ((a [Z]) * (a [Z]))) + ((a [W]) * (a [W])))

# /opt/brlcad/include/brlcad/vmath.h: 1941
def QMAGNITUDE(a):
    return (sqrt ((QMAGSQ (a))))

# /opt/brlcad/include/brlcad/vmath.h: 1944
def QDOT(a, b):
    return (((((a [X]) * (b [X])) + ((a [Y]) * (b [Y]))) + ((a [Z]) * (b [Z]))) + ((a [W]) * (b [W])))

# /opt/brlcad/include/brlcad/vmath.h: 2003
def V3RPP_DISJOINT(_l1, _h1, _l2, _h2):
    return (((((((_l1 [X]) > (_h2 [X])) or ((_l1 [Y]) > (_h2 [Y]))) or ((_l1 [Z]) > (_h2 [Z]))) or ((_l2 [X]) > (_h1 [X]))) or ((_l2 [Y]) > (_h1 [Y]))) or ((_l2 [Z]) > (_h1 [Z])))

# /opt/brlcad/include/brlcad/vmath.h: 2011
def V3RPP_DISJOINT_TOL(_l1, _h1, _l2, _h2, _t):
    return (((((((_l1 [X]) > ((_h2 [X]) + _t)) or ((_l1 [Y]) > ((_h2 [Y]) + _t))) or ((_l1 [Z]) > ((_h2 [Z]) + _t))) or ((_l2 [X]) > ((_h1 [X]) + _t))) or ((_l2 [Y]) > ((_h1 [Y]) + _t))) or ((_l2 [Z]) > ((_h1 [Z]) + _t)))

# /opt/brlcad/include/brlcad/vmath.h: 2020
def V3RPP_OVERLAP(_l1, _h1, _l2, _h2):
    return (not (((((((_l1 [X]) > (_h2 [X])) or ((_l1 [Y]) > (_h2 [Y]))) or ((_l1 [Z]) > (_h2 [Z]))) or ((_l2 [X]) > (_h1 [X]))) or ((_l2 [Y]) > (_h1 [Y]))) or ((_l2 [Z]) > (_h1 [Z]))))

# /opt/brlcad/include/brlcad/vmath.h: 2028
def V3RPP_OVERLAP_TOL(_l1, _h1, _l2, _h2, _t):
    return (not (((((((_l1 [X]) > ((_h2 [X]) + _t)) or ((_l1 [Y]) > ((_h2 [Y]) + _t))) or ((_l1 [Z]) > ((_h2 [Z]) + _t))) or ((_l2 [X]) > ((_h1 [X]) + _t))) or ((_l2 [Y]) > ((_h1 [Y]) + _t))) or ((_l2 [Z]) > ((_h1 [Z]) + _t))))

# /opt/brlcad/include/brlcad/vmath.h: 2041
def V3PT_IN_RPP(_pt, _lo, _hi):
    return (((((((_pt [X]) >= (_lo [X])) and ((_pt [X]) <= (_hi [X]))) and ((_pt [Y]) >= (_lo [Y]))) and ((_pt [Y]) <= (_hi [Y]))) and ((_pt [Z]) >= (_lo [Z]))) and ((_pt [Z]) <= (_hi [Z])))

# /opt/brlcad/include/brlcad/vmath.h: 2051
def V3PT_IN_RPP_TOL(_pt, _lo, _hi, _t):
    return (((((((_pt [X]) >= ((_lo [X]) - _t)) and ((_pt [X]) <= ((_hi [X]) + _t))) and ((_pt [Y]) >= ((_lo [Y]) - _t))) and ((_pt [Y]) <= ((_hi [Y]) + _t))) and ((_pt [Z]) >= ((_lo [Z]) - _t))) and ((_pt [Z]) <= ((_hi [Z]) + _t)))

# /opt/brlcad/include/brlcad/vmath.h: 2060
def V3PT_OUT_RPP_TOL(_pt, _lo, _hi, _t):
    return (((((((_pt [X]) < ((_lo [X]) - _t)) or ((_pt [X]) > ((_hi [X]) + _t))) or ((_pt [Y]) < ((_lo [Y]) - _t))) or ((_pt [Y]) > ((_hi [Y]) + _t))) or ((_pt [Z]) < ((_lo [Z]) - _t))) or ((_pt [Z]) > ((_hi [Z]) + _t)))

# /opt/brlcad/include/brlcad/vmath.h: 2071
def V3RPP1_IN_RPP2(_lo1, _hi1, _lo2, _hi2):
    return (((((((_lo1 [X]) >= (_lo2 [X])) and ((_hi1 [X]) <= (_hi2 [X]))) and ((_lo1 [Y]) >= (_lo2 [Y]))) and ((_hi1 [Y]) <= (_hi2 [Y]))) and ((_lo1 [Z]) >= (_lo2 [Z]))) and ((_hi1 [Z]) <= (_hi2 [Z])))

# No inserted files

