'''Wrapper for wdb.h

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

_libs["/opt/brlcad/lib/libwdb.dylib"] = load_library("/opt/brlcad/lib/libwdb.dylib")

# 1 libraries
# End libraries

# Begin modules

from libbu import *
from libbn import *
from librt import *

# 3 modules
# End modules

# /opt/brlcad/include/brlcad/./rt/wdb.h: 49
class struct_rt_wdb_(Structure):
    pass

struct_rt_wdb_.__slots__ = [
    'l',
    'type',
    'dbip',
    'wdb_initial_tree_state',
    'wdb_ttol',
    'wdb_tol',
    'wdb_resp',
    'wdb_prestr',
    'wdb_ncharadd',
    'wdb_num_dups',
    'wdb_item_default',
    'wdb_air_default',
    'wdb_mat_default',
    'wdb_los_default',
    'wdb_name',
    'wdb_observers',
    'wdb_interp',
]
struct_rt_wdb_._fields_ = [
    ('l', struct_bu_list),
    ('type', c_int),
    ('dbip', POINTER(struct_db_i)),
    ('wdb_initial_tree_state', struct_db_tree_state),
    ('wdb_ttol', struct_rt_tess_tol),
    ('wdb_tol', struct_bn_tol),
    ('wdb_resp', POINTER(struct_resource)),
    ('wdb_prestr', struct_bu_vls),
    ('wdb_ncharadd', c_int),
    ('wdb_num_dups', c_int),
    ('wdb_item_default', c_int),
    ('wdb_air_default', c_int),
    ('wdb_mat_default', c_int),
    ('wdb_los_default', c_int),
    ('wdb_name', struct_bu_vls),
    ('wdb_observers', struct_bu_observer),
    ('wdb_interp', POINTER(None)),
]

# /opt/brlcad/include/brlcad/./rt/wdb.h: 92
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_fopen'):
    _wdb_fopen = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_fopen
    _wdb_fopen.argtypes = [String]
    _wdb_fopen.restype = POINTER(struct_rt_wdb)

# /opt/brlcad/include/brlcad/./rt/wdb.h: 104
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_fopen_v'):
    _wdb_fopen_v = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_fopen_v
    _wdb_fopen_v.argtypes = [String, c_int]
    _wdb_fopen_v.restype = POINTER(struct_rt_wdb)

# /opt/brlcad/include/brlcad/./rt/wdb.h: 117
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_dbopen'):
    _wdb_dbopen = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_dbopen
    _wdb_dbopen.argtypes = [POINTER(struct_db_i), c_int]
    _wdb_dbopen.restype = POINTER(struct_rt_wdb)

# /opt/brlcad/include/brlcad/./rt/wdb.h: 131
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_import'):
    _wdb_import = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_import
    _wdb_import.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_rt_db_internal), String, mat_t]
    _wdb_import.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 144
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_export_external'):
    _wdb_export_external = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_export_external
    _wdb_export_external.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_bu_external), String, c_int, c_ubyte]
    _wdb_export_external.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 166
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_put_internal'):
    _wdb_put_internal = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_put_internal
    _wdb_put_internal.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_rt_db_internal), c_double]
    _wdb_put_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 190
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_export'):
    _wdb_export = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_export
    _wdb_export.argtypes = [POINTER(struct_rt_wdb), String, POINTER(None), c_int, c_double]
    _wdb_export.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 195
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_init'):
    _wdb_init = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_init
    _wdb_init.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_db_i), c_int]
    _wdb_init.restype = None

# /opt/brlcad/include/brlcad/./rt/wdb.h: 204
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_close'):
    _wdb_close = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_close
    _wdb_close.argtypes = [POINTER(struct_rt_wdb)]
    _wdb_close.restype = None

# /opt/brlcad/include/brlcad/./rt/wdb.h: 215
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_import_from_path'):
    _wdb_import_from_path = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_import_from_path
    _wdb_import_from_path.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), String, POINTER(struct_rt_wdb)]
    _wdb_import_from_path.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 231
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'wdb_import_from_path2'):
    _wdb_import_from_path2 = _libs['/opt/brlcad/lib/libwdb.dylib'].wdb_import_from_path2
    _wdb_import_from_path2.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), String, POINTER(struct_rt_wdb), matp_t]
    _wdb_import_from_path2.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 77
class struct_wmember(Structure):
    pass

struct_wmember.__slots__ = [
    'l',
    'wm_op',
    'wm_mat',
    'wm_name',
]
struct_wmember._fields_ = [
    ('l', struct_bu_list),
    ('wm_op', c_int),
    ('wm_mat', mat_t),
    ('wm_name', String),
]

# /opt/brlcad/include/brlcad/wdb.h: 93
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_id'):
    mk_id = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_id
    mk_id.argtypes = [POINTER(struct_rt_wdb), String]
    mk_id.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 101
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_id_units'):
    mk_id_units = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_id_units
    mk_id_units.argtypes = [POINTER(struct_rt_wdb), String, String]
    mk_id_units.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 120
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_id_editunits'):
    mk_id_editunits = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_id_editunits
    mk_id_editunits.argtypes = [POINTER(struct_rt_wdb), String, c_double]
    mk_id_editunits.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 129
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_half'):
    mk_half = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_half
    mk_half.argtypes = [POINTER(struct_rt_wdb), String, vect_t, fastf_t]
    mk_half.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 135
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_grip'):
    mk_grip = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_grip
    mk_grip.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, fastf_t]
    mk_grip.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 145
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_rpp'):
    mk_rpp = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_rpp
    mk_rpp.argtypes = [POINTER(struct_rt_wdb), String, point_t, point_t]
    mk_rpp.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 153
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_wedge'):
    mk_wedge = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_wedge
    mk_wedge.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, fastf_t, fastf_t, fastf_t, fastf_t]
    mk_wedge.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 158
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_arb4'):
    mk_arb4 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_arb4
    mk_arb4.argtypes = [POINTER(struct_rt_wdb), String, POINTER(fastf_t)]
    mk_arb4.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 160
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_arb5'):
    mk_arb5 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_arb5
    mk_arb5.argtypes = [POINTER(struct_rt_wdb), String, POINTER(fastf_t)]
    mk_arb5.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 162
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_arb6'):
    mk_arb6 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_arb6
    mk_arb6.argtypes = [POINTER(struct_rt_wdb), String, POINTER(fastf_t)]
    mk_arb6.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 164
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_arb7'):
    mk_arb7 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_arb7
    mk_arb7.argtypes = [POINTER(struct_rt_wdb), String, POINTER(fastf_t)]
    mk_arb7.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 174
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_arb8'):
    mk_arb8 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_arb8
    mk_arb8.argtypes = [POINTER(struct_rt_wdb), String, POINTER(fastf_t)]
    mk_arb8.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 179
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_sph'):
    mk_sph = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_sph
    mk_sph.argtypes = [POINTER(struct_rt_wdb), String, point_t, fastf_t]
    mk_sph.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 187
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_ell'):
    mk_ell = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_ell
    mk_ell.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, vect_t]
    mk_ell.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 194
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_tor'):
    mk_tor = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_tor
    mk_tor.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, c_double, c_double]
    mk_tor.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 200
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_rcc'):
    mk_rcc = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_rcc
    mk_rcc.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, fastf_t]
    mk_rcc.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 206
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_tgc'):
    mk_tgc = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_tgc
    mk_tgc.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, vect_t, vect_t, vect_t]
    mk_tgc.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 215
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_cone'):
    mk_cone = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_cone
    mk_cone.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, fastf_t, fastf_t, fastf_t]
    mk_cone.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 222
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_trc_h'):
    mk_trc_h = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_trc_h
    mk_trc_h.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, fastf_t, fastf_t]
    mk_trc_h.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 228
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_trc_top'):
    mk_trc_top = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_trc_top
    mk_trc_top.argtypes = [POINTER(struct_rt_wdb), String, point_t, point_t, fastf_t, fastf_t]
    mk_trc_top.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 236
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_rpc'):
    mk_rpc = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_rpc
    mk_rpc.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, c_double]
    mk_rpc.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 251
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_rhc'):
    mk_rhc = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_rhc
    mk_rhc.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, fastf_t, fastf_t]
    mk_rhc.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 265
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_epa'):
    mk_epa = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_epa
    mk_epa.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, fastf_t, fastf_t]
    mk_epa.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 281
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_ehy'):
    mk_ehy = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_ehy
    mk_ehy.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, fastf_t, fastf_t, fastf_t]
    mk_ehy.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 296
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_hyp'):
    mk_hyp = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_hyp
    mk_hyp.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, fastf_t, fastf_t]
    mk_hyp.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 312
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_eto'):
    mk_eto = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_eto
    mk_eto.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, fastf_t, fastf_t]
    mk_eto.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 325
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_metaball'):
    mk_metaball = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_metaball
    mk_metaball.argtypes = [POINTER(struct_rt_wdb), String, c_size_t, c_int, fastf_t, POINTER(fastf_t) * 5]
    mk_metaball.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 338
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_arbn'):
    mk_arbn = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_arbn
    mk_arbn.argtypes = [POINTER(struct_rt_wdb), String, c_size_t, POINTER(plane_t)]
    mk_arbn.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 340
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_ars'):
    mk_ars = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_ars
    mk_ars.argtypes = [POINTER(struct_rt_wdb), String, c_size_t, c_size_t, POINTER(POINTER(fastf_t))]
    mk_ars.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 347
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_constraint'):
    mk_constraint = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_constraint
    mk_constraint.argtypes = [POINTER(struct_rt_wdb), String, String]
    mk_constraint.restype = c_int

enum_anon_136 = c_int # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FLOAT = 0 # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_DOUBLE = (WDB_BINUNIF_FLOAT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_CHAR = (WDB_BINUNIF_DOUBLE + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_UCHAR = (WDB_BINUNIF_CHAR + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_SHORT = (WDB_BINUNIF_UCHAR + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_USHORT = (WDB_BINUNIF_SHORT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_INT = (WDB_BINUNIF_USHORT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_UINT = (WDB_BINUNIF_INT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_LONG = (WDB_BINUNIF_UINT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_ULONG = (WDB_BINUNIF_LONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_LONGLONG = (WDB_BINUNIF_ULONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_ULONGLONG = (WDB_BINUNIF_LONGLONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_INT8 = (WDB_BINUNIF_ULONGLONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_UINT8 = (WDB_BINUNIF_INT8 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_INT16 = (WDB_BINUNIF_UINT8 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_UINT16 = (WDB_BINUNIF_INT16 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_INT32 = (WDB_BINUNIF_UINT16 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_UINT32 = (WDB_BINUNIF_INT32 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_INT64 = (WDB_BINUNIF_UINT32 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_UINT64 = (WDB_BINUNIF_INT64 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_FLOAT = (WDB_BINUNIF_UINT64 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_DOUBLE = (WDB_BINUNIF_FILE_FLOAT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_CHAR = (WDB_BINUNIF_FILE_DOUBLE + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_UCHAR = (WDB_BINUNIF_FILE_CHAR + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_SHORT = (WDB_BINUNIF_FILE_UCHAR + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_USHORT = (WDB_BINUNIF_FILE_SHORT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_INT = (WDB_BINUNIF_FILE_USHORT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_UINT = (WDB_BINUNIF_FILE_INT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_LONG = (WDB_BINUNIF_FILE_UINT + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_ULONG = (WDB_BINUNIF_FILE_LONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_LONGLONG = (WDB_BINUNIF_FILE_ULONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_ULONGLONG = (WDB_BINUNIF_FILE_LONGLONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_INT8 = (WDB_BINUNIF_FILE_ULONGLONG + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_UINT8 = (WDB_BINUNIF_FILE_INT8 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_INT16 = (WDB_BINUNIF_FILE_UINT8 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_UINT16 = (WDB_BINUNIF_FILE_INT16 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_INT32 = (WDB_BINUNIF_FILE_UINT16 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_UINT32 = (WDB_BINUNIF_FILE_INT32 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_INT64 = (WDB_BINUNIF_FILE_UINT32 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

WDB_BINUNIF_FILE_UINT64 = (WDB_BINUNIF_FILE_INT64 + 1) # /opt/brlcad/include/brlcad/wdb.h: 391

wdb_binunif = enum_anon_136 # /opt/brlcad/include/brlcad/wdb.h: 391

# /opt/brlcad/include/brlcad/wdb.h: 405
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_binunif'):
    mk_binunif = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_binunif
    mk_binunif.argtypes = [POINTER(struct_rt_wdb), String, POINTER(None), wdb_binunif, c_long]
    mk_binunif.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 411
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_bot'):
    mk_bot = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_bot
    mk_bot.argtypes = [POINTER(struct_rt_wdb), String, c_ubyte, c_ubyte, c_ubyte, c_size_t, c_size_t, POINTER(fastf_t), POINTER(c_int), POINTER(fastf_t), POINTER(struct_bu_bitv)]
    mk_bot.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 438
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_bot_w_normals'):
    mk_bot_w_normals = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_bot_w_normals
    mk_bot_w_normals.argtypes = [POINTER(struct_rt_wdb), String, c_ubyte, c_ubyte, c_ubyte, c_size_t, c_size_t, POINTER(fastf_t), POINTER(c_int), POINTER(fastf_t), POINTER(struct_bu_bitv), c_size_t, POINTER(fastf_t), POINTER(c_int)]
    mk_bot_w_normals.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 472
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_brep'):
    mk_brep = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_brep
    mk_brep.argtypes = [POINTER(struct_rt_wdb), String, POINTER(None)]
    mk_brep.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 481
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_bspline'):
    mk_bspline = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_bspline
    mk_bspline.argtypes = [POINTER(struct_rt_wdb), String, POINTER(POINTER(struct_face_g_snurb))]
    mk_bspline.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 488
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_nmg'):
    mk_nmg = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_nmg
    mk_nmg.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_model)]
    mk_nmg.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 496
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_bot_from_nmg'):
    mk_bot_from_nmg = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_bot_from_nmg
    mk_bot_from_nmg.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_shell)]
    mk_bot_from_nmg.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 502
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_sketch'):
    mk_sketch = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_sketch
    mk_sketch.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_rt_sketch_internal)]
    mk_sketch.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 510
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_annot'):
    mk_annot = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_annot
    mk_annot.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_rt_annot_internal)]
    mk_annot.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 518
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_script'):
    mk_script = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_script
    mk_script.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_rt_script_internal)]
    mk_script.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 526
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_extrusion'):
    mk_extrusion = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_extrusion
    mk_extrusion.argtypes = [POINTER(struct_rt_wdb), String, String, point_t, vect_t, vect_t, vect_t, c_int]
    mk_extrusion.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 542
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_cline'):
    mk_cline = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_cline
    mk_cline.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, fastf_t, fastf_t]
    mk_cline.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 555
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_particle'):
    mk_particle = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_particle
    mk_particle.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, c_double, c_double]
    mk_particle.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 566
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_pipe'):
    mk_pipe = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_pipe
    mk_pipe.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_bu_list)]
    mk_pipe.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 572
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_pipe_free'):
    mk_pipe_free = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_pipe_free
    mk_pipe_free.argtypes = [POINTER(struct_bu_list)]
    mk_pipe_free.restype = None

# /opt/brlcad/include/brlcad/wdb.h: 577
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_add_pipe_pt'):
    mk_add_pipe_pt = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_add_pipe_pt
    mk_add_pipe_pt.argtypes = [POINTER(struct_bu_list), point_t, c_double, c_double, c_double]
    mk_add_pipe_pt.restype = None

# /opt/brlcad/include/brlcad/wdb.h: 587
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_pipe_init'):
    mk_pipe_init = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_pipe_init
    mk_pipe_init.argtypes = [POINTER(struct_bu_list)]
    mk_pipe_init.restype = None

# /opt/brlcad/include/brlcad/wdb.h: 593
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_dsp'):
    mk_dsp = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_dsp
    mk_dsp.argtypes = [POINTER(struct_rt_wdb), String, String, c_size_t, c_size_t, matp_t]
    mk_dsp.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 599
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_ebm'):
    mk_ebm = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_ebm
    mk_ebm.argtypes = [POINTER(struct_rt_wdb), String, String, c_size_t, c_size_t, fastf_t, matp_t]
    mk_ebm.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 605
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_hrt'):
    mk_hrt = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_hrt
    mk_hrt.argtypes = [POINTER(struct_rt_wdb), String, point_t, vect_t, vect_t, vect_t, fastf_t]
    mk_hrt.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 611
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_vol'):
    mk_vol = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_vol
    mk_vol.argtypes = [POINTER(struct_rt_wdb), String, String, c_size_t, c_size_t, c_size_t, c_size_t, c_size_t, vect_t, matp_t]
    mk_vol.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 621
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_submodel'):
    mk_submodel = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_submodel
    mk_submodel.argtypes = [POINTER(struct_rt_wdb), String, String, String, c_int]
    mk_submodel.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 630
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_write_color_table'):
    mk_write_color_table = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_write_color_table
    mk_write_color_table.argtypes = [POINTER(struct_rt_wdb)]
    mk_write_color_table.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 644
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_addmember'):
    mk_addmember = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_addmember
    mk_addmember.argtypes = [String, POINTER(struct_bu_list), mat_t, c_int]
    mk_addmember.restype = POINTER(struct_wmember)

# /opt/brlcad/include/brlcad/wdb.h: 673
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_comb'):
    mk_comb = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_comb
    mk_comb.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_bu_list), c_int, String, String, POINTER(c_ubyte), c_int, c_int, c_int, c_int, c_int, c_int, c_int]
    mk_comb.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 693
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_comb1'):
    mk_comb1 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_comb1
    mk_comb1.argtypes = [POINTER(struct_rt_wdb), String, String, c_int]
    mk_comb1.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 703
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_region1'):
    mk_region1 = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_region1
    mk_region1.argtypes = [POINTER(struct_rt_wdb), String, String, String, String, POINTER(c_ubyte)]
    mk_region1.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 725
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_conversion'):
    mk_conversion = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_conversion
    mk_conversion.argtypes = [String]
    mk_conversion.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 732
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_set_conversion'):
    mk_set_conversion = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_set_conversion
    mk_set_conversion.argtypes = [c_double]
    mk_set_conversion.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 738
try:
    mk_conv2mm = (c_double).in_dll(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_conv2mm')
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 744
try:
    mk_version = (c_int).in_dll(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_version')
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 749
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'mk_freemembers'):
    mk_freemembers = _libs['/opt/brlcad/lib/libwdb.dylib'].mk_freemembers
    mk_freemembers.argtypes = [POINTER(struct_bu_list)]
    mk_freemembers.restype = None

# /opt/brlcad/include/brlcad/wdb.h: 785
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'make_hole'):
    make_hole = _libs['/opt/brlcad/lib/libwdb.dylib'].make_hole
    make_hole.argtypes = [POINTER(struct_rt_wdb), point_t, vect_t, fastf_t, c_int, POINTER(POINTER(struct_directory))]
    make_hole.restype = c_int

# /opt/brlcad/include/brlcad/wdb.h: 813
if hasattr(_libs['/opt/brlcad/lib/libwdb.dylib'], 'make_hole_in_prepped_regions'):
    make_hole_in_prepped_regions = _libs['/opt/brlcad/lib/libwdb.dylib'].make_hole_in_prepped_regions
    make_hole_in_prepped_regions.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_rt_i), point_t, vect_t, fastf_t, POINTER(struct_bu_ptbl)]
    make_hole_in_prepped_regions.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 79
try:
    _RT_WDB_NULL = NULL
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 80
try:
    _RT_WDB_TYPE_DB_DISK = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 81
try:
    _RT_WDB_TYPE_DB_DISK_APPEND_ONLY = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 82
try:
    _RT_WDB_TYPE_DB_INMEM = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 83
try:
    _RT_WDB_TYPE_DB_INMEM_APPEND_ONLY = 5
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 87
try:
    WMEMBER_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 649
def mk_lcomb(_fp, _name, _headp, _rf, _shadername, _shaderargs, _rgb, _inh):
    return (mk_comb (_fp, _name, pointer((_headp.contents.l)), _rf, _shadername, _shaderargs, _rgb, 0, 0, 0, 0, _inh, 0, 0))

# /opt/brlcad/include/brlcad/wdb.h: 655
def mk_lrcomb(fp, name, _headp, region_flag, shadername, shaderargs, rgb, id, air, material, los, inherit_flag):
    return (mk_comb (fp, name, pointer((_headp.contents.l)), region_flag, shadername, shaderargs, rgb, id, air, material, los, inherit_flag, 0, 0))

# /opt/brlcad/include/brlcad/wdb.h: 711
try:
    WMOP_INTERSECT = DB_OP_INTERSECT
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 712
try:
    WMOP_SUBTRACT = DB_OP_SUBTRACT
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 713
try:
    WMOP_UNION = DB_OP_UNION
except:
    pass

# /opt/brlcad/include/brlcad/wdb.h: 751
def mk_export_fwrite(wdbp, name, gp, id):
    return (wdb_export (wdbp, name, gp, id, mk_conv2mm))

wmember = struct_wmember # /opt/brlcad/include/brlcad/wdb.h: 77

# No inserted files

