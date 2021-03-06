'''Wrapper for raytrace.h

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

_libs["/opt/brlcad/lib/librt.dylib"] = load_library("/opt/brlcad/lib/librt.dylib")

# 1 libraries
# End libraries

# Begin modules

from libbu import *
from libbn import *

# 2 modules
# End modules

NULL = None # <built-in>

__int32_t = c_int # /usr/include/i386/_types.h: 44

__darwin_time_t = c_long # /usr/include/i386/_types.h: 120

__darwin_id_t = c_uint32 # /usr/include/sys/_types.h: 61

__darwin_suseconds_t = __int32_t # /usr/include/sys/_types.h: 74

id_t = __darwin_id_t # /usr/include/sys/_types/_id_t.h: 30

time_t = __darwin_time_t # /usr/include/sys/_types/_time_t.h: 30

# /usr/include/stdio.h: 259
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'printf'):
    _func = _libs['/opt/brlcad/lib/librt.dylib'].printf
    _restype = c_int
    _argtypes = [String]
    printf = _variadic_function(_func,_restype,_argtypes)

# /usr/include/stdio.h: 266
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'scanf'):
    _func = _libs['/opt/brlcad/lib/librt.dylib'].scanf
    _restype = c_int
    _argtypes = [String]
    scanf = _variadic_function(_func,_restype,_argtypes)

# /opt/brlcad/include/brlcad/bu/avs.h: 66
class struct_bu_attribute_value_pair(Structure):
    pass

struct_bu_attribute_value_pair.__slots__ = [
    'name',
    'value',
]
struct_bu_attribute_value_pair._fields_ = [
    ('name', String),
    ('value', String),
]

# /opt/brlcad/include/brlcad/bu/avs.h: 89
class struct_bu_attribute_value_set(Structure):
    pass

struct_bu_attribute_value_set.__slots__ = [
    'magic',
    'count',
    'max',
    'readonly_min',
    'readonly_max',
    'avp',
]
struct_bu_attribute_value_set._fields_ = [
    ('magic', c_uint32),
    ('count', c_size_t),
    ('max', c_size_t),
    ('readonly_min', POINTER(None)),
    ('readonly_max', POINTER(None)),
    ('avp', POINTER(struct_bu_attribute_value_pair)),
]

# /usr/include/sys/_types/_timeval.h: 30
class struct_timeval(Structure):
    pass

struct_timeval.__slots__ = [
    'tv_sec',
    'tv_usec',
]
struct_timeval._fields_ = [
    ('tv_sec', __darwin_time_t),
    ('tv_usec', __darwin_suseconds_t),
]

rlim_t = c_uint64 # /usr/include/sys/resource.h: 89

# /usr/include/sys/resource.h: 152
class struct_rusage(Structure):
    pass

struct_rusage.__slots__ = [
    'ru_utime',
    'ru_stime',
    'ru_maxrss',
    'ru_ixrss',
    'ru_idrss',
    'ru_isrss',
    'ru_minflt',
    'ru_majflt',
    'ru_nswap',
    'ru_inblock',
    'ru_oublock',
    'ru_msgsnd',
    'ru_msgrcv',
    'ru_nsignals',
    'ru_nvcsw',
    'ru_nivcsw',
]
struct_rusage._fields_ = [
    ('ru_utime', struct_timeval),
    ('ru_stime', struct_timeval),
    ('ru_maxrss', c_long),
    ('ru_ixrss', c_long),
    ('ru_idrss', c_long),
    ('ru_isrss', c_long),
    ('ru_minflt', c_long),
    ('ru_majflt', c_long),
    ('ru_nswap', c_long),
    ('ru_inblock', c_long),
    ('ru_oublock', c_long),
    ('ru_msgsnd', c_long),
    ('ru_msgrcv', c_long),
    ('ru_nsignals', c_long),
    ('ru_nvcsw', c_long),
    ('ru_nivcsw', c_long),
]

rusage_info_t = POINTER(None) # /usr/include/sys/resource.h: 192

# /usr/include/sys/resource.h: 194
class struct_rusage_info_v0(Structure):
    pass

struct_rusage_info_v0.__slots__ = [
    'ri_uuid',
    'ri_user_time',
    'ri_system_time',
    'ri_pkg_idle_wkups',
    'ri_interrupt_wkups',
    'ri_pageins',
    'ri_wired_size',
    'ri_resident_size',
    'ri_phys_footprint',
    'ri_proc_start_abstime',
    'ri_proc_exit_abstime',
]
struct_rusage_info_v0._fields_ = [
    ('ri_uuid', c_uint8 * 16),
    ('ri_user_time', c_uint64),
    ('ri_system_time', c_uint64),
    ('ri_pkg_idle_wkups', c_uint64),
    ('ri_interrupt_wkups', c_uint64),
    ('ri_pageins', c_uint64),
    ('ri_wired_size', c_uint64),
    ('ri_resident_size', c_uint64),
    ('ri_phys_footprint', c_uint64),
    ('ri_proc_start_abstime', c_uint64),
    ('ri_proc_exit_abstime', c_uint64),
]

# /usr/include/sys/resource.h: 208
class struct_rusage_info_v1(Structure):
    pass

struct_rusage_info_v1.__slots__ = [
    'ri_uuid',
    'ri_user_time',
    'ri_system_time',
    'ri_pkg_idle_wkups',
    'ri_interrupt_wkups',
    'ri_pageins',
    'ri_wired_size',
    'ri_resident_size',
    'ri_phys_footprint',
    'ri_proc_start_abstime',
    'ri_proc_exit_abstime',
    'ri_child_user_time',
    'ri_child_system_time',
    'ri_child_pkg_idle_wkups',
    'ri_child_interrupt_wkups',
    'ri_child_pageins',
    'ri_child_elapsed_abstime',
]
struct_rusage_info_v1._fields_ = [
    ('ri_uuid', c_uint8 * 16),
    ('ri_user_time', c_uint64),
    ('ri_system_time', c_uint64),
    ('ri_pkg_idle_wkups', c_uint64),
    ('ri_interrupt_wkups', c_uint64),
    ('ri_pageins', c_uint64),
    ('ri_wired_size', c_uint64),
    ('ri_resident_size', c_uint64),
    ('ri_phys_footprint', c_uint64),
    ('ri_proc_start_abstime', c_uint64),
    ('ri_proc_exit_abstime', c_uint64),
    ('ri_child_user_time', c_uint64),
    ('ri_child_system_time', c_uint64),
    ('ri_child_pkg_idle_wkups', c_uint64),
    ('ri_child_interrupt_wkups', c_uint64),
    ('ri_child_pageins', c_uint64),
    ('ri_child_elapsed_abstime', c_uint64),
]

# /usr/include/sys/resource.h: 228
class struct_rusage_info_v2(Structure):
    pass

struct_rusage_info_v2.__slots__ = [
    'ri_uuid',
    'ri_user_time',
    'ri_system_time',
    'ri_pkg_idle_wkups',
    'ri_interrupt_wkups',
    'ri_pageins',
    'ri_wired_size',
    'ri_resident_size',
    'ri_phys_footprint',
    'ri_proc_start_abstime',
    'ri_proc_exit_abstime',
    'ri_child_user_time',
    'ri_child_system_time',
    'ri_child_pkg_idle_wkups',
    'ri_child_interrupt_wkups',
    'ri_child_pageins',
    'ri_child_elapsed_abstime',
    'ri_diskio_bytesread',
    'ri_diskio_byteswritten',
]
struct_rusage_info_v2._fields_ = [
    ('ri_uuid', c_uint8 * 16),
    ('ri_user_time', c_uint64),
    ('ri_system_time', c_uint64),
    ('ri_pkg_idle_wkups', c_uint64),
    ('ri_interrupt_wkups', c_uint64),
    ('ri_pageins', c_uint64),
    ('ri_wired_size', c_uint64),
    ('ri_resident_size', c_uint64),
    ('ri_phys_footprint', c_uint64),
    ('ri_proc_start_abstime', c_uint64),
    ('ri_proc_exit_abstime', c_uint64),
    ('ri_child_user_time', c_uint64),
    ('ri_child_system_time', c_uint64),
    ('ri_child_pkg_idle_wkups', c_uint64),
    ('ri_child_interrupt_wkups', c_uint64),
    ('ri_child_pageins', c_uint64),
    ('ri_child_elapsed_abstime', c_uint64),
    ('ri_diskio_bytesread', c_uint64),
    ('ri_diskio_byteswritten', c_uint64),
]

# /usr/include/sys/resource.h: 250
class struct_rusage_info_v3(Structure):
    pass

struct_rusage_info_v3.__slots__ = [
    'ri_uuid',
    'ri_user_time',
    'ri_system_time',
    'ri_pkg_idle_wkups',
    'ri_interrupt_wkups',
    'ri_pageins',
    'ri_wired_size',
    'ri_resident_size',
    'ri_phys_footprint',
    'ri_proc_start_abstime',
    'ri_proc_exit_abstime',
    'ri_child_user_time',
    'ri_child_system_time',
    'ri_child_pkg_idle_wkups',
    'ri_child_interrupt_wkups',
    'ri_child_pageins',
    'ri_child_elapsed_abstime',
    'ri_diskio_bytesread',
    'ri_diskio_byteswritten',
    'ri_cpu_time_qos_default',
    'ri_cpu_time_qos_maintenance',
    'ri_cpu_time_qos_background',
    'ri_cpu_time_qos_utility',
    'ri_cpu_time_qos_legacy',
    'ri_cpu_time_qos_user_initiated',
    'ri_cpu_time_qos_user_interactive',
    'ri_billed_system_time',
    'ri_serviced_system_time',
]
struct_rusage_info_v3._fields_ = [
    ('ri_uuid', c_uint8 * 16),
    ('ri_user_time', c_uint64),
    ('ri_system_time', c_uint64),
    ('ri_pkg_idle_wkups', c_uint64),
    ('ri_interrupt_wkups', c_uint64),
    ('ri_pageins', c_uint64),
    ('ri_wired_size', c_uint64),
    ('ri_resident_size', c_uint64),
    ('ri_phys_footprint', c_uint64),
    ('ri_proc_start_abstime', c_uint64),
    ('ri_proc_exit_abstime', c_uint64),
    ('ri_child_user_time', c_uint64),
    ('ri_child_system_time', c_uint64),
    ('ri_child_pkg_idle_wkups', c_uint64),
    ('ri_child_interrupt_wkups', c_uint64),
    ('ri_child_pageins', c_uint64),
    ('ri_child_elapsed_abstime', c_uint64),
    ('ri_diskio_bytesread', c_uint64),
    ('ri_diskio_byteswritten', c_uint64),
    ('ri_cpu_time_qos_default', c_uint64),
    ('ri_cpu_time_qos_maintenance', c_uint64),
    ('ri_cpu_time_qos_background', c_uint64),
    ('ri_cpu_time_qos_utility', c_uint64),
    ('ri_cpu_time_qos_legacy', c_uint64),
    ('ri_cpu_time_qos_user_initiated', c_uint64),
    ('ri_cpu_time_qos_user_interactive', c_uint64),
    ('ri_billed_system_time', c_uint64),
    ('ri_serviced_system_time', c_uint64),
]

rusage_info_current = struct_rusage_info_v3 # /usr/include/sys/resource.h: 281

# /usr/include/sys/resource.h: 325
class struct_rlimit(Structure):
    pass

struct_rlimit.__slots__ = [
    'rlim_cur',
    'rlim_max',
]
struct_rlimit._fields_ = [
    ('rlim_cur', rlim_t),
    ('rlim_max', rlim_t),
]

# /usr/include/sys/resource.h: 353
class struct_proc_rlimit_control_wakeupmon(Structure):
    pass

struct_proc_rlimit_control_wakeupmon.__slots__ = [
    'wm_flags',
    'wm_rate',
]
struct_proc_rlimit_control_wakeupmon._fields_ = [
    ('wm_flags', c_uint32),
    ('wm_rate', c_int32),
]

# /usr/include/sys/resource.h: 385
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'getpriority'):
    getpriority = _libs['/opt/brlcad/lib/librt.dylib'].getpriority
    getpriority.argtypes = [c_int, id_t]
    getpriority.restype = c_int

# /usr/include/sys/resource.h: 387
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'getiopolicy_np'):
    getiopolicy_np = _libs['/opt/brlcad/lib/librt.dylib'].getiopolicy_np
    getiopolicy_np.argtypes = [c_int, c_int]
    getiopolicy_np.restype = c_int

# /usr/include/sys/resource.h: 389
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'getrlimit'):
    getrlimit = _libs['/opt/brlcad/lib/librt.dylib'].getrlimit
    getrlimit.argtypes = [c_int, POINTER(struct_rlimit)]
    getrlimit.restype = c_int

# /usr/include/sys/resource.h: 390
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'getrusage'):
    getrusage = _libs['/opt/brlcad/lib/librt.dylib'].getrusage
    getrusage.argtypes = [c_int, POINTER(struct_rusage)]
    getrusage.restype = c_int

# /usr/include/sys/resource.h: 391
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'setpriority'):
    setpriority = _libs['/opt/brlcad/lib/librt.dylib'].setpriority
    setpriority.argtypes = [c_int, id_t, c_int]
    setpriority.restype = c_int

# /usr/include/sys/resource.h: 393
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'setiopolicy_np'):
    setiopolicy_np = _libs['/opt/brlcad/lib/librt.dylib'].setiopolicy_np
    setiopolicy_np.argtypes = [c_int, c_int, c_int]
    setiopolicy_np.restype = c_int

# /usr/include/sys/resource.h: 395
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'setrlimit'):
    setrlimit = _libs['/opt/brlcad/lib/librt.dylib'].setrlimit
    setrlimit.argtypes = [c_int, POINTER(struct_rlimit)]
    setrlimit.restype = c_int

# /opt/brlcad/include/brlcad/bu/hash.h: 173
class struct_bu_hash_entry(Structure):
    pass

# /opt/brlcad/include/brlcad/bu/hash.h: 190
class struct_bu_hash_tbl(Structure):
    pass

struct_bu_hash_entry.__slots__ = [
    'magic',
    'key',
    'value',
    'key_len',
    'next',
]
struct_bu_hash_entry._fields_ = [
    ('magic', c_uint32),
    ('key', POINTER(c_uint8)),
    ('value', POINTER(None)),
    ('key_len', c_int),
    ('next', POINTER(struct_bu_hash_entry)),
]

struct_bu_hash_tbl.__slots__ = [
    'magic',
    'mask',
    'num_lists',
    'num_entries',
    'lists',
]
struct_bu_hash_tbl._fields_ = [
    ('magic', c_uint32),
    ('mask', c_ulong),
    ('num_lists', c_ulong),
    ('num_entries', c_ulong),
    ('lists', POINTER(POINTER(struct_bu_hash_entry))),
]

# /opt/brlcad/include/brlcad/bu/hist.h: 49
class struct_bu_hist(Structure):
    pass

struct_bu_hist.__slots__ = [
    'magic',
    'hg_min',
    'hg_max',
    'hg_clumpsize',
    'hg_nsamples',
    'hg_nbins',
    'hg_bins',
]
struct_bu_hist._fields_ = [
    ('magic', c_uint32),
    ('hg_min', fastf_t),
    ('hg_max', fastf_t),
    ('hg_clumpsize', fastf_t),
    ('hg_nsamples', c_size_t),
    ('hg_nbins', c_size_t),
    ('hg_bins', POINTER(c_long)),
]

# /opt/brlcad/include/brlcad/bu/mapped_file.h: 79
class struct_bu_mapped_file(Structure):
    pass

struct_bu_mapped_file.__slots__ = [
    'name',
    'buf',
    'buflen',
    'is_mapped',
    'appl',
    'apbuf',
    'apbuflen',
    'modtime',
    'uses',
    'dont_restat',
]
struct_bu_mapped_file._fields_ = [
    ('name', String),
    ('buf', POINTER(None)),
    ('buflen', c_size_t),
    ('is_mapped', c_int),
    ('appl', String),
    ('apbuf', POINTER(None)),
    ('apbuflen', c_size_t),
    ('modtime', time_t),
    ('uses', c_int),
    ('dont_restat', c_int),
]

# /opt/brlcad/include/brlcad/bu/parse.h: 139
class struct_bu_structparse(Structure):
    pass

struct_bu_structparse.__slots__ = [
    'sp_fmt',
    'sp_count',
    'sp_name',
    'sp_offset',
    'sp_hook',
    'sp_desc',
    'sp_default',
]
struct_bu_structparse._fields_ = [
    ('sp_fmt', c_char * 4),
    ('sp_count', c_size_t),
    ('sp_name', String),
    ('sp_offset', c_size_t),
    ('sp_hook', CFUNCTYPE(UNCHECKED(None), POINTER(struct_bu_structparse), String, POINTER(None), String, POINTER(None))),
    ('sp_desc', String),
    ('sp_default', POINTER(None)),
]

# /opt/brlcad/include/brlcad/bu/parse.h: 210
class struct_bu_external(Structure):
    pass

struct_bu_external.__slots__ = [
    'ext_magic',
    'ext_nbytes',
    'ext_buf',
]
struct_bu_external._fields_ = [
    ('ext_magic', c_uint32),
    ('ext_nbytes', c_size_t),
    ('ext_buf', POINTER(c_uint8)),
]

# /opt/brlcad/include/brlcad/bu/log.h: 151
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bu_log'):
    _func = _libs['/opt/brlcad/lib/librt.dylib'].bu_log
    _restype = None
    _argtypes = [String]
    bu_log = _variadic_function(_func,_restype,_argtypes)

# /opt/brlcad/include/brlcad/bu/ptbl.h: 54
class struct_bu_ptbl(Structure):
    pass

struct_bu_ptbl.__slots__ = [
    'l',
    'end',
    'blen',
    'buffer',
]
struct_bu_ptbl._fields_ = [
    ('l', struct_bu_list),
    ('end', off_t),
    ('blen', c_size_t),
    ('buffer', POINTER(POINTER(c_long))),
]

# /opt/brlcad/include/brlcad/bn/version.h: 37
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_version'):
    bn_version = _libs['/opt/brlcad/lib/librt.dylib'].bn_version
    bn_version.argtypes = []
    if sizeof(c_int) == sizeof(c_void_p):
        bn_version.restype = ReturnString
    else:
        bn_version.restype = String
        bn_version.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bn/tol.h: 72
class struct_bn_tol(Structure):
    pass

struct_bn_tol.__slots__ = [
    'magic',
    'dist',
    'dist_sq',
    'perp',
    'para',
]
struct_bn_tol._fields_ = [
    ('magic', c_uint32),
    ('dist', c_double),
    ('dist_sq', c_double),
    ('perp', c_double),
    ('para', c_double),
]

mat3_t = fastf_t * 9 # /opt/brlcad/include/brlcad/bn/anim.h: 63

# /opt/brlcad/include/brlcad/bn/anim.h: 149
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_v_permute'):
    anim_v_permute = _libs['/opt/brlcad/lib/librt.dylib'].anim_v_permute
    anim_v_permute.argtypes = [mat_t]
    anim_v_permute.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 159
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_v_unpermute'):
    anim_v_unpermute = _libs['/opt/brlcad/lib/librt.dylib'].anim_v_unpermute
    anim_v_unpermute.argtypes = [mat_t]
    anim_v_unpermute.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 164
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_tran'):
    anim_tran = _libs['/opt/brlcad/lib/librt.dylib'].anim_tran
    anim_tran.argtypes = [mat_t]
    anim_tran.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 174
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_mat2zyx'):
    anim_mat2zyx = _libs['/opt/brlcad/lib/librt.dylib'].anim_mat2zyx
    anim_mat2zyx.argtypes = [mat_t, vect_t]
    anim_mat2zyx.restype = c_int

# /opt/brlcad/include/brlcad/bn/anim.h: 186
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_mat2ypr'):
    anim_mat2ypr = _libs['/opt/brlcad/lib/librt.dylib'].anim_mat2ypr
    anim_mat2ypr.argtypes = [mat_t, vect_t]
    anim_mat2ypr.restype = c_int

# /opt/brlcad/include/brlcad/bn/anim.h: 197
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_mat2quat'):
    anim_mat2quat = _libs['/opt/brlcad/lib/librt.dylib'].anim_mat2quat
    anim_mat2quat.argtypes = [quat_t, mat_t]
    anim_mat2quat.restype = c_int

# /opt/brlcad/include/brlcad/bn/anim.h: 205
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_ypr2mat'):
    anim_ypr2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_ypr2mat
    anim_ypr2mat.argtypes = [mat_t, vect_t]
    anim_ypr2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 220
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_ypr2vmat'):
    anim_ypr2vmat = _libs['/opt/brlcad/lib/librt.dylib'].anim_ypr2vmat
    anim_ypr2vmat.argtypes = [mat_t, vect_t]
    anim_ypr2vmat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 228
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_y_p_r2mat'):
    anim_y_p_r2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_y_p_r2mat
    anim_y_p_r2mat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_y_p_r2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 237
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_dy_p_r2mat'):
    anim_dy_p_r2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_dy_p_r2mat
    anim_dy_p_r2mat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_dy_p_r2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 247
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_dy_p_r2vmat'):
    anim_dy_p_r2vmat = _libs['/opt/brlcad/lib/librt.dylib'].anim_dy_p_r2vmat
    anim_dy_p_r2vmat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_dy_p_r2vmat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 257
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_x_y_z2mat'):
    anim_x_y_z2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_x_y_z2mat
    anim_x_y_z2mat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_x_y_z2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 267
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_dx_y_z2mat'):
    anim_dx_y_z2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_dx_y_z2mat
    anim_dx_y_z2mat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_dx_y_z2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 277
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_zyx2mat'):
    anim_zyx2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_zyx2mat
    anim_zyx2mat.argtypes = [mat_t, vect_t]
    anim_zyx2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 285
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_z_y_x2mat'):
    anim_z_y_x2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_z_y_x2mat
    anim_z_y_x2mat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_z_y_x2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 296
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_dz_y_x2mat'):
    anim_dz_y_x2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_dz_y_x2mat
    anim_dz_y_x2mat.argtypes = [mat_t, c_double, c_double, c_double]
    anim_dz_y_x2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 307
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_quat2mat'):
    anim_quat2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_quat2mat
    anim_quat2mat.argtypes = [mat_t, quat_t]
    anim_quat2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 318
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_dir2mat'):
    anim_dir2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_dir2mat
    anim_dir2mat.argtypes = [mat_t, vect_t, vect_t]
    anim_dir2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 330
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_dirn2mat'):
    anim_dirn2mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_dirn2mat
    anim_dirn2mat.argtypes = [mat_t, vect_t, vect_t]
    anim_dirn2mat.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 342
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_steer_mat'):
    anim_steer_mat = _libs['/opt/brlcad/lib/librt.dylib'].anim_steer_mat
    anim_steer_mat.argtypes = [mat_t, vect_t, c_int]
    anim_steer_mat.restype = c_int

# /opt/brlcad/include/brlcad/bn/anim.h: 352
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_add_trans'):
    anim_add_trans = _libs['/opt/brlcad/lib/librt.dylib'].anim_add_trans
    anim_add_trans.argtypes = [mat_t, vect_t, vect_t]
    anim_add_trans.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 359
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_rotatez'):
    anim_rotatez = _libs['/opt/brlcad/lib/librt.dylib'].anim_rotatez
    anim_rotatez.argtypes = [fastf_t, vect_t]
    anim_rotatez.restype = None

# /opt/brlcad/include/brlcad/bn/anim.h: 383
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'anim_view_rev'):
    anim_view_rev = _libs['/opt/brlcad/lib/librt.dylib'].anim_view_rev
    anim_view_rev.argtypes = [mat_t]
    anim_view_rev.restype = None

# /opt/brlcad/include/brlcad/bn/complex.h: 41
class struct_bn_complex(Structure):
    pass

struct_bn_complex.__slots__ = [
    're',
    'im',
]
struct_bn_complex._fields_ = [
    ('re', c_double),
    ('im', c_double),
]

bn_complex_t = struct_bn_complex # /opt/brlcad/include/brlcad/bn/complex.h: 41

# /opt/brlcad/include/brlcad/bn/poly.h: 51
class struct_bn_poly(Structure):
    pass

struct_bn_poly.__slots__ = [
    'magic',
    'dgr',
    'cf',
]
struct_bn_poly._fields_ = [
    ('magic', c_uint32),
    ('dgr', c_size_t),
    ('cf', fastf_t * (6 + 1)),
]

bn_poly_t = struct_bn_poly # /opt/brlcad/include/brlcad/bn/poly.h: 51

# /opt/brlcad/include/brlcad/bn/tabdata.h: 90
class struct_bn_table(Structure):
    pass

struct_bn_table.__slots__ = [
    'magic',
    'nx',
    'x',
]
struct_bn_table._fields_ = [
    ('magic', c_uint32),
    ('nx', c_size_t),
    ('x', fastf_t * 1),
]

# /opt/brlcad/include/brlcad/bn/tabdata.h: 117
class struct_bn_tabdata(Structure):
    pass

struct_bn_tabdata.__slots__ = [
    'magic',
    'ny',
    'table',
    'y',
]
struct_bn_tabdata._fields_ = [
    ('magic', c_uint32),
    ('ny', c_size_t),
    ('table', POINTER(struct_bn_table)),
    ('y', fastf_t * 1),
]

# /opt/brlcad/include/brlcad/bn/vlist.h: 67
class struct_bn_vlist(Structure):
    pass

struct_bn_vlist.__slots__ = [
    'l',
    'nused',
    'cmd',
    'pt',
]
struct_bn_vlist._fields_ = [
    ('l', struct_bu_list),
    ('nused', c_size_t),
    ('cmd', c_int * 35),
    ('pt', point_t * 35),
]

# /opt/brlcad/include/brlcad/bn/vlist.h: 184
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_cmd_cnt'):
    bn_vlist_cmd_cnt = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_cmd_cnt
    bn_vlist_cmd_cnt.argtypes = [POINTER(struct_bn_vlist)]
    bn_vlist_cmd_cnt.restype = c_int

# /opt/brlcad/include/brlcad/bn/vlist.h: 185
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_bbox'):
    bn_vlist_bbox = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_bbox
    bn_vlist_bbox.argtypes = [POINTER(struct_bn_vlist), POINTER(point_t), POINTER(point_t)]
    bn_vlist_bbox.restype = c_int

# /opt/brlcad/include/brlcad/bn/vlist.h: 193
class struct_bn_vlblock(Structure):
    pass

struct_bn_vlblock.__slots__ = [
    'magic',
    'nused',
    'max',
    'rgb',
    'head',
    'free_vlist_hd',
]
struct_bn_vlblock._fields_ = [
    ('magic', c_uint32),
    ('nused', c_size_t),
    ('max', c_size_t),
    ('rgb', POINTER(c_long)),
    ('head', POINTER(struct_bu_list)),
    ('free_vlist_hd', POINTER(struct_bu_list)),
]

# /opt/brlcad/include/brlcad/bn/vlist.h: 217
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_3string'):
    bn_vlist_3string = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_3string
    bn_vlist_3string.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), String, point_t, mat_t, c_double]
    bn_vlist_3string.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 239
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_2string'):
    bn_vlist_2string = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_2string
    bn_vlist_2string.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), String, c_double, c_double, c_double, c_double]
    bn_vlist_2string.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 251
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_get_cmd_description'):
    bn_vlist_get_cmd_description = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_get_cmd_description
    bn_vlist_get_cmd_description.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        bn_vlist_get_cmd_description.restype = ReturnString
    else:
        bn_vlist_get_cmd_description.restype = String
        bn_vlist_get_cmd_description.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bn/vlist.h: 260
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_ck_vlist'):
    bn_ck_vlist = _libs['/opt/brlcad/lib/librt.dylib'].bn_ck_vlist
    bn_ck_vlist.argtypes = [POINTER(struct_bu_list)]
    bn_ck_vlist.restype = c_int

# /opt/brlcad/include/brlcad/bn/vlist.h: 267
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_copy'):
    bn_vlist_copy = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_copy
    bn_vlist_copy.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), POINTER(struct_bu_list)]
    bn_vlist_copy.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 279
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_export'):
    bn_vlist_export = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_export
    bn_vlist_export.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_list), String]
    bn_vlist_export.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 288
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_import'):
    bn_vlist_import = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_import
    bn_vlist_import.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), POINTER(struct_bu_vls), POINTER(c_ubyte)]
    bn_vlist_import.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 293
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_cleanup'):
    bn_vlist_cleanup = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_cleanup
    bn_vlist_cleanup.argtypes = [POINTER(struct_bu_list)]
    bn_vlist_cleanup.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 295
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlblock_init'):
    bn_vlblock_init = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlblock_init
    bn_vlblock_init.argtypes = [POINTER(struct_bu_list), c_int]
    bn_vlblock_init.restype = POINTER(struct_bn_vlblock)

# /opt/brlcad/include/brlcad/bn/vlist.h: 298
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlblock_free'):
    bn_vlblock_free = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlblock_free
    bn_vlblock_free.argtypes = [POINTER(struct_bn_vlblock)]
    bn_vlblock_free.restype = None

# /opt/brlcad/include/brlcad/bn/vlist.h: 300
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlblock_find'):
    bn_vlblock_find = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlblock_find
    bn_vlblock_find.argtypes = [POINTER(struct_bn_vlblock), c_int, c_int, c_int]
    bn_vlblock_find.restype = POINTER(struct_bu_list)

# /opt/brlcad/include/brlcad/bn/vlist.h: 306
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bn_vlist_rpp'):
    bn_vlist_rpp = _libs['/opt/brlcad/lib/librt.dylib'].bn_vlist_rpp
    bn_vlist_rpp.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), point_t, point_t]
    bn_vlist_rpp.restype = None

# /opt/brlcad/include/brlcad/bu/observer.h: 46
class struct_bu_observer(Structure):
    pass

struct_bu_observer.__slots__ = [
    'l',
    'observer',
    'cmd',
]
struct_bu_observer._fields_ = [
    ('l', struct_bu_list),
    ('observer', struct_bu_vls),
    ('cmd', struct_bu_vls),
]

enum_anon_74 = c_int # /opt/brlcad/include/brlcad/./rt/op.h: 60

DB_OP_NULL = 0 # /opt/brlcad/include/brlcad/./rt/op.h: 60

DB_OP_UNION = 'u' # /opt/brlcad/include/brlcad/./rt/op.h: 60

DB_OP_SUBTRACT = '-' # /opt/brlcad/include/brlcad/./rt/op.h: 60

DB_OP_INTERSECT = '+' # /opt/brlcad/include/brlcad/./rt/op.h: 60

db_op_t = enum_anon_74 # /opt/brlcad/include/brlcad/./rt/op.h: 60

# /opt/brlcad/include/brlcad/./rt/op.h: 72
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_str2op'):
    db_str2op = _libs['/opt/brlcad/lib/librt.dylib'].db_str2op
    db_str2op.argtypes = [String]
    db_str2op.restype = db_op_t

# /opt/brlcad/include/brlcad/./rt/db5.h: 56
class struct_db5_ondisk_header(Structure):
    pass

struct_db5_ondisk_header.__slots__ = [
    'db5h_magic1',
    'db5h_hflags',
    'db5h_aflags',
    'db5h_bflags',
    'db5h_major_type',
    'db5h_minor_type',
]
struct_db5_ondisk_header._fields_ = [
    ('db5h_magic1', c_ubyte),
    ('db5h_hflags', c_ubyte),
    ('db5h_aflags', c_ubyte),
    ('db5h_bflags', c_ubyte),
    ('db5h_major_type', c_ubyte),
    ('db5h_minor_type', c_ubyte),
]

# /opt/brlcad/include/brlcad/./rt/db5.h: 193
try:
    binu_types = (POINTER(POINTER(c_char))).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'binu_types')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 200
class struct_db5_raw_internal(Structure):
    pass

struct_db5_raw_internal.__slots__ = [
    'magic',
    'h_object_width',
    'h_name_hidden',
    'h_name_present',
    'h_name_width',
    'h_dli',
    'a_width',
    'a_present',
    'a_zzz',
    'b_width',
    'b_present',
    'b_zzz',
    'major_type',
    'minor_type',
    'object_length',
    'name',
    'body',
    'attributes',
    'buf',
]
struct_db5_raw_internal._fields_ = [
    ('magic', c_uint32),
    ('h_object_width', c_ubyte),
    ('h_name_hidden', c_ubyte),
    ('h_name_present', c_ubyte),
    ('h_name_width', c_ubyte),
    ('h_dli', c_ubyte),
    ('a_width', c_ubyte),
    ('a_present', c_ubyte),
    ('a_zzz', c_ubyte),
    ('b_width', c_ubyte),
    ('b_present', c_ubyte),
    ('b_zzz', c_ubyte),
    ('major_type', c_ubyte),
    ('minor_type', c_ubyte),
    ('object_length', c_size_t),
    ('name', struct_bu_external),
    ('body', struct_bu_external),
    ('attributes', struct_bu_external),
    ('buf', POINTER(c_ubyte)),
]

# /opt/brlcad/include/brlcad/./rt/db5.h: 229
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_encode_length'):
    db5_encode_length = _libs['/opt/brlcad/lib/librt.dylib'].db5_encode_length
    db5_encode_length.argtypes = [POINTER(c_ubyte), c_size_t, c_int]
    db5_encode_length.restype = POINTER(c_ubyte)

# /opt/brlcad/include/brlcad/./rt/db5.h: 232
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_get_raw_internal_ptr'):
    db5_get_raw_internal_ptr = _libs['/opt/brlcad/lib/librt.dylib'].db5_get_raw_internal_ptr
    db5_get_raw_internal_ptr.argtypes = [POINTER(struct_db5_raw_internal), POINTER(c_ubyte)]
    db5_get_raw_internal_ptr.restype = POINTER(c_ubyte)

# /opt/brlcad/include/brlcad/nmg.h: 212
try:
    nmg_debug = (c_uint32).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_debug')
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 221
class struct_knot_vector(Structure):
    pass

struct_knot_vector.__slots__ = [
    'magic',
    'k_size',
    'knots',
]
struct_knot_vector._fields_ = [
    ('magic', c_uint32),
    ('k_size', c_int),
    ('knots', POINTER(fastf_t)),
]

# /opt/brlcad/include/brlcad/nmg.h: 245
class struct_model(Structure):
    pass

struct_model.__slots__ = [
    'magic',
    'r_hd',
    'manifolds',
    'index',
    'maxindex',
]
struct_model._fields_ = [
    ('magic', c_uint32),
    ('r_hd', struct_bu_list),
    ('manifolds', String),
    ('index', c_long),
    ('maxindex', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 261
class struct_nmgregion_a(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 253
class struct_nmgregion(Structure):
    pass

struct_nmgregion.__slots__ = [
    'l',
    'm_p',
    'ra_p',
    's_hd',
    'index',
]
struct_nmgregion._fields_ = [
    ('l', struct_bu_list),
    ('m_p', POINTER(struct_model)),
    ('ra_p', POINTER(struct_nmgregion_a)),
    ('s_hd', struct_bu_list),
    ('index', c_long),
]

struct_nmgregion_a.__slots__ = [
    'magic',
    'min_pt',
    'max_pt',
    'index',
]
struct_nmgregion_a._fields_ = [
    ('magic', c_uint32),
    ('min_pt', point_t),
    ('max_pt', point_t),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 297
class struct_shell_a(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 545
class struct_vertexuse(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 285
class struct_shell(Structure):
    pass

struct_shell.__slots__ = [
    'l',
    'r_p',
    'sa_p',
    'fu_hd',
    'lu_hd',
    'eu_hd',
    'vu_p',
    'index',
]
struct_shell._fields_ = [
    ('l', struct_bu_list),
    ('r_p', POINTER(struct_nmgregion)),
    ('sa_p', POINTER(struct_shell_a)),
    ('fu_hd', struct_bu_list),
    ('lu_hd', struct_bu_list),
    ('eu_hd', struct_bu_list),
    ('vu_p', POINTER(struct_vertexuse)),
    ('index', c_long),
]

struct_shell_a.__slots__ = [
    'magic',
    'min_pt',
    'max_pt',
    'index',
]
struct_shell_a._fields_ = [
    ('magic', c_uint32),
    ('min_pt', point_t),
    ('max_pt', point_t),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 352
class struct_faceuse(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 324
class struct_face_g_plane(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 331
class struct_face_g_snurb(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 311
class union_anon_76(Union):
    pass

union_anon_76.__slots__ = [
    'magic_p',
    'plane_p',
    'snurb_p',
]
union_anon_76._fields_ = [
    ('magic_p', POINTER(c_uint32)),
    ('plane_p', POINTER(struct_face_g_plane)),
    ('snurb_p', POINTER(struct_face_g_snurb)),
]

# /opt/brlcad/include/brlcad/nmg.h: 308
class struct_face(Structure):
    pass

struct_face.__slots__ = [
    'l',
    'fu_p',
    'g',
    'flip',
    'min_pt',
    'max_pt',
    'index',
]
struct_face._fields_ = [
    ('l', struct_bu_list),
    ('fu_p', POINTER(struct_faceuse)),
    ('g', union_anon_76),
    ('flip', c_int),
    ('min_pt', point_t),
    ('max_pt', point_t),
    ('index', c_long),
]

struct_face_g_plane.__slots__ = [
    'magic',
    'f_hd',
    'N',
    'index',
]
struct_face_g_plane._fields_ = [
    ('magic', c_uint32),
    ('f_hd', struct_bu_list),
    ('N', plane_t),
    ('index', c_long),
]

struct_face_g_snurb.__slots__ = [
    'l',
    'f_hd',
    'order',
    'u',
    'v',
    's_size',
    'pt_type',
    'ctl_points',
    'dir',
    'min_pt',
    'max_pt',
    'index',
]
struct_face_g_snurb._fields_ = [
    ('l', struct_bu_list),
    ('f_hd', struct_bu_list),
    ('order', c_int * 2),
    ('u', struct_knot_vector),
    ('v', struct_knot_vector),
    ('s_size', c_int * 2),
    ('pt_type', c_int),
    ('ctl_points', POINTER(fastf_t)),
    ('dir', c_int),
    ('min_pt', point_t),
    ('max_pt', point_t),
    ('index', c_long),
]

struct_faceuse.__slots__ = [
    'l',
    's_p',
    'fumate_p',
    'orientation',
    'outside',
    'f_p',
    'lu_hd',
    'index',
]
struct_faceuse._fields_ = [
    ('l', struct_bu_list),
    ('s_p', POINTER(struct_shell)),
    ('fumate_p', POINTER(struct_faceuse)),
    ('orientation', c_int),
    ('outside', c_int),
    ('f_p', POINTER(struct_face)),
    ('lu_hd', struct_bu_list),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 432
class struct_loopuse(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 425
class struct_loop_g(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 418
class struct_loop(Structure):
    pass

struct_loop.__slots__ = [
    'magic',
    'lu_p',
    'lg_p',
    'index',
]
struct_loop._fields_ = [
    ('magic', c_uint32),
    ('lu_p', POINTER(struct_loopuse)),
    ('lg_p', POINTER(struct_loop_g)),
    ('index', c_long),
]

struct_loop_g.__slots__ = [
    'magic',
    'min_pt',
    'max_pt',
    'index',
]
struct_loop_g._fields_ = [
    ('magic', c_uint32),
    ('min_pt', point_t),
    ('max_pt', point_t),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 434
class union_anon_77(Union):
    pass

union_anon_77.__slots__ = [
    'fu_p',
    's_p',
    'magic_p',
]
union_anon_77._fields_ = [
    ('fu_p', POINTER(struct_faceuse)),
    ('s_p', POINTER(struct_shell)),
    ('magic_p', POINTER(c_uint32)),
]

struct_loopuse.__slots__ = [
    'l',
    'up',
    'lumate_p',
    'orientation',
    'l_p',
    'down_hd',
    'index',
]
struct_loopuse._fields_ = [
    ('l', struct_bu_list),
    ('up', union_anon_77),
    ('lumate_p', POINTER(struct_loopuse)),
    ('orientation', c_int),
    ('l_p', POINTER(struct_loop)),
    ('down_hd', struct_bu_list),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 504
class struct_edgeuse(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 464
class struct_edge(Structure):
    pass

struct_edge.__slots__ = [
    'magic',
    'eu_p',
    'is_real',
    'index',
]
struct_edge._fields_ = [
    ('magic', c_uint32),
    ('eu_p', POINTER(struct_edgeuse)),
    ('is_real', c_long),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 476
class struct_edge_g_lseg(Structure):
    pass

struct_edge_g_lseg.__slots__ = [
    'l',
    'eu_hd2',
    'e_pt',
    'e_dir',
    'index',
]
struct_edge_g_lseg._fields_ = [
    ('l', struct_bu_list),
    ('eu_hd2', struct_bu_list),
    ('e_pt', point_t),
    ('e_dir', vect_t),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 492
class struct_edge_g_cnurb(Structure):
    pass

struct_edge_g_cnurb.__slots__ = [
    'l',
    'eu_hd2',
    'order',
    'k',
    'c_size',
    'pt_type',
    'ctl_points',
    'index',
]
struct_edge_g_cnurb._fields_ = [
    ('l', struct_bu_list),
    ('eu_hd2', struct_bu_list),
    ('order', c_int),
    ('k', struct_knot_vector),
    ('c_size', c_int),
    ('pt_type', c_int),
    ('ctl_points', POINTER(fastf_t)),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 507
class union_anon_78(Union):
    pass

union_anon_78.__slots__ = [
    'lu_p',
    's_p',
    'magic_p',
]
union_anon_78._fields_ = [
    ('lu_p', POINTER(struct_loopuse)),
    ('s_p', POINTER(struct_shell)),
    ('magic_p', POINTER(c_uint32)),
]

# /opt/brlcad/include/brlcad/nmg.h: 517
class union_anon_79(Union):
    pass

union_anon_79.__slots__ = [
    'magic_p',
    'lseg_p',
    'cnurb_p',
]
union_anon_79._fields_ = [
    ('magic_p', POINTER(c_uint32)),
    ('lseg_p', POINTER(struct_edge_g_lseg)),
    ('cnurb_p', POINTER(struct_edge_g_cnurb)),
]

struct_edgeuse.__slots__ = [
    'l',
    'l2',
    'up',
    'eumate_p',
    'radial_p',
    'e_p',
    'orientation',
    'vu_p',
    'g',
    'index',
]
struct_edgeuse._fields_ = [
    ('l', struct_bu_list),
    ('l2', struct_bu_list),
    ('up', union_anon_78),
    ('eumate_p', POINTER(struct_edgeuse)),
    ('radial_p', POINTER(struct_edgeuse)),
    ('e_p', POINTER(struct_edge)),
    ('orientation', c_int),
    ('vu_p', POINTER(struct_vertexuse)),
    ('g', union_anon_79),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 539
class struct_vertex_g(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 532
class struct_vertex(Structure):
    pass

struct_vertex.__slots__ = [
    'magic',
    'vu_hd',
    'vg_p',
    'index',
]
struct_vertex._fields_ = [
    ('magic', c_uint32),
    ('vu_hd', struct_bu_list),
    ('vg_p', POINTER(struct_vertex_g)),
    ('index', c_long),
]

struct_vertex_g.__slots__ = [
    'magic',
    'coord',
    'index',
]
struct_vertex_g._fields_ = [
    ('magic', c_uint32),
    ('coord', point_t),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 547
class union_anon_80(Union):
    pass

union_anon_80.__slots__ = [
    's_p',
    'lu_p',
    'eu_p',
    'magic_p',
]
union_anon_80._fields_ = [
    ('s_p', POINTER(struct_shell)),
    ('lu_p', POINTER(struct_loopuse)),
    ('eu_p', POINTER(struct_edgeuse)),
    ('magic_p', POINTER(c_uint32)),
]

# /opt/brlcad/include/brlcad/nmg.h: 562
class struct_vertexuse_a_plane(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 568
class struct_vertexuse_a_cnurb(Structure):
    pass

# /opt/brlcad/include/brlcad/nmg.h: 554
class union_anon_81(Union):
    pass

union_anon_81.__slots__ = [
    'magic_p',
    'plane_p',
    'cnurb_p',
]
union_anon_81._fields_ = [
    ('magic_p', POINTER(c_uint32)),
    ('plane_p', POINTER(struct_vertexuse_a_plane)),
    ('cnurb_p', POINTER(struct_vertexuse_a_cnurb)),
]

struct_vertexuse.__slots__ = [
    'l',
    'up',
    'v_p',
    'a',
    'index',
]
struct_vertexuse._fields_ = [
    ('l', struct_bu_list),
    ('up', union_anon_80),
    ('v_p', POINTER(struct_vertex)),
    ('a', union_anon_81),
    ('index', c_long),
]

struct_vertexuse_a_plane.__slots__ = [
    'magic',
    'N',
    'index',
]
struct_vertexuse_a_plane._fields_ = [
    ('magic', c_uint32),
    ('N', vect_t),
    ('index', c_long),
]

struct_vertexuse_a_cnurb.__slots__ = [
    'magic',
    'param',
    'index',
]
struct_vertexuse_a_cnurb._fields_ = [
    ('magic', c_uint32),
    ('param', fastf_t * 3),
    ('index', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 678
class struct_nmg_boolstruct(Structure):
    pass

struct_nmg_boolstruct.__slots__ = [
    'ilist',
    'tol',
    'pt',
    'dir',
    'coplanar',
    'vertlist',
    'vlsize',
    'model',
]
struct_nmg_boolstruct._fields_ = [
    ('ilist', struct_bu_ptbl),
    ('tol', fastf_t),
    ('pt', point_t),
    ('dir', vect_t),
    ('coplanar', c_int),
    ('vertlist', String),
    ('vlsize', c_int),
    ('model', POINTER(struct_model)),
]

# /opt/brlcad/include/brlcad/nmg.h: 700
class struct_nmg_struct_counts(Structure):
    pass

struct_nmg_struct_counts.__slots__ = [
    'model',
    'region',
    'region_a',
    'shell',
    'shell_a',
    'faceuse',
    'face',
    'face_g_plane',
    'face_g_snurb',
    'loopuse',
    'loop',
    'loop_g',
    'edgeuse',
    'edge',
    'edge_g_lseg',
    'edge_g_cnurb',
    'vertexuse',
    'vertexuse_a_plane',
    'vertexuse_a_cnurb',
    'vertex',
    'vertex_g',
    'max_structs',
    'face_loops',
    'face_edges',
    'face_lone_verts',
    'wire_loops',
    'wire_loop_edges',
    'wire_edges',
    'wire_lone_verts',
    'shells_of_lone_vert',
]
struct_nmg_struct_counts._fields_ = [
    ('model', c_long),
    ('region', c_long),
    ('region_a', c_long),
    ('shell', c_long),
    ('shell_a', c_long),
    ('faceuse', c_long),
    ('face', c_long),
    ('face_g_plane', c_long),
    ('face_g_snurb', c_long),
    ('loopuse', c_long),
    ('loop', c_long),
    ('loop_g', c_long),
    ('edgeuse', c_long),
    ('edge', c_long),
    ('edge_g_lseg', c_long),
    ('edge_g_cnurb', c_long),
    ('vertexuse', c_long),
    ('vertexuse_a_plane', c_long),
    ('vertexuse_a_cnurb', c_long),
    ('vertex', c_long),
    ('vertex_g', c_long),
    ('max_structs', c_long),
    ('face_loops', c_long),
    ('face_edges', c_long),
    ('face_lone_verts', c_long),
    ('wire_loops', c_long),
    ('wire_loop_edges', c_long),
    ('wire_edges', c_long),
    ('wire_lone_verts', c_long),
    ('shells_of_lone_vert', c_long),
]

# /opt/brlcad/include/brlcad/nmg.h: 800
class struct_nmg_visit_handlers(Structure):
    pass

struct_nmg_visit_handlers.__slots__ = [
    'bef_model',
    'aft_model',
    'bef_region',
    'aft_region',
    'vis_region_a',
    'bef_shell',
    'aft_shell',
    'vis_shell_a',
    'bef_faceuse',
    'aft_faceuse',
    'vis_face',
    'vis_face_g',
    'bef_loopuse',
    'aft_loopuse',
    'vis_loop',
    'vis_loop_g',
    'bef_edgeuse',
    'aft_edgeuse',
    'vis_edge',
    'vis_edge_g',
    'bef_vertexuse',
    'aft_vertexuse',
    'vis_vertexuse_a',
    'vis_vertex',
    'vis_vertex_g',
]
struct_nmg_visit_handlers._fields_ = [
    ('bef_model', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_model', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('bef_region', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_region', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_region_a', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('bef_shell', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_shell', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_shell_a', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('bef_faceuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_faceuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int, POINTER(struct_bu_list))),
    ('vis_face', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_face_g', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('bef_loopuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_loopuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_loop', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_loop_g', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('bef_edgeuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_edgeuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_edge', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_edge_g', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('bef_vertexuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('aft_vertexuse', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_vertexuse_a', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_vertex', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
    ('vis_vertex_g', CFUNCTYPE(UNCHECKED(None), POINTER(c_uint32), POINTER(None), c_int)),
]

# /opt/brlcad/include/brlcad/nmg.h: 840
class struct_nmg_radial(Structure):
    pass

struct_nmg_radial.__slots__ = [
    'l',
    'eu',
    'fu',
    's',
    'existing_flag',
    'is_crack',
    'is_outie',
    'needs_flip',
    'ang',
]
struct_nmg_radial._fields_ = [
    ('l', struct_bu_list),
    ('eu', POINTER(struct_edgeuse)),
    ('fu', POINTER(struct_faceuse)),
    ('s', POINTER(struct_shell)),
    ('existing_flag', c_int),
    ('is_crack', c_int),
    ('is_outie', c_int),
    ('needs_flip', c_int),
    ('ang', fastf_t),
]

# /opt/brlcad/include/brlcad/nmg.h: 853
class struct_nmg_inter_struct(Structure):
    pass

struct_nmg_inter_struct.__slots__ = [
    'magic',
    'l1',
    'l2',
    'mag1',
    'mag2',
    'mag_len',
    's1',
    's2',
    'fu1',
    'fu2',
    'tol',
    'coplanar',
    'on_eg',
    'pt',
    'dir',
    'pt2d',
    'dir2d',
    'vert2d',
    'maxindex',
    'proj',
    'twod',
]
struct_nmg_inter_struct._fields_ = [
    ('magic', c_uint32),
    ('l1', POINTER(struct_bu_ptbl)),
    ('l2', POINTER(struct_bu_ptbl)),
    ('mag1', POINTER(fastf_t)),
    ('mag2', POINTER(fastf_t)),
    ('mag_len', c_size_t),
    ('s1', POINTER(struct_shell)),
    ('s2', POINTER(struct_shell)),
    ('fu1', POINTER(struct_faceuse)),
    ('fu2', POINTER(struct_faceuse)),
    ('tol', struct_bn_tol),
    ('coplanar', c_int),
    ('on_eg', POINTER(struct_edge_g_lseg)),
    ('pt', point_t),
    ('dir', vect_t),
    ('pt2d', point_t),
    ('dir2d', vect_t),
    ('vert2d', POINTER(fastf_t)),
    ('maxindex', c_size_t),
    ('proj', mat_t),
    ('twod', POINTER(c_uint32)),
]

# /opt/brlcad/include/brlcad/nmg.h: 941
class struct_nmg_nurb_poly(Structure):
    pass

struct_nmg_nurb_poly.__slots__ = [
    'next',
    'ply',
    'uv',
]
struct_nmg_nurb_poly._fields_ = [
    ('next', POINTER(struct_nmg_nurb_poly)),
    ('ply', point_t * 3),
    ('uv', (fastf_t * 2) * 3),
]

# /opt/brlcad/include/brlcad/nmg.h: 947
class struct_nmg_nurb_uv_hit(Structure):
    pass

struct_nmg_nurb_uv_hit.__slots__ = [
    'next',
    'sub',
    'u',
    'v',
]
struct_nmg_nurb_uv_hit._fields_ = [
    ('next', POINTER(struct_nmg_nurb_uv_hit)),
    ('sub', c_int),
    ('u', fastf_t),
    ('v', fastf_t),
]

# /opt/brlcad/include/brlcad/nmg.h: 955
class struct_oslo_mat(Structure):
    pass

struct_oslo_mat.__slots__ = [
    'next',
    'offset',
    'osize',
    'o_vec',
]
struct_oslo_mat._fields_ = [
    ('next', POINTER(struct_oslo_mat)),
    ('offset', c_int),
    ('osize', c_int),
    ('o_vec', POINTER(fastf_t)),
]

# /opt/brlcad/include/brlcad/nmg.h: 964
class struct_bezier_2d_list(Structure):
    pass

struct_bezier_2d_list.__slots__ = [
    'l',
    'ctl',
]
struct_bezier_2d_list._fields_ = [
    ('l', struct_bu_list),
    ('ctl', POINTER(point2d_t)),
]

# /opt/brlcad/include/brlcad/nmg.h: 974
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bezier'):
    bezier = _libs['/opt/brlcad/lib/librt.dylib'].bezier
    bezier.argtypes = [POINTER(point2d_t), c_int, c_double, POINTER(point2d_t), POINTER(point2d_t), point2d_t, point2d_t]
    bezier.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 980
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bezier_roots'):
    bezier_roots = _libs['/opt/brlcad/lib/librt.dylib'].bezier_roots
    bezier_roots.argtypes = [POINTER(point2d_t), c_int, POINTER(POINTER(point2d_t)), POINTER(POINTER(point2d_t)), point2d_t, point2d_t, point2d_t, c_int, fastf_t]
    bezier_roots.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 985
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'bezier_subdivide'):
    bezier_subdivide = _libs['/opt/brlcad/lib/librt.dylib'].bezier_subdivide
    bezier_subdivide.argtypes = [POINTER(struct_bezier_2d_list), c_int, fastf_t, c_int]
    bezier_subdivide.restype = POINTER(struct_bezier_2d_list)

# /opt/brlcad/include/brlcad/nmg.h: 993
try:
    re_nmgfree = (struct_bu_list).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 're_nmgfree')
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1106
class struct_nmg_ray(Structure):
    pass

struct_nmg_ray.__slots__ = [
    'magic',
    'r_pt',
    'r_dir',
    'r_min',
    'r_max',
]
struct_nmg_ray._fields_ = [
    ('magic', c_uint32),
    ('r_pt', point_t),
    ('r_dir', vect_t),
    ('r_min', fastf_t),
    ('r_max', fastf_t),
]

# /opt/brlcad/include/brlcad/nmg.h: 1114
class struct_nmg_hit(Structure):
    pass

struct_nmg_hit.__slots__ = [
    'hit_magic',
    'hit_dist',
    'hit_point',
    'hit_normal',
    'hit_vpriv',
    'hit_private',
    'hit_surfno',
    'hit_rayp',
]
struct_nmg_hit._fields_ = [
    ('hit_magic', c_uint32),
    ('hit_dist', fastf_t),
    ('hit_point', point_t),
    ('hit_normal', vect_t),
    ('hit_vpriv', vect_t),
    ('hit_private', POINTER(None)),
    ('hit_surfno', c_int),
    ('hit_rayp', POINTER(struct_nmg_ray)),
]

# /opt/brlcad/include/brlcad/nmg.h: 1125
class struct_nmg_seg(Structure):
    pass

struct_nmg_seg.__slots__ = [
    'l',
    'seg_in',
    'seg_out',
    'seg_stp',
]
struct_nmg_seg._fields_ = [
    ('l', struct_bu_list),
    ('seg_in', struct_nmg_hit),
    ('seg_out', struct_nmg_hit),
    ('seg_stp', POINTER(None)),
]

# /opt/brlcad/include/brlcad/nmg.h: 1132
class struct_nmg_hitmiss(Structure):
    pass

struct_nmg_hitmiss.__slots__ = [
    'l',
    'hit',
    'dist_in_plane',
    'in_out',
    'inbound_use',
    'inbound_norm',
    'outbound_use',
    'outbound_norm',
    'start_stop',
    'other',
]
struct_nmg_hitmiss._fields_ = [
    ('l', struct_bu_list),
    ('hit', struct_nmg_hit),
    ('dist_in_plane', fastf_t),
    ('in_out', c_int),
    ('inbound_use', POINTER(c_long)),
    ('inbound_norm', vect_t),
    ('outbound_use', POINTER(c_long)),
    ('outbound_norm', vect_t),
    ('start_stop', c_int),
    ('other', POINTER(struct_nmg_hitmiss)),
]

# /opt/brlcad/include/brlcad/nmg.h: 1169
class struct_nmg_ray_data(Structure):
    pass

struct_nmg_ray_data.__slots__ = [
    'magic',
    'rd_m',
    'manifolds',
    'rd_invdir',
    'rp',
    'ap',
    'seghead',
    'stp',
    'tol',
    'hitmiss',
    'rd_hit',
    'rd_miss',
    'plane_pt',
    'ray_dist_to_plane',
    'face_subhit',
    'classifying_ray',
]
struct_nmg_ray_data._fields_ = [
    ('magic', c_uint32),
    ('rd_m', POINTER(struct_model)),
    ('manifolds', String),
    ('rd_invdir', vect_t),
    ('rp', POINTER(struct_nmg_ray)),
    ('ap', POINTER(POINTER(None))),
    ('seghead', POINTER(struct_nmg_seg)),
    ('stp', POINTER(POINTER(None))),
    ('tol', POINTER(struct_bn_tol)),
    ('hitmiss', POINTER(POINTER(struct_nmg_hitmiss))),
    ('rd_hit', struct_bu_list),
    ('rd_miss', struct_bu_list),
    ('plane_pt', point_t),
    ('ray_dist_to_plane', fastf_t),
    ('face_subhit', c_int),
    ('classifying_ray', c_int),
]

# /opt/brlcad/include/brlcad/nmg.h: 1216
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'ray_in_rpp'):
    ray_in_rpp = _libs['/opt/brlcad/lib/librt.dylib'].ray_in_rpp
    ray_in_rpp.argtypes = [POINTER(struct_nmg_ray), POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t)]
    ray_in_rpp.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1224
try:
    nmg_vlblock_anim_upcall = (POINTER(CFUNCTYPE(UNCHECKED(None), ))).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_anim_upcall')
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1229
try:
    nmg_mged_debug_display_hack = (POINTER(CFUNCTYPE(UNCHECKED(None), ))).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mged_debug_display_hack')
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1236
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mm'):
    nmg_mm = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mm
    nmg_mm.argtypes = []
    nmg_mm.restype = POINTER(struct_model)

# /opt/brlcad/include/brlcad/nmg.h: 1237
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mmr'):
    nmg_mmr = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mmr
    nmg_mmr.argtypes = []
    nmg_mmr.restype = POINTER(struct_model)

# /opt/brlcad/include/brlcad/nmg.h: 1238
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mrsv'):
    nmg_mrsv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mrsv
    nmg_mrsv.argtypes = [POINTER(struct_model)]
    nmg_mrsv.restype = POINTER(struct_nmgregion)

# /opt/brlcad/include/brlcad/nmg.h: 1239
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_msv'):
    nmg_msv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_msv
    nmg_msv.argtypes = [POINTER(struct_nmgregion)]
    nmg_msv.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1240
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mf'):
    nmg_mf = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mf
    nmg_mf.argtypes = [POINTER(struct_loopuse)]
    nmg_mf.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1241
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mlv'):
    nmg_mlv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mlv
    nmg_mlv.argtypes = [POINTER(c_uint32), POINTER(struct_vertex), c_int]
    nmg_mlv.restype = POINTER(struct_loopuse)

# /opt/brlcad/include/brlcad/nmg.h: 1244
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_me'):
    nmg_me = _libs['/opt/brlcad/lib/librt.dylib'].nmg_me
    nmg_me.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex), POINTER(struct_shell)]
    nmg_me.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1247
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_meonvu'):
    nmg_meonvu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_meonvu
    nmg_meonvu.argtypes = [POINTER(struct_vertexuse)]
    nmg_meonvu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1248
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ml'):
    nmg_ml = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ml
    nmg_ml.argtypes = [POINTER(struct_shell)]
    nmg_ml.restype = POINTER(struct_loopuse)

# /opt/brlcad/include/brlcad/nmg.h: 1250
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_keg'):
    nmg_keg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_keg
    nmg_keg.argtypes = [POINTER(struct_edgeuse)]
    nmg_keg.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1251
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kvu'):
    nmg_kvu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kvu
    nmg_kvu.argtypes = [POINTER(struct_vertexuse)]
    nmg_kvu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1252
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kfu'):
    nmg_kfu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kfu
    nmg_kfu.argtypes = [POINTER(struct_faceuse)]
    nmg_kfu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1253
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_klu'):
    nmg_klu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_klu
    nmg_klu.argtypes = [POINTER(struct_loopuse)]
    nmg_klu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1254
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_keu'):
    nmg_keu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_keu
    nmg_keu.argtypes = [POINTER(struct_edgeuse)]
    nmg_keu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1255
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_keu_zl'):
    nmg_keu_zl = _libs['/opt/brlcad/lib/librt.dylib'].nmg_keu_zl
    nmg_keu_zl.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_keu_zl.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1257
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ks'):
    nmg_ks = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ks
    nmg_ks.argtypes = [POINTER(struct_shell)]
    nmg_ks.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1258
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kr'):
    nmg_kr = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kr
    nmg_kr.argtypes = [POINTER(struct_nmgregion)]
    nmg_kr.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1259
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_km'):
    nmg_km = _libs['/opt/brlcad/lib/librt.dylib'].nmg_km
    nmg_km.argtypes = [POINTER(struct_model)]
    nmg_km.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1261
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertex_gv'):
    nmg_vertex_gv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertex_gv
    nmg_vertex_gv.argtypes = [POINTER(struct_vertex), point_t]
    nmg_vertex_gv.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1263
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertex_g'):
    nmg_vertex_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertex_g
    nmg_vertex_g.argtypes = [POINTER(struct_vertex), fastf_t, fastf_t, fastf_t]
    nmg_vertex_g.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1267
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertexuse_nv'):
    nmg_vertexuse_nv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertexuse_nv
    nmg_vertexuse_nv.argtypes = [POINTER(struct_vertexuse), vect_t]
    nmg_vertexuse_nv.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1269
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertexuse_a_cnurb'):
    nmg_vertexuse_a_cnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertexuse_a_cnurb
    nmg_vertexuse_a_cnurb.argtypes = [POINTER(struct_vertexuse), POINTER(fastf_t)]
    nmg_vertexuse_a_cnurb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1271
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_g'):
    nmg_edge_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_g
    nmg_edge_g.argtypes = [POINTER(struct_edgeuse)]
    nmg_edge_g.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1272
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_g_cnurb'):
    nmg_edge_g_cnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_g_cnurb
    nmg_edge_g_cnurb.argtypes = [POINTER(struct_edgeuse), c_int, c_int, POINTER(fastf_t), c_int, c_int, POINTER(fastf_t)]
    nmg_edge_g_cnurb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1279
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_g_cnurb_plinear'):
    nmg_edge_g_cnurb_plinear = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_g_cnurb_plinear
    nmg_edge_g_cnurb_plinear.argtypes = [POINTER(struct_edgeuse)]
    nmg_edge_g_cnurb_plinear.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1280
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_use_edge_g'):
    nmg_use_edge_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_use_edge_g
    nmg_use_edge_g.argtypes = [POINTER(struct_edgeuse), POINTER(c_uint32)]
    nmg_use_edge_g.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1282
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_g'):
    nmg_loop_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_g
    nmg_loop_g.argtypes = [POINTER(struct_loop), POINTER(struct_bn_tol)]
    nmg_loop_g.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1284
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_g'):
    nmg_face_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_g
    nmg_face_g.argtypes = [POINTER(struct_faceuse), plane_t]
    nmg_face_g.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1286
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_new_g'):
    nmg_face_new_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_new_g
    nmg_face_new_g.argtypes = [POINTER(struct_faceuse), plane_t]
    nmg_face_new_g.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1288
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_g_snurb'):
    nmg_face_g_snurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_g_snurb
    nmg_face_g_snurb.argtypes = [POINTER(struct_faceuse), c_int, c_int, c_int, c_int, POINTER(fastf_t), POINTER(fastf_t), c_int, c_int, c_int, POINTER(fastf_t)]
    nmg_face_g_snurb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1299
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_bb'):
    nmg_face_bb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_bb
    nmg_face_bb.argtypes = [POINTER(struct_face), POINTER(struct_bn_tol)]
    nmg_face_bb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1301
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_shell_a'):
    nmg_shell_a = _libs['/opt/brlcad/lib/librt.dylib'].nmg_shell_a
    nmg_shell_a.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_shell_a.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1303
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_region_a'):
    nmg_region_a = _libs['/opt/brlcad/lib/librt.dylib'].nmg_region_a
    nmg_region_a.argtypes = [POINTER(struct_nmgregion), POINTER(struct_bn_tol)]
    nmg_region_a.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1306
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_demote_lu'):
    nmg_demote_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_demote_lu
    nmg_demote_lu.argtypes = [POINTER(struct_loopuse)]
    nmg_demote_lu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1307
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_demote_eu'):
    nmg_demote_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_demote_eu
    nmg_demote_eu.argtypes = [POINTER(struct_edgeuse)]
    nmg_demote_eu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1309
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_movevu'):
    nmg_movevu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_movevu
    nmg_movevu.argtypes = [POINTER(struct_vertexuse), POINTER(struct_vertex)]
    nmg_movevu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1311
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_je'):
    nmg_je = _libs['/opt/brlcad/lib/librt.dylib'].nmg_je
    nmg_je.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse)]
    nmg_je.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1313
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_unglueedge'):
    nmg_unglueedge = _libs['/opt/brlcad/lib/librt.dylib'].nmg_unglueedge
    nmg_unglueedge.argtypes = [POINTER(struct_edgeuse)]
    nmg_unglueedge.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1314
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_jv'):
    nmg_jv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_jv
    nmg_jv.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex)]
    nmg_jv.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1316
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_jfg'):
    nmg_jfg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_jfg
    nmg_jfg.argtypes = [POINTER(struct_face), POINTER(struct_face)]
    nmg_jfg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1318
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_jeg'):
    nmg_jeg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_jeg
    nmg_jeg.argtypes = [POINTER(struct_edge_g_lseg), POINTER(struct_edge_g_lseg)]
    nmg_jeg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1323
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_merge_regions'):
    nmg_merge_regions = _libs['/opt/brlcad/lib/librt.dylib'].nmg_merge_regions
    nmg_merge_regions.argtypes = [POINTER(struct_nmgregion), POINTER(struct_nmgregion), POINTER(struct_bn_tol)]
    nmg_merge_regions.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1328
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_shell_coplanar_face_merge'):
    nmg_shell_coplanar_face_merge = _libs['/opt/brlcad/lib/librt.dylib'].nmg_shell_coplanar_face_merge
    nmg_shell_coplanar_face_merge.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol), c_int, POINTER(struct_bu_list)]
    nmg_shell_coplanar_face_merge.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1332
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_simplify_shell'):
    nmg_simplify_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_simplify_shell
    nmg_simplify_shell.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list)]
    nmg_simplify_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1333
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_rm_redundancies'):
    nmg_rm_redundancies = _libs['/opt/brlcad/lib/librt.dylib'].nmg_rm_redundancies
    nmg_rm_redundancies.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_rm_redundancies.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1336
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_sanitize_s_lv'):
    nmg_sanitize_s_lv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_sanitize_s_lv
    nmg_sanitize_s_lv.argtypes = [POINTER(struct_shell), c_int]
    nmg_sanitize_s_lv.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1338
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_s_split_touchingloops'):
    nmg_s_split_touchingloops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_s_split_touchingloops
    nmg_s_split_touchingloops.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_s_split_touchingloops.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1340
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_s_join_touchingloops'):
    nmg_s_join_touchingloops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_s_join_touchingloops
    nmg_s_join_touchingloops.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_s_join_touchingloops.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1342
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_js'):
    nmg_js = _libs['/opt/brlcad/lib/librt.dylib'].nmg_js
    nmg_js.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_js.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1346
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_invert_shell'):
    nmg_invert_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_invert_shell
    nmg_invert_shell.argtypes = [POINTER(struct_shell)]
    nmg_invert_shell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1349
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cmface'):
    nmg_cmface = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cmface
    nmg_cmface.argtypes = [POINTER(struct_shell), POINTER(POINTER(POINTER(struct_vertex))), c_int]
    nmg_cmface.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1352
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cface'):
    nmg_cface = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cface
    nmg_cface.argtypes = [POINTER(struct_shell), POINTER(POINTER(struct_vertex)), c_int]
    nmg_cface.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1355
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_add_loop_to_face'):
    nmg_add_loop_to_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_add_loop_to_face
    nmg_add_loop_to_face.argtypes = [POINTER(struct_shell), POINTER(struct_faceuse), POINTER(POINTER(struct_vertex)), c_int, c_int]
    nmg_add_loop_to_face.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1360
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_fu_planeeqn'):
    nmg_fu_planeeqn = _libs['/opt/brlcad/lib/librt.dylib'].nmg_fu_planeeqn
    nmg_fu_planeeqn.argtypes = [POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_fu_planeeqn.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1362
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_gluefaces'):
    nmg_gluefaces = _libs['/opt/brlcad/lib/librt.dylib'].nmg_gluefaces
    nmg_gluefaces.argtypes = [POINTER(POINTER(struct_faceuse)), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_gluefaces.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1366
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_simplify_face'):
    nmg_simplify_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_simplify_face
    nmg_simplify_face.argtypes = [POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_simplify_face.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1367
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_reverse_face'):
    nmg_reverse_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_reverse_face
    nmg_reverse_face.argtypes = [POINTER(struct_faceuse)]
    nmg_reverse_face.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1368
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mv_fu_between_shells'):
    nmg_mv_fu_between_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mv_fu_between_shells
    nmg_mv_fu_between_shells.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_faceuse)]
    nmg_mv_fu_between_shells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1371
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_jf'):
    nmg_jf = _libs['/opt/brlcad/lib/librt.dylib'].nmg_jf
    nmg_jf.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse)]
    nmg_jf.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1373
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_dup_face'):
    nmg_dup_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_dup_face
    nmg_dup_face.argtypes = [POINTER(struct_faceuse), POINTER(struct_shell)]
    nmg_dup_face.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1376
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_jl'):
    nmg_jl = _libs['/opt/brlcad/lib/librt.dylib'].nmg_jl
    nmg_jl.argtypes = [POINTER(struct_loopuse), POINTER(struct_edgeuse)]
    nmg_jl.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1378
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_join_2loops'):
    nmg_join_2loops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_join_2loops
    nmg_join_2loops.argtypes = [POINTER(struct_vertexuse), POINTER(struct_vertexuse)]
    nmg_join_2loops.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1380
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_join_singvu_loop'):
    nmg_join_singvu_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_join_singvu_loop
    nmg_join_singvu_loop.argtypes = [POINTER(struct_vertexuse), POINTER(struct_vertexuse)]
    nmg_join_singvu_loop.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1382
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_join_2singvu_loops'):
    nmg_join_2singvu_loops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_join_2singvu_loops
    nmg_join_2singvu_loops.argtypes = [POINTER(struct_vertexuse), POINTER(struct_vertexuse)]
    nmg_join_2singvu_loops.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1384
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cut_loop'):
    nmg_cut_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cut_loop
    nmg_cut_loop.argtypes = [POINTER(struct_vertexuse), POINTER(struct_vertexuse), POINTER(struct_bu_list)]
    nmg_cut_loop.restype = POINTER(struct_loopuse)

# /opt/brlcad/include/brlcad/nmg.h: 1387
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_split_lu_at_vu'):
    nmg_split_lu_at_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_split_lu_at_vu
    nmg_split_lu_at_vu.argtypes = [POINTER(struct_loopuse), POINTER(struct_vertexuse)]
    nmg_split_lu_at_vu.restype = POINTER(struct_loopuse)

# /opt/brlcad/include/brlcad/nmg.h: 1389
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_repeated_v_in_lu'):
    nmg_find_repeated_v_in_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_repeated_v_in_lu
    nmg_find_repeated_v_in_lu.argtypes = [POINTER(struct_vertexuse)]
    nmg_find_repeated_v_in_lu.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1390
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_split_touchingloops'):
    nmg_split_touchingloops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_split_touchingloops
    nmg_split_touchingloops.argtypes = [POINTER(struct_loopuse), POINTER(struct_bn_tol)]
    nmg_split_touchingloops.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1392
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_join_touchingloops'):
    nmg_join_touchingloops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_join_touchingloops
    nmg_join_touchingloops.argtypes = [POINTER(struct_loopuse)]
    nmg_join_touchingloops.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1393
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_get_touching_jaunts'):
    nmg_get_touching_jaunts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_get_touching_jaunts
    nmg_get_touching_jaunts.argtypes = [POINTER(struct_loopuse), POINTER(struct_bu_ptbl), POINTER(c_int)]
    nmg_get_touching_jaunts.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1396
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kill_accordions'):
    nmg_kill_accordions = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kill_accordions
    nmg_kill_accordions.argtypes = [POINTER(struct_loopuse)]
    nmg_kill_accordions.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1397
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_split_at_touching_jaunt'):
    nmg_loop_split_at_touching_jaunt = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_split_at_touching_jaunt
    nmg_loop_split_at_touching_jaunt.argtypes = [POINTER(struct_loopuse), POINTER(struct_bn_tol)]
    nmg_loop_split_at_touching_jaunt.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1399
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_simplify_loop'):
    nmg_simplify_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_simplify_loop
    nmg_simplify_loop.argtypes = [POINTER(struct_loopuse), POINTER(struct_bu_list)]
    nmg_simplify_loop.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1400
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kill_snakes'):
    nmg_kill_snakes = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kill_snakes
    nmg_kill_snakes.argtypes = [POINTER(struct_loopuse), POINTER(struct_bu_list)]
    nmg_kill_snakes.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1401
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mv_lu_between_shells'):
    nmg_mv_lu_between_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mv_lu_between_shells
    nmg_mv_lu_between_shells.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_loopuse)]
    nmg_mv_lu_between_shells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1404
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_moveltof'):
    nmg_moveltof = _libs['/opt/brlcad/lib/librt.dylib'].nmg_moveltof
    nmg_moveltof.argtypes = [POINTER(struct_faceuse), POINTER(struct_shell)]
    nmg_moveltof.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1406
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_dup_loop'):
    nmg_dup_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_dup_loop
    nmg_dup_loop.argtypes = [POINTER(struct_loopuse), POINTER(c_uint32), POINTER(POINTER(c_long))]
    nmg_dup_loop.restype = POINTER(struct_loopuse)

# /opt/brlcad/include/brlcad/nmg.h: 1409
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_set_lu_orientation'):
    nmg_set_lu_orientation = _libs['/opt/brlcad/lib/librt.dylib'].nmg_set_lu_orientation
    nmg_set_lu_orientation.argtypes = [POINTER(struct_loopuse), c_int]
    nmg_set_lu_orientation.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1411
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_lu_reorient'):
    nmg_lu_reorient = _libs['/opt/brlcad/lib/librt.dylib'].nmg_lu_reorient
    nmg_lu_reorient.argtypes = [POINTER(struct_loopuse)]
    nmg_lu_reorient.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1413
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eusplit'):
    nmg_eusplit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eusplit
    nmg_eusplit.argtypes = [POINTER(struct_vertex), POINTER(struct_edgeuse), c_int]
    nmg_eusplit.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1416
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_esplit'):
    nmg_esplit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_esplit
    nmg_esplit.argtypes = [POINTER(struct_vertex), POINTER(struct_edgeuse), c_int]
    nmg_esplit.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1419
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ebreak'):
    nmg_ebreak = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ebreak
    nmg_ebreak.argtypes = [POINTER(struct_vertex), POINTER(struct_edgeuse)]
    nmg_ebreak.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1421
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ebreaker'):
    nmg_ebreaker = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ebreaker
    nmg_ebreaker.argtypes = [POINTER(struct_vertex), POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_ebreaker.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1424
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_e2break'):
    nmg_e2break = _libs['/opt/brlcad/lib/librt.dylib'].nmg_e2break
    nmg_e2break.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse)]
    nmg_e2break.restype = POINTER(struct_vertex)

# /opt/brlcad/include/brlcad/nmg.h: 1426
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_unbreak_edge'):
    nmg_unbreak_edge = _libs['/opt/brlcad/lib/librt.dylib'].nmg_unbreak_edge
    nmg_unbreak_edge.argtypes = [POINTER(struct_edgeuse)]
    nmg_unbreak_edge.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1427
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_unbreak_shell_edge_unsafe'):
    nmg_unbreak_shell_edge_unsafe = _libs['/opt/brlcad/lib/librt.dylib'].nmg_unbreak_shell_edge_unsafe
    nmg_unbreak_shell_edge_unsafe.argtypes = [POINTER(struct_edgeuse)]
    nmg_unbreak_shell_edge_unsafe.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1428
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eins'):
    nmg_eins = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eins
    nmg_eins.argtypes = [POINTER(struct_edgeuse)]
    nmg_eins.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1429
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mv_eu_between_shells'):
    nmg_mv_eu_between_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mv_eu_between_shells
    nmg_mv_eu_between_shells.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_edgeuse)]
    nmg_mv_eu_between_shells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1433
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mv_vu_between_shells'):
    nmg_mv_vu_between_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mv_vu_between_shells
    nmg_mv_vu_between_shells.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_vertexuse)]
    nmg_mv_vu_between_shells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1439
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_model'):
    nmg_find_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_model
    nmg_find_model.argtypes = [POINTER(c_uint32)]
    nmg_find_model.restype = POINTER(struct_model)

# /opt/brlcad/include/brlcad/nmg.h: 1440
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_shell'):
    nmg_find_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_shell
    nmg_find_shell.argtypes = [POINTER(c_uint32)]
    nmg_find_shell.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1441
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_model_bb'):
    nmg_model_bb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_model_bb
    nmg_model_bb.argtypes = [point_t, point_t, POINTER(struct_model)]
    nmg_model_bb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1447
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_shell_is_empty'):
    nmg_shell_is_empty = _libs['/opt/brlcad/lib/librt.dylib'].nmg_shell_is_empty
    nmg_shell_is_empty.argtypes = [POINTER(struct_shell)]
    nmg_shell_is_empty.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1448
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_s_of_lu'):
    nmg_find_s_of_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_s_of_lu
    nmg_find_s_of_lu.argtypes = [POINTER(struct_loopuse)]
    nmg_find_s_of_lu.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1449
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_s_of_eu'):
    nmg_find_s_of_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_s_of_eu
    nmg_find_s_of_eu.argtypes = [POINTER(struct_edgeuse)]
    nmg_find_s_of_eu.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1450
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_s_of_vu'):
    nmg_find_s_of_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_s_of_vu
    nmg_find_s_of_vu.argtypes = [POINTER(struct_vertexuse)]
    nmg_find_s_of_vu.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1453
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_fu_of_eu'):
    nmg_find_fu_of_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_fu_of_eu
    nmg_find_fu_of_eu.argtypes = [POINTER(struct_edgeuse)]
    nmg_find_fu_of_eu.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1454
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_fu_of_lu'):
    nmg_find_fu_of_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_fu_of_lu
    nmg_find_fu_of_lu.argtypes = [POINTER(struct_loopuse)]
    nmg_find_fu_of_lu.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1455
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_fu_of_vu'):
    nmg_find_fu_of_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_fu_of_vu
    nmg_find_fu_of_vu.argtypes = [POINTER(struct_vertexuse)]
    nmg_find_fu_of_vu.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1456
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_fu_with_fg_in_s'):
    nmg_find_fu_with_fg_in_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_fu_with_fg_in_s
    nmg_find_fu_with_fg_in_s.argtypes = [POINTER(struct_shell), POINTER(struct_faceuse)]
    nmg_find_fu_with_fg_in_s.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1458
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_measure_fu_angle'):
    nmg_measure_fu_angle = _libs['/opt/brlcad/lib/librt.dylib'].nmg_measure_fu_angle
    nmg_measure_fu_angle.argtypes = [POINTER(struct_edgeuse), vect_t, vect_t, vect_t]
    nmg_measure_fu_angle.restype = c_double

# /opt/brlcad/include/brlcad/nmg.h: 1464
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_lu_of_vu'):
    nmg_find_lu_of_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_lu_of_vu
    nmg_find_lu_of_vu.argtypes = [POINTER(struct_vertexuse)]
    nmg_find_lu_of_vu.restype = POINTER(struct_loopuse)

# /opt/brlcad/include/brlcad/nmg.h: 1465
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_is_a_crack'):
    nmg_loop_is_a_crack = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_is_a_crack
    nmg_loop_is_a_crack.argtypes = [POINTER(struct_loopuse)]
    nmg_loop_is_a_crack.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1466
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_is_ccw'):
    nmg_loop_is_ccw = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_is_ccw
    nmg_loop_is_ccw.argtypes = [POINTER(struct_loopuse), plane_t, POINTER(struct_bn_tol)]
    nmg_loop_is_ccw.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1469
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_touches_self'):
    nmg_loop_touches_self = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_touches_self
    nmg_loop_touches_self.argtypes = [POINTER(struct_loopuse)]
    nmg_loop_touches_self.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1470
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_2lu_identical'):
    nmg_2lu_identical = _libs['/opt/brlcad/lib/librt.dylib'].nmg_2lu_identical
    nmg_2lu_identical.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse)]
    nmg_2lu_identical.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1474
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_matching_eu_in_s'):
    nmg_find_matching_eu_in_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_matching_eu_in_s
    nmg_find_matching_eu_in_s.argtypes = [POINTER(struct_edgeuse), POINTER(struct_shell)]
    nmg_find_matching_eu_in_s.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1476
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_findeu'):
    nmg_findeu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_findeu
    nmg_findeu.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex), POINTER(struct_shell), POINTER(struct_edgeuse), c_int]
    nmg_findeu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1481
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eu_in_face'):
    nmg_find_eu_in_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eu_in_face
    nmg_find_eu_in_face.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex), POINTER(struct_faceuse), POINTER(struct_edgeuse), c_int]
    nmg_find_eu_in_face.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1486
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_e'):
    nmg_find_e = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_e
    nmg_find_e.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex), POINTER(struct_shell), POINTER(struct_edge)]
    nmg_find_e.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1490
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eu_of_vu'):
    nmg_find_eu_of_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eu_of_vu
    nmg_find_eu_of_vu.argtypes = [POINTER(struct_vertexuse)]
    nmg_find_eu_of_vu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1491
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eu_with_vu_in_lu'):
    nmg_find_eu_with_vu_in_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eu_with_vu_in_lu
    nmg_find_eu_with_vu_in_lu.argtypes = [POINTER(struct_loopuse), POINTER(struct_vertexuse)]
    nmg_find_eu_with_vu_in_lu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1493
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_faceradial'):
    nmg_faceradial = _libs['/opt/brlcad/lib/librt.dylib'].nmg_faceradial
    nmg_faceradial.argtypes = [POINTER(struct_edgeuse)]
    nmg_faceradial.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1494
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_face_edge_in_shell'):
    nmg_radial_face_edge_in_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_face_edge_in_shell
    nmg_radial_face_edge_in_shell.argtypes = [POINTER(struct_edgeuse)]
    nmg_radial_face_edge_in_shell.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1495
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_edge_between_2fu'):
    nmg_find_edge_between_2fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_edge_between_2fu
    nmg_find_edge_between_2fu.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_find_edge_between_2fu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1499
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_e_nearest_pt2'):
    nmg_find_e_nearest_pt2 = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_e_nearest_pt2
    nmg_find_e_nearest_pt2.argtypes = [POINTER(c_uint32), point_t, mat_t, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_find_e_nearest_pt2.restype = POINTER(struct_edge)

# /opt/brlcad/include/brlcad/nmg.h: 1504
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_matching_eu_in_s'):
    nmg_find_matching_eu_in_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_matching_eu_in_s
    nmg_find_matching_eu_in_s.argtypes = [POINTER(struct_edgeuse), POINTER(struct_shell)]
    nmg_find_matching_eu_in_s.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1506
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eu_2vecs_perp'):
    nmg_eu_2vecs_perp = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eu_2vecs_perp
    nmg_eu_2vecs_perp.argtypes = [vect_t, vect_t, vect_t, POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_eu_2vecs_perp.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1511
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eu_leftvec'):
    nmg_find_eu_leftvec = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eu_leftvec
    nmg_find_eu_leftvec.argtypes = [vect_t, POINTER(struct_edgeuse)]
    nmg_find_eu_leftvec.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1513
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eu_left_non_unit'):
    nmg_find_eu_left_non_unit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eu_left_non_unit
    nmg_find_eu_left_non_unit.argtypes = [vect_t, POINTER(struct_edgeuse)]
    nmg_find_eu_left_non_unit.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1515
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_ot_same_eu_of_e'):
    nmg_find_ot_same_eu_of_e = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_ot_same_eu_of_e
    nmg_find_ot_same_eu_of_e.argtypes = [POINTER(struct_edge)]
    nmg_find_ot_same_eu_of_e.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1518
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_v_in_face'):
    nmg_find_v_in_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_v_in_face
    nmg_find_v_in_face.argtypes = [POINTER(struct_vertex), POINTER(struct_faceuse)]
    nmg_find_v_in_face.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1520
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_v_in_shell'):
    nmg_find_v_in_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_v_in_shell
    nmg_find_v_in_shell.argtypes = [POINTER(struct_vertex), POINTER(struct_shell), c_int]
    nmg_find_v_in_shell.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1523
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_pt_in_lu'):
    nmg_find_pt_in_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_pt_in_lu
    nmg_find_pt_in_lu.argtypes = [POINTER(struct_loopuse), point_t, POINTER(struct_bn_tol)]
    nmg_find_pt_in_lu.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1526
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_pt_in_face'):
    nmg_find_pt_in_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_pt_in_face
    nmg_find_pt_in_face.argtypes = [POINTER(struct_faceuse), point_t, POINTER(struct_bn_tol)]
    nmg_find_pt_in_face.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1529
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_pt_in_shell'):
    nmg_find_pt_in_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_pt_in_shell
    nmg_find_pt_in_shell.argtypes = [POINTER(struct_shell), point_t, POINTER(struct_bn_tol)]
    nmg_find_pt_in_shell.restype = POINTER(struct_vertex)

# /opt/brlcad/include/brlcad/nmg.h: 1532
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_pt_in_model'):
    nmg_find_pt_in_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_pt_in_model
    nmg_find_pt_in_model.argtypes = [POINTER(struct_model), point_t, POINTER(struct_bn_tol)]
    nmg_find_pt_in_model.restype = POINTER(struct_vertex)

# /opt/brlcad/include/brlcad/nmg.h: 1535
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_vertex_in_edgelist'):
    nmg_is_vertex_in_edgelist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_vertex_in_edgelist
    nmg_is_vertex_in_edgelist.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_list)]
    nmg_is_vertex_in_edgelist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1537
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_vertex_in_looplist'):
    nmg_is_vertex_in_looplist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_vertex_in_looplist
    nmg_is_vertex_in_looplist.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_list), c_int]
    nmg_is_vertex_in_looplist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1540
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_vertex_in_face'):
    nmg_is_vertex_in_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_vertex_in_face
    nmg_is_vertex_in_face.argtypes = [POINTER(struct_vertex), POINTER(struct_face)]
    nmg_is_vertex_in_face.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1542
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_vertex_a_selfloop_in_shell'):
    nmg_is_vertex_a_selfloop_in_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_vertex_a_selfloop_in_shell
    nmg_is_vertex_a_selfloop_in_shell.argtypes = [POINTER(struct_vertex), POINTER(struct_shell)]
    nmg_is_vertex_a_selfloop_in_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1544
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_vertex_in_facelist'):
    nmg_is_vertex_in_facelist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_vertex_in_facelist
    nmg_is_vertex_in_facelist.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_list)]
    nmg_is_vertex_in_facelist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1546
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_edge_in_edgelist'):
    nmg_is_edge_in_edgelist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_edge_in_edgelist
    nmg_is_edge_in_edgelist.argtypes = [POINTER(struct_edge), POINTER(struct_bu_list)]
    nmg_is_edge_in_edgelist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1548
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_edge_in_looplist'):
    nmg_is_edge_in_looplist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_edge_in_looplist
    nmg_is_edge_in_looplist.argtypes = [POINTER(struct_edge), POINTER(struct_bu_list)]
    nmg_is_edge_in_looplist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1550
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_edge_in_facelist'):
    nmg_is_edge_in_facelist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_edge_in_facelist
    nmg_is_edge_in_facelist.argtypes = [POINTER(struct_edge), POINTER(struct_bu_list)]
    nmg_is_edge_in_facelist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1552
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_loop_in_facelist'):
    nmg_is_loop_in_facelist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_loop_in_facelist
    nmg_is_loop_in_facelist.argtypes = [POINTER(struct_loop), POINTER(struct_bu_list)]
    nmg_is_loop_in_facelist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1556
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertex_tabulate'):
    nmg_vertex_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertex_tabulate
    nmg_vertex_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_vertex_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1559
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertexuse_normal_tabulate'):
    nmg_vertexuse_normal_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertexuse_normal_tabulate
    nmg_vertexuse_normal_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_vertexuse_normal_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1562
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edgeuse_tabulate'):
    nmg_edgeuse_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edgeuse_tabulate
    nmg_edgeuse_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_edgeuse_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1565
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_tabulate'):
    nmg_edge_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_tabulate
    nmg_edge_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_edge_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1568
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_g_tabulate'):
    nmg_edge_g_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_g_tabulate
    nmg_edge_g_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_edge_g_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1571
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_tabulate'):
    nmg_face_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_tabulate
    nmg_face_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_face_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1574
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edgeuse_with_eg_tabulate'):
    nmg_edgeuse_with_eg_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edgeuse_with_eg_tabulate
    nmg_edgeuse_with_eg_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_edge_g_lseg)]
    nmg_edgeuse_with_eg_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1576
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edgeuse_on_line_tabulate'):
    nmg_edgeuse_on_line_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edgeuse_on_line_tabulate
    nmg_edgeuse_on_line_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(c_uint32), point_t, vect_t, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_edgeuse_on_line_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1582
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_e_and_v_tabulate'):
    nmg_e_and_v_tabulate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_e_and_v_tabulate
    nmg_e_and_v_tabulate.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_e_and_v_tabulate.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1586
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_2edgeuse_g_coincident'):
    nmg_2edgeuse_g_coincident = _libs['/opt/brlcad/lib/librt.dylib'].nmg_2edgeuse_g_coincident
    nmg_2edgeuse_g_coincident.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_2edgeuse_g_coincident.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1591
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_translate_face'):
    nmg_translate_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_translate_face
    nmg_translate_face.argtypes = [POINTER(struct_faceuse), vect_t, POINTER(struct_bu_list)]
    nmg_translate_face.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1592
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_extrude_face'):
    nmg_extrude_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_extrude_face
    nmg_extrude_face.argtypes = [POINTER(struct_faceuse), vect_t, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_extrude_face.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1593
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_vertex_in_lu'):
    nmg_find_vertex_in_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_vertex_in_lu
    nmg_find_vertex_in_lu.argtypes = [POINTER(struct_vertex), POINTER(struct_loopuse)]
    nmg_find_vertex_in_lu.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 1594
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_fix_overlapping_loops'):
    nmg_fix_overlapping_loops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_fix_overlapping_loops
    nmg_fix_overlapping_loops.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_fix_overlapping_loops.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1595
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_crossed_loops'):
    nmg_break_crossed_loops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_crossed_loops
    nmg_break_crossed_loops.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_break_crossed_loops.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1596
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_extrude_cleanup'):
    nmg_extrude_cleanup = _libs['/opt/brlcad/lib/librt.dylib'].nmg_extrude_cleanup
    nmg_extrude_cleanup.argtypes = [POINTER(struct_shell), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_extrude_cleanup.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1597
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_hollow_shell'):
    nmg_hollow_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_hollow_shell
    nmg_hollow_shell.argtypes = [POINTER(struct_shell), fastf_t, c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_hollow_shell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1598
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_extrude_shell'):
    nmg_extrude_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_extrude_shell
    nmg_extrude_shell.argtypes = [POINTER(struct_shell), fastf_t, c_int, c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_extrude_shell.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1601
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_orientation'):
    nmg_orientation = _libs['/opt/brlcad/lib/librt.dylib'].nmg_orientation
    nmg_orientation.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        nmg_orientation.restype = ReturnString
    else:
        nmg_orientation.restype = String
        nmg_orientation.errcheck = ReturnString

# /opt/brlcad/include/brlcad/nmg.h: 1602
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_orient'):
    nmg_pr_orient = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_orient
    nmg_pr_orient.argtypes = [c_int, String]
    nmg_pr_orient.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1604
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_m'):
    nmg_pr_m = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_m
    nmg_pr_m.argtypes = [POINTER(struct_model)]
    nmg_pr_m.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1605
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_r'):
    nmg_pr_r = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_r
    nmg_pr_r.argtypes = [POINTER(struct_nmgregion), String]
    nmg_pr_r.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1607
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_sa'):
    nmg_pr_sa = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_sa
    nmg_pr_sa.argtypes = [POINTER(struct_shell_a), String]
    nmg_pr_sa.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1609
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_lg'):
    nmg_pr_lg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_lg
    nmg_pr_lg.argtypes = [POINTER(struct_loop_g), String]
    nmg_pr_lg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1611
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_fg'):
    nmg_pr_fg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_fg
    nmg_pr_fg.argtypes = [POINTER(c_uint32), String]
    nmg_pr_fg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1613
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_s'):
    nmg_pr_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_s
    nmg_pr_s.argtypes = [POINTER(struct_shell), String]
    nmg_pr_s.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1615
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_s_briefly'):
    nmg_pr_s_briefly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_s_briefly
    nmg_pr_s_briefly.argtypes = [POINTER(struct_shell), String]
    nmg_pr_s_briefly.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1617
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_f'):
    nmg_pr_f = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_f
    nmg_pr_f.argtypes = [POINTER(struct_face), String]
    nmg_pr_f.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1619
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_fu'):
    nmg_pr_fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_fu
    nmg_pr_fu.argtypes = [POINTER(struct_faceuse), String]
    nmg_pr_fu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1621
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_fu_briefly'):
    nmg_pr_fu_briefly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_fu_briefly
    nmg_pr_fu_briefly.argtypes = [POINTER(struct_faceuse), String]
    nmg_pr_fu_briefly.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1623
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_l'):
    nmg_pr_l = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_l
    nmg_pr_l.argtypes = [POINTER(struct_loop), String]
    nmg_pr_l.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1625
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_lu'):
    nmg_pr_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_lu
    nmg_pr_lu.argtypes = [POINTER(struct_loopuse), String]
    nmg_pr_lu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1627
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_lu_briefly'):
    nmg_pr_lu_briefly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_lu_briefly
    nmg_pr_lu_briefly.argtypes = [POINTER(struct_loopuse), String]
    nmg_pr_lu_briefly.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1629
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_eg'):
    nmg_pr_eg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_eg
    nmg_pr_eg.argtypes = [POINTER(c_uint32), String]
    nmg_pr_eg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1631
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_e'):
    nmg_pr_e = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_e
    nmg_pr_e.argtypes = [POINTER(struct_edge), String]
    nmg_pr_e.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1633
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_eu'):
    nmg_pr_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_eu
    nmg_pr_eu.argtypes = [POINTER(struct_edgeuse), String]
    nmg_pr_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1635
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_eu_briefly'):
    nmg_pr_eu_briefly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_eu_briefly
    nmg_pr_eu_briefly.argtypes = [POINTER(struct_edgeuse), String]
    nmg_pr_eu_briefly.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1637
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_eu_endpoints'):
    nmg_pr_eu_endpoints = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_eu_endpoints
    nmg_pr_eu_endpoints.argtypes = [POINTER(struct_edgeuse), String]
    nmg_pr_eu_endpoints.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1639
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_vg'):
    nmg_pr_vg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_vg
    nmg_pr_vg.argtypes = [POINTER(struct_vertex_g), String]
    nmg_pr_vg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1641
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_v'):
    nmg_pr_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_v
    nmg_pr_v.argtypes = [POINTER(struct_vertex), String]
    nmg_pr_v.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1643
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_vu'):
    nmg_pr_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_vu
    nmg_pr_vu.argtypes = [POINTER(struct_vertexuse), String]
    nmg_pr_vu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1645
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_vu_briefly'):
    nmg_pr_vu_briefly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_vu_briefly
    nmg_pr_vu_briefly.argtypes = [POINTER(struct_vertexuse), String]
    nmg_pr_vu_briefly.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1647
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_vua'):
    nmg_pr_vua = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_vua
    nmg_pr_vua.argtypes = [POINTER(c_uint32), String]
    nmg_pr_vua.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1649
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_euprint'):
    nmg_euprint = _libs['/opt/brlcad/lib/librt.dylib'].nmg_euprint
    nmg_euprint.argtypes = [String, POINTER(struct_edgeuse)]
    nmg_euprint.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1651
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_ptbl'):
    nmg_pr_ptbl = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_ptbl
    nmg_pr_ptbl.argtypes = [String, POINTER(struct_bu_ptbl), c_int]
    nmg_pr_ptbl.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1654
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_ptbl_vert_list'):
    nmg_pr_ptbl_vert_list = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_ptbl_vert_list
    nmg_pr_ptbl_vert_list.argtypes = [String, POINTER(struct_bu_ptbl), POINTER(fastf_t)]
    nmg_pr_ptbl_vert_list.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1657
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_one_eu_vecs'):
    nmg_pr_one_eu_vecs = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_one_eu_vecs
    nmg_pr_one_eu_vecs.argtypes = [POINTER(struct_edgeuse), vect_t, vect_t, vect_t, POINTER(struct_bn_tol)]
    nmg_pr_one_eu_vecs.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1662
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_fu_around_eu_vecs'):
    nmg_pr_fu_around_eu_vecs = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_fu_around_eu_vecs
    nmg_pr_fu_around_eu_vecs.argtypes = [POINTER(struct_edgeuse), vect_t, vect_t, vect_t, POINTER(struct_bn_tol)]
    nmg_pr_fu_around_eu_vecs.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1667
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_fu_around_eu'):
    nmg_pr_fu_around_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_fu_around_eu
    nmg_pr_fu_around_eu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_pr_fu_around_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1669
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pl_lu_around_eu'):
    nmg_pl_lu_around_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pl_lu_around_eu
    nmg_pl_lu_around_eu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_bu_list)]
    nmg_pl_lu_around_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1670
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_fus_in_fg'):
    nmg_pr_fus_in_fg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_fus_in_fg
    nmg_pr_fus_in_fg.argtypes = [POINTER(c_uint32)]
    nmg_pr_fus_in_fg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1673
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_calc_lu_uv_orient'):
    nmg_snurb_calc_lu_uv_orient = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_calc_lu_uv_orient
    nmg_snurb_calc_lu_uv_orient.argtypes = [POINTER(struct_loopuse)]
    nmg_snurb_calc_lu_uv_orient.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1674
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_fu_eval'):
    nmg_snurb_fu_eval = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_fu_eval
    nmg_snurb_fu_eval.argtypes = [POINTER(struct_faceuse), fastf_t, fastf_t, point_t]
    nmg_snurb_fu_eval.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1678
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_fu_get_norm'):
    nmg_snurb_fu_get_norm = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_fu_get_norm
    nmg_snurb_fu_get_norm.argtypes = [POINTER(struct_faceuse), fastf_t, fastf_t, vect_t]
    nmg_snurb_fu_get_norm.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1682
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_fu_get_norm_at_vu'):
    nmg_snurb_fu_get_norm_at_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_fu_get_norm_at_vu
    nmg_snurb_fu_get_norm_at_vu.argtypes = [POINTER(struct_faceuse), POINTER(struct_vertexuse), vect_t]
    nmg_snurb_fu_get_norm_at_vu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1685
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_zero_length_edges'):
    nmg_find_zero_length_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_zero_length_edges
    nmg_find_zero_length_edges.argtypes = [POINTER(struct_model), POINTER(struct_bu_list)]
    nmg_find_zero_length_edges.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1686
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_top_face_in_dir'):
    nmg_find_top_face_in_dir = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_top_face_in_dir
    nmg_find_top_face_in_dir.argtypes = [POINTER(struct_shell), c_int, POINTER(c_long)]
    nmg_find_top_face_in_dir.restype = POINTER(struct_face)

# /opt/brlcad/include/brlcad/nmg.h: 1688
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_top_face'):
    nmg_find_top_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_top_face
    nmg_find_top_face.argtypes = [POINTER(struct_shell), POINTER(c_int), POINTER(c_long)]
    nmg_find_top_face.restype = POINTER(struct_face)

# /opt/brlcad/include/brlcad/nmg.h: 1691
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_outer_and_void_shells'):
    nmg_find_outer_and_void_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_outer_and_void_shells
    nmg_find_outer_and_void_shells.argtypes = [POINTER(struct_nmgregion), POINTER(POINTER(POINTER(struct_bu_ptbl))), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_find_outer_and_void_shells.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1695
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mark_edges_real'):
    nmg_mark_edges_real = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mark_edges_real
    nmg_mark_edges_real.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_mark_edges_real.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1696
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_tabulate_face_g_verts'):
    nmg_tabulate_face_g_verts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_tabulate_face_g_verts
    nmg_tabulate_face_g_verts.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_face_g_plane)]
    nmg_tabulate_face_g_verts.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1698
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_shell_self'):
    nmg_isect_shell_self = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_shell_self
    nmg_isect_shell_self.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_isect_shell_self.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1701
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_next_radial_eu'):
    nmg_next_radial_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_next_radial_eu
    nmg_next_radial_eu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_shell), c_int]
    nmg_next_radial_eu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1704
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_prev_radial_eu'):
    nmg_prev_radial_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_prev_radial_eu
    nmg_prev_radial_eu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_shell), c_int]
    nmg_prev_radial_eu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1707
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_face_count'):
    nmg_radial_face_count = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_face_count
    nmg_radial_face_count.argtypes = [POINTER(struct_edgeuse), POINTER(struct_shell)]
    nmg_radial_face_count.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1709
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_check_closed_shell'):
    nmg_check_closed_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_check_closed_shell
    nmg_check_closed_shell.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_check_closed_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1711
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_move_lu_between_fus'):
    nmg_move_lu_between_fus = _libs['/opt/brlcad/lib/librt.dylib'].nmg_move_lu_between_fus
    nmg_move_lu_between_fus.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_loopuse)]
    nmg_move_lu_between_fus.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1714
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_plane_newell'):
    nmg_loop_plane_newell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_plane_newell
    nmg_loop_plane_newell.argtypes = [POINTER(struct_loopuse), plane_t]
    nmg_loop_plane_newell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1716
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_plane_area'):
    nmg_loop_plane_area = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_plane_area
    nmg_loop_plane_area.argtypes = [POINTER(struct_loopuse), plane_t]
    nmg_loop_plane_area.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1718
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_plane_area2'):
    nmg_loop_plane_area2 = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_plane_area2
    nmg_loop_plane_area2.argtypes = [POINTER(struct_loopuse), plane_t, POINTER(struct_bn_tol)]
    nmg_loop_plane_area2.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1721
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_calc_face_plane'):
    nmg_calc_face_plane = _libs['/opt/brlcad/lib/librt.dylib'].nmg_calc_face_plane
    nmg_calc_face_plane.argtypes = [POINTER(struct_faceuse), plane_t, POINTER(struct_bu_list)]
    nmg_calc_face_plane.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1723
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_calc_face_g'):
    nmg_calc_face_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_calc_face_g
    nmg_calc_face_g.argtypes = [POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_calc_face_g.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1724
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_faceuse_area'):
    nmg_faceuse_area = _libs['/opt/brlcad/lib/librt.dylib'].nmg_faceuse_area
    nmg_faceuse_area.argtypes = [POINTER(struct_faceuse)]
    nmg_faceuse_area.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1725
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_shell_area'):
    nmg_shell_area = _libs['/opt/brlcad/lib/librt.dylib'].nmg_shell_area
    nmg_shell_area.argtypes = [POINTER(struct_shell)]
    nmg_shell_area.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1726
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_region_area'):
    nmg_region_area = _libs['/opt/brlcad/lib/librt.dylib'].nmg_region_area
    nmg_region_area.argtypes = [POINTER(struct_nmgregion)]
    nmg_region_area.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1727
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_model_area'):
    nmg_model_area = _libs['/opt/brlcad/lib/librt.dylib'].nmg_model_area
    nmg_model_area.argtypes = [POINTER(struct_model)]
    nmg_model_area.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1729
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_purge_unwanted_intersection_points'):
    nmg_purge_unwanted_intersection_points = _libs['/opt/brlcad/lib/librt.dylib'].nmg_purge_unwanted_intersection_points
    nmg_purge_unwanted_intersection_points.argtypes = [POINTER(struct_bu_ptbl), POINTER(fastf_t), POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_purge_unwanted_intersection_points.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1733
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_in_or_ref'):
    nmg_in_or_ref = _libs['/opt/brlcad/lib/librt.dylib'].nmg_in_or_ref
    nmg_in_or_ref.argtypes = [POINTER(struct_vertexuse), POINTER(struct_bu_ptbl)]
    nmg_in_or_ref.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1735
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_rebound'):
    nmg_rebound = _libs['/opt/brlcad/lib/librt.dylib'].nmg_rebound
    nmg_rebound.argtypes = [POINTER(struct_model), POINTER(struct_bn_tol)]
    nmg_rebound.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1737
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_count_shell_kids'):
    nmg_count_shell_kids = _libs['/opt/brlcad/lib/librt.dylib'].nmg_count_shell_kids
    nmg_count_shell_kids.argtypes = [POINTER(struct_model), POINTER(c_size_t), POINTER(c_size_t), POINTER(c_size_t)]
    nmg_count_shell_kids.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1741
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_close_shell'):
    nmg_close_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_close_shell
    nmg_close_shell.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_close_shell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1743
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_dup_shell'):
    nmg_dup_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_dup_shell
    nmg_dup_shell.argtypes = [POINTER(struct_shell), POINTER(POINTER(POINTER(c_long))), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_dup_shell.restype = POINTER(struct_shell)

# /opt/brlcad/include/brlcad/nmg.h: 1747
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pop_eu'):
    nmg_pop_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pop_eu
    nmg_pop_eu.argtypes = [POINTER(struct_bu_ptbl)]
    nmg_pop_eu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1748
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_reverse_radials'):
    nmg_reverse_radials = _libs['/opt/brlcad/lib/librt.dylib'].nmg_reverse_radials
    nmg_reverse_radials.argtypes = [POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_reverse_radials.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1750
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_reverse_face_and_radials'):
    nmg_reverse_face_and_radials = _libs['/opt/brlcad/lib/librt.dylib'].nmg_reverse_face_and_radials
    nmg_reverse_face_and_radials.argtypes = [POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_reverse_face_and_radials.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1752
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_shell_is_void'):
    nmg_shell_is_void = _libs['/opt/brlcad/lib/librt.dylib'].nmg_shell_is_void
    nmg_shell_is_void.argtypes = [POINTER(struct_shell)]
    nmg_shell_is_void.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1753
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_propagate_normals'):
    nmg_propagate_normals = _libs['/opt/brlcad/lib/librt.dylib'].nmg_propagate_normals
    nmg_propagate_normals.argtypes = [POINTER(struct_faceuse), POINTER(c_long), POINTER(struct_bn_tol)]
    nmg_propagate_normals.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1756
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_connect_same_fu_orients'):
    nmg_connect_same_fu_orients = _libs['/opt/brlcad/lib/librt.dylib'].nmg_connect_same_fu_orients
    nmg_connect_same_fu_orients.argtypes = [POINTER(struct_shell)]
    nmg_connect_same_fu_orients.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1757
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_fix_decomposed_shell_normals'):
    nmg_fix_decomposed_shell_normals = _libs['/opt/brlcad/lib/librt.dylib'].nmg_fix_decomposed_shell_normals
    nmg_fix_decomposed_shell_normals.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_fix_decomposed_shell_normals.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1759
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mk_model_from_region'):
    nmg_mk_model_from_region = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mk_model_from_region
    nmg_mk_model_from_region.argtypes = [POINTER(struct_nmgregion), c_int, POINTER(struct_bu_list)]
    nmg_mk_model_from_region.restype = POINTER(struct_model)

# /opt/brlcad/include/brlcad/nmg.h: 1761
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_fix_normals'):
    nmg_fix_normals = _libs['/opt/brlcad/lib/librt.dylib'].nmg_fix_normals
    nmg_fix_normals.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_fix_normals.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1764
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_long_edges'):
    nmg_break_long_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_long_edges
    nmg_break_long_edges.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_break_long_edges.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1766
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mk_new_face_from_loop'):
    nmg_mk_new_face_from_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mk_new_face_from_loop
    nmg_mk_new_face_from_loop.argtypes = [POINTER(struct_loopuse)]
    nmg_mk_new_face_from_loop.restype = POINTER(struct_faceuse)

# /opt/brlcad/include/brlcad/nmg.h: 1767
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_split_loops_into_faces'):
    nmg_split_loops_into_faces = _libs['/opt/brlcad/lib/librt.dylib'].nmg_split_loops_into_faces
    nmg_split_loops_into_faces.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_split_loops_into_faces.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1769
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_decompose_shell'):
    nmg_decompose_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_decompose_shell
    nmg_decompose_shell.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_decompose_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1771
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_unbreak_region_edges'):
    nmg_unbreak_region_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_unbreak_region_edges
    nmg_unbreak_region_edges.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list)]
    nmg_unbreak_region_edges.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1772
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlist_to_eu'):
    nmg_vlist_to_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlist_to_eu
    nmg_vlist_to_eu.argtypes = [POINTER(struct_bu_list), POINTER(struct_shell)]
    nmg_vlist_to_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1774
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mv_shell_to_region'):
    nmg_mv_shell_to_region = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mv_shell_to_region
    nmg_mv_shell_to_region.argtypes = [POINTER(struct_shell), POINTER(struct_nmgregion)]
    nmg_mv_shell_to_region.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1776
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_isect_faces'):
    nmg_find_isect_faces = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_isect_faces
    nmg_find_isect_faces.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_ptbl), POINTER(c_int), POINTER(struct_bn_tol)]
    nmg_find_isect_faces.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1780
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_simple_vertex_solve'):
    nmg_simple_vertex_solve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_simple_vertex_solve
    nmg_simple_vertex_solve.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_simple_vertex_solve.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1783
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_vert_on_fus'):
    nmg_ck_vert_on_fus = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_vert_on_fus
    nmg_ck_vert_on_fus.argtypes = [POINTER(struct_vertex), POINTER(struct_bn_tol)]
    nmg_ck_vert_on_fus.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1785
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_make_faces_at_vert'):
    nmg_make_faces_at_vert = _libs['/opt/brlcad/lib/librt.dylib'].nmg_make_faces_at_vert
    nmg_make_faces_at_vert.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_ptbl), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_make_faces_at_vert.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1789
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kill_cracks_at_vertex'):
    nmg_kill_cracks_at_vertex = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kill_cracks_at_vertex
    nmg_kill_cracks_at_vertex.argtypes = [POINTER(struct_vertex)]
    nmg_kill_cracks_at_vertex.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1790
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_complex_vertex_solve'):
    nmg_complex_vertex_solve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_complex_vertex_solve
    nmg_complex_vertex_solve.argtypes = [POINTER(struct_vertex), POINTER(struct_bu_ptbl), c_int, c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_complex_vertex_solve.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1796
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_bad_face_normals'):
    nmg_bad_face_normals = _libs['/opt/brlcad/lib/librt.dylib'].nmg_bad_face_normals
    nmg_bad_face_normals.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_bad_face_normals.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1798
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_faces_are_radial'):
    nmg_faces_are_radial = _libs['/opt/brlcad/lib/librt.dylib'].nmg_faces_are_radial
    nmg_faces_are_radial.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse)]
    nmg_faces_are_radial.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1800
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_move_edge_thru_pt'):
    nmg_move_edge_thru_pt = _libs['/opt/brlcad/lib/librt.dylib'].nmg_move_edge_thru_pt
    nmg_move_edge_thru_pt.argtypes = [POINTER(struct_edgeuse), point_t, POINTER(struct_bn_tol)]
    nmg_move_edge_thru_pt.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1803
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlist_to_wire_edges'):
    nmg_vlist_to_wire_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlist_to_wire_edges
    nmg_vlist_to_wire_edges.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list)]
    nmg_vlist_to_wire_edges.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1805
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_follow_free_edges_to_vertex'):
    nmg_follow_free_edges_to_vertex = _libs['/opt/brlcad/lib/librt.dylib'].nmg_follow_free_edges_to_vertex
    nmg_follow_free_edges_to_vertex.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex), POINTER(struct_bu_ptbl), POINTER(struct_shell), POINTER(struct_edgeuse), POINTER(struct_bu_ptbl), POINTER(c_int)]
    nmg_follow_free_edges_to_vertex.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1812
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_glue_face_in_shell'):
    nmg_glue_face_in_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_glue_face_in_shell
    nmg_glue_face_in_shell.argtypes = [POINTER(struct_faceuse), POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_glue_face_in_shell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1815
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_open_shells_connect'):
    nmg_open_shells_connect = _libs['/opt/brlcad/lib/librt.dylib'].nmg_open_shells_connect
    nmg_open_shells_connect.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(POINTER(c_long)), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_open_shells_connect.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1820
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_in_vert'):
    nmg_in_vert = _libs['/opt/brlcad/lib/librt.dylib'].nmg_in_vert
    nmg_in_vert.argtypes = [POINTER(struct_vertex), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_in_vert.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1824
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mirror_model'):
    nmg_mirror_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mirror_model
    nmg_mirror_model.argtypes = [POINTER(struct_model), POINTER(struct_bu_list)]
    nmg_mirror_model.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1825
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kill_cracks'):
    nmg_kill_cracks = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kill_cracks
    nmg_kill_cracks.argtypes = [POINTER(struct_shell)]
    nmg_kill_cracks.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1826
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_kill_zero_length_edgeuses'):
    nmg_kill_zero_length_edgeuses = _libs['/opt/brlcad/lib/librt.dylib'].nmg_kill_zero_length_edgeuses
    nmg_kill_zero_length_edgeuses.argtypes = [POINTER(struct_model)]
    nmg_kill_zero_length_edgeuses.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1827
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_make_faces_within_tol'):
    nmg_make_faces_within_tol = _libs['/opt/brlcad/lib/librt.dylib'].nmg_make_faces_within_tol
    nmg_make_faces_within_tol.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_make_faces_within_tol.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1830
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_intersect_loops_self'):
    nmg_intersect_loops_self = _libs['/opt/brlcad/lib/librt.dylib'].nmg_intersect_loops_self
    nmg_intersect_loops_self.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_intersect_loops_self.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1832
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_join_cnurbs'):
    nmg_join_cnurbs = _libs['/opt/brlcad/lib/librt.dylib'].nmg_join_cnurbs
    nmg_join_cnurbs.argtypes = [POINTER(struct_bu_list)]
    nmg_join_cnurbs.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 1833
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_arc2d_to_cnurb'):
    nmg_arc2d_to_cnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_arc2d_to_cnurb
    nmg_arc2d_to_cnurb.argtypes = [point_t, point_t, point_t, c_int, POINTER(struct_bn_tol)]
    nmg_arc2d_to_cnurb.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 1838
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_edge_at_verts'):
    nmg_break_edge_at_verts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_edge_at_verts
    nmg_break_edge_at_verts.argtypes = [POINTER(struct_edge), POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_break_edge_at_verts.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1841
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_loop_plane_area'):
    nmg_loop_plane_area = _libs['/opt/brlcad/lib/librt.dylib'].nmg_loop_plane_area
    nmg_loop_plane_area.argtypes = [POINTER(struct_loopuse), plane_t]
    nmg_loop_plane_area.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 1843
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_edges'):
    nmg_break_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_edges
    nmg_break_edges.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_break_edges.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1845
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_lu_is_convex'):
    nmg_lu_is_convex = _libs['/opt/brlcad/lib/librt.dylib'].nmg_lu_is_convex
    nmg_lu_is_convex.argtypes = [POINTER(struct_loopuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_lu_is_convex.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1848
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_simplify_shell_edges'):
    nmg_simplify_shell_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_simplify_shell_edges
    nmg_simplify_shell_edges.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_simplify_shell_edges.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1850
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_collapse'):
    nmg_edge_collapse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_collapse
    nmg_edge_collapse.argtypes = [POINTER(struct_model), POINTER(struct_bn_tol), fastf_t, fastf_t, POINTER(struct_bu_list)]
    nmg_edge_collapse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1857
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_clone_model'):
    nmg_clone_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_clone_model
    nmg_clone_model.argtypes = [POINTER(struct_model)]
    nmg_clone_model.restype = POINTER(struct_model)

# /opt/brlcad/include/brlcad/nmg.h: 1860
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_triangulate_shell'):
    nmg_triangulate_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_triangulate_shell
    nmg_triangulate_shell.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_triangulate_shell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1865
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_triangulate_model'):
    nmg_triangulate_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_triangulate_model
    nmg_triangulate_model.argtypes = [POINTER(struct_model), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_triangulate_model.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1868
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_triangulate_fu'):
    nmg_triangulate_fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_triangulate_fu
    nmg_triangulate_fu.argtypes = [POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_triangulate_fu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1871
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_dump_model'):
    nmg_dump_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_dump_model
    nmg_dump_model.argtypes = [POINTER(struct_model)]
    nmg_dump_model.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1874
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_dangling_face'):
    nmg_dangling_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_dangling_face
    nmg_dangling_face.argtypes = [POINTER(struct_faceuse), String]
    nmg_dangling_face.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1880
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_shell_manifolds'):
    nmg_shell_manifolds = _libs['/opt/brlcad/lib/librt.dylib'].nmg_shell_manifolds
    nmg_shell_manifolds.argtypes = [POINTER(struct_shell), String]
    if sizeof(c_int) == sizeof(c_void_p):
        nmg_shell_manifolds.restype = ReturnString
    else:
        nmg_shell_manifolds.restype = String
        nmg_shell_manifolds.errcheck = ReturnString

# /opt/brlcad/include/brlcad/nmg.h: 1882
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_manifolds'):
    nmg_manifolds = _libs['/opt/brlcad/lib/librt.dylib'].nmg_manifolds
    nmg_manifolds.argtypes = [POINTER(struct_model)]
    if sizeof(c_int) == sizeof(c_void_p):
        nmg_manifolds.restype = ReturnString
    else:
        nmg_manifolds.restype = String
        nmg_manifolds.errcheck = ReturnString

# /opt/brlcad/include/brlcad/nmg.h: 1885
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_common_bigloop'):
    nmg_is_common_bigloop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_common_bigloop
    nmg_is_common_bigloop.argtypes = [POINTER(struct_face), POINTER(struct_face)]
    nmg_is_common_bigloop.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1887
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_region_v_unique'):
    nmg_region_v_unique = _libs['/opt/brlcad/lib/librt.dylib'].nmg_region_v_unique
    nmg_region_v_unique.argtypes = [POINTER(struct_nmgregion), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_region_v_unique.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1889
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ptbl_vfuse'):
    nmg_ptbl_vfuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ptbl_vfuse
    nmg_ptbl_vfuse.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_ptbl_vfuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1891
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_region_both_vfuse'):
    nmg_region_both_vfuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_region_both_vfuse
    nmg_region_both_vfuse.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_region_both_vfuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1895
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vertex_fuse'):
    nmg_vertex_fuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vertex_fuse
    nmg_vertex_fuse.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_vertex_fuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1897
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cnurb_is_linear'):
    nmg_cnurb_is_linear = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cnurb_is_linear
    nmg_cnurb_is_linear.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_cnurb_is_linear.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1898
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_is_planar'):
    nmg_snurb_is_planar = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_is_planar
    nmg_snurb_is_planar.argtypes = [POINTER(struct_face_g_snurb), POINTER(struct_bn_tol)]
    nmg_snurb_is_planar.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1900
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eval_linear_trim_curve'):
    nmg_eval_linear_trim_curve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eval_linear_trim_curve
    nmg_eval_linear_trim_curve.argtypes = [POINTER(struct_face_g_snurb), fastf_t * 3, point_t]
    nmg_eval_linear_trim_curve.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1903
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eval_trim_curve'):
    nmg_eval_trim_curve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eval_trim_curve
    nmg_eval_trim_curve.argtypes = [POINTER(struct_edge_g_cnurb), POINTER(struct_face_g_snurb), fastf_t, point_t]
    nmg_eval_trim_curve.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1907
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eval_trim_to_tol'):
    nmg_eval_trim_to_tol = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eval_trim_to_tol
    nmg_eval_trim_to_tol.argtypes = [POINTER(struct_edge_g_cnurb), POINTER(struct_face_g_snurb), fastf_t, fastf_t, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_eval_trim_to_tol.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1914
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eval_linear_trim_to_tol'):
    nmg_eval_linear_trim_to_tol = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eval_linear_trim_to_tol
    nmg_eval_linear_trim_to_tol.argtypes = [POINTER(struct_edge_g_cnurb), POINTER(struct_face_g_snurb), fastf_t * 3, fastf_t * 3, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_eval_linear_trim_to_tol.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1920
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cnurb_lseg_coincident'):
    nmg_cnurb_lseg_coincident = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cnurb_lseg_coincident
    nmg_cnurb_lseg_coincident.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edge_g_cnurb), POINTER(struct_face_g_snurb), point_t, point_t, POINTER(struct_bn_tol)]
    nmg_cnurb_lseg_coincident.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1926
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cnurb_is_on_crv'):
    nmg_cnurb_is_on_crv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cnurb_is_on_crv
    nmg_cnurb_is_on_crv.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edge_g_cnurb), POINTER(struct_face_g_snurb), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_cnurb_is_on_crv.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1931
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_fuse'):
    nmg_edge_fuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_fuse
    nmg_edge_fuse.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_edge_fuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1933
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_edge_g_fuse'):
    nmg_edge_g_fuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_edge_g_fuse
    nmg_edge_g_fuse.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_edge_g_fuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1935
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_fu_verts'):
    nmg_ck_fu_verts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_fu_verts
    nmg_ck_fu_verts.argtypes = [POINTER(struct_faceuse), POINTER(struct_face), POINTER(struct_bn_tol)]
    nmg_ck_fu_verts.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1938
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_fg_verts'):
    nmg_ck_fg_verts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_fg_verts
    nmg_ck_fg_verts.argtypes = [POINTER(struct_faceuse), POINTER(struct_face), POINTER(struct_bn_tol)]
    nmg_ck_fg_verts.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1941
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_two_face_fuse'):
    nmg_two_face_fuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_two_face_fuse
    nmg_two_face_fuse.argtypes = [POINTER(struct_face), POINTER(struct_face), POINTER(struct_bn_tol)]
    nmg_two_face_fuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1944
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_model_face_fuse'):
    nmg_model_face_fuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_model_face_fuse
    nmg_model_face_fuse.argtypes = [POINTER(struct_model), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_model_face_fuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1946
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_all_es_on_v'):
    nmg_break_all_es_on_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_all_es_on_v
    nmg_break_all_es_on_v.argtypes = [POINTER(c_uint32), POINTER(struct_vertex), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_break_all_es_on_v.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1949
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_e_on_v'):
    nmg_break_e_on_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_e_on_v
    nmg_break_e_on_v.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_break_e_on_v.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1952
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_model_break_e_on_v'):
    nmg_model_break_e_on_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_model_break_e_on_v
    nmg_model_break_e_on_v.argtypes = [POINTER(c_uint32), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_model_break_e_on_v.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1955
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_model_fuse'):
    nmg_model_fuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_model_fuse
    nmg_model_fuse.argtypes = [POINTER(struct_model), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_model_fuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1960
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_sorted_list_insert'):
    nmg_radial_sorted_list_insert = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_sorted_list_insert
    nmg_radial_sorted_list_insert.argtypes = [POINTER(struct_bu_list), POINTER(struct_nmg_radial)]
    nmg_radial_sorted_list_insert.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1962
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_verify_pointers'):
    nmg_radial_verify_pointers = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_verify_pointers
    nmg_radial_verify_pointers.argtypes = [POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_radial_verify_pointers.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1964
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_verify_monotone'):
    nmg_radial_verify_monotone = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_verify_monotone
    nmg_radial_verify_monotone.argtypes = [POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_radial_verify_monotone.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1966
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_insure_radial_list_is_increasing'):
    nmg_insure_radial_list_is_increasing = _libs['/opt/brlcad/lib/librt.dylib'].nmg_insure_radial_list_is_increasing
    nmg_insure_radial_list_is_increasing.argtypes = [POINTER(struct_bu_list), fastf_t, fastf_t]
    nmg_insure_radial_list_is_increasing.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1968
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_build_list'):
    nmg_radial_build_list = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_build_list
    nmg_radial_build_list.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_ptbl), c_int, POINTER(struct_edgeuse), vect_t, vect_t, vect_t, POINTER(struct_bn_tol)]
    nmg_radial_build_list.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1976
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_merge_lists'):
    nmg_radial_merge_lists = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_merge_lists
    nmg_radial_merge_lists.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_radial_merge_lists.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1979
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_crack_outie'):
    nmg_is_crack_outie = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_crack_outie
    nmg_is_crack_outie.argtypes = [POINTER(struct_edgeuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_is_crack_outie.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1982
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_radial_eu'):
    nmg_find_radial_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_radial_eu
    nmg_find_radial_eu.argtypes = [POINTER(struct_bu_list), POINTER(struct_edgeuse)]
    nmg_find_radial_eu.restype = POINTER(struct_nmg_radial)

# /opt/brlcad/include/brlcad/nmg.h: 1984
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_next_use_of_2e_in_lu'):
    nmg_find_next_use_of_2e_in_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_next_use_of_2e_in_lu
    nmg_find_next_use_of_2e_in_lu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edge), POINTER(struct_edge)]
    nmg_find_next_use_of_2e_in_lu.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 1987
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_mark_cracks'):
    nmg_radial_mark_cracks = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_mark_cracks
    nmg_radial_mark_cracks.argtypes = [POINTER(struct_bu_list), POINTER(struct_edge), POINTER(struct_edge), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_radial_mark_cracks.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 1992
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_find_an_original'):
    nmg_radial_find_an_original = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_find_an_original
    nmg_radial_find_an_original.argtypes = [POINTER(struct_bu_list), POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_radial_find_an_original.restype = POINTER(struct_nmg_radial)

# /opt/brlcad/include/brlcad/nmg.h: 1995
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_mark_flips'):
    nmg_radial_mark_flips = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_mark_flips
    nmg_radial_mark_flips.argtypes = [POINTER(struct_bu_list), POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_radial_mark_flips.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 1998
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_check_parity'):
    nmg_radial_check_parity = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_check_parity
    nmg_radial_check_parity.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_radial_check_parity.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2001
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_implement_decisions'):
    nmg_radial_implement_decisions = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_implement_decisions
    nmg_radial_implement_decisions.argtypes = [POINTER(struct_bu_list), POINTER(struct_bn_tol), POINTER(struct_edgeuse), vect_t, vect_t, vect_t]
    nmg_radial_implement_decisions.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2007
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_radial'):
    nmg_pr_radial = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_radial
    nmg_pr_radial.argtypes = [String, POINTER(struct_nmg_radial)]
    nmg_pr_radial.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2009
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_radial_list'):
    nmg_pr_radial_list = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_radial_list
    nmg_pr_radial_list.argtypes = [POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_pr_radial_list.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2011
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_do_radial_flips'):
    nmg_do_radial_flips = _libs['/opt/brlcad/lib/librt.dylib'].nmg_do_radial_flips
    nmg_do_radial_flips.argtypes = [POINTER(struct_bu_list)]
    nmg_do_radial_flips.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2012
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_do_radial_join'):
    nmg_do_radial_join = _libs['/opt/brlcad/lib/librt.dylib'].nmg_do_radial_join
    nmg_do_radial_join.argtypes = [POINTER(struct_bu_list), POINTER(struct_edgeuse), vect_t, vect_t, vect_t, POINTER(struct_bn_tol)]
    nmg_do_radial_join.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2016
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_join_eu_NEW'):
    nmg_radial_join_eu_NEW = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_join_eu_NEW
    nmg_radial_join_eu_NEW.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_radial_join_eu_NEW.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2019
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_exchange_marked'):
    nmg_radial_exchange_marked = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_exchange_marked
    nmg_radial_exchange_marked.argtypes = [POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_radial_exchange_marked.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2021
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_s_radial_harmonize'):
    nmg_s_radial_harmonize = _libs['/opt/brlcad/lib/librt.dylib'].nmg_s_radial_harmonize
    nmg_s_radial_harmonize.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_s_radial_harmonize.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2024
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_s_radial_check'):
    nmg_s_radial_check = _libs['/opt/brlcad/lib/librt.dylib'].nmg_s_radial_check
    nmg_s_radial_check.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_s_radial_check.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2027
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_r_radial_check'):
    nmg_r_radial_check = _libs['/opt/brlcad/lib/librt.dylib'].nmg_r_radial_check
    nmg_r_radial_check.argtypes = [POINTER(struct_nmgregion), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_r_radial_check.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2032
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pick_best_edge_g'):
    nmg_pick_best_edge_g = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pick_best_edge_g
    nmg_pick_best_edge_g.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_pick_best_edge_g.restype = POINTER(struct_edge_g_lseg)

# /opt/brlcad/include/brlcad/nmg.h: 2037
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_vertex'):
    nmg_visit_vertex = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_vertex
    nmg_visit_vertex.argtypes = [POINTER(struct_vertex), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_vertex.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2040
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_vertexuse'):
    nmg_visit_vertexuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_vertexuse
    nmg_visit_vertexuse.argtypes = [POINTER(struct_vertexuse), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_vertexuse.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2043
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_edge'):
    nmg_visit_edge = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_edge
    nmg_visit_edge.argtypes = [POINTER(struct_edge), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_edge.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2046
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_edgeuse'):
    nmg_visit_edgeuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_edgeuse
    nmg_visit_edgeuse.argtypes = [POINTER(struct_edgeuse), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_edgeuse.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2049
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_loop'):
    nmg_visit_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_loop
    nmg_visit_loop.argtypes = [POINTER(struct_loop), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_loop.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2052
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_loopuse'):
    nmg_visit_loopuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_loopuse
    nmg_visit_loopuse.argtypes = [POINTER(struct_loopuse), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_loopuse.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2055
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_face'):
    nmg_visit_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_face
    nmg_visit_face.argtypes = [POINTER(struct_face), POINTER(struct_nmg_visit_handlers), POINTER(None)]
    nmg_visit_face.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2058
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_faceuse'):
    nmg_visit_faceuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_faceuse
    nmg_visit_faceuse.argtypes = [POINTER(struct_faceuse), POINTER(struct_nmg_visit_handlers), POINTER(None), POINTER(struct_bu_list)]
    nmg_visit_faceuse.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2062
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_shell'):
    nmg_visit_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_shell
    nmg_visit_shell.argtypes = [POINTER(struct_shell), POINTER(struct_nmg_visit_handlers), POINTER(None), POINTER(struct_bu_list)]
    nmg_visit_shell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2066
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_region'):
    nmg_visit_region = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_region
    nmg_visit_region.argtypes = [POINTER(struct_nmgregion), POINTER(struct_nmg_visit_handlers), POINTER(None), POINTER(struct_bu_list)]
    nmg_visit_region.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2070
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit_model'):
    nmg_visit_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit_model
    nmg_visit_model.argtypes = [POINTER(struct_model), POINTER(struct_nmg_visit_handlers), POINTER(None), POINTER(struct_bu_list)]
    nmg_visit_model.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2074
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_visit'):
    nmg_visit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_visit
    nmg_visit.argtypes = [POINTER(c_uint32), POINTER(struct_nmg_visit_handlers), POINTER(None), POINTER(struct_bu_list)]
    nmg_visit.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2081
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_classify_pt_loop'):
    nmg_classify_pt_loop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_classify_pt_loop
    nmg_classify_pt_loop.argtypes = [point_t, POINTER(struct_loopuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_classify_pt_loop.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2086
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_classify_s_vs_s'):
    nmg_classify_s_vs_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_classify_s_vs_s
    nmg_classify_s_vs_s.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_classify_s_vs_s.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2091
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_classify_lu_lu'):
    nmg_classify_lu_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_classify_lu_lu
    nmg_classify_lu_lu.argtypes = [POINTER(struct_loopuse), POINTER(struct_loopuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_classify_lu_lu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2096
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_class_pt_f'):
        continue
    nmg_class_pt_f = _lib.nmg_class_pt_f
    nmg_class_pt_f.argtypes = [point_t, POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_class_pt_f.restype = c_int
    break

# /opt/brlcad/include/brlcad/nmg.h: 2099
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_class_pt_s'):
    nmg_class_pt_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_class_pt_s
    nmg_class_pt_s.argtypes = [point_t, POINTER(struct_shell), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_class_pt_s.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2106
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eu_is_part_of_crack'):
    nmg_eu_is_part_of_crack = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eu_is_part_of_crack
    nmg_eu_is_part_of_crack.argtypes = [POINTER(struct_edgeuse)]
    nmg_eu_is_part_of_crack.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2108
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_class_pt_lu_except'):
    nmg_class_pt_lu_except = _libs['/opt/brlcad/lib/librt.dylib'].nmg_class_pt_lu_except
    nmg_class_pt_lu_except.argtypes = [point_t, POINTER(struct_loopuse), POINTER(struct_edge), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_class_pt_lu_except.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2114
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_class_pt_fu_except'):
    nmg_class_pt_fu_except = _libs['/opt/brlcad/lib/librt.dylib'].nmg_class_pt_fu_except
    nmg_class_pt_fu_except.argtypes = [point_t, POINTER(struct_faceuse), POINTER(struct_loopuse), CFUNCTYPE(UNCHECKED(None), POINTER(struct_edgeuse), point_t, String, POINTER(struct_bu_list)), CFUNCTYPE(UNCHECKED(None), POINTER(struct_vertexuse), point_t, String), String, c_int, c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_class_pt_fu_except.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2131
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vu_to_vlist'):
    nmg_vu_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vu_to_vlist
    nmg_vu_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_vertexuse), POINTER(struct_bu_list)]
    nmg_vu_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2134
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eu_to_vlist'):
    nmg_eu_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eu_to_vlist
    nmg_eu_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list), POINTER(struct_bu_list)]
    nmg_eu_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2137
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_lu_to_vlist'):
    nmg_lu_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_lu_to_vlist
    nmg_lu_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_loopuse), c_int, vectp_t, POINTER(struct_bu_list)]
    nmg_lu_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2142
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_fu_to_vlist'):
    nmg_snurb_fu_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_fu_to_vlist
    nmg_snurb_fu_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_faceuse), c_int, POINTER(struct_bu_list)]
    nmg_snurb_fu_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2146
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_s_to_vlist'):
    nmg_s_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_s_to_vlist
    nmg_s_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_shell), c_int, POINTER(struct_bu_list)]
    nmg_s_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2150
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_r_to_vlist'):
    nmg_r_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_r_to_vlist
    nmg_r_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_nmgregion), c_int, POINTER(struct_bu_list)]
    nmg_r_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2154
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_m_to_vlist'):
    nmg_m_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_m_to_vlist
    nmg_m_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_model), c_int, POINTER(struct_bu_list)]
    nmg_m_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2158
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_offset_eu_vert'):
    nmg_offset_eu_vert = _libs['/opt/brlcad/lib/librt.dylib'].nmg_offset_eu_vert
    nmg_offset_eu_vert.argtypes = [point_t, POINTER(struct_edgeuse), vect_t, c_int]
    nmg_offset_eu_vert.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2201
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_v'):
    nmg_vlblock_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_v
    nmg_vlblock_v.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_vertex), POINTER(c_long), POINTER(struct_bu_list)]
    nmg_vlblock_v.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2205
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_e'):
    nmg_vlblock_e = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_e
    nmg_vlblock_e.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_edge), POINTER(c_long), c_int, c_int, c_int, POINTER(struct_bu_list)]
    nmg_vlblock_e.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2212
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_eu'):
    nmg_vlblock_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_eu
    nmg_vlblock_eu.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_edgeuse), POINTER(c_long), c_int, c_int, c_int, c_int, POINTER(struct_bu_list)]
    nmg_vlblock_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2220
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_euleft'):
    nmg_vlblock_euleft = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_euleft
    nmg_vlblock_euleft.argtypes = [POINTER(struct_bu_list), POINTER(struct_edgeuse), point_t, mat_t, vect_t, vect_t, c_double, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_vlblock_euleft.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2229
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_around_eu'):
    nmg_vlblock_around_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_around_eu
    nmg_vlblock_around_eu.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_edgeuse), POINTER(c_long), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_vlblock_around_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2235
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_lu'):
    nmg_vlblock_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_lu
    nmg_vlblock_lu.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_loopuse), POINTER(c_long), c_int, c_int, c_int, c_int, POINTER(struct_bu_list)]
    nmg_vlblock_lu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2243
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_fu'):
    nmg_vlblock_fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_fu
    nmg_vlblock_fu.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_faceuse), POINTER(c_long), c_int, POINTER(struct_bu_list)]
    nmg_vlblock_fu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2246
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_s'):
    nmg_vlblock_s = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_s
    nmg_vlblock_s.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_shell), c_int, POINTER(struct_bu_list)]
    nmg_vlblock_s.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2250
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_r'):
    nmg_vlblock_r = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_r
    nmg_vlblock_r.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_nmgregion), c_int, POINTER(struct_bu_list)]
    nmg_vlblock_r.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2254
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlblock_m'):
    nmg_vlblock_m = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlblock_m
    nmg_vlblock_m.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_model), c_int, POINTER(struct_bu_list)]
    nmg_vlblock_m.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2260
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pl_edges_in_2_shells'):
    nmg_pl_edges_in_2_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pl_edges_in_2_shells
    nmg_pl_edges_in_2_shells.argtypes = [POINTER(struct_bn_vlblock), POINTER(c_long), POINTER(struct_edgeuse), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_pl_edges_in_2_shells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2266
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pl_isect'):
    nmg_pl_isect = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pl_isect
    nmg_pl_isect.argtypes = [String, POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_pl_isect.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2270
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pl_comb_fu'):
    nmg_pl_comb_fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pl_comb_fu
    nmg_pl_comb_fu.argtypes = [c_int, c_int, POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_pl_comb_fu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2274
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pl_2fu'):
    nmg_pl_2fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pl_2fu
    nmg_pl_2fu.argtypes = [String, POINTER(struct_faceuse), POINTER(struct_faceuse), c_int, POINTER(struct_bu_list)]
    nmg_pl_2fu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2280
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_show_broken_classifier_stuff'):
    nmg_show_broken_classifier_stuff = _libs['/opt/brlcad/lib/librt.dylib'].nmg_show_broken_classifier_stuff
    nmg_show_broken_classifier_stuff.argtypes = [POINTER(c_uint32), POINTER(POINTER(c_char)), c_int, c_int, String, POINTER(struct_bu_list)]
    nmg_show_broken_classifier_stuff.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2286
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_plot'):
    nmg_face_plot = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_plot
    nmg_face_plot.argtypes = [POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_face_plot.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2287
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_2face_plot'):
    nmg_2face_plot = _libs['/opt/brlcad/lib/librt.dylib'].nmg_2face_plot
    nmg_2face_plot.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_2face_plot.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2290
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_lu_plot'):
    nmg_face_lu_plot = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_lu_plot
    nmg_face_lu_plot.argtypes = [POINTER(struct_loopuse), POINTER(struct_vertexuse), POINTER(struct_vertexuse), POINTER(struct_bu_list)]
    nmg_face_lu_plot.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2294
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_plot_lu_ray'):
    nmg_plot_lu_ray = _libs['/opt/brlcad/lib/librt.dylib'].nmg_plot_lu_ray
    nmg_plot_lu_ray.argtypes = [POINTER(struct_loopuse), POINTER(struct_vertexuse), POINTER(struct_vertexuse), vect_t, POINTER(struct_bu_list)]
    nmg_plot_lu_ray.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2299
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_plot_ray_face'):
    nmg_plot_ray_face = _libs['/opt/brlcad/lib/librt.dylib'].nmg_plot_ray_face
    nmg_plot_ray_face.argtypes = [String, point_t, vect_t, POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_plot_ray_face.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2304
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_plot_lu_around_eu'):
    nmg_plot_lu_around_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_plot_lu_around_eu
    nmg_plot_lu_around_eu.argtypes = [String, POINTER(struct_edgeuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_plot_lu_around_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2308
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_snurb_to_vlist'):
    nmg_snurb_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_snurb_to_vlist
    nmg_snurb_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_face_g_snurb), c_int, POINTER(struct_bu_list)]
    nmg_snurb_to_vlist.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2312
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cnurb_to_vlist'):
    nmg_cnurb_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cnurb_to_vlist
    nmg_cnurb_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_edgeuse), c_int, c_int, POINTER(struct_bu_list)]
    nmg_cnurb_to_vlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2321
try:
    nmg_eue_dist = (c_double).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eue_dist')
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 2325
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mesh_two_faces'):
    nmg_mesh_two_faces = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mesh_two_faces
    nmg_mesh_two_faces.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_mesh_two_faces.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2328
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_radial_join_eu'):
    nmg_radial_join_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_radial_join_eu
    nmg_radial_join_eu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_radial_join_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2331
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mesh_faces'):
    nmg_mesh_faces = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mesh_faces
    nmg_mesh_faces.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_mesh_faces.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2335
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mesh_face_shell'):
    nmg_mesh_face_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mesh_face_shell
    nmg_mesh_face_shell.argtypes = [POINTER(struct_faceuse), POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_mesh_face_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2338
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mesh_shell_shell'):
    nmg_mesh_shell_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mesh_shell_shell
    nmg_mesh_shell_shell.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_mesh_shell_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2342
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_measure_fu_angle'):
    nmg_measure_fu_angle = _libs['/opt/brlcad/lib/librt.dylib'].nmg_measure_fu_angle
    nmg_measure_fu_angle.argtypes = [POINTER(struct_edgeuse), vect_t, vect_t, vect_t]
    nmg_measure_fu_angle.restype = c_double

# /opt/brlcad/include/brlcad/nmg.h: 2348
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_do_bool'):
    nmg_do_bool = _libs['/opt/brlcad/lib/librt.dylib'].nmg_do_bool
    nmg_do_bool.argtypes = [POINTER(struct_nmgregion), POINTER(struct_nmgregion), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_do_bool.restype = POINTER(struct_nmgregion)

# /opt/brlcad/include/brlcad/nmg.h: 2351
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_two_region_vertex_fuse'):
        continue
    nmg_two_region_vertex_fuse = _lib.nmg_two_region_vertex_fuse
    nmg_two_region_vertex_fuse.argtypes = [POINTER(struct_nmgregion), POINTER(struct_nmgregion), POINTER(struct_bn_tol)]
    nmg_two_region_vertex_fuse.restype = c_int
    break

# /opt/brlcad/include/brlcad/nmg.h: 2357
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_class_shells'):
    nmg_class_shells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_class_shells
    nmg_class_shells.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(POINTER(c_char)), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_class_shells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2365
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_vu_ptbl'):
    nmg_ck_vu_ptbl = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_vu_ptbl
    nmg_ck_vu_ptbl.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_faceuse)]
    nmg_ck_vu_ptbl.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2367
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_vu_angle_measure'):
        continue
    nmg_vu_angle_measure = _lib.nmg_vu_angle_measure
    nmg_vu_angle_measure.argtypes = [POINTER(struct_vertexuse), vect_t, vect_t, c_int, c_int]
    nmg_vu_angle_measure.restype = c_double
    break

# /opt/brlcad/include/brlcad/nmg.h: 2372
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_wedge_class'):
        continue
    nmg_wedge_class = _lib.nmg_wedge_class
    nmg_wedge_class.argtypes = [c_int, c_double, c_double]
    nmg_wedge_class.restype = c_int
    break

# /opt/brlcad/include/brlcad/nmg.h: 2375
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_sanitize_fu'):
        continue
    nmg_sanitize_fu = _lib.nmg_sanitize_fu
    nmg_sanitize_fu.argtypes = [POINTER(struct_faceuse)]
    nmg_sanitize_fu.restype = None
    break

# /opt/brlcad/include/brlcad/nmg.h: 2376
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_unlist_v'):
        continue
    nmg_unlist_v = _lib.nmg_unlist_v
    nmg_unlist_v.argtypes = [POINTER(struct_bu_ptbl), POINTER(fastf_t), POINTER(struct_vertex)]
    nmg_unlist_v.restype = None
    break

# /opt/brlcad/include/brlcad/nmg.h: 2379
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_face_cutjoin'):
    nmg_face_cutjoin = _libs['/opt/brlcad/lib/librt.dylib'].nmg_face_cutjoin
    nmg_face_cutjoin.argtypes = [POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(fastf_t), POINTER(fastf_t), POINTER(struct_faceuse), POINTER(struct_faceuse), point_t, vect_t, POINTER(struct_edge_g_lseg), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_face_cutjoin.restype = POINTER(struct_edge_g_lseg)

# /opt/brlcad/include/brlcad/nmg.h: 2390
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_fcut_face_2d'):
    nmg_fcut_face_2d = _libs['/opt/brlcad/lib/librt.dylib'].nmg_fcut_face_2d
    nmg_fcut_face_2d.argtypes = [POINTER(struct_bu_ptbl), POINTER(fastf_t), POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_fcut_face_2d.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2396
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'nmg_insert_vu_if_on_edge'):
        continue
    nmg_insert_vu_if_on_edge = _lib.nmg_insert_vu_if_on_edge
    nmg_insert_vu_if_on_edge.argtypes = [POINTER(struct_vertexuse), POINTER(struct_vertexuse), POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_insert_vu_if_on_edge.restype = c_int
    break

# /opt/brlcad/include/brlcad/nmg.h: 2405
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_lu_orientation'):
    nmg_ck_lu_orientation = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_lu_orientation
    nmg_ck_lu_orientation.argtypes = [POINTER(struct_loopuse), POINTER(struct_bn_tol)]
    nmg_ck_lu_orientation.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2407
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_class_name'):
    nmg_class_name = _libs['/opt/brlcad/lib/librt.dylib'].nmg_class_name
    nmg_class_name.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        nmg_class_name.restype = ReturnString
    else:
        nmg_class_name.restype = String
        nmg_class_name.errcheck = ReturnString

# /opt/brlcad/include/brlcad/nmg.h: 2408
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_evaluate_boolean'):
    nmg_evaluate_boolean = _libs['/opt/brlcad/lib/librt.dylib'].nmg_evaluate_boolean
    nmg_evaluate_boolean.argtypes = [POINTER(struct_shell), POINTER(struct_shell), c_int, POINTER(POINTER(c_char)), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_evaluate_boolean.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2423
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vvg'):
    nmg_vvg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vvg
    nmg_vvg.argtypes = [POINTER(struct_vertex_g)]
    nmg_vvg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2424
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vvertex'):
    nmg_vvertex = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vvertex
    nmg_vvertex.argtypes = [POINTER(struct_vertex), POINTER(struct_vertexuse)]
    nmg_vvertex.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2426
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vvua'):
    nmg_vvua = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vvua
    nmg_vvua.argtypes = [POINTER(c_uint32)]
    nmg_vvua.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2427
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vvu'):
    nmg_vvu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vvu
    nmg_vvu.argtypes = [POINTER(struct_vertexuse), POINTER(c_uint32)]
    nmg_vvu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2429
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_veg'):
    nmg_veg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_veg
    nmg_veg.argtypes = [POINTER(c_uint32)]
    nmg_veg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2430
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vedge'):
    nmg_vedge = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vedge
    nmg_vedge.argtypes = [POINTER(struct_edge), POINTER(struct_edgeuse)]
    nmg_vedge.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2432
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_veu'):
    nmg_veu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_veu
    nmg_veu.argtypes = [POINTER(struct_bu_list), POINTER(c_uint32)]
    nmg_veu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2434
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlg'):
    nmg_vlg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlg
    nmg_vlg.argtypes = [POINTER(struct_loop_g)]
    nmg_vlg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2435
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vloop'):
    nmg_vloop = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vloop
    nmg_vloop.argtypes = [POINTER(struct_loop), POINTER(struct_loopuse)]
    nmg_vloop.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2437
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vlu'):
    nmg_vlu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vlu
    nmg_vlu.argtypes = [POINTER(struct_bu_list), POINTER(c_uint32)]
    nmg_vlu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2439
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vfg'):
    nmg_vfg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vfg
    nmg_vfg.argtypes = [POINTER(struct_face_g_plane)]
    nmg_vfg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2440
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vface'):
    nmg_vface = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vface
    nmg_vface.argtypes = [POINTER(struct_face), POINTER(struct_faceuse)]
    nmg_vface.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2442
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vfu'):
    nmg_vfu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vfu
    nmg_vfu.argtypes = [POINTER(struct_bu_list), POINTER(struct_shell)]
    nmg_vfu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2444
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vsshell'):
    nmg_vsshell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vsshell
    nmg_vsshell.argtypes = [POINTER(struct_shell), POINTER(struct_nmgregion)]
    nmg_vsshell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2446
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vshell'):
    nmg_vshell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vshell
    nmg_vshell.argtypes = [POINTER(struct_bu_list), POINTER(struct_nmgregion)]
    nmg_vshell.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2448
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vregion'):
    nmg_vregion = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vregion
    nmg_vregion.argtypes = [POINTER(struct_bu_list), POINTER(struct_model)]
    nmg_vregion.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2450
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vmodel'):
    nmg_vmodel = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vmodel
    nmg_vmodel.argtypes = [POINTER(struct_model)]
    nmg_vmodel.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2453
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_e'):
    nmg_ck_e = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_e
    nmg_ck_e.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edge), String]
    nmg_ck_e.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2456
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_vu'):
    nmg_ck_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_vu
    nmg_ck_vu.argtypes = [POINTER(c_uint32), POINTER(struct_vertexuse), String]
    nmg_ck_vu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2459
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_eu'):
    nmg_ck_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_eu
    nmg_ck_eu.argtypes = [POINTER(c_uint32), POINTER(struct_edgeuse), String]
    nmg_ck_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2462
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_lg'):
    nmg_ck_lg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_lg
    nmg_ck_lg.argtypes = [POINTER(struct_loop), POINTER(struct_loop_g), String]
    nmg_ck_lg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2465
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_l'):
    nmg_ck_l = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_l
    nmg_ck_l.argtypes = [POINTER(struct_loopuse), POINTER(struct_loop), String]
    nmg_ck_l.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2468
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_lu'):
    nmg_ck_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_lu
    nmg_ck_lu.argtypes = [POINTER(c_uint32), POINTER(struct_loopuse), String]
    nmg_ck_lu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2471
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_fg'):
    nmg_ck_fg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_fg
    nmg_ck_fg.argtypes = [POINTER(struct_face), POINTER(struct_face_g_plane), String]
    nmg_ck_fg.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2474
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_f'):
    nmg_ck_f = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_f
    nmg_ck_f.argtypes = [POINTER(struct_faceuse), POINTER(struct_face), String]
    nmg_ck_f.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2477
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_fu'):
    nmg_ck_fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_fu
    nmg_ck_fu.argtypes = [POINTER(struct_shell), POINTER(struct_faceuse), String]
    nmg_ck_fu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2480
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_eg_verts'):
    nmg_ck_eg_verts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_eg_verts
    nmg_ck_eg_verts.argtypes = [POINTER(struct_edge_g_lseg), POINTER(struct_bn_tol)]
    nmg_ck_eg_verts.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2482
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_geometry'):
    nmg_ck_geometry = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_geometry
    nmg_ck_geometry.argtypes = [POINTER(struct_model), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_ck_geometry.restype = c_size_t

# /opt/brlcad/include/brlcad/nmg.h: 2485
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_face_worthless_edges'):
    nmg_ck_face_worthless_edges = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_face_worthless_edges
    nmg_ck_face_worthless_edges.argtypes = [POINTER(struct_faceuse)]
    nmg_ck_face_worthless_edges.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2486
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_lueu'):
    nmg_ck_lueu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_lueu
    nmg_ck_lueu.argtypes = [POINTER(struct_loopuse), String]
    nmg_ck_lueu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2487
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_check_radial'):
    nmg_check_radial = _libs['/opt/brlcad/lib/librt.dylib'].nmg_check_radial
    nmg_check_radial.argtypes = [POINTER(struct_edgeuse), POINTER(struct_bn_tol)]
    nmg_check_radial.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2488
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_eu_2s_orient_bad'):
    nmg_eu_2s_orient_bad = _libs['/opt/brlcad/lib/librt.dylib'].nmg_eu_2s_orient_bad
    nmg_eu_2s_orient_bad.argtypes = [POINTER(struct_edgeuse), POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_eu_2s_orient_bad.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2492
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_closed_surf'):
    nmg_ck_closed_surf = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_closed_surf
    nmg_ck_closed_surf.argtypes = [POINTER(struct_shell), POINTER(struct_bn_tol)]
    nmg_ck_closed_surf.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2494
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_closed_region'):
    nmg_ck_closed_region = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_closed_region
    nmg_ck_closed_region.argtypes = [POINTER(struct_nmgregion), POINTER(struct_bn_tol)]
    nmg_ck_closed_region.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2496
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_v_in_2fus'):
    nmg_ck_v_in_2fus = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_v_in_2fus
    nmg_ck_v_in_2fus.argtypes = [POINTER(struct_vertex), POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_ck_v_in_2fus.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2500
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ck_vs_in_region'):
    nmg_ck_vs_in_region = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ck_vs_in_region
    nmg_ck_vs_in_region.argtypes = [POINTER(struct_nmgregion), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_ck_vs_in_region.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2506
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_make_dualvu'):
    nmg_make_dualvu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_make_dualvu
    nmg_make_dualvu.argtypes = [POINTER(struct_vertex), POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_make_dualvu.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 2509
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_enlist_vu'):
    nmg_enlist_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_enlist_vu
    nmg_enlist_vu.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_vertexuse), POINTER(struct_vertexuse), fastf_t]
    nmg_enlist_vu.restype = POINTER(struct_vertexuse)

# /opt/brlcad/include/brlcad/nmg.h: 2513
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect2d_prep'):
    nmg_isect2d_prep = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect2d_prep
    nmg_isect2d_prep.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(c_uint32)]
    nmg_isect2d_prep.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2515
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect2d_cleanup'):
    nmg_isect2d_cleanup = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect2d_cleanup
    nmg_isect2d_cleanup.argtypes = [POINTER(struct_nmg_inter_struct)]
    nmg_isect2d_cleanup.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2516
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect2d_final_cleanup'):
    nmg_isect2d_final_cleanup = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect2d_final_cleanup
    nmg_isect2d_final_cleanup.argtypes = []
    nmg_isect2d_final_cleanup.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2517
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_2faceuse'):
    nmg_isect_2faceuse = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_2faceuse
    nmg_isect_2faceuse.argtypes = [point_t, vect_t, POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bn_tol)]
    nmg_isect_2faceuse.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2522
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_vert2p_face2p'):
    nmg_isect_vert2p_face2p = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_vert2p_face2p
    nmg_isect_vert2p_face2p.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_vertexuse), POINTER(struct_faceuse)]
    nmg_isect_vert2p_face2p.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2525
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_eu_on_v'):
    nmg_break_eu_on_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_eu_on_v
    nmg_break_eu_on_v.argtypes = [POINTER(struct_edgeuse), POINTER(struct_vertex), POINTER(struct_faceuse), POINTER(struct_nmg_inter_struct)]
    nmg_break_eu_on_v.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 2529
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_break_eg_on_v'):
    nmg_break_eg_on_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_break_eg_on_v
    nmg_break_eg_on_v.argtypes = [POINTER(struct_edge_g_lseg), POINTER(struct_vertex), POINTER(struct_bn_tol)]
    nmg_break_eg_on_v.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2532
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_2colinear_edge2p'):
    nmg_isect_2colinear_edge2p = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_2colinear_edge2p
    nmg_isect_2colinear_edge2p.argtypes = [POINTER(struct_edgeuse), POINTER(struct_edgeuse), POINTER(struct_faceuse), POINTER(struct_nmg_inter_struct), POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl)]
    nmg_isect_2colinear_edge2p.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2538
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_edge2p_edge2p'):
    nmg_isect_edge2p_edge2p = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_edge2p_edge2p
    nmg_isect_edge2p_edge2p.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_edgeuse), POINTER(struct_edgeuse), POINTER(struct_faceuse), POINTER(struct_faceuse)]
    nmg_isect_edge2p_edge2p.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2543
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_construct_nice_ray'):
    nmg_isect_construct_nice_ray = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_construct_nice_ray
    nmg_isect_construct_nice_ray.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_faceuse)]
    nmg_isect_construct_nice_ray.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2545
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_enlist_one_vu'):
    nmg_enlist_one_vu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_enlist_one_vu
    nmg_enlist_one_vu.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_vertexuse), fastf_t]
    nmg_enlist_one_vu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2548
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_line2_edge2p'):
    nmg_isect_line2_edge2p = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_line2_edge2p
    nmg_isect_line2_edge2p.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_bu_ptbl), POINTER(struct_edgeuse), POINTER(struct_faceuse), POINTER(struct_faceuse)]
    nmg_isect_line2_edge2p.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2553
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_line2_vertex2'):
    nmg_isect_line2_vertex2 = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_line2_vertex2
    nmg_isect_line2_vertex2.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_vertexuse), POINTER(struct_faceuse)]
    nmg_isect_line2_vertex2.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2556
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_two_ptbls'):
    nmg_isect_two_ptbls = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_two_ptbls
    nmg_isect_two_ptbls.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl)]
    nmg_isect_two_ptbls.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2559
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eg_on_line'):
    nmg_find_eg_on_line = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eg_on_line
    nmg_find_eg_on_line.argtypes = [POINTER(c_uint32), point_t, vect_t, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_find_eg_on_line.restype = POINTER(struct_edge_g_lseg)

# /opt/brlcad/include/brlcad/nmg.h: 2564
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_k0eu'):
    nmg_k0eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_k0eu
    nmg_k0eu.argtypes = [POINTER(struct_vertex)]
    nmg_k0eu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2565
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_repair_v_near_v'):
    nmg_repair_v_near_v = _libs['/opt/brlcad/lib/librt.dylib'].nmg_repair_v_near_v
    nmg_repair_v_near_v.argtypes = [POINTER(struct_vertex), POINTER(struct_vertex), POINTER(struct_edge_g_lseg), POINTER(struct_edge_g_lseg), c_int, POINTER(struct_bn_tol)]
    nmg_repair_v_near_v.restype = POINTER(struct_vertex)

# /opt/brlcad/include/brlcad/nmg.h: 2571
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_search_v_eg'):
    nmg_search_v_eg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_search_v_eg
    nmg_search_v_eg.argtypes = [POINTER(struct_edgeuse), c_int, POINTER(struct_edge_g_lseg), POINTER(struct_edge_g_lseg), POINTER(struct_vertex), POINTER(struct_bn_tol)]
    nmg_search_v_eg.restype = POINTER(struct_vertex)

# /opt/brlcad/include/brlcad/nmg.h: 2577
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_common_v_2eg'):
    nmg_common_v_2eg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_common_v_2eg
    nmg_common_v_2eg.argtypes = [POINTER(struct_edge_g_lseg), POINTER(struct_edge_g_lseg), POINTER(struct_bn_tol)]
    nmg_common_v_2eg.restype = POINTER(struct_vertex)

# /opt/brlcad/include/brlcad/nmg.h: 2580
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_vertex_on_inter'):
    nmg_is_vertex_on_inter = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_vertex_on_inter
    nmg_is_vertex_on_inter.argtypes = [POINTER(struct_vertex), POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_nmg_inter_struct), POINTER(struct_bu_list)]
    nmg_is_vertex_on_inter.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2585
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_eu_verts'):
    nmg_isect_eu_verts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_eu_verts
    nmg_isect_eu_verts.argtypes = [POINTER(struct_edgeuse), POINTER(struct_vertex_g), POINTER(struct_vertex_g), POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_isect_eu_verts.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2591
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_eu_eu'):
    nmg_isect_eu_eu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_eu_eu
    nmg_isect_eu_eu.argtypes = [POINTER(struct_edgeuse), POINTER(struct_vertex_g), POINTER(struct_vertex_g), vect_t, POINTER(struct_edgeuse), POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(struct_bn_tol)]
    nmg_isect_eu_eu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2599
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_eu_fu'):
    nmg_isect_eu_fu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_eu_fu
    nmg_isect_eu_fu.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_bu_ptbl), POINTER(struct_edgeuse), POINTER(struct_faceuse), POINTER(struct_bu_list)]
    nmg_isect_eu_fu.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2604
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_fu_jra'):
    nmg_isect_fu_jra = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_fu_jra
    nmg_isect_fu_jra.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(struct_bu_list)]
    nmg_isect_fu_jra.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2610
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_line2_face2pNEW'):
    nmg_isect_line2_face2pNEW = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_line2_face2pNEW
    nmg_isect_line2_face2pNEW.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_ptbl), POINTER(struct_bu_ptbl), POINTER(struct_bu_list)]
    nmg_isect_line2_face2pNEW.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2615
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_is_eu_on_line3'):
    nmg_is_eu_on_line3 = _libs['/opt/brlcad/lib/librt.dylib'].nmg_is_eu_on_line3
    nmg_is_eu_on_line3.argtypes = [POINTER(struct_edgeuse), point_t, vect_t, POINTER(struct_bn_tol)]
    nmg_is_eu_on_line3.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2619
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_eg_between_2fg'):
    nmg_find_eg_between_2fg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_eg_between_2fg
    nmg_find_eg_between_2fg.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_find_eg_between_2fg.restype = POINTER(struct_edge_g_lseg)

# /opt/brlcad/include/brlcad/nmg.h: 2623
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_does_fu_use_eg'):
    nmg_does_fu_use_eg = _libs['/opt/brlcad/lib/librt.dylib'].nmg_does_fu_use_eg
    nmg_does_fu_use_eg.argtypes = [POINTER(struct_faceuse), POINTER(c_uint32)]
    nmg_does_fu_use_eg.restype = POINTER(struct_edgeuse)

# /opt/brlcad/include/brlcad/nmg.h: 2625
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_line_on_plane'):
    rt_line_on_plane = _libs['/opt/brlcad/lib/librt.dylib'].rt_line_on_plane
    rt_line_on_plane.argtypes = [point_t, vect_t, plane_t, POINTER(struct_bn_tol)]
    rt_line_on_plane.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2629
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_cut_lu_into_coplanar_and_non'):
    nmg_cut_lu_into_coplanar_and_non = _libs['/opt/brlcad/lib/librt.dylib'].nmg_cut_lu_into_coplanar_and_non
    nmg_cut_lu_into_coplanar_and_non.argtypes = [POINTER(struct_loopuse), plane_t, POINTER(struct_nmg_inter_struct), POINTER(struct_bu_list)]
    nmg_cut_lu_into_coplanar_and_non.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2633
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_check_radial_angles'):
    nmg_check_radial_angles = _libs['/opt/brlcad/lib/librt.dylib'].nmg_check_radial_angles
    nmg_check_radial_angles.argtypes = [String, POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_check_radial_angles.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2637
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_faces_can_be_intersected'):
    nmg_faces_can_be_intersected = _libs['/opt/brlcad/lib/librt.dylib'].nmg_faces_can_be_intersected
    nmg_faces_can_be_intersected.argtypes = [POINTER(struct_nmg_inter_struct), POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_faces_can_be_intersected.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2642
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_two_generic_faces'):
    nmg_isect_two_generic_faces = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_two_generic_faces
    nmg_isect_two_generic_faces.argtypes = [POINTER(struct_faceuse), POINTER(struct_faceuse), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_isect_two_generic_faces.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2646
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_crackshells'):
    nmg_crackshells = _libs['/opt/brlcad/lib/librt.dylib'].nmg_crackshells
    nmg_crackshells.argtypes = [POINTER(struct_shell), POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_crackshells.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2650
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_fu_touchingloops'):
    nmg_fu_touchingloops = _libs['/opt/brlcad/lib/librt.dylib'].nmg_fu_touchingloops
    nmg_fu_touchingloops.argtypes = [POINTER(struct_faceuse)]
    nmg_fu_touchingloops.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2654
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_index_of_struct'):
    nmg_index_of_struct = _libs['/opt/brlcad/lib/librt.dylib'].nmg_index_of_struct
    nmg_index_of_struct.argtypes = [POINTER(c_uint32)]
    nmg_index_of_struct.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2655
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_m_set_high_bit'):
    nmg_m_set_high_bit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_m_set_high_bit
    nmg_m_set_high_bit.argtypes = [POINTER(struct_model)]
    nmg_m_set_high_bit.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2656
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_m_reindex'):
    nmg_m_reindex = _libs['/opt/brlcad/lib/librt.dylib'].nmg_m_reindex
    nmg_m_reindex.argtypes = [POINTER(struct_model), c_long]
    nmg_m_reindex.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2657
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_vls_struct_counts'):
    nmg_vls_struct_counts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_vls_struct_counts
    nmg_vls_struct_counts.argtypes = [POINTER(struct_bu_vls), POINTER(struct_nmg_struct_counts)]
    nmg_vls_struct_counts.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2659
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_struct_counts'):
    nmg_pr_struct_counts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_struct_counts
    nmg_pr_struct_counts.argtypes = [POINTER(struct_nmg_struct_counts), String]
    nmg_pr_struct_counts.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2661
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_m_struct_count'):
    nmg_m_struct_count = _libs['/opt/brlcad/lib/librt.dylib'].nmg_m_struct_count
    nmg_m_struct_count.argtypes = [POINTER(struct_nmg_struct_counts), POINTER(struct_model)]
    nmg_m_struct_count.restype = POINTER(POINTER(c_uint32))

# /opt/brlcad/include/brlcad/nmg.h: 2663
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_pr_m_struct_counts'):
    nmg_pr_m_struct_counts = _libs['/opt/brlcad/lib/librt.dylib'].nmg_pr_m_struct_counts
    nmg_pr_m_struct_counts.argtypes = [POINTER(struct_model), String]
    nmg_pr_m_struct_counts.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2665
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_merge_models'):
    nmg_merge_models = _libs['/opt/brlcad/lib/librt.dylib'].nmg_merge_models
    nmg_merge_models.argtypes = [POINTER(struct_model), POINTER(struct_model)]
    nmg_merge_models.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2667
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_find_max_index'):
    nmg_find_max_index = _libs['/opt/brlcad/lib/librt.dylib'].nmg_find_max_index
    nmg_find_max_index.argtypes = [POINTER(struct_model)]
    nmg_find_max_index.restype = c_long

# /opt/brlcad/include/brlcad/nmg.h: 2670
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_rt_inout_str'):
    nmg_rt_inout_str = _libs['/opt/brlcad/lib/librt.dylib'].nmg_rt_inout_str
    nmg_rt_inout_str.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        nmg_rt_inout_str.restype = ReturnString
    else:
        nmg_rt_inout_str.restype = String
        nmg_rt_inout_str.errcheck = ReturnString

# /opt/brlcad/include/brlcad/nmg.h: 2672
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_rt_print_hitlist'):
    nmg_rt_print_hitlist = _libs['/opt/brlcad/lib/librt.dylib'].nmg_rt_print_hitlist
    nmg_rt_print_hitlist.argtypes = [POINTER(struct_bu_list)]
    nmg_rt_print_hitlist.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2674
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_rt_print_hitmiss'):
    nmg_rt_print_hitmiss = _libs['/opt/brlcad/lib/librt.dylib'].nmg_rt_print_hitmiss
    nmg_rt_print_hitmiss.argtypes = [POINTER(struct_nmg_hitmiss)]
    nmg_rt_print_hitmiss.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2676
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_class_ray_vs_shell'):
    nmg_class_ray_vs_shell = _libs['/opt/brlcad/lib/librt.dylib'].nmg_class_ray_vs_shell
    nmg_class_ray_vs_shell.argtypes = [POINTER(struct_nmg_ray), POINTER(struct_shell), c_int, POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_class_ray_vs_shell.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2682
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_isect_ray_model'):
    nmg_isect_ray_model = _libs['/opt/brlcad/lib/librt.dylib'].nmg_isect_ray_model
    nmg_isect_ray_model.argtypes = [POINTER(struct_nmg_ray_data), POINTER(struct_bu_list)]
    nmg_isect_ray_model.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2690
class struct_nmg_curvature(Structure):
    pass

struct_nmg_curvature.__slots__ = [
    'crv_pdir',
    'crv_c1',
    'crv_c2',
]
struct_nmg_curvature._fields_ = [
    ('crv_pdir', vect_t),
    ('crv_c1', fastf_t),
    ('crv_c2', fastf_t),
]

# /opt/brlcad/include/brlcad/nmg.h: 2697
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_basis_eval'):
    nmg_nurb_basis_eval = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_basis_eval
    nmg_nurb_basis_eval.argtypes = [POINTER(struct_knot_vector), c_int, c_int, fastf_t]
    nmg_nurb_basis_eval.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 2701
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_bezier'):
    nmg_nurb_bezier = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_bezier
    nmg_nurb_bezier.argtypes = [POINTER(struct_bu_list), POINTER(struct_face_g_snurb)]
    nmg_nurb_bezier.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2702
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_bez_check'):
    nmg_bez_check = _libs['/opt/brlcad/lib/librt.dylib'].nmg_bez_check
    nmg_bez_check.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_bez_check.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2703
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nurb_crv_is_bezier'):
    nurb_crv_is_bezier = _libs['/opt/brlcad/lib/librt.dylib'].nurb_crv_is_bezier
    nurb_crv_is_bezier.argtypes = [POINTER(struct_edge_g_cnurb)]
    nurb_crv_is_bezier.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2704
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nurb_c_to_bezier'):
    nurb_c_to_bezier = _libs['/opt/brlcad/lib/librt.dylib'].nurb_c_to_bezier
    nurb_c_to_bezier.argtypes = [POINTER(struct_bu_list), POINTER(struct_edge_g_cnurb)]
    nurb_c_to_bezier.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2707
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_bound'):
    nmg_nurb_s_bound = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_bound
    nmg_nurb_s_bound.argtypes = [POINTER(struct_face_g_snurb), point_t, point_t]
    nmg_nurb_s_bound.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2708
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_bound'):
    nmg_nurb_c_bound = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_bound
    nmg_nurb_c_bound.argtypes = [POINTER(struct_edge_g_cnurb), point_t, point_t]
    nmg_nurb_c_bound.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2709
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_check'):
    nmg_nurb_s_check = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_check
    nmg_nurb_s_check.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_nurb_s_check.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2710
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_check'):
    nmg_nurb_c_check = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_check
    nmg_nurb_c_check.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_nurb_c_check.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2713
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_scopy'):
    nmg_nurb_scopy = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_scopy
    nmg_nurb_scopy.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_nurb_scopy.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2714
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_crv_copy'):
    nmg_nurb_crv_copy = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_crv_copy
    nmg_nurb_crv_copy.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_nurb_crv_copy.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 2717
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_diff'):
    nmg_nurb_s_diff = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_diff
    nmg_nurb_s_diff.argtypes = [POINTER(struct_face_g_snurb), c_int]
    nmg_nurb_s_diff.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2718
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_diff'):
    nmg_nurb_c_diff = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_diff
    nmg_nurb_c_diff.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_nurb_c_diff.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 2719
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_mesh_diff'):
    nmg_nurb_mesh_diff = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_mesh_diff
    nmg_nurb_mesh_diff.argtypes = [c_int, POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), c_int, c_int, c_int, c_int]
    nmg_nurb_mesh_diff.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2725
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_eval'):
    nmg_nurb_s_eval = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_eval
    nmg_nurb_s_eval.argtypes = [POINTER(struct_face_g_snurb), fastf_t, fastf_t, POINTER(fastf_t)]
    nmg_nurb_s_eval.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2726
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_eval'):
    nmg_nurb_c_eval = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_eval
    nmg_nurb_c_eval.argtypes = [POINTER(struct_edge_g_cnurb), fastf_t, POINTER(fastf_t)]
    nmg_nurb_c_eval.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2727
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_eval_crv'):
    nmg_nurb_eval_crv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_eval_crv
    nmg_nurb_eval_crv.argtypes = [POINTER(fastf_t), c_int, fastf_t, POINTER(struct_knot_vector), c_int, c_int]
    nmg_nurb_eval_crv.restype = POINTER(fastf_t)

# /opt/brlcad/include/brlcad/nmg.h: 2730
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_pr_crv'):
    nmg_nurb_pr_crv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_pr_crv
    nmg_nurb_pr_crv.argtypes = [POINTER(fastf_t), c_int, c_int]
    nmg_nurb_pr_crv.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2733
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_flat'):
    nmg_nurb_s_flat = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_flat
    nmg_nurb_s_flat.argtypes = [POINTER(struct_face_g_snurb), fastf_t]
    nmg_nurb_s_flat.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2734
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_crv_flat'):
    nmg_nurb_crv_flat = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_crv_flat
    nmg_nurb_crv_flat.argtypes = [POINTER(fastf_t), c_int, c_int]
    nmg_nurb_crv_flat.restype = fastf_t

# /opt/brlcad/include/brlcad/nmg.h: 2737
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvknot'):
    nmg_nurb_kvknot = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvknot
    nmg_nurb_kvknot.argtypes = [POINTER(struct_knot_vector), c_int, fastf_t, fastf_t, c_int]
    nmg_nurb_kvknot.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2739
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvmult'):
    nmg_nurb_kvmult = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvmult
    nmg_nurb_kvmult.argtypes = [POINTER(struct_knot_vector), POINTER(struct_knot_vector), c_int, fastf_t]
    nmg_nurb_kvmult.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2742
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvgen'):
    nmg_nurb_kvgen = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvgen
    nmg_nurb_kvgen.argtypes = [POINTER(struct_knot_vector), fastf_t, fastf_t, c_int]
    nmg_nurb_kvgen.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2744
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvmerge'):
    nmg_nurb_kvmerge = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvmerge
    nmg_nurb_kvmerge.argtypes = [POINTER(struct_knot_vector), POINTER(struct_knot_vector), POINTER(struct_knot_vector)]
    nmg_nurb_kvmerge.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2747
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvcheck'):
    nmg_nurb_kvcheck = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvcheck
    nmg_nurb_kvcheck.argtypes = [fastf_t, POINTER(struct_knot_vector)]
    nmg_nurb_kvcheck.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2748
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvextract'):
    nmg_nurb_kvextract = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvextract
    nmg_nurb_kvextract.argtypes = [POINTER(struct_knot_vector), POINTER(struct_knot_vector), c_int, c_int]
    nmg_nurb_kvextract.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2751
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvcopy'):
    nmg_nurb_kvcopy = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvcopy
    nmg_nurb_kvcopy.argtypes = [POINTER(struct_knot_vector), POINTER(struct_knot_vector)]
    nmg_nurb_kvcopy.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2753
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_kvnorm'):
    nmg_nurb_kvnorm = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_kvnorm
    nmg_nurb_kvnorm.argtypes = [POINTER(struct_knot_vector)]
    nmg_nurb_kvnorm.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2754
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_knot_index'):
    nmg_nurb_knot_index = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_knot_index
    nmg_nurb_knot_index.argtypes = [POINTER(struct_knot_vector), fastf_t, c_int]
    nmg_nurb_knot_index.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2755
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_gen_knot_vector'):
    nmg_nurb_gen_knot_vector = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_gen_knot_vector
    nmg_nurb_gen_knot_vector.argtypes = [POINTER(struct_knot_vector), c_int, fastf_t, fastf_t]
    nmg_nurb_gen_knot_vector.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2759
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_norm'):
    nmg_nurb_s_norm = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_norm
    nmg_nurb_s_norm.argtypes = [POINTER(struct_face_g_snurb), fastf_t, fastf_t, POINTER(fastf_t)]
    nmg_nurb_s_norm.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2762
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_curvature'):
    nmg_nurb_curvature = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_curvature
    nmg_nurb_curvature.argtypes = [POINTER(struct_nmg_curvature), POINTER(struct_face_g_snurb), fastf_t, fastf_t]
    nmg_nurb_curvature.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2768
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_plot'):
    nmg_nurb_s_plot = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_plot
    nmg_nurb_s_plot.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_nurb_s_plot.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2771
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_cinterp'):
    nmg_nurb_cinterp = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_cinterp
    nmg_nurb_cinterp.argtypes = [POINTER(struct_edge_g_cnurb), c_int, POINTER(fastf_t), c_int]
    nmg_nurb_cinterp.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2773
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_sinterp'):
    nmg_nurb_sinterp = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_sinterp
    nmg_nurb_sinterp.argtypes = [POINTER(struct_face_g_snurb), c_int, POINTER(fastf_t), c_int, c_int]
    nmg_nurb_sinterp.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2777
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_to_poly'):
    nmg_nurb_to_poly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_to_poly
    nmg_nurb_to_poly.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_nurb_to_poly.restype = POINTER(struct_nmg_nurb_poly)

# /opt/brlcad/include/brlcad/nmg.h: 2778
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_mk_poly'):
    nmg_nurb_mk_poly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_mk_poly
    nmg_nurb_mk_poly.argtypes = [POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), fastf_t * 2, fastf_t * 2, fastf_t * 2]
    nmg_nurb_mk_poly.restype = POINTER(struct_nmg_nurb_poly)

# /opt/brlcad/include/brlcad/nmg.h: 2782
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_project_srf'):
    nmg_nurb_project_srf = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_project_srf
    nmg_nurb_project_srf.argtypes = [POINTER(struct_face_g_snurb), plane_t, plane_t]
    nmg_nurb_project_srf.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2784
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_clip_srf'):
    nmg_nurb_clip_srf = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_clip_srf
    nmg_nurb_clip_srf.argtypes = [POINTER(struct_face_g_snurb), c_int, POINTER(fastf_t), POINTER(fastf_t)]
    nmg_nurb_clip_srf.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2786
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_region_from_srf'):
    nmg_nurb_region_from_srf = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_region_from_srf
    nmg_nurb_region_from_srf.argtypes = [POINTER(struct_face_g_snurb), c_int, fastf_t, fastf_t]
    nmg_nurb_region_from_srf.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2788
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_intersect'):
    nmg_nurb_intersect = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_intersect
    nmg_nurb_intersect.argtypes = [POINTER(struct_face_g_snurb), plane_t, plane_t, c_double, POINTER(struct_bu_list)]
    nmg_nurb_intersect.restype = POINTER(struct_nmg_nurb_uv_hit)

# /opt/brlcad/include/brlcad/nmg.h: 2792
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_refine'):
    nmg_nurb_s_refine = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_refine
    nmg_nurb_s_refine.argtypes = [POINTER(struct_face_g_snurb), c_int, POINTER(struct_knot_vector)]
    nmg_nurb_s_refine.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2794
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_refine'):
    nmg_nurb_c_refine = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_refine
    nmg_nurb_c_refine.argtypes = [POINTER(struct_edge_g_cnurb), POINTER(struct_knot_vector)]
    nmg_nurb_c_refine.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 2798
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_solve'):
    nmg_nurb_solve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_solve
    nmg_nurb_solve.argtypes = [POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), c_int, c_int]
    nmg_nurb_solve.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2800
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_doolittle'):
    nmg_nurb_doolittle = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_doolittle
    nmg_nurb_doolittle.argtypes = [POINTER(fastf_t), POINTER(fastf_t), c_int, c_int]
    nmg_nurb_doolittle.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2802
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_forw_solve'):
    nmg_nurb_forw_solve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_forw_solve
    nmg_nurb_forw_solve.argtypes = [POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), c_int]
    nmg_nurb_forw_solve.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2804
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_back_solve'):
    nmg_nurb_back_solve = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_back_solve
    nmg_nurb_back_solve.argtypes = [POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), c_int]
    nmg_nurb_back_solve.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2806
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_p_mat'):
    nmg_nurb_p_mat = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_p_mat
    nmg_nurb_p_mat.argtypes = [POINTER(fastf_t), c_int]
    nmg_nurb_p_mat.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2809
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_split'):
    nmg_nurb_s_split = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_split
    nmg_nurb_s_split.argtypes = [POINTER(struct_bu_list), POINTER(struct_face_g_snurb), c_int]
    nmg_nurb_s_split.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2811
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_split'):
    nmg_nurb_c_split = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_split
    nmg_nurb_c_split.argtypes = [POINTER(struct_bu_list), POINTER(struct_edge_g_cnurb)]
    nmg_nurb_c_split.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2814
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_uv_in_lu'):
    nmg_uv_in_lu = _libs['/opt/brlcad/lib/librt.dylib'].nmg_uv_in_lu
    nmg_uv_in_lu.argtypes = [fastf_t, fastf_t, POINTER(struct_loopuse)]
    nmg_uv_in_lu.restype = c_int

# /opt/brlcad/include/brlcad/nmg.h: 2817
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_new_snurb'):
    nmg_nurb_new_snurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_new_snurb
    nmg_nurb_new_snurb.argtypes = [c_int, c_int, c_int, c_int, c_int, c_int, c_int]
    nmg_nurb_new_snurb.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2820
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_new_cnurb'):
    nmg_nurb_new_cnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_new_cnurb
    nmg_nurb_new_cnurb.argtypes = [c_int, c_int, c_int, c_int]
    nmg_nurb_new_cnurb.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 2822
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_free_snurb'):
    nmg_nurb_free_snurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_free_snurb
    nmg_nurb_free_snurb.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_nurb_free_snurb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2823
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_free_cnurb'):
    nmg_nurb_free_cnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_free_cnurb
    nmg_nurb_free_cnurb.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_nurb_free_cnurb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2824
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_print'):
    nmg_nurb_c_print = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_print
    nmg_nurb_c_print.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_nurb_c_print.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2825
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_print'):
    nmg_nurb_s_print = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_print
    nmg_nurb_s_print.argtypes = [String, POINTER(struct_face_g_snurb)]
    nmg_nurb_s_print.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2826
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_pr_kv'):
    nmg_nurb_pr_kv = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_pr_kv
    nmg_nurb_pr_kv.argtypes = [POINTER(struct_knot_vector)]
    nmg_nurb_pr_kv.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2827
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_pr_mesh'):
    nmg_nurb_pr_mesh = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_pr_mesh
    nmg_nurb_pr_mesh.argtypes = [POINTER(struct_face_g_snurb)]
    nmg_nurb_pr_mesh.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2828
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_print_pt_type'):
    nmg_nurb_print_pt_type = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_print_pt_type
    nmg_nurb_print_pt_type.argtypes = [c_int]
    nmg_nurb_print_pt_type.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2829
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_clean_cnurb'):
    nmg_nurb_clean_cnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_clean_cnurb
    nmg_nurb_clean_cnurb.argtypes = [POINTER(struct_edge_g_cnurb)]
    nmg_nurb_clean_cnurb.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2832
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_s_xsplit'):
    nmg_nurb_s_xsplit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_s_xsplit
    nmg_nurb_s_xsplit.argtypes = [POINTER(struct_face_g_snurb), fastf_t, c_int]
    nmg_nurb_s_xsplit.restype = POINTER(struct_face_g_snurb)

# /opt/brlcad/include/brlcad/nmg.h: 2834
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_c_xsplit'):
    nmg_nurb_c_xsplit = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_c_xsplit
    nmg_nurb_c_xsplit.argtypes = [POINTER(struct_edge_g_cnurb), fastf_t]
    nmg_nurb_c_xsplit.restype = POINTER(struct_edge_g_cnurb)

# /opt/brlcad/include/brlcad/nmg.h: 2837
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_calc_oslo'):
    nmg_nurb_calc_oslo = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_calc_oslo
    nmg_nurb_calc_oslo.argtypes = [c_int, POINTER(struct_knot_vector), POINTER(struct_knot_vector)]
    nmg_nurb_calc_oslo.restype = POINTER(struct_oslo_mat)

# /opt/brlcad/include/brlcad/nmg.h: 2840
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_pr_oslo'):
    nmg_nurb_pr_oslo = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_pr_oslo
    nmg_nurb_pr_oslo.argtypes = [POINTER(struct_oslo_mat)]
    nmg_nurb_pr_oslo.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2841
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_free_oslo'):
    nmg_nurb_free_oslo = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_free_oslo
    nmg_nurb_free_oslo.argtypes = [POINTER(struct_oslo_mat)]
    nmg_nurb_free_oslo.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2844
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_nurb_map_oslo'):
    nmg_nurb_map_oslo = _libs['/opt/brlcad/lib/librt.dylib'].nmg_nurb_map_oslo
    nmg_nurb_map_oslo.argtypes = [POINTER(struct_oslo_mat), POINTER(fastf_t), POINTER(fastf_t), c_int, c_int, c_int, c_int, c_int]
    nmg_nurb_map_oslo.restype = None

# /opt/brlcad/include/brlcad/nmg.h: 2850
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_cnurb_par_edge'):
    rt_cnurb_par_edge = _libs['/opt/brlcad/lib/librt.dylib'].rt_cnurb_par_edge
    rt_cnurb_par_edge.argtypes = [POINTER(struct_edge_g_cnurb), fastf_t]
    rt_cnurb_par_edge.restype = fastf_t

# /opt/brlcad/include/brlcad/pc.h: 85
class union_anon_82(Union):
    pass

union_anon_82.__slots__ = [
    'expression',
    'ptr',
]
union_anon_82._fields_ = [
    ('expression', struct_bu_vls),
    ('ptr', POINTER(None)),
]

# /opt/brlcad/include/brlcad/pc.h: 77
class struct_pc_param(Structure):
    pass

struct_pc_param.__slots__ = [
    'l',
    'name',
    'ctype',
    'dtype',
    'data',
]
struct_pc_param._fields_ = [
    ('l', struct_bu_list),
    ('name', struct_bu_vls),
    ('ctype', c_int),
    ('dtype', c_int),
    ('data', union_anon_82),
]

# /opt/brlcad/include/brlcad/pc.h: 91
class struct_pc_constraint_fp(Structure):
    pass

struct_pc_constraint_fp.__slots__ = [
    'nargs',
    'dimension',
    'fp',
]
struct_pc_constraint_fp._fields_ = [
    ('nargs', c_int),
    ('dimension', c_int),
    ('fp', CFUNCTYPE(UNCHECKED(c_int), POINTER(POINTER(c_double)))),
]

# /opt/brlcad/include/brlcad/pc.h: 101
class union_anon_83(Union):
    pass

union_anon_83.__slots__ = [
    'expression',
    'cf',
]
union_anon_83._fields_ = [
    ('expression', struct_bu_vls),
    ('cf', struct_pc_constraint_fp),
]

# /opt/brlcad/include/brlcad/pc.h: 97
class struct_pc_constrnt(Structure):
    pass

struct_pc_constrnt.__slots__ = [
    'l',
    'name',
    'ctype',
    'data',
    'args',
]
struct_pc_constrnt._fields_ = [
    ('l', struct_bu_list),
    ('name', struct_bu_vls),
    ('ctype', c_int),
    ('data', union_anon_83),
    ('args', POINTER(POINTER(c_char))),
]

# /opt/brlcad/include/brlcad/pc.h: 108
class struct_pc_pc_set(Structure):
    pass

struct_pc_pc_set.__slots__ = [
    'ps',
    'cs',
]
struct_pc_pc_set._fields_ = [
    ('ps', POINTER(struct_pc_param)),
    ('cs', POINTER(struct_pc_constrnt)),
]

# /opt/brlcad/include/brlcad/bu/color.h: 52
class struct_bu_color(Structure):
    pass

struct_bu_color.__slots__ = [
    'buc_magic',
    'buc_rgb',
]
struct_bu_color._fields_ = [
    ('buc_magic', c_uint32),
    ('buc_rgb', fastf_t * 3),
]

# /opt/brlcad/include/brlcad/brep/defines.h: 54
class struct__on_brep_placeholder(Structure):
    pass

struct__on_brep_placeholder.__slots__ = [
    'dummy',
]
struct__on_brep_placeholder._fields_ = [
    ('dummy', c_int),
]

ON_Brep = struct__on_brep_placeholder # /opt/brlcad/include/brlcad/brep/defines.h: 54

# /opt/brlcad/include/brlcad/./rt/geom.h: 59
class struct_rt_tor_internal(Structure):
    pass

struct_rt_tor_internal.__slots__ = [
    'magic',
    'v',
    'h',
    'r_h',
    'r_a',
    'a',
    'b',
    'r_b',
]
struct_rt_tor_internal._fields_ = [
    ('magic', c_uint32),
    ('v', point_t),
    ('h', vect_t),
    ('r_h', fastf_t),
    ('r_a', fastf_t),
    ('a', vect_t),
    ('b', vect_t),
    ('r_b', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 78
class struct_rt_tgc_internal(Structure):
    pass

struct_rt_tgc_internal.__slots__ = [
    'magic',
    'v',
    'h',
    'a',
    'b',
    'c',
    'd',
]
struct_rt_tgc_internal._fields_ = [
    ('magic', c_uint32),
    ('v', point_t),
    ('h', vect_t),
    ('a', vect_t),
    ('b', vect_t),
    ('c', vect_t),
    ('d', vect_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 95
class struct_rt_ell_internal(Structure):
    pass

struct_rt_ell_internal.__slots__ = [
    'magic',
    'v',
    'a',
    'b',
    'c',
]
struct_rt_ell_internal._fields_ = [
    ('magic', c_uint32),
    ('v', point_t),
    ('a', vect_t),
    ('b', vect_t),
    ('c', vect_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 110
class struct_rt_superell_internal(Structure):
    pass

struct_rt_superell_internal.__slots__ = [
    'magic',
    'v',
    'a',
    'b',
    'c',
    'n',
    'e',
]
struct_rt_superell_internal._fields_ = [
    ('magic', c_uint32),
    ('v', point_t),
    ('a', vect_t),
    ('b', vect_t),
    ('c', vect_t),
    ('n', c_double),
    ('e', c_double),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 155
class struct_rt_metaball_internal(Structure):
    pass

struct_rt_metaball_internal.__slots__ = [
    'magic',
    'method',
    'threshold',
    'initstep',
    'finalstep',
    'metaball_ctrl_head',
]
struct_rt_metaball_internal._fields_ = [
    ('magic', c_uint32),
    ('method', c_int),
    ('threshold', fastf_t),
    ('initstep', fastf_t),
    ('finalstep', fastf_t),
    ('metaball_ctrl_head', struct_bu_list),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 168
class struct_wdb_metaballpt(Structure):
    pass

struct_wdb_metaballpt.__slots__ = [
    'l',
    'type',
    'fldstr',
    'sweat',
    'coord',
    'coord2',
]
struct_wdb_metaballpt._fields_ = [
    ('l', struct_bu_list),
    ('type', c_int),
    ('fldstr', fastf_t),
    ('sweat', fastf_t),
    ('coord', point_t),
    ('coord2', point_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 190
class struct_rt_arb_internal(Structure):
    pass

struct_rt_arb_internal.__slots__ = [
    'magic',
    'pt',
]
struct_rt_arb_internal._fields_ = [
    ('magic', c_uint32),
    ('pt', point_t * 8),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 202
class struct_rt_ars_internal(Structure):
    pass

struct_rt_ars_internal.__slots__ = [
    'magic',
    'ncurves',
    'pts_per_curve',
    'curves',
]
struct_rt_ars_internal._fields_ = [
    ('magic', c_uint32),
    ('ncurves', c_size_t),
    ('pts_per_curve', c_size_t),
    ('curves', POINTER(POINTER(fastf_t))),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 216
class struct_rt_half_internal(Structure):
    pass

struct_rt_half_internal.__slots__ = [
    'magic',
    'eqn',
]
struct_rt_half_internal._fields_ = [
    ('magic', c_uint32),
    ('eqn', plane_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 228
class struct_rt_grip_internal(Structure):
    pass

struct_rt_grip_internal.__slots__ = [
    'magic',
    'center',
    'normal',
    'mag',
]
struct_rt_grip_internal._fields_ = [
    ('magic', c_uint32),
    ('center', point_t),
    ('normal', vect_t),
    ('mag', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 243
class struct_rt_joint_internal(Structure):
    pass

struct_rt_joint_internal.__slots__ = [
    'magic',
    'location',
    'reference_path_1',
    'reference_path_2',
    'vector1',
    'vector2',
    'value',
]
struct_rt_joint_internal._fields_ = [
    ('magic', c_uint32),
    ('location', point_t),
    ('reference_path_1', struct_bu_vls),
    ('reference_path_2', struct_bu_vls),
    ('vector1', vect_t),
    ('vector2', vect_t),
    ('value', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 262
class struct_rt_pg_face_internal(Structure):
    pass

struct_rt_pg_face_internal.__slots__ = [
    'npts',
    'verts',
    'norms',
]
struct_rt_pg_face_internal._fields_ = [
    ('npts', c_size_t),
    ('verts', POINTER(fastf_t)),
    ('norms', POINTER(fastf_t)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 267
class struct_rt_pg_internal(Structure):
    pass

struct_rt_pg_internal.__slots__ = [
    'magic',
    'npoly',
    'poly',
    'max_npts',
]
struct_rt_pg_internal._fields_ = [
    ('magic', c_uint32),
    ('npoly', c_size_t),
    ('poly', POINTER(struct_rt_pg_face_internal)),
    ('max_npts', c_size_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 280
class struct_rt_nurb_internal(Structure):
    pass

struct_rt_nurb_internal.__slots__ = [
    'magic',
    'nsrf',
    'srfs',
    'brep',
]
struct_rt_nurb_internal._fields_ = [
    ('magic', c_uint32),
    ('nsrf', c_int),
    ('srfs', POINTER(POINTER(struct_face_g_snurb))),
    ('brep', POINTER(ON_Brep)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 296
class struct_rt_brep_internal(Structure):
    pass

struct_rt_brep_internal.__slots__ = [
    'magic',
    'brep',
]
struct_rt_brep_internal._fields_ = [
    ('magic', c_uint32),
    ('brep', POINTER(ON_Brep)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 322
class struct_rt_ebm_internal(Structure):
    pass

struct_rt_ebm_internal.__slots__ = [
    'magic',
    'file',
    'xdim',
    'ydim',
    'tallness',
    'mat',
    'mp',
]
struct_rt_ebm_internal._fields_ = [
    ('magic', c_uint32),
    ('file', c_char * 256),
    ('xdim', c_uint32),
    ('ydim', c_uint32),
    ('tallness', fastf_t),
    ('mat', mat_t),
    ('mp', POINTER(struct_bu_mapped_file)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 344
class struct_rt_vol_internal(Structure):
    pass

struct_rt_vol_internal.__slots__ = [
    'magic',
    'file',
    'xdim',
    'ydim',
    'zdim',
    'lo',
    'hi',
    'cellsize',
    'mat',
    'map',
]
struct_rt_vol_internal._fields_ = [
    ('magic', c_uint32),
    ('file', c_char * 128),
    ('xdim', c_uint32),
    ('ydim', c_uint32),
    ('zdim', c_uint32),
    ('lo', c_uint32),
    ('hi', c_uint32),
    ('cellsize', vect_t),
    ('mat', mat_t),
    ('map', POINTER(c_ubyte)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 368
class struct_rt_hf_internal(Structure):
    pass

struct_rt_hf_internal.__slots__ = [
    'magic',
    'cfile',
    'dfile',
    'fmt',
    'w',
    'n',
    'shorts',
    'file2mm',
    'v',
    'x',
    'y',
    'xlen',
    'ylen',
    'zscale',
    'mp',
]
struct_rt_hf_internal._fields_ = [
    ('magic', c_uint32),
    ('cfile', c_char * 128),
    ('dfile', c_char * 128),
    ('fmt', c_char * 8),
    ('w', c_uint32),
    ('n', c_uint32),
    ('shorts', c_uint32),
    ('file2mm', fastf_t),
    ('v', vect_t),
    ('x', vect_t),
    ('y', vect_t),
    ('xlen', fastf_t),
    ('ylen', fastf_t),
    ('zscale', fastf_t),
    ('mp', POINTER(struct_bu_mapped_file)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 398
class struct_rt_arbn_internal(Structure):
    pass

struct_rt_arbn_internal.__slots__ = [
    'magic',
    'neqn',
    'eqn',
]
struct_rt_arbn_internal._fields_ = [
    ('magic', c_uint32),
    ('neqn', c_size_t),
    ('eqn', POINTER(plane_t)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 411
class struct_rt_pipe_internal(Structure):
    pass

struct_rt_pipe_internal.__slots__ = [
    'pipe_magic',
    'pipe_segs_head',
    'pipe_count',
]
struct_rt_pipe_internal._fields_ = [
    ('pipe_magic', c_uint32),
    ('pipe_segs_head', struct_bu_list),
    ('pipe_count', c_int),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 418
class struct_wdb_pipept(Structure):
    pass

struct_wdb_pipept.__slots__ = [
    'l',
    'pp_coord',
    'pp_id',
    'pp_od',
    'pp_bendradius',
]
struct_wdb_pipept._fields_ = [
    ('l', struct_bu_list),
    ('pp_coord', point_t),
    ('pp_id', fastf_t),
    ('pp_od', fastf_t),
    ('pp_bendradius', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 433
class struct_rt_part_internal(Structure):
    pass

struct_rt_part_internal.__slots__ = [
    'part_magic',
    'part_V',
    'part_H',
    'part_vrad',
    'part_hrad',
    'part_type',
]
struct_rt_part_internal._fields_ = [
    ('part_magic', c_uint32),
    ('part_V', point_t),
    ('part_H', vect_t),
    ('part_vrad', fastf_t),
    ('part_hrad', fastf_t),
    ('part_type', c_int),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 454
class struct_rt_rpc_internal(Structure):
    pass

struct_rt_rpc_internal.__slots__ = [
    'rpc_magic',
    'rpc_V',
    'rpc_H',
    'rpc_B',
    'rpc_r',
]
struct_rt_rpc_internal._fields_ = [
    ('rpc_magic', c_uint32),
    ('rpc_V', point_t),
    ('rpc_H', vect_t),
    ('rpc_B', vect_t),
    ('rpc_r', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 469
class struct_rt_rhc_internal(Structure):
    pass

struct_rt_rhc_internal.__slots__ = [
    'rhc_magic',
    'rhc_V',
    'rhc_H',
    'rhc_B',
    'rhc_r',
    'rhc_c',
]
struct_rt_rhc_internal._fields_ = [
    ('rhc_magic', c_uint32),
    ('rhc_V', point_t),
    ('rhc_H', vect_t),
    ('rhc_B', vect_t),
    ('rhc_r', fastf_t),
    ('rhc_c', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 485
class struct_rt_epa_internal(Structure):
    pass

struct_rt_epa_internal.__slots__ = [
    'epa_magic',
    'epa_V',
    'epa_H',
    'epa_Au',
    'epa_r1',
    'epa_r2',
]
struct_rt_epa_internal._fields_ = [
    ('epa_magic', c_uint32),
    ('epa_V', point_t),
    ('epa_H', vect_t),
    ('epa_Au', vect_t),
    ('epa_r1', fastf_t),
    ('epa_r2', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 501
class struct_rt_ehy_internal(Structure):
    pass

struct_rt_ehy_internal.__slots__ = [
    'ehy_magic',
    'ehy_V',
    'ehy_H',
    'ehy_Au',
    'ehy_r1',
    'ehy_r2',
    'ehy_c',
]
struct_rt_ehy_internal._fields_ = [
    ('ehy_magic', c_uint32),
    ('ehy_V', point_t),
    ('ehy_H', vect_t),
    ('ehy_Au', vect_t),
    ('ehy_r1', fastf_t),
    ('ehy_r2', fastf_t),
    ('ehy_c', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 518
class struct_rt_hyp_internal(Structure):
    pass

struct_rt_hyp_internal.__slots__ = [
    'hyp_magic',
    'hyp_Vi',
    'hyp_Hi',
    'hyp_A',
    'hyp_b',
    'hyp_bnr',
]
struct_rt_hyp_internal._fields_ = [
    ('hyp_magic', c_uint32),
    ('hyp_Vi', point_t),
    ('hyp_Hi', vect_t),
    ('hyp_A', vect_t),
    ('hyp_b', fastf_t),
    ('hyp_bnr', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 534
class struct_rt_eto_internal(Structure):
    pass

struct_rt_eto_internal.__slots__ = [
    'eto_magic',
    'eto_V',
    'eto_N',
    'eto_C',
    'eto_r',
    'eto_rd',
]
struct_rt_eto_internal._fields_ = [
    ('eto_magic', c_uint32),
    ('eto_V', point_t),
    ('eto_N', vect_t),
    ('eto_C', vect_t),
    ('eto_r', fastf_t),
    ('eto_rd', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/db_internal.h: 46
class struct_rt_db_internal(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 551
class struct_rt_dsp_internal(Structure):
    pass

struct_rt_dsp_internal.__slots__ = [
    'magic',
    'dsp_name',
    'dsp_xcnt',
    'dsp_ycnt',
    'dsp_smooth',
    'dsp_cuttype',
    'dsp_mtos',
    'dsp_stom',
    'dsp_buf',
    'dsp_mp',
    'dsp_bip',
    'dsp_datasrc',
]
struct_rt_dsp_internal._fields_ = [
    ('magic', c_uint32),
    ('dsp_name', struct_bu_vls),
    ('dsp_xcnt', c_uint32),
    ('dsp_ycnt', c_uint32),
    ('dsp_smooth', c_ushort),
    ('dsp_cuttype', c_ubyte),
    ('dsp_mtos', mat_t),
    ('dsp_stom', mat_t),
    ('dsp_buf', POINTER(c_ushort)),
    ('dsp_mp', POINTER(struct_bu_mapped_file)),
    ('dsp_bip', POINTER(struct_rt_db_internal)),
    ('dsp_datasrc', c_char),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 592
class struct_rt_curve(Structure):
    pass

struct_rt_curve.__slots__ = [
    'count',
    'reverse',
    'segment',
]
struct_rt_curve._fields_ = [
    ('count', c_size_t),
    ('reverse', POINTER(c_int)),
    ('segment', POINTER(POINTER(None))),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 604
class struct_line_seg(Structure):
    pass

struct_line_seg.__slots__ = [
    'magic',
    'start',
    'end',
]
struct_line_seg._fields_ = [
    ('magic', c_uint32),
    ('start', c_int),
    ('end', c_int),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 611
class struct_carc_seg(Structure):
    pass

struct_carc_seg.__slots__ = [
    'magic',
    'start',
    'end',
    'radius',
    'center_is_left',
    'orientation',
    'center',
]
struct_carc_seg._fields_ = [
    ('magic', c_uint32),
    ('start', c_int),
    ('end', c_int),
    ('radius', fastf_t),
    ('center_is_left', c_int),
    ('orientation', c_int),
    ('center', c_int),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 625
class struct_nurb_seg(Structure):
    pass

struct_nurb_seg.__slots__ = [
    'magic',
    'order',
    'pt_type',
    'k',
    'c_size',
    'ctl_points',
    'weights',
]
struct_nurb_seg._fields_ = [
    ('magic', c_uint32),
    ('order', c_int),
    ('pt_type', c_int),
    ('k', struct_knot_vector),
    ('c_size', c_int),
    ('ctl_points', POINTER(c_int)),
    ('weights', POINTER(fastf_t)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 637
class struct_bezier_seg(Structure):
    pass

struct_bezier_seg.__slots__ = [
    'magic',
    'degree',
    'ctl_points',
]
struct_bezier_seg._fields_ = [
    ('magic', c_uint32),
    ('degree', c_int),
    ('ctl_points', POINTER(c_int)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 646
class struct_rt_sketch_internal(Structure):
    pass

struct_rt_sketch_internal.__slots__ = [
    'magic',
    'V',
    'u_vec',
    'v_vec',
    'vert_count',
    'verts',
    'curve',
]
struct_rt_sketch_internal._fields_ = [
    ('magic', c_uint32),
    ('V', point_t),
    ('u_vec', vect_t),
    ('v_vec', vect_t),
    ('vert_count', c_size_t),
    ('verts', POINTER(point2d_t)),
    ('curve', struct_rt_curve),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 679
class struct_db_i(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 671
class struct_rt_submodel_internal(Structure):
    pass

struct_rt_submodel_internal.__slots__ = [
    'magic',
    'file',
    'treetop',
    'meth',
    'root2leaf',
    'dbip',
]
struct_rt_submodel_internal._fields_ = [
    ('magic', c_uint32),
    ('file', struct_bu_vls),
    ('treetop', struct_bu_vls),
    ('meth', c_int),
    ('root2leaf', mat_t),
    ('dbip', POINTER(struct_db_i)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 690
class struct_rt_extrude_internal(Structure):
    pass

struct_rt_extrude_internal.__slots__ = [
    'magic',
    'V',
    'h',
    'u_vec',
    'v_vec',
    'keypoint',
    'sketch_name',
    'skt',
]
struct_rt_extrude_internal._fields_ = [
    ('magic', c_uint32),
    ('V', point_t),
    ('h', vect_t),
    ('u_vec', vect_t),
    ('v_vec', vect_t),
    ('keypoint', c_int),
    ('sketch_name', String),
    ('skt', POINTER(struct_rt_sketch_internal)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 715
class struct_rt_revolve_internal(Structure):
    pass

struct_rt_revolve_internal.__slots__ = [
    'magic',
    'v3d',
    'axis3d',
    'v2d',
    'axis2d',
    'r',
    'ang',
    'sketch_name',
    'skt',
]
struct_rt_revolve_internal._fields_ = [
    ('magic', c_uint32),
    ('v3d', point_t),
    ('axis3d', vect_t),
    ('v2d', point2d_t),
    ('axis2d', vect2d_t),
    ('r', vect_t),
    ('ang', fastf_t),
    ('sketch_name', struct_bu_vls),
    ('skt', POINTER(struct_rt_sketch_internal)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 739
class struct_rt_cline_internal(Structure):
    pass

struct_rt_cline_internal.__slots__ = [
    'magic',
    'v',
    'h',
    'radius',
    'thickness',
]
struct_rt_cline_internal._fields_ = [
    ('magic', c_uint32),
    ('v', point_t),
    ('h', vect_t),
    ('radius', fastf_t),
    ('thickness', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 756
class struct_rt_bot_internal(Structure):
    pass

struct_rt_bot_internal.__slots__ = [
    'magic',
    'mode',
    'orientation',
    'bot_flags',
    'num_vertices',
    'num_faces',
    'faces',
    'vertices',
    'thickness',
    'face_mode',
    'num_normals',
    'normals',
    'num_face_normals',
    'face_normals',
    'tie',
]
struct_rt_bot_internal._fields_ = [
    ('magic', c_uint32),
    ('mode', c_ubyte),
    ('orientation', c_ubyte),
    ('bot_flags', c_ubyte),
    ('num_vertices', c_size_t),
    ('num_faces', c_size_t),
    ('faces', POINTER(c_int)),
    ('vertices', POINTER(fastf_t)),
    ('thickness', POINTER(fastf_t)),
    ('face_mode', POINTER(struct_bu_bitv)),
    ('num_normals', c_size_t),
    ('normals', POINTER(fastf_t)),
    ('num_face_normals', c_size_t),
    ('face_normals', POINTER(c_int)),
    ('tie', POINTER(None)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 801
class struct_rt_bot_list(Structure):
    pass

struct_rt_bot_list.__slots__ = [
    'l',
    'bot',
]
struct_rt_bot_list._fields_ = [
    ('l', struct_bu_list),
    ('bot', POINTER(struct_rt_bot_internal)),
]

enum_anon_86 = c_int # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_PNT = 0 # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_COL = (0 + 1) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_SCA = (0 + 2) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_NRM = (0 + 4) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_COL_SCA = ((0 + 1) + 2) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_COL_NRM = ((0 + 1) + 4) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_SCA_NRM = ((0 + 2) + 4) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

RT_PNT_TYPE_COL_SCA_NRM = (((0 + 1) + 2) + 4) # /opt/brlcad/include/brlcad/./rt/geom.h: 866

rt_pnt_type = enum_anon_86 # /opt/brlcad/include/brlcad/./rt/geom.h: 866

# /opt/brlcad/include/brlcad/./rt/geom.h: 868
class struct_pnt(Structure):
    pass

struct_pnt.__slots__ = [
    'l',
    'v',
]
struct_pnt._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 872
class struct_pnt_color(Structure):
    pass

struct_pnt_color.__slots__ = [
    'l',
    'v',
    'c',
]
struct_pnt_color._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('c', struct_bu_color),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 877
class struct_pnt_scale(Structure):
    pass

struct_pnt_scale.__slots__ = [
    'l',
    'v',
    's',
]
struct_pnt_scale._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('s', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 882
class struct_pnt_normal(Structure):
    pass

struct_pnt_normal.__slots__ = [
    'l',
    'v',
    'n',
]
struct_pnt_normal._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('n', vect_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 887
class struct_pnt_color_scale(Structure):
    pass

struct_pnt_color_scale.__slots__ = [
    'l',
    'v',
    'c',
    's',
]
struct_pnt_color_scale._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('c', struct_bu_color),
    ('s', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 893
class struct_pnt_color_normal(Structure):
    pass

struct_pnt_color_normal.__slots__ = [
    'l',
    'v',
    'c',
    'n',
]
struct_pnt_color_normal._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('c', struct_bu_color),
    ('n', vect_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 899
class struct_pnt_scale_normal(Structure):
    pass

struct_pnt_scale_normal.__slots__ = [
    'l',
    'v',
    's',
    'n',
]
struct_pnt_scale_normal._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('s', fastf_t),
    ('n', vect_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 905
class struct_pnt_color_scale_normal(Structure):
    pass

struct_pnt_color_scale_normal.__slots__ = [
    'l',
    'v',
    'c',
    's',
    'n',
]
struct_pnt_color_scale_normal._fields_ = [
    ('l', struct_bu_list),
    ('v', point_t),
    ('c', struct_bu_color),
    ('s', fastf_t),
    ('n', vect_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 914
class struct_rt_pnts_internal(Structure):
    pass

struct_rt_pnts_internal.__slots__ = [
    'magic',
    'scale',
    'type',
    'count',
    'point',
]
struct_rt_pnts_internal._fields_ = [
    ('magic', c_uint32),
    ('scale', c_double),
    ('type', rt_pnt_type),
    ('count', c_ulong),
    ('point', POINTER(None)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 935
class struct_rt_ant(Structure):
    pass

struct_rt_ant.__slots__ = [
    'count',
    'reverse',
    'segments',
]
struct_rt_ant._fields_ = [
    ('count', c_size_t),
    ('reverse', POINTER(c_int)),
    ('segments', POINTER(POINTER(None))),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 946
class struct_txt_seg(Structure):
    pass

struct_txt_seg.__slots__ = [
    'magic',
    'ref_pt',
    'pt_rel_pos',
    'label',
]
struct_txt_seg._fields_ = [
    ('magic', c_uint32),
    ('ref_pt', c_int),
    ('pt_rel_pos', c_int),
    ('label', struct_bu_vls),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 953
class struct_rt_annot_internal(Structure):
    pass

struct_rt_annot_internal.__slots__ = [
    'magic',
    'V',
    'vert_count',
    'verts',
    'ant',
]
struct_rt_annot_internal._fields_ = [
    ('magic', c_uint32),
    ('V', point_t),
    ('vert_count', c_size_t),
    ('verts', POINTER(point2d_t)),
    ('ant', struct_rt_ant),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 1010
class struct_rt_datum_internal(Structure):
    pass

struct_rt_datum_internal.__slots__ = [
    'magic',
    'pnt',
    'dir',
    'w',
    'next',
]
struct_rt_datum_internal._fields_ = [
    ('magic', c_uint32),
    ('pnt', point_t),
    ('dir', vect_t),
    ('w', fastf_t),
    ('next', POINTER(struct_rt_datum_internal)),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 1029
class struct_rt_hrt_internal(Structure):
    pass

struct_rt_hrt_internal.__slots__ = [
    'hrt_magic',
    'v',
    'xdir',
    'ydir',
    'zdir',
    'd',
]
struct_rt_hrt_internal._fields_ = [
    ('hrt_magic', c_uint32),
    ('v', point_t),
    ('xdir', vect_t),
    ('ydir', vect_t),
    ('zdir', vect_t),
    ('d', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/geom.h: 1043
class struct_rt_script_internal(Structure):
    pass

struct_rt_script_internal.__slots__ = [
    'magic',
    's_type',
]
struct_rt_script_internal._fields_ = [
    ('magic', c_uint32),
    ('s_type', struct_bu_vls),
]

# /opt/brlcad/include/brlcad/rt/resource.h: 61
class struct_resource(Structure):
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 59
class struct_directory(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 51
class struct_db_full_path(Structure):
    pass

struct_db_full_path.__slots__ = [
    'magic',
    'fp_len',
    'fp_maxlen',
    'fp_names',
    'fp_bool',
]
struct_db_full_path._fields_ = [
    ('magic', c_uint32),
    ('fp_len', c_size_t),
    ('fp_maxlen', c_size_t),
    ('fp_names', POINTER(POINTER(struct_directory))),
    ('fp_bool', POINTER(c_int)),
]

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 72
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_full_path_init'):
    db_full_path_init = _libs['/opt/brlcad/lib/librt.dylib'].db_full_path_init
    db_full_path_init.argtypes = [POINTER(struct_db_full_path)]
    db_full_path_init.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 74
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_add_node_to_full_path'):
    db_add_node_to_full_path = _libs['/opt/brlcad/lib/librt.dylib'].db_add_node_to_full_path
    db_add_node_to_full_path.argtypes = [POINTER(struct_db_full_path), POINTER(struct_directory)]
    db_add_node_to_full_path.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 77
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dup_full_path'):
    db_dup_full_path = _libs['/opt/brlcad/lib/librt.dylib'].db_dup_full_path
    db_dup_full_path.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_full_path)]
    db_dup_full_path.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 85
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_extend_full_path'):
    db_extend_full_path = _libs['/opt/brlcad/lib/librt.dylib'].db_extend_full_path
    db_extend_full_path.argtypes = [POINTER(struct_db_full_path), c_size_t]
    db_extend_full_path.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 88
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_append_full_path'):
    db_append_full_path = _libs['/opt/brlcad/lib/librt.dylib'].db_append_full_path
    db_append_full_path.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_full_path)]
    db_append_full_path.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 94
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dup_path_tail'):
    db_dup_path_tail = _libs['/opt/brlcad/lib/librt.dylib'].db_dup_path_tail
    db_dup_path_tail.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_full_path), off_t]
    db_dup_path_tail.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 103
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_path_to_string'):
    db_path_to_string = _libs['/opt/brlcad/lib/librt.dylib'].db_path_to_string
    db_path_to_string.argtypes = [POINTER(struct_db_full_path)]
    if sizeof(c_int) == sizeof(c_void_p):
        db_path_to_string.restype = ReturnString
    else:
        db_path_to_string.restype = String
        db_path_to_string.errcheck = ReturnString

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 109
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_path_to_vls'):
    db_path_to_vls = _libs['/opt/brlcad/lib/librt.dylib'].db_path_to_vls
    db_path_to_vls.argtypes = [POINTER(struct_bu_vls), POINTER(struct_db_full_path)]
    db_path_to_vls.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 119
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_fullpath_to_vls'):
    db_fullpath_to_vls = _libs['/opt/brlcad/lib/librt.dylib'].db_fullpath_to_vls
    db_fullpath_to_vls.argtypes = [POINTER(struct_bu_vls), POINTER(struct_db_full_path), POINTER(struct_db_i), c_int]
    db_fullpath_to_vls.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 125
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_pr_full_path'):
    db_pr_full_path = _libs['/opt/brlcad/lib/librt.dylib'].db_pr_full_path
    db_pr_full_path.argtypes = [String, POINTER(struct_db_full_path)]
    db_pr_full_path.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 139
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_string_to_path'):
    db_string_to_path = _libs['/opt/brlcad/lib/librt.dylib'].db_string_to_path
    db_string_to_path.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_i), String]
    db_string_to_path.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 154
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_argv_to_path'):
    db_argv_to_path = _libs['/opt/brlcad/lib/librt.dylib'].db_argv_to_path
    db_argv_to_path.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_i), c_int, POINTER(POINTER(c_char))]
    db_argv_to_path.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 164
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_full_path'):
    db_free_full_path = _libs['/opt/brlcad/lib/librt.dylib'].db_free_full_path
    db_free_full_path.argtypes = [POINTER(struct_db_full_path)]
    db_free_full_path.restype = None

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 172
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_identical_full_paths'):
    db_identical_full_paths = _libs['/opt/brlcad/lib/librt.dylib'].db_identical_full_paths
    db_identical_full_paths.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_full_path)]
    db_identical_full_paths.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 181
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_full_path_subset'):
    db_full_path_subset = _libs['/opt/brlcad/lib/librt.dylib'].db_full_path_subset
    db_full_path_subset.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_full_path), c_int]
    db_full_path_subset.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 192
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_full_path_match_top'):
    db_full_path_match_top = _libs['/opt/brlcad/lib/librt.dylib'].db_full_path_match_top
    db_full_path_match_top.argtypes = [POINTER(struct_db_full_path), POINTER(struct_db_full_path)]
    db_full_path_match_top.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 201
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_full_path_search'):
    db_full_path_search = _libs['/opt/brlcad/lib/librt.dylib'].db_full_path_search
    db_full_path_search.argtypes = [POINTER(struct_db_full_path), POINTER(struct_directory)]
    db_full_path_search.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 214
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_path_to_mat'):
    db_path_to_mat = _libs['/opt/brlcad/lib/librt.dylib'].db_path_to_mat
    db_path_to_mat.argtypes = [POINTER(struct_db_i), POINTER(struct_db_full_path), mat_t, c_int, POINTER(struct_resource)]
    db_path_to_mat.restype = c_int

# /opt/brlcad/include/brlcad/./rt/tol.h: 86
class struct_rt_tess_tol(Structure):
    pass

struct_rt_tess_tol.__slots__ = [
    'magic',
    'abs',
    'rel',
    'norm',
]
struct_rt_tess_tol._fields_ = [
    ('magic', c_uint32),
    ('abs', c_double),
    ('rel', c_double),
    ('norm', c_double),
]

# /opt/brlcad/include/brlcad/./rt/tol.h: 102
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_tol_default'):
    rt_tol_default = _libs['/opt/brlcad/lib/librt.dylib'].rt_tol_default
    rt_tol_default.argtypes = [POINTER(struct_bn_tol)]
    rt_tol_default.restype = POINTER(struct_bn_tol)

# /opt/brlcad/include/brlcad/rt/mem.h: 37
class struct_mem_map(Structure):
    pass

struct_mem_map.__slots__ = [
    'm_nxtp',
    'm_size',
    'm_addr',
]
struct_mem_map._fields_ = [
    ('m_nxtp', POINTER(struct_mem_map)),
    ('m_size', c_size_t),
    ('m_addr', off_t),
]

# /opt/brlcad/include/brlcad/rt/mem.h: 56
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_memalloc'):
    rt_memalloc = _libs['/opt/brlcad/lib/librt.dylib'].rt_memalloc
    rt_memalloc.argtypes = [POINTER(POINTER(struct_mem_map)), c_size_t]
    rt_memalloc.restype = c_size_t

# /opt/brlcad/include/brlcad/rt/mem.h: 69
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_memalloc_nosplit'):
    rt_memalloc_nosplit = _libs['/opt/brlcad/lib/librt.dylib'].rt_memalloc_nosplit
    rt_memalloc_nosplit.argtypes = [POINTER(POINTER(struct_mem_map)), c_size_t]
    rt_memalloc_nosplit.restype = POINTER(struct_mem_map)

# /opt/brlcad/include/brlcad/rt/mem.h: 80
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_memget'):
    rt_memget = _libs['/opt/brlcad/lib/librt.dylib'].rt_memget
    rt_memget.argtypes = [POINTER(POINTER(struct_mem_map)), c_size_t, off_t]
    rt_memget.restype = c_size_t

# /opt/brlcad/include/brlcad/rt/mem.h: 93
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_memfree'):
    rt_memfree = _libs['/opt/brlcad/lib/librt.dylib'].rt_memfree
    rt_memfree.argtypes = [POINTER(POINTER(struct_mem_map)), c_size_t, off_t]
    rt_memfree.restype = None

# /opt/brlcad/include/brlcad/rt/mem.h: 101
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_mempurge'):
    rt_mempurge = _libs['/opt/brlcad/lib/librt.dylib'].rt_mempurge
    rt_mempurge.argtypes = [POINTER(POINTER(struct_mem_map))]
    rt_mempurge.restype = None

# /opt/brlcad/include/brlcad/rt/mem.h: 106
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_memprint'):
    rt_memprint = _libs['/opt/brlcad/lib/librt.dylib'].rt_memprint
    rt_memprint.argtypes = [POINTER(POINTER(struct_mem_map))]
    rt_memprint.restype = None

# /opt/brlcad/include/brlcad/rt/mem.h: 111
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_memclose'):
    rt_memclose = _libs['/opt/brlcad/lib/librt.dylib'].rt_memclose
    rt_memclose.argtypes = []
    rt_memclose.restype = None

# /opt/brlcad/include/brlcad/rt/region.h: 44
class struct_region(Structure):
    pass

# /opt/brlcad/include/brlcad/rt/mater.h: 38
class struct_mater_info(Structure):
    pass

struct_mater_info.__slots__ = [
    'ma_color',
    'ma_temperature',
    'ma_color_valid',
    'ma_cinherit',
    'ma_minherit',
    'ma_shader',
]
struct_mater_info._fields_ = [
    ('ma_color', c_float * 3),
    ('ma_temperature', c_float),
    ('ma_color_valid', c_char),
    ('ma_cinherit', c_char),
    ('ma_minherit', c_char),
    ('ma_shader', String),
]

# /opt/brlcad/include/brlcad/rt/mater.h: 50
class struct_mater(Structure):
    pass

struct_mater.__slots__ = [
    'mt_low',
    'mt_high',
    'mt_r',
    'mt_g',
    'mt_b',
    'mt_daddr',
    'mt_forw',
]
struct_mater._fields_ = [
    ('mt_low', c_short),
    ('mt_high', c_short),
    ('mt_r', c_ubyte),
    ('mt_g', c_ubyte),
    ('mt_b', c_ubyte),
    ('mt_daddr', off_t),
    ('mt_forw', POINTER(struct_mater)),
]

# /opt/brlcad/include/brlcad/rt/mater.h: 63
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_region_color_map'):
    rt_region_color_map = _libs['/opt/brlcad/lib/librt.dylib'].rt_region_color_map
    rt_region_color_map.argtypes = [POINTER(struct_region)]
    rt_region_color_map.restype = None

# /opt/brlcad/include/brlcad/rt/mater.h: 66
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_color_addrec'):
    rt_color_addrec = _libs['/opt/brlcad/lib/librt.dylib'].rt_color_addrec
    rt_color_addrec.argtypes = [c_int, c_int, c_int, c_int, c_int, off_t]
    rt_color_addrec.restype = None

# /opt/brlcad/include/brlcad/rt/mater.h: 72
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_insert_color'):
    rt_insert_color = _libs['/opt/brlcad/lib/librt.dylib'].rt_insert_color
    rt_insert_color.argtypes = [POINTER(struct_mater)]
    rt_insert_color.restype = None

# /opt/brlcad/include/brlcad/rt/mater.h: 73
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_vls_color_map'):
    rt_vls_color_map = _libs['/opt/brlcad/lib/librt.dylib'].rt_vls_color_map
    rt_vls_color_map.argtypes = [POINTER(struct_bu_vls)]
    rt_vls_color_map.restype = None

# /opt/brlcad/include/brlcad/rt/mater.h: 74
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_material_head'):
    rt_material_head = _libs['/opt/brlcad/lib/librt.dylib'].rt_material_head
    rt_material_head.argtypes = []
    rt_material_head.restype = POINTER(struct_mater)

# /opt/brlcad/include/brlcad/rt/mater.h: 75
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_new_material_head'):
    rt_new_material_head = _libs['/opt/brlcad/lib/librt.dylib'].rt_new_material_head
    rt_new_material_head.argtypes = [POINTER(struct_mater)]
    rt_new_material_head.restype = None

# /opt/brlcad/include/brlcad/rt/mater.h: 76
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dup_material_head'):
    rt_dup_material_head = _libs['/opt/brlcad/lib/librt.dylib'].rt_dup_material_head
    rt_dup_material_head.argtypes = []
    rt_dup_material_head.restype = POINTER(struct_mater)

# /opt/brlcad/include/brlcad/rt/mater.h: 77
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_color_free'):
    rt_color_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_color_free
    rt_color_free.argtypes = []
    rt_color_free.restype = None

# /opt/brlcad/include/brlcad/rt/anim.h: 52
class struct_anim_mat(Structure):
    pass

struct_anim_mat.__slots__ = [
    'anm_op',
    'anm_mat',
]
struct_anim_mat._fields_ = [
    ('anm_op', c_int),
    ('anm_mat', mat_t),
]

# /opt/brlcad/include/brlcad/rt/anim.h: 62
class struct_rt_anim_property(Structure):
    pass

struct_rt_anim_property.__slots__ = [
    'magic',
    'anp_op',
    'anp_shader',
]
struct_rt_anim_property._fields_ = [
    ('magic', c_uint32),
    ('anp_op', c_int),
    ('anp_shader', struct_bu_vls),
]

# /opt/brlcad/include/brlcad/rt/anim.h: 71
class struct_rt_anim_color(Structure):
    pass

struct_rt_anim_color.__slots__ = [
    'anc_rgb',
]
struct_rt_anim_color._fields_ = [
    ('anc_rgb', c_int * 3),
]

# /opt/brlcad/include/brlcad/rt/anim.h: 76
class struct_animate(Structure):
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 81
class union_animate_specific(Union):
    pass

union_animate_specific.__slots__ = [
    'anu_m',
    'anu_p',
    'anu_c',
    'anu_t',
]
union_animate_specific._fields_ = [
    ('anu_m', struct_anim_mat),
    ('anu_p', struct_rt_anim_property),
    ('anu_c', struct_rt_anim_color),
    ('anu_t', c_float),
]

struct_animate.__slots__ = [
    'magic',
    'an_forw',
    'an_path',
    'an_type',
    'an_u',
]
struct_animate._fields_ = [
    ('magic', c_uint32),
    ('an_forw', POINTER(struct_animate)),
    ('an_path', struct_db_full_path),
    ('an_type', c_int),
    ('an_u', union_animate_specific),
]

# /opt/brlcad/include/brlcad/rt/anim.h: 100
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_parse_1anim'):
    db_parse_1anim = _libs['/opt/brlcad/lib/librt.dylib'].db_parse_1anim
    db_parse_1anim.argtypes = [POINTER(struct_db_i), c_int, POINTER(POINTER(c_char))]
    db_parse_1anim.restype = POINTER(struct_animate)

# /opt/brlcad/include/brlcad/rt/anim.h: 109
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_parse_anim'):
    db_parse_anim = _libs['/opt/brlcad/lib/librt.dylib'].db_parse_anim
    db_parse_anim.argtypes = [POINTER(struct_db_i), c_int, POINTER(POINTER(c_char))]
    db_parse_anim.restype = c_int

# /opt/brlcad/include/brlcad/rt/anim.h: 123
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_add_anim'):
    db_add_anim = _libs['/opt/brlcad/lib/librt.dylib'].db_add_anim
    db_add_anim.argtypes = [POINTER(struct_db_i), POINTER(struct_animate), c_int]
    db_add_anim.restype = c_int

# /opt/brlcad/include/brlcad/rt/anim.h: 134
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_do_anim'):
    db_do_anim = _libs['/opt/brlcad/lib/librt.dylib'].db_do_anim
    db_do_anim.argtypes = [POINTER(struct_animate), mat_t, mat_t, POINTER(struct_mater_info)]
    db_do_anim.restype = c_int

# /opt/brlcad/include/brlcad/rt/anim.h: 144
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_anim'):
    db_free_anim = _libs['/opt/brlcad/lib/librt.dylib'].db_free_anim
    db_free_anim.argtypes = [POINTER(struct_db_i)]
    db_free_anim.restype = None

# /opt/brlcad/include/brlcad/rt/anim.h: 166
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_parse_1anim'):
    db_parse_1anim = _libs['/opt/brlcad/lib/librt.dylib'].db_parse_1anim
    db_parse_1anim.argtypes = [POINTER(struct_db_i), c_int, POINTER(POINTER(c_char))]
    db_parse_1anim.restype = POINTER(struct_animate)

# /opt/brlcad/include/brlcad/rt/anim.h: 174
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_1anim'):
    db_free_1anim = _libs['/opt/brlcad/lib/librt.dylib'].db_free_1anim
    db_free_1anim.argtypes = [POINTER(struct_animate)]
    db_free_1anim.restype = None

# /opt/brlcad/include/brlcad/rt/anim.h: 182
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_apply_anims'):
    db_apply_anims = _libs['/opt/brlcad/lib/librt.dylib'].db_apply_anims
    db_apply_anims.argtypes = [POINTER(struct_db_full_path), POINTER(struct_directory), mat_t, mat_t, POINTER(struct_mater_info)]
    db_apply_anims.restype = None

# /opt/brlcad/include/brlcad/rt/directory.h: 62
class union_anon_87(Union):
    pass

union_anon_87.__slots__ = [
    'file_offset',
    'ptr',
]
union_anon_87._fields_ = [
    ('file_offset', off_t),
    ('ptr', POINTER(None)),
]

struct_directory.__slots__ = [
    'd_magic',
    'd_namep',
    'd_un',
    'd_forw',
    'd_animate',
    'd_uses',
    'd_len',
    'd_nref',
    'd_flags',
    'd_major_type',
    'd_minor_type',
    'd_use_hd',
    'd_shortname',
    'u_data',
]
struct_directory._fields_ = [
    ('d_magic', c_uint32),
    ('d_namep', String),
    ('d_un', union_anon_87),
    ('d_forw', POINTER(struct_directory)),
    ('d_animate', POINTER(struct_animate)),
    ('d_uses', c_long),
    ('d_len', c_size_t),
    ('d_nref', c_long),
    ('d_flags', c_int),
    ('d_major_type', c_ubyte),
    ('d_minor_type', c_ubyte),
    ('d_use_hd', struct_bu_list),
    ('d_shortname', c_char * 16),
    ('u_data', POINTER(None)),
]

# /opt/brlcad/include/brlcad/rt/directory.h: 141
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_argv_to_dpv'):
    db_argv_to_dpv = _libs['/opt/brlcad/lib/librt.dylib'].db_argv_to_dpv
    db_argv_to_dpv.argtypes = [POINTER(struct_db_i), POINTER(POINTER(c_char))]
    db_argv_to_dpv.restype = POINTER(POINTER(struct_directory))

# /opt/brlcad/include/brlcad/rt/directory.h: 148
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dpv_to_argv'):
    db_dpv_to_argv = _libs['/opt/brlcad/lib/librt.dylib'].db_dpv_to_argv
    db_dpv_to_argv.argtypes = [POINTER(POINTER(struct_directory))]
    db_dpv_to_argv.restype = POINTER(POINTER(c_char))

# /opt/brlcad/include/brlcad/./rt/wdb.h: 49
class struct_rt_wdb(Structure):
    pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 79
for _lib in _libs.values():
    try:
        dbi_eof = (off_t).in_dll(_lib, 'dbi_eof')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 80
for _lib in _libs.values():
    try:
        dbi_nrec = (c_size_t).in_dll(_lib, 'dbi_nrec')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 81
for _lib in _libs.values():
    try:
        dbi_uses = (c_int).in_dll(_lib, 'dbi_uses')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 82
for _lib in _libs.values():
    try:
        dbi_freep = (POINTER(struct_mem_map)).in_dll(_lib, 'dbi_freep')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 83
for _lib in _libs.values():
    try:
        dbi_inmem = (POINTER(None)).in_dll(_lib, 'dbi_inmem')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 84
for _lib in _libs.values():
    try:
        dbi_anroot = (POINTER(struct_animate)).in_dll(_lib, 'dbi_anroot')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 85
for _lib in _libs.values():
    try:
        dbi_mf = (POINTER(struct_bu_mapped_file)).in_dll(_lib, 'dbi_mf')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 86
for _lib in _libs.values():
    try:
        dbi_clients = (struct_bu_ptbl).in_dll(_lib, 'dbi_clients')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 87
for _lib in _libs.values():
    try:
        dbi_version = (c_int).in_dll(_lib, 'dbi_version')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 88
for _lib in _libs.values():
    try:
        dbi_wdbp = (POINTER(struct_rt_wdb)).in_dll(_lib, 'dbi_wdbp')
        break
    except:
        pass

# /opt/brlcad/include/brlcad/rt/tree.h: 147
class union_tree(Union):
    pass

struct_region.__slots__ = [
    'l',
    'reg_name',
    'reg_treetop',
    'reg_bit',
    'reg_regionid',
    'reg_aircode',
    'reg_gmater',
    'reg_los',
    'reg_mater',
    'reg_mfuncs',
    'reg_udata',
    'reg_transmit',
    'reg_instnum',
    'reg_all_unions',
    'reg_is_fastgen',
    'attr_values',
]
struct_region._fields_ = [
    ('l', struct_bu_list),
    ('reg_name', String),
    ('reg_treetop', POINTER(union_tree)),
    ('reg_bit', c_int),
    ('reg_regionid', c_int),
    ('reg_aircode', c_int),
    ('reg_gmater', c_int),
    ('reg_los', c_int),
    ('reg_mater', struct_mater_info),
    ('reg_mfuncs', POINTER(None)),
    ('reg_udata', POINTER(None)),
    ('reg_transmit', c_int),
    ('reg_instnum', c_long),
    ('reg_all_unions', c_short),
    ('reg_is_fastgen', c_short),
    ('attr_values', struct_bu_attribute_value_set),
]

# /opt/brlcad/include/brlcad/rt/region.h: 103
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_region'):
    rt_pr_region = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_region
    rt_pr_region.argtypes = [POINTER(struct_region)]
    rt_pr_region.restype = None

# /opt/brlcad/include/brlcad/rt/region.h: 113
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_region_mat'):
    db_region_mat = _libs['/opt/brlcad/lib/librt.dylib'].db_region_mat
    db_region_mat.argtypes = [mat_t, POINTER(struct_db_i), String, POINTER(struct_resource)]
    db_region_mat.restype = c_int

# /opt/brlcad/include/brlcad/rt/soltab.h: 43
class struct_bound_rpp(Structure):
    pass

struct_bound_rpp.__slots__ = [
    'min',
    'max',
]
struct_bound_rpp._fields_ = [
    ('min', point_t),
    ('max', point_t),
]

# /opt/brlcad/include/brlcad/rt/functab.h: 69
class struct_rt_functab(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 61
class struct_rt_i(Structure):
    pass

# /opt/brlcad/include/brlcad/rt/soltab.h: 56
class struct_soltab(Structure):
    pass

struct_soltab.__slots__ = [
    'l',
    'l2',
    'st_meth',
    'st_rtip',
    'st_uses',
    'st_id',
    'st_center',
    'st_aradius',
    'st_bradius',
    'st_specific',
    'st_dp',
    'st_min',
    'st_max',
    'st_bit',
    'st_regions',
    'st_matp',
    'st_path',
    'st_npieces',
    'st_piecestate_num',
    'st_piece_rpps',
]
struct_soltab._fields_ = [
    ('l', struct_bu_list),
    ('l2', struct_bu_list),
    ('st_meth', POINTER(struct_rt_functab)),
    ('st_rtip', POINTER(struct_rt_i)),
    ('st_uses', c_long),
    ('st_id', c_int),
    ('st_center', point_t),
    ('st_aradius', fastf_t),
    ('st_bradius', fastf_t),
    ('st_specific', POINTER(None)),
    ('st_dp', POINTER(struct_directory)),
    ('st_min', point_t),
    ('st_max', point_t),
    ('st_bit', c_long),
    ('st_regions', struct_bu_ptbl),
    ('st_matp', matp_t),
    ('st_path', struct_db_full_path),
    ('st_npieces', c_long),
    ('st_piecestate_num', c_long),
    ('st_piece_rpps', POINTER(struct_bound_rpp)),
]

# /opt/brlcad/include/brlcad/rt/soltab.h: 101
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_free_soltab'):
    rt_free_soltab = _libs['/opt/brlcad/lib/librt.dylib'].rt_free_soltab
    rt_free_soltab.argtypes = [POINTER(struct_soltab)]
    rt_free_soltab.restype = None

# /opt/brlcad/include/brlcad/rt/soltab.h: 104
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_soltab'):
    rt_pr_soltab = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_soltab
    rt_pr_soltab.argtypes = [POINTER(struct_soltab)]
    rt_pr_soltab.restype = None

# /opt/brlcad/include/brlcad/rt/xray.h: 41
class struct_xray(Structure):
    pass

struct_xray.__slots__ = [
    'magic',
    'index',
    'r_pt',
    'r_dir',
    'r_min',
    'r_max',
]
struct_xray._fields_ = [
    ('magic', c_uint32),
    ('index', c_int),
    ('r_pt', point_t),
    ('r_dir', vect_t),
    ('r_min', fastf_t),
    ('r_max', fastf_t),
]

# /opt/brlcad/include/brlcad/rt/xray.h: 57
class struct_xrays(Structure):
    pass

struct_xrays.__slots__ = [
    'l',
    'ray',
]
struct_xrays._fields_ = [
    ('l', struct_bu_list),
    ('ray', struct_xray),
]

# /opt/brlcad/include/brlcad/rt/xray.h: 74
class struct_pixel_ext(Structure):
    pass

struct_pixel_ext.__slots__ = [
    'magic',
    'corner',
]
struct_pixel_ext._fields_ = [
    ('magic', c_uint32),
    ('corner', struct_xray * 4),
]

# /opt/brlcad/include/brlcad/rt/hit.h: 61
class struct_hit(Structure):
    pass

struct_hit.__slots__ = [
    'hit_magic',
    'hit_dist',
    'hit_point',
    'hit_normal',
    'hit_vpriv',
    'hit_private',
    'hit_surfno',
    'hit_rayp',
]
struct_hit._fields_ = [
    ('hit_magic', c_uint32),
    ('hit_dist', fastf_t),
    ('hit_point', point_t),
    ('hit_normal', vect_t),
    ('hit_vpriv', vect_t),
    ('hit_private', POINTER(None)),
    ('hit_surfno', c_int),
    ('hit_rayp', POINTER(struct_xray)),
]

# /opt/brlcad/include/brlcad/rt/hit.h: 118
class struct_curvature(Structure):
    pass

struct_curvature.__slots__ = [
    'crv_pdir',
    'crv_c1',
    'crv_c2',
]
struct_curvature._fields_ = [
    ('crv_pdir', vect_t),
    ('crv_c1', fastf_t),
    ('crv_c2', fastf_t),
]

# /opt/brlcad/include/brlcad/rt/hit.h: 152
class struct_uvcoord(Structure):
    pass

struct_uvcoord.__slots__ = [
    'uv_u',
    'uv_v',
    'uv_du',
    'uv_dv',
]
struct_uvcoord._fields_ = [
    ('uv_u', fastf_t),
    ('uv_v', fastf_t),
    ('uv_du', fastf_t),
    ('uv_dv', fastf_t),
]

# /opt/brlcad/include/brlcad/rt/hit.h: 172
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_hit'):
    rt_pr_hit = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_hit
    rt_pr_hit.argtypes = [String, POINTER(struct_hit)]
    rt_pr_hit.restype = None

# /opt/brlcad/include/brlcad/rt/hit.h: 174
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_hit_vls'):
    rt_pr_hit_vls = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_hit_vls
    rt_pr_hit_vls.argtypes = [POINTER(struct_bu_vls), String, POINTER(struct_hit)]
    rt_pr_hit_vls.restype = None

# /opt/brlcad/include/brlcad/rt/hit.h: 177
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_hitarray_vls'):
    rt_pr_hitarray_vls = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_hitarray_vls
    rt_pr_hitarray_vls.argtypes = [POINTER(struct_bu_vls), String, POINTER(struct_hit), c_int]
    rt_pr_hitarray_vls.restype = None

# /opt/brlcad/include/brlcad/rt/seg.h: 59
class struct_seg(Structure):
    pass

struct_seg.__slots__ = [
    'l',
    'seg_in',
    'seg_out',
    'seg_stp',
]
struct_seg._fields_ = [
    ('l', struct_bu_list),
    ('seg_in', struct_hit),
    ('seg_out', struct_hit),
    ('seg_stp', POINTER(struct_soltab)),
]

# /opt/brlcad/include/brlcad/rt/seg.h: 101
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_seg'):
    rt_pr_seg = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_seg
    rt_pr_seg.argtypes = [POINTER(struct_seg)]
    rt_pr_seg.restype = None

# /opt/brlcad/include/brlcad/rt/seg.h: 102
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_seg_vls'):
    rt_pr_seg_vls = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_seg_vls
    rt_pr_seg_vls.argtypes = [POINTER(struct_bu_vls), POINTER(struct_seg)]
    rt_pr_seg_vls.restype = None

# /opt/brlcad/include/brlcad/rt/ray_partition.h: 53
class struct_partition(Structure):
    pass

struct_partition.__slots__ = [
    'pt_magic',
    'pt_forw',
    'pt_back',
    'pt_inseg',
    'pt_inhit',
    'pt_outseg',
    'pt_outhit',
    'pt_regionp',
    'pt_inflip',
    'pt_outflip',
    'pt_overlap_reg',
    'pt_seglist',
]
struct_partition._fields_ = [
    ('pt_magic', c_uint32),
    ('pt_forw', POINTER(struct_partition)),
    ('pt_back', POINTER(struct_partition)),
    ('pt_inseg', POINTER(struct_seg)),
    ('pt_inhit', POINTER(struct_hit)),
    ('pt_outseg', POINTER(struct_seg)),
    ('pt_outhit', POINTER(struct_hit)),
    ('pt_regionp', POINTER(struct_region)),
    ('pt_inflip', c_char),
    ('pt_outflip', c_char),
    ('pt_overlap_reg', POINTER(POINTER(struct_region))),
    ('pt_seglist', struct_bu_ptbl),
]

# /opt/brlcad/include/brlcad/rt/application.h: 99
class struct_application(Structure):
    pass

# /opt/brlcad/include/brlcad/rt/ray_partition.h: 136
class struct_partition_list(Structure):
    pass

struct_partition_list.__slots__ = [
    'l',
    'ap',
    'PartHeadp',
    'segHeadp',
    'userptr',
]
struct_partition_list._fields_ = [
    ('l', struct_bu_list),
    ('ap', POINTER(struct_application)),
    ('PartHeadp', struct_partition),
    ('segHeadp', struct_seg),
    ('userptr', POINTER(None)),
]

# /opt/brlcad/include/brlcad/rt/ray_partition.h: 149
class struct_partition_bundle(Structure):
    pass

struct_partition_bundle.__slots__ = [
    'hits',
    'misses',
    'list',
    'ap',
]
struct_partition_bundle._fields_ = [
    ('hits', c_int),
    ('misses', c_int),
    ('list', POINTER(struct_partition_list)),
    ('ap', POINTER(struct_application)),
]

# /opt/brlcad/include/brlcad/rt/ray_partition.h: 160
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_partition_len'):
    rt_partition_len = _libs['/opt/brlcad/lib/librt.dylib'].rt_partition_len
    rt_partition_len.argtypes = [POINTER(struct_partition)]
    rt_partition_len.restype = c_int

struct_application.__slots__ = [
    'a_magic',
    'a_ray',
    'a_hit',
    'a_miss',
    'a_onehit',
    'a_ray_length',
    'a_rt_i',
    'a_zero1',
    'a_resource',
    'a_overlap',
    'a_multioverlap',
    'a_logoverlap',
    'a_level',
    'a_x',
    'a_y',
    'a_purpose',
    'a_rbeam',
    'a_diverge',
    'a_return',
    'a_no_booleans',
    'attrs',
    'a_bot_reverse_normal_disabled',
    'a_pixelext',
    'a_finished_segs_hdp',
    'a_Final_Part_hdp',
    'a_inv_dir',
    'a_user',
    'a_uptr',
    'a_spectrum',
    'a_color',
    'a_dist',
    'a_uvec',
    'a_vvec',
    'a_refrac_index',
    'a_cumlen',
    'a_flag',
    'a_zero2',
]
struct_application._fields_ = [
    ('a_magic', c_uint32),
    ('a_ray', struct_xray),
    ('a_hit', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_application), POINTER(struct_partition), POINTER(struct_seg))),
    ('a_miss', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_application))),
    ('a_onehit', c_int),
    ('a_ray_length', fastf_t),
    ('a_rt_i', POINTER(struct_rt_i)),
    ('a_zero1', c_int),
    ('a_resource', POINTER(struct_resource)),
    ('a_overlap', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_application), POINTER(struct_partition), POINTER(struct_region), POINTER(struct_region), POINTER(struct_partition))),
    ('a_multioverlap', CFUNCTYPE(UNCHECKED(None), POINTER(struct_application), POINTER(struct_partition), POINTER(struct_bu_ptbl), POINTER(struct_partition))),
    ('a_logoverlap', CFUNCTYPE(UNCHECKED(None), POINTER(struct_application), POINTER(struct_partition), POINTER(struct_bu_ptbl), POINTER(struct_partition))),
    ('a_level', c_int),
    ('a_x', c_int),
    ('a_y', c_int),
    ('a_purpose', String),
    ('a_rbeam', fastf_t),
    ('a_diverge', fastf_t),
    ('a_return', c_int),
    ('a_no_booleans', c_int),
    ('attrs', POINTER(POINTER(c_char))),
    ('a_bot_reverse_normal_disabled', c_int),
    ('a_pixelext', POINTER(struct_pixel_ext)),
    ('a_finished_segs_hdp', POINTER(struct_seg)),
    ('a_Final_Part_hdp', POINTER(struct_partition)),
    ('a_inv_dir', vect_t),
    ('a_user', c_int),
    ('a_uptr', POINTER(None)),
    ('a_spectrum', POINTER(struct_bn_tabdata)),
    ('a_color', fastf_t * 3),
    ('a_dist', fastf_t),
    ('a_uvec', vect_t),
    ('a_vvec', vect_t),
    ('a_refrac_index', fastf_t),
    ('a_cumlen', fastf_t),
    ('a_flag', c_int),
    ('a_zero2', c_int),
]

# /opt/brlcad/include/brlcad/rt/application.h: 176
class struct_application_bundle(Structure):
    pass

struct_application_bundle.__slots__ = [
    'b_magic',
    'b_rays',
    'b_ap',
    'b_hit',
    'b_miss',
    'b_user',
    'b_uptr',
    'b_return',
]
struct_application_bundle._fields_ = [
    ('b_magic', c_uint32),
    ('b_rays', struct_xrays),
    ('b_ap', struct_application),
    ('b_hit', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_application_bundle), POINTER(struct_partition_bundle))),
    ('b_miss', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_application_bundle))),
    ('b_user', c_int),
    ('b_uptr', POINTER(None)),
    ('b_return', c_int),
]

# /opt/brlcad/include/brlcad/./rt/nmg.h: 42
class struct_hitmiss(Structure):
    pass

struct_hitmiss.__slots__ = [
    'l',
    'hit',
    'dist_in_plane',
    'in_out',
    'inbound_use',
    'inbound_norm',
    'outbound_use',
    'outbound_norm',
    'start_stop',
    'other',
]
struct_hitmiss._fields_ = [
    ('l', struct_bu_list),
    ('hit', struct_hit),
    ('dist_in_plane', fastf_t),
    ('in_out', c_int),
    ('inbound_use', POINTER(c_long)),
    ('inbound_norm', vect_t),
    ('outbound_use', POINTER(c_long)),
    ('outbound_norm', vect_t),
    ('start_stop', c_int),
    ('other', POINTER(struct_hitmiss)),
]

# /opt/brlcad/include/brlcad/./rt/nmg.h: 81
class struct_ray_data(Structure):
    pass

struct_ray_data.__slots__ = [
    'magic',
    'rd_m',
    'manifolds',
    'rd_invdir',
    'rp',
    'ap',
    'seghead',
    'stp',
    'tol',
    'hitmiss',
    'rd_hit',
    'rd_miss',
    'plane_pt',
    'ray_dist_to_plane',
    'face_subhit',
    'classifying_ray',
]
struct_ray_data._fields_ = [
    ('magic', c_uint32),
    ('rd_m', POINTER(struct_model)),
    ('manifolds', String),
    ('rd_invdir', vect_t),
    ('rp', POINTER(struct_xray)),
    ('ap', POINTER(struct_application)),
    ('seghead', POINTER(struct_seg)),
    ('stp', POINTER(struct_soltab)),
    ('tol', POINTER(struct_bn_tol)),
    ('hitmiss', POINTER(POINTER(struct_hitmiss))),
    ('rd_hit', struct_bu_list),
    ('rd_miss', struct_bu_list),
    ('plane_pt', point_t),
    ('ray_dist_to_plane', fastf_t),
    ('face_subhit', c_int),
    ('classifying_ray', c_int),
]

# /opt/brlcad/include/brlcad/./rt/nmg.h: 134
try:
    nmg_plot_anim_upcall = (POINTER(CFUNCTYPE(UNCHECKED(None), ))).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_plot_anim_upcall')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/nmg.h: 138
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_nmg_print_hitlist'):
    rt_nmg_print_hitlist = _libs['/opt/brlcad/lib/librt.dylib'].rt_nmg_print_hitlist
    rt_nmg_print_hitlist.argtypes = [POINTER(struct_bu_list)]
    rt_nmg_print_hitlist.restype = None

# /opt/brlcad/include/brlcad/./rt/nmg.h: 139
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_nmg_print_hitmiss'):
    rt_nmg_print_hitmiss = _libs['/opt/brlcad/lib/librt.dylib'].rt_nmg_print_hitmiss
    rt_nmg_print_hitmiss.argtypes = [POINTER(struct_hitmiss)]
    rt_nmg_print_hitmiss.restype = None

# /opt/brlcad/include/brlcad/./rt/nmg.h: 140
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_isect_ray_model'):
    rt_isect_ray_model = _libs['/opt/brlcad/lib/librt.dylib'].rt_isect_ray_model
    rt_isect_ray_model.argtypes = [POINTER(struct_ray_data), POINTER(struct_bu_list)]
    rt_isect_ray_model.restype = None

# /opt/brlcad/include/brlcad/./rt/nmg.h: 150
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_ray_segs'):
    nmg_ray_segs = _libs['/opt/brlcad/lib/librt.dylib'].nmg_ray_segs
    nmg_ray_segs.argtypes = [POINTER(struct_ray_data), POINTER(struct_bu_list)]
    nmg_ray_segs.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 152
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_to_arb'):
    nmg_to_arb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_to_arb
    nmg_to_arb.argtypes = [POINTER(struct_model), POINTER(struct_rt_arb_internal)]
    nmg_to_arb.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 154
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_to_tgc'):
    nmg_to_tgc = _libs['/opt/brlcad/lib/librt.dylib'].nmg_to_tgc
    nmg_to_tgc.argtypes = [POINTER(struct_model), POINTER(struct_rt_tgc_internal), POINTER(struct_bn_tol)]
    nmg_to_tgc.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 157
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_to_poly'):
    nmg_to_poly = _libs['/opt/brlcad/lib/librt.dylib'].nmg_to_poly
    nmg_to_poly.argtypes = [POINTER(struct_model), POINTER(struct_rt_pg_internal), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_to_poly.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 161
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_bot'):
    nmg_bot = _libs['/opt/brlcad/lib/librt.dylib'].nmg_bot
    nmg_bot.argtypes = [POINTER(struct_shell), POINTER(struct_bu_list), POINTER(struct_bn_tol)]
    nmg_bot.restype = POINTER(struct_rt_bot_internal)

# /opt/brlcad/include/brlcad/rt/tree.h: 56
class struct_db_tree_state(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/nmg.h: 165
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_booltree_leaf_tess'):
    nmg_booltree_leaf_tess = _libs['/opt/brlcad/lib/librt.dylib'].nmg_booltree_leaf_tess
    nmg_booltree_leaf_tess.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_db_internal), POINTER(None)]
    nmg_booltree_leaf_tess.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/./rt/nmg.h: 169
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_booltree_leaf_tnurb'):
    nmg_booltree_leaf_tnurb = _libs['/opt/brlcad/lib/librt.dylib'].nmg_booltree_leaf_tnurb
    nmg_booltree_leaf_tnurb.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_db_internal), POINTER(None)]
    nmg_booltree_leaf_tnurb.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/./rt/nmg.h: 173
try:
    nmg_bool_eval_silent = (c_int).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_bool_eval_silent')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/nmg.h: 174
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_booltree_evaluate'):
    nmg_booltree_evaluate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_booltree_evaluate
    nmg_booltree_evaluate.argtypes = [POINTER(union_tree), POINTER(struct_bu_list), POINTER(struct_bn_tol), POINTER(struct_resource)]
    nmg_booltree_evaluate.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/./rt/nmg.h: 178
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_boolean'):
    nmg_boolean = _libs['/opt/brlcad/lib/librt.dylib'].nmg_boolean
    nmg_boolean.argtypes = [POINTER(union_tree), POINTER(struct_model), POINTER(struct_bu_list), POINTER(struct_bn_tol), POINTER(struct_resource)]
    nmg_boolean.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 188
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_triangulate_model_mc'):
    nmg_triangulate_model_mc = _libs['/opt/brlcad/lib/librt.dylib'].nmg_triangulate_model_mc
    nmg_triangulate_model_mc.argtypes = [POINTER(struct_model), POINTER(struct_bn_tol)]
    nmg_triangulate_model_mc.restype = None

# /opt/brlcad/include/brlcad/./rt/nmg.h: 190
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mc_realize_cube'):
    nmg_mc_realize_cube = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mc_realize_cube
    nmg_mc_realize_cube.argtypes = [POINTER(struct_shell), c_int, POINTER(point_t), POINTER(struct_bn_tol)]
    nmg_mc_realize_cube.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 194
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_mc_evaluate'):
    nmg_mc_evaluate = _libs['/opt/brlcad/lib/librt.dylib'].nmg_mc_evaluate
    nmg_mc_evaluate.argtypes = [POINTER(struct_shell), POINTER(struct_rt_i), POINTER(struct_db_full_path), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol)]
    nmg_mc_evaluate.restype = c_int

# /opt/brlcad/include/brlcad/./rt/nmg.h: 202
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'nmg_stash_model_to_file'):
    nmg_stash_model_to_file = _libs['/opt/brlcad/lib/librt.dylib'].nmg_stash_model_to_file
    nmg_stash_model_to_file.argtypes = [String, POINTER(struct_model), String]
    nmg_stash_model_to_file.restype = None

# /opt/brlcad/include/brlcad/./rt/nongeom.h: 41
class struct_rt_comb_internal(Structure):
    pass

struct_db_tree_state.__slots__ = [
    'magic',
    'ts_dbip',
    'ts_sofar',
    'ts_regionid',
    'ts_aircode',
    'ts_gmater',
    'ts_los',
    'ts_mater',
    'ts_mat',
    'ts_is_fastgen',
    'ts_attrs',
    'ts_stop_at_regions',
    'ts_region_start_func',
    'ts_region_end_func',
    'ts_leaf_func',
    'ts_ttol',
    'ts_tol',
    'ts_m',
    'ts_rtip',
    'ts_resp',
]
struct_db_tree_state._fields_ = [
    ('magic', c_uint32),
    ('ts_dbip', POINTER(struct_db_i)),
    ('ts_sofar', c_int),
    ('ts_regionid', c_int),
    ('ts_aircode', c_int),
    ('ts_gmater', c_int),
    ('ts_los', c_int),
    ('ts_mater', struct_mater_info),
    ('ts_mat', mat_t),
    ('ts_is_fastgen', c_int),
    ('ts_attrs', struct_bu_attribute_value_set),
    ('ts_stop_at_regions', c_int),
    ('ts_region_start_func', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_comb_internal), POINTER(None))),
    ('ts_region_end_func', CFUNCTYPE(UNCHECKED(POINTER(union_tree)), POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(union_tree), POINTER(None))),
    ('ts_leaf_func', CFUNCTYPE(UNCHECKED(POINTER(union_tree)), POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_db_internal), POINTER(None))),
    ('ts_ttol', POINTER(struct_rt_tess_tol)),
    ('ts_tol', POINTER(struct_bn_tol)),
    ('ts_m', POINTER(POINTER(struct_model))),
    ('ts_rtip', POINTER(struct_rt_i)),
    ('ts_resp', POINTER(struct_resource)),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 110
try:
    rt_initial_tree_state = (struct_db_tree_state).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_initial_tree_state')
except:
    pass

# /opt/brlcad/include/brlcad/rt/tree.h: 115
class struct_db_traverse(Structure):
    pass

struct_db_traverse.__slots__ = [
    'magic',
    'dbip',
    'comb_enter_func',
    'comb_exit_func',
    'leaf_func',
    'resp',
    'client_data',
]
struct_db_traverse._fields_ = [
    ('magic', c_uint32),
    ('dbip', POINTER(struct_db_i)),
    ('comb_enter_func', CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_directory), POINTER(None))),
    ('comb_exit_func', CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_directory), POINTER(None))),
    ('leaf_func', CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_directory), POINTER(None))),
    ('resp', POINTER(struct_resource)),
    ('client_data', POINTER(None)),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 140
class struct_combined_tree_state(Structure):
    pass

struct_combined_tree_state.__slots__ = [
    'magic',
    'cts_s',
    'cts_p',
]
struct_combined_tree_state._fields_ = [
    ('magic', c_uint32),
    ('cts_s', struct_db_tree_state),
    ('cts_p', struct_db_full_path),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 150
class struct_tree_node(Structure):
    pass

struct_tree_node.__slots__ = [
    'magic',
    'tb_op',
    'tb_regionp',
    'tb_left',
    'tb_right',
]
struct_tree_node._fields_ = [
    ('magic', c_uint32),
    ('tb_op', c_int),
    ('tb_regionp', POINTER(struct_region)),
    ('tb_left', POINTER(union_tree)),
    ('tb_right', POINTER(union_tree)),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 157
class struct_tree_leaf(Structure):
    pass

struct_tree_leaf.__slots__ = [
    'magic',
    'tu_op',
    'tu_regionp',
    'tu_stp',
]
struct_tree_leaf._fields_ = [
    ('magic', c_uint32),
    ('tu_op', c_int),
    ('tu_regionp', POINTER(struct_region)),
    ('tu_stp', POINTER(struct_soltab)),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 163
class struct_tree_cts(Structure):
    pass

struct_tree_cts.__slots__ = [
    'magic',
    'tc_op',
    'tc_pad',
    'tc_ctsp',
]
struct_tree_cts._fields_ = [
    ('magic', c_uint32),
    ('tc_op', c_int),
    ('tc_pad', POINTER(struct_region)),
    ('tc_ctsp', POINTER(struct_combined_tree_state)),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 169
class struct_tree_nmgregion(Structure):
    pass

struct_tree_nmgregion.__slots__ = [
    'magic',
    'td_op',
    'td_name',
    'td_r',
]
struct_tree_nmgregion._fields_ = [
    ('magic', c_uint32),
    ('td_op', c_int),
    ('td_name', String),
    ('td_r', POINTER(struct_nmgregion)),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 175
class struct_tree_db_leaf(Structure):
    pass

struct_tree_db_leaf.__slots__ = [
    'magic',
    'tl_op',
    'tl_mat',
    'tl_name',
]
struct_tree_db_leaf._fields_ = [
    ('magic', c_uint32),
    ('tl_op', c_int),
    ('tl_mat', matp_t),
    ('tl_name', String),
]

union_tree.__slots__ = [
    'magic',
    'tr_b',
    'tr_a',
    'tr_c',
    'tr_d',
    'tr_l',
]
union_tree._fields_ = [
    ('magic', c_uint32),
    ('tr_b', struct_tree_node),
    ('tr_a', struct_tree_leaf),
    ('tr_c', struct_tree_cts),
    ('tr_d', struct_tree_nmgregion),
    ('tr_l', struct_tree_db_leaf),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 227
class struct_rt_tree_array(Structure):
    pass

struct_rt_tree_array.__slots__ = [
    'tl_tree',
    'tl_op',
]
struct_rt_tree_array._fields_ = [
    ('tl_tree', POINTER(union_tree)),
    ('tl_op', c_int),
]

# /opt/brlcad/include/brlcad/rt/tree.h: 279
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_tree'):
    rt_pr_tree = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_tree
    rt_pr_tree.argtypes = [POINTER(union_tree), c_int]
    rt_pr_tree.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 281
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_tree_vls'):
    rt_pr_tree_vls = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_tree_vls
    rt_pr_tree_vls.argtypes = [POINTER(struct_bu_vls), POINTER(union_tree)]
    rt_pr_tree_vls.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 283
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_tree_str'):
    rt_pr_tree_str = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_tree_str
    rt_pr_tree_str.argtypes = [POINTER(union_tree)]
    if sizeof(c_int) == sizeof(c_void_p):
        rt_pr_tree_str.restype = ReturnString
    else:
        rt_pr_tree_str.restype = String
        rt_pr_tree_str.errcheck = ReturnString

# /opt/brlcad/include/brlcad/rt/tree.h: 286
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_tree_val'):
    rt_pr_tree_val = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_tree_val
    rt_pr_tree_val.argtypes = [POINTER(union_tree), POINTER(struct_partition), c_int, c_int]
    rt_pr_tree_val.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 295
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dup_db_tree_state'):
    db_dup_db_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_dup_db_tree_state
    db_dup_db_tree_state.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_tree_state)]
    db_dup_db_tree_state.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 302
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_db_tree_state'):
    db_free_db_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_free_db_tree_state
    db_free_db_tree_state.argtypes = [POINTER(struct_db_tree_state)]
    db_free_db_tree_state.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 309
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_init_db_tree_state'):
    db_init_db_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_init_db_tree_state
    db_init_db_tree_state.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_i), POINTER(struct_resource)]
    db_init_db_tree_state.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 312
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_new_combined_tree_state'):
    db_new_combined_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_new_combined_tree_state
    db_new_combined_tree_state.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path)]
    db_new_combined_tree_state.restype = POINTER(struct_combined_tree_state)

# /opt/brlcad/include/brlcad/rt/tree.h: 314
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dup_combined_tree_state'):
    db_dup_combined_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_dup_combined_tree_state
    db_dup_combined_tree_state.argtypes = [POINTER(struct_combined_tree_state)]
    db_dup_combined_tree_state.restype = POINTER(struct_combined_tree_state)

# /opt/brlcad/include/brlcad/rt/tree.h: 315
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_combined_tree_state'):
    db_free_combined_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_free_combined_tree_state
    db_free_combined_tree_state.argtypes = [POINTER(struct_combined_tree_state)]
    db_free_combined_tree_state.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 316
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_pr_tree_state'):
    db_pr_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_pr_tree_state
    db_pr_tree_state.argtypes = [POINTER(struct_db_tree_state)]
    db_pr_tree_state.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 317
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_pr_combined_tree_state'):
    db_pr_combined_tree_state = _libs['/opt/brlcad/lib/librt.dylib'].db_pr_combined_tree_state
    db_pr_combined_tree_state.argtypes = [POINTER(struct_combined_tree_state)]
    db_pr_combined_tree_state.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 329
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_apply_state_from_comb'):
    db_apply_state_from_comb = _libs['/opt/brlcad/lib/librt.dylib'].db_apply_state_from_comb
    db_apply_state_from_comb.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_comb_internal)]
    db_apply_state_from_comb.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 341
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_apply_state_from_memb'):
    db_apply_state_from_memb = _libs['/opt/brlcad/lib/librt.dylib'].db_apply_state_from_memb
    db_apply_state_from_memb.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(union_tree)]
    db_apply_state_from_memb.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 351
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_apply_state_from_one_member'):
    db_apply_state_from_one_member = _libs['/opt/brlcad/lib/librt.dylib'].db_apply_state_from_one_member
    db_apply_state_from_one_member.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), String, c_int, POINTER(union_tree)]
    db_apply_state_from_one_member.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 364
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_find_named_leaf'):
    db_find_named_leaf = _libs['/opt/brlcad/lib/librt.dylib'].db_find_named_leaf
    db_find_named_leaf.argtypes = [POINTER(union_tree), String]
    db_find_named_leaf.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 376
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_find_named_leafs_parent'):
    db_find_named_leafs_parent = _libs['/opt/brlcad/lib/librt.dylib'].db_find_named_leafs_parent
    db_find_named_leafs_parent.argtypes = [POINTER(c_int), POINTER(union_tree), String]
    db_find_named_leafs_parent.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 379
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_del_lhs'):
    db_tree_del_lhs = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_del_lhs
    db_tree_del_lhs.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    db_tree_del_lhs.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 381
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_del_rhs'):
    db_tree_del_rhs = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_del_rhs
    db_tree_del_rhs.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    db_tree_del_rhs.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 404
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_del_dbleaf'):
    db_tree_del_dbleaf = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_del_dbleaf
    db_tree_del_dbleaf.argtypes = [POINTER(POINTER(union_tree)), String, POINTER(struct_resource), c_int]
    db_tree_del_dbleaf.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 413
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_mul_dbleaf'):
    db_tree_mul_dbleaf = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_mul_dbleaf
    db_tree_mul_dbleaf.argtypes = [POINTER(union_tree), mat_t]
    db_tree_mul_dbleaf.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 423
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_funcleaf'):
    db_tree_funcleaf = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_funcleaf
    db_tree_funcleaf.argtypes = [POINTER(struct_db_i), POINTER(struct_rt_comb_internal), POINTER(union_tree), CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_rt_comb_internal), POINTER(union_tree), POINTER(None), POINTER(None), POINTER(None), POINTER(None)), POINTER(None), POINTER(None), POINTER(None), POINTER(None)]
    db_tree_funcleaf.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 452
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_follow_path'):
    db_follow_path = _libs['/opt/brlcad/lib/librt.dylib'].db_follow_path
    db_follow_path.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_db_full_path), c_int, c_long]
    db_follow_path.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 468
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_follow_path_for_state'):
    db_follow_path_for_state = _libs['/opt/brlcad/lib/librt.dylib'].db_follow_path_for_state
    db_follow_path_for_state.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), String, c_int]
    db_follow_path_for_state.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 479
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_recurse'):
    db_recurse = _libs['/opt/brlcad/lib/librt.dylib'].db_recurse
    db_recurse.argtypes = [POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(POINTER(struct_combined_tree_state)), POINTER(None)]
    db_recurse.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 483
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dup_subtree'):
    db_dup_subtree = _libs['/opt/brlcad/lib/librt.dylib'].db_dup_subtree
    db_dup_subtree.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    db_dup_subtree.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 485
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_ck_tree'):
    db_ck_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_ck_tree
    db_ck_tree.argtypes = [POINTER(union_tree)]
    db_ck_tree.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 492
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_tree'):
    db_free_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_free_tree
    db_free_tree.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    db_free_tree.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 501
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_left_hvy_node'):
    db_left_hvy_node = _libs['/opt/brlcad/lib/librt.dylib'].db_left_hvy_node
    db_left_hvy_node.argtypes = [POINTER(union_tree)]
    db_left_hvy_node.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 510
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_non_union_push'):
    db_non_union_push = _libs['/opt/brlcad/lib/librt.dylib'].db_non_union_push
    db_non_union_push.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    db_non_union_push.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 517
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_count_tree_nodes'):
    db_count_tree_nodes = _libs['/opt/brlcad/lib/librt.dylib'].db_count_tree_nodes
    db_count_tree_nodes.argtypes = [POINTER(union_tree), c_int]
    db_count_tree_nodes.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 526
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_is_tree_all_unions'):
    db_is_tree_all_unions = _libs['/opt/brlcad/lib/librt.dylib'].db_is_tree_all_unions
    db_is_tree_all_unions.argtypes = [POINTER(union_tree)]
    db_is_tree_all_unions.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 527
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_count_subtree_regions'):
    db_count_subtree_regions = _libs['/opt/brlcad/lib/librt.dylib'].db_count_subtree_regions
    db_count_subtree_regions.argtypes = [POINTER(union_tree)]
    db_count_subtree_regions.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 528
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tally_subtree_regions'):
    db_tally_subtree_regions = _libs['/opt/brlcad/lib/librt.dylib'].db_tally_subtree_regions
    db_tally_subtree_regions.argtypes = [POINTER(union_tree), POINTER(POINTER(union_tree)), c_int, c_int, POINTER(struct_resource)]
    db_tally_subtree_regions.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 586
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_walk_tree'):
    db_walk_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_walk_tree
    db_walk_tree.argtypes = [POINTER(struct_db_i), c_int, POINTER(POINTER(c_char)), c_int, POINTER(struct_db_tree_state), CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_comb_internal), POINTER(None)), CFUNCTYPE(UNCHECKED(POINTER(union_tree)), POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(union_tree), POINTER(None)), CFUNCTYPE(UNCHECKED(POINTER(union_tree)), POINTER(struct_db_tree_state), POINTER(struct_db_full_path), POINTER(struct_rt_db_internal), POINTER(None)), POINTER(None)]
    db_walk_tree.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 629
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_list'):
    db_tree_list = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_list
    db_tree_list.argtypes = [POINTER(struct_bu_vls), POINTER(union_tree)]
    db_tree_list.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 635
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_parse'):
    db_tree_parse = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_parse
    db_tree_parse.argtypes = [POINTER(struct_bu_vls), String, POINTER(struct_resource)]
    db_tree_parse.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 644
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_functree'):
    db_functree = _libs['/opt/brlcad/lib/librt.dylib'].db_functree
    db_functree.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_directory), POINTER(None)), CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_directory), POINTER(None)), POINTER(struct_resource), POINTER(None)]
    db_functree.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 671
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bound_tree'):
    rt_bound_tree = _libs['/opt/brlcad/lib/librt.dylib'].rt_bound_tree
    rt_bound_tree.argtypes = [POINTER(union_tree), vect_t, vect_t]
    rt_bound_tree.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 687
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_tree_elim_nops'):
    rt_tree_elim_nops = _libs['/opt/brlcad/lib/librt.dylib'].rt_tree_elim_nops
    rt_tree_elim_nops.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    rt_tree_elim_nops.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 693
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_nleaves'):
    db_tree_nleaves = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_nleaves
    db_tree_nleaves.argtypes = [POINTER(union_tree)]
    db_tree_nleaves.restype = c_size_t

# /opt/brlcad/include/brlcad/rt/tree.h: 709
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_flatten_tree'):
    db_flatten_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_flatten_tree
    db_flatten_tree.argtypes = [POINTER(struct_rt_tree_array), POINTER(union_tree), c_int, c_int, POINTER(struct_resource)]
    db_flatten_tree.restype = POINTER(struct_rt_tree_array)

# /opt/brlcad/include/brlcad/rt/tree.h: 716
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_flatten_describe'):
    db_tree_flatten_describe = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_flatten_describe
    db_tree_flatten_describe.argtypes = [POINTER(struct_bu_vls), POINTER(union_tree), c_int, c_int, c_double, POINTER(struct_resource)]
    db_tree_flatten_describe.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 723
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_tree_describe'):
    db_tree_describe = _libs['/opt/brlcad/lib/librt.dylib'].db_tree_describe
    db_tree_describe.argtypes = [POINTER(struct_bu_vls), POINTER(union_tree), c_int, c_int, c_double]
    db_tree_describe.restype = None

# /opt/brlcad/include/brlcad/rt/tree.h: 738
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_ck_left_heavy_tree'):
    db_ck_left_heavy_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_ck_left_heavy_tree
    db_ck_left_heavy_tree.argtypes = [POINTER(union_tree), c_int]
    db_ck_left_heavy_tree.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 755
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_ck_v4gift_tree'):
    db_ck_v4gift_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_ck_v4gift_tree
    db_ck_v4gift_tree.argtypes = [POINTER(union_tree)]
    db_ck_v4gift_tree.restype = c_int

# /opt/brlcad/include/brlcad/rt/tree.h: 764
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_mkbool_tree'):
    db_mkbool_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_mkbool_tree
    db_mkbool_tree.argtypes = [POINTER(struct_rt_tree_array), c_size_t, POINTER(struct_resource)]
    db_mkbool_tree.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 768
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_mkgift_tree'):
    db_mkgift_tree = _libs['/opt/brlcad/lib/librt.dylib'].db_mkgift_tree
    db_mkgift_tree.argtypes = [POINTER(struct_rt_tree_array), c_size_t, POINTER(struct_resource)]
    db_mkgift_tree.restype = POINTER(union_tree)

# /opt/brlcad/include/brlcad/rt/tree.h: 773
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_optim_tree'):
    rt_optim_tree = _libs['/opt/brlcad/lib/librt.dylib'].rt_optim_tree
    rt_optim_tree.argtypes = [POINTER(union_tree), POINTER(struct_resource)]
    rt_optim_tree.restype = None

# /opt/brlcad/include/brlcad/./rt/piece.h: 57
class struct_rt_piecestate(Structure):
    pass

struct_resource.__slots__ = [
    're_magic',
    're_cpu',
    're_seg',
    're_seg_blocks',
    're_seglen',
    're_segget',
    're_segfree',
    're_parthead',
    're_partlen',
    're_partget',
    're_partfree',
    're_solid_bitv',
    're_region_ptbl',
    're_nmgfree',
    're_boolstack',
    're_boolslen',
    're_randptr',
    're_nshootray',
    're_nmiss_model',
    're_shots',
    're_shot_hit',
    're_shot_miss',
    're_prune_solrpp',
    're_ndup',
    're_nempty_cells',
    're_pieces',
    're_piece_ndup',
    're_piece_shots',
    're_piece_shot_hit',
    're_piece_shot_miss',
    're_pieces_pending',
    're_tree_hd',
    're_tree_get',
    're_tree_malloc',
    're_tree_free',
    're_directory_hd',
    're_directory_blocks',
]
struct_resource._fields_ = [
    ('re_magic', c_uint32),
    ('re_cpu', c_int),
    ('re_seg', struct_bu_list),
    ('re_seg_blocks', struct_bu_ptbl),
    ('re_seglen', c_long),
    ('re_segget', c_long),
    ('re_segfree', c_long),
    ('re_parthead', struct_bu_list),
    ('re_partlen', c_long),
    ('re_partget', c_long),
    ('re_partfree', c_long),
    ('re_solid_bitv', struct_bu_list),
    ('re_region_ptbl', struct_bu_list),
    ('re_nmgfree', struct_bu_list),
    ('re_boolstack', POINTER(POINTER(union_tree))),
    ('re_boolslen', c_long),
    ('re_randptr', POINTER(c_float)),
    ('re_nshootray', c_long),
    ('re_nmiss_model', c_long),
    ('re_shots', c_long),
    ('re_shot_hit', c_long),
    ('re_shot_miss', c_long),
    ('re_prune_solrpp', c_long),
    ('re_ndup', c_long),
    ('re_nempty_cells', c_long),
    ('re_pieces', POINTER(struct_rt_piecestate)),
    ('re_piece_ndup', c_long),
    ('re_piece_shots', c_long),
    ('re_piece_shot_hit', c_long),
    ('re_piece_shot_miss', c_long),
    ('re_pieces_pending', struct_bu_ptbl),
    ('re_tree_hd', POINTER(union_tree)),
    ('re_tree_get', c_long),
    ('re_tree_malloc', c_long),
    ('re_tree_free', c_long),
    ('re_directory_hd', POINTER(struct_directory)),
    ('re_directory_blocks', struct_bu_ptbl),
]

# /opt/brlcad/include/brlcad/rt/resource.h: 109
try:
    rt_uniresource = (struct_resource).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_uniresource')
except:
    pass

struct_rt_db_internal.__slots__ = [
    'idb_magic',
    'idb_major_type',
    'idb_minor_type',
    'idb_meth',
    'idb_ptr',
    'idb_avs',
]
struct_rt_db_internal._fields_ = [
    ('idb_magic', c_uint32),
    ('idb_major_type', c_int),
    ('idb_minor_type', c_int),
    ('idb_meth', POINTER(struct_rt_functab)),
    ('idb_ptr', POINTER(None)),
    ('idb_avs', struct_bu_attribute_value_set),
]

# /opt/brlcad/include/brlcad/./rt/db_internal.h: 73
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_get_internal'):
    rt_db_get_internal = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_get_internal
    rt_db_get_internal.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_directory), POINTER(struct_db_i), mat_t, POINTER(struct_resource)]
    rt_db_get_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_internal.h: 88
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_put_internal'):
    rt_db_put_internal = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_put_internal
    rt_db_put_internal.argtypes = [POINTER(struct_directory), POINTER(struct_db_i), POINTER(struct_rt_db_internal), POINTER(struct_resource)]
    rt_db_put_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_internal.h: 110
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_free_internal'):
    rt_db_free_internal = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_free_internal
    rt_db_free_internal.argtypes = [POINTER(struct_rt_db_internal)]
    rt_db_free_internal.restype = None

# /opt/brlcad/include/brlcad/./rt/db_internal.h: 120
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_lookup_internal'):
    rt_db_lookup_internal = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_lookup_internal
    rt_db_lookup_internal.argtypes = [POINTER(struct_db_i), String, POINTER(POINTER(struct_directory)), POINTER(struct_rt_db_internal), c_int, POINTER(struct_resource)]
    rt_db_lookup_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/piece.h: 84
class struct_rt_piecelist(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 70
class union_cutter(Union):
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 46
class struct_cutnode(Structure):
    pass

struct_cutnode.__slots__ = [
    'cn_type',
    'cn_axis',
    'cn_point',
    'cn_l',
    'cn_r',
]
struct_cutnode._fields_ = [
    ('cn_type', c_int),
    ('cn_axis', c_int),
    ('cn_point', fastf_t),
    ('cn_l', POINTER(union_cutter)),
    ('cn_r', POINTER(union_cutter)),
]

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 54
class struct_boxnode(Structure):
    pass

struct_boxnode.__slots__ = [
    'bn_type',
    'bn_min',
    'bn_max',
    'bn_list',
    'bn_len',
    'bn_maxlen',
    'bn_piecelist',
    'bn_piecelen',
    'bn_maxpiecelen',
]
struct_boxnode._fields_ = [
    ('bn_type', c_int),
    ('bn_min', fastf_t * 3),
    ('bn_max', fastf_t * 3),
    ('bn_list', POINTER(POINTER(struct_soltab))),
    ('bn_len', c_size_t),
    ('bn_maxlen', c_size_t),
    ('bn_piecelist', POINTER(struct_rt_piecelist)),
    ('bn_piecelen', c_size_t),
    ('bn_maxpiecelen', c_size_t),
]

union_cutter.__slots__ = [
    'cut_type',
    'cut_forw',
    'cn',
    'bn',
]
union_cutter._fields_ = [
    ('cut_type', c_int),
    ('cut_forw', POINTER(union_cutter)),
    ('cn', struct_cutnode),
    ('bn', struct_boxnode),
]

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 85
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_cut'):
    rt_pr_cut = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_cut
    rt_pr_cut.argtypes = [POINTER(union_cutter), c_int]
    rt_pr_cut.restype = None

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 91
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_cut_info'):
    rt_pr_cut_info = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_cut_info
    rt_pr_cut_info.argtypes = [POINTER(struct_rt_i), String]
    rt_pr_cut_info.restype = None

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 93
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'remove_from_bsp'):
    remove_from_bsp = _libs['/opt/brlcad/lib/librt.dylib'].remove_from_bsp
    remove_from_bsp.argtypes = [POINTER(struct_soltab), POINTER(union_cutter), POINTER(struct_bn_tol)]
    remove_from_bsp.restype = None

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 96
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'insert_in_bsp'):
    insert_in_bsp = _libs['/opt/brlcad/lib/librt.dylib'].insert_in_bsp
    insert_in_bsp.argtypes = [POINTER(struct_soltab), POINTER(union_cutter)]
    insert_in_bsp.restype = None

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 98
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'fill_out_bsp'):
    fill_out_bsp = _libs['/opt/brlcad/lib/librt.dylib'].fill_out_bsp
    fill_out_bsp.argtypes = [POINTER(struct_rt_i), POINTER(union_cutter), POINTER(struct_resource), fastf_t * 6]
    fill_out_bsp.restype = None

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 103
class struct_bvh_build_node(Structure):
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 104
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'hlbvh_create'):
    hlbvh_create = _libs['/opt/brlcad/lib/librt.dylib'].hlbvh_create
    hlbvh_create.argtypes = [c_long, POINTER(struct_bu_pool), POINTER(fastf_t), POINTER(fastf_t), POINTER(c_long), c_long, POINTER(POINTER(c_long))]
    hlbvh_create.restype = POINTER(struct_bvh_build_node)

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 117
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_cut_extend'):
    rt_cut_extend = _libs['/opt/brlcad/lib/librt.dylib'].rt_cut_extend
    rt_cut_extend.argtypes = [POINTER(union_cutter), POINTER(struct_soltab), POINTER(struct_rt_i)]
    rt_cut_extend.restype = None

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 126
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_cell_n_on_ray'):
    rt_cell_n_on_ray = _libs['/opt/brlcad/lib/librt.dylib'].rt_cell_n_on_ray
    rt_cell_n_on_ray.argtypes = [POINTER(struct_application), c_int]
    rt_cell_n_on_ray.restype = POINTER(union_cutter)

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 134
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_cut_clean'):
    rt_cut_clean = _libs['/opt/brlcad/lib/librt.dylib'].rt_cut_clean
    rt_cut_clean.argtypes = [POINTER(struct_rt_i)]
    rt_cut_clean.restype = None

struct_rt_comb_internal.__slots__ = [
    'magic',
    'tree',
    'region_flag',
    'is_fastgen',
    'region_id',
    'aircode',
    'GIFTmater',
    'los',
    'rgb_valid',
    'rgb',
    'temperature',
    'shader',
    'material',
    'inherit',
]
struct_rt_comb_internal._fields_ = [
    ('magic', c_uint32),
    ('tree', POINTER(union_tree)),
    ('region_flag', c_char),
    ('is_fastgen', c_char),
    ('region_id', c_long),
    ('aircode', c_long),
    ('GIFTmater', c_long),
    ('los', c_long),
    ('rgb_valid', c_char),
    ('rgb', c_ubyte * 3),
    ('temperature', c_float),
    ('shader', struct_bu_vls),
    ('material', struct_bu_vls),
    ('inherit', c_char),
]

# /opt/brlcad/include/brlcad/./rt/nongeom.h: 107
class union_anon_88(Union):
    pass

union_anon_88.__slots__ = [
    'flt',
    'dbl',
    'int8',
    'int16',
    'int32',
    'int64',
    'uint8',
    'uint16',
    'uint32',
    'uint64',
]
union_anon_88._fields_ = [
    ('flt', POINTER(c_float)),
    ('dbl', POINTER(c_double)),
    ('int8', String),
    ('int16', POINTER(c_short)),
    ('int32', POINTER(c_int)),
    ('int64', POINTER(c_long)),
    ('uint8', POINTER(c_ubyte)),
    ('uint16', POINTER(c_ushort)),
    ('uint32', POINTER(c_uint)),
    ('uint64', POINTER(c_ulong)),
]

# /opt/brlcad/include/brlcad/./rt/nongeom.h: 103
class struct_rt_binunif_internal(Structure):
    pass

struct_rt_binunif_internal.__slots__ = [
    'magic',
    'type',
    'count',
    'u',
]
struct_rt_binunif_internal._fields_ = [
    ('magic', c_uint32),
    ('type', c_int),
    ('count', c_size_t),
    ('u', union_anon_88),
]

# /opt/brlcad/include/brlcad/./rt/nongeom.h: 127
class struct_rt_constraint_internal(Structure):
    pass

struct_rt_constraint_internal.__slots__ = [
    'magic',
    'id',
    'type',
    'expression',
]
struct_rt_constraint_internal._fields_ = [
    ('magic', c_uint32),
    ('id', c_int),
    ('type', c_int),
    ('expression', struct_bu_vls),
]

struct_rt_wdb.__slots__ = [
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
struct_rt_wdb._fields_ = [
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
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_fopen'):
    wdb_fopen = _libs['/opt/brlcad/lib/librt.dylib'].wdb_fopen
    wdb_fopen.argtypes = [String]
    wdb_fopen.restype = POINTER(struct_rt_wdb)

# /opt/brlcad/include/brlcad/./rt/wdb.h: 104
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_fopen_v'):
    wdb_fopen_v = _libs['/opt/brlcad/lib/librt.dylib'].wdb_fopen_v
    wdb_fopen_v.argtypes = [String, c_int]
    wdb_fopen_v.restype = POINTER(struct_rt_wdb)

# /opt/brlcad/include/brlcad/./rt/wdb.h: 117
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_dbopen'):
    wdb_dbopen = _libs['/opt/brlcad/lib/librt.dylib'].wdb_dbopen
    wdb_dbopen.argtypes = [POINTER(struct_db_i), c_int]
    wdb_dbopen.restype = POINTER(struct_rt_wdb)

# /opt/brlcad/include/brlcad/./rt/wdb.h: 131
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_import'):
    wdb_import = _libs['/opt/brlcad/lib/librt.dylib'].wdb_import
    wdb_import.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_rt_db_internal), String, mat_t]
    wdb_import.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 144
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_export_external'):
    wdb_export_external = _libs['/opt/brlcad/lib/librt.dylib'].wdb_export_external
    wdb_export_external.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_bu_external), String, c_int, c_ubyte]
    wdb_export_external.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 166
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_put_internal'):
    wdb_put_internal = _libs['/opt/brlcad/lib/librt.dylib'].wdb_put_internal
    wdb_put_internal.argtypes = [POINTER(struct_rt_wdb), String, POINTER(struct_rt_db_internal), c_double]
    wdb_put_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 190
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_export'):
    wdb_export = _libs['/opt/brlcad/lib/librt.dylib'].wdb_export
    wdb_export.argtypes = [POINTER(struct_rt_wdb), String, POINTER(None), c_int, c_double]
    wdb_export.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 195
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_init'):
    wdb_init = _libs['/opt/brlcad/lib/librt.dylib'].wdb_init
    wdb_init.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_db_i), c_int]
    wdb_init.restype = None

# /opt/brlcad/include/brlcad/./rt/wdb.h: 204
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_close'):
    wdb_close = _libs['/opt/brlcad/lib/librt.dylib'].wdb_close
    wdb_close.argtypes = [POINTER(struct_rt_wdb)]
    wdb_close.restype = None

# /opt/brlcad/include/brlcad/./rt/wdb.h: 215
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_import_from_path'):
    wdb_import_from_path = _libs['/opt/brlcad/lib/librt.dylib'].wdb_import_from_path
    wdb_import_from_path.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), String, POINTER(struct_rt_wdb)]
    wdb_import_from_path.restype = c_int

# /opt/brlcad/include/brlcad/./rt/wdb.h: 231
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'wdb_import_from_path2'):
    wdb_import_from_path2 = _libs['/opt/brlcad/lib/librt.dylib'].wdb_import_from_path2
    wdb_import_from_path2.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), String, POINTER(struct_rt_wdb), matp_t]
    wdb_import_from_path2.restype = c_int

# /opt/brlcad/include/brlcad/./rt/piece.h: 41
class struct_rt_htbl(Structure):
    pass

struct_rt_htbl.__slots__ = [
    'l',
    'end',
    'blen',
    'hits',
]
struct_rt_htbl._fields_ = [
    ('l', struct_bu_list),
    ('end', c_size_t),
    ('blen', c_size_t),
    ('hits', POINTER(struct_hit)),
]

struct_rt_piecestate.__slots__ = [
    'magic',
    'ray_seqno',
    'stp',
    'shot',
    'mindist',
    'maxdist',
    'htab',
    'cutp',
]
struct_rt_piecestate._fields_ = [
    ('magic', c_uint32),
    ('ray_seqno', c_long),
    ('stp', POINTER(struct_soltab)),
    ('shot', POINTER(struct_bu_bitv)),
    ('mindist', fastf_t),
    ('maxdist', fastf_t),
    ('htab', struct_rt_htbl),
    ('cutp', POINTER(union_cutter)),
]

struct_rt_piecelist.__slots__ = [
    'magic',
    'npieces',
    'pieces',
    'stp',
]
struct_rt_piecelist._fields_ = [
    ('magic', c_uint32),
    ('npieces', c_size_t),
    ('pieces', POINTER(c_long)),
    ('stp', POINTER(struct_soltab)),
]

# /opt/brlcad/include/brlcad/./rt/global.h: 39
class struct_rt_g(Structure):
    pass

struct_rt_g.__slots__ = [
    'debug',
    'rtg_parallel',
    'rtg_vlfree',
    'rtg_headwdb',
]
struct_rt_g._fields_ = [
    ('debug', c_uint32),
    ('rtg_parallel', c_int8),
    ('rtg_vlfree', struct_bu_list),
    ('rtg_headwdb', struct_rt_wdb),
]

# /opt/brlcad/include/brlcad/./rt/global.h: 51
try:
    RTG = (struct_rt_g).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'RTG')
except:
    pass

struct_rt_i.__slots__ = [
    'rti_magic',
    'useair',
    'rti_save_overlaps',
    'rti_dont_instance',
    'rti_hasty_prep',
    'rti_nlights',
    'rti_prismtrace',
    'rti_region_fix_file',
    'rti_space_partition',
    'rti_tol',
    'rti_ttol',
    'rti_max_beam_radius',
    'mdl_min',
    'mdl_max',
    'rti_pmin',
    'rti_pmax',
    'rti_radius',
    'rti_dbip',
    'needprep',
    'Regions',
    'HeadRegion',
    'Orca_hash_tbl',
    'delete_regs',
    'nregions',
    'nsolids',
    'rti_nrays',
    'nmiss_model',
    'nshots',
    'nmiss',
    'nhits',
    'nmiss_tree',
    'nmiss_solid',
    'ndup',
    'nempty_cells',
    'rti_CutHead',
    'rti_inf_box',
    'rti_CutFree',
    'rti_busy_cutter_nodes',
    'rti_cuts_waiting',
    'rti_cut_maxlen',
    'rti_ncut_by_type',
    'rti_cut_totobj',
    'rti_cut_maxdepth',
    'rti_sol_by_type',
    'rti_nsol_by_type',
    'rti_maxsol_by_type',
    'rti_air_discards',
    'rti_hist_cellsize',
    'rti_hist_cell_pieces',
    'rti_hist_cutdepth',
    'rti_Solids',
    'rti_solidheads',
    'rti_resources',
    'rti_cutlen',
    'rti_cutdepth',
    'rti_treetop',
    'rti_uses',
    'rti_nsolids_with_pieces',
    'rti_add_to_new_solids_list',
    'rti_new_solids',
]
struct_rt_i._fields_ = [
    ('rti_magic', c_uint32),
    ('useair', c_int),
    ('rti_save_overlaps', c_int),
    ('rti_dont_instance', c_int),
    ('rti_hasty_prep', c_int),
    ('rti_nlights', c_int),
    ('rti_prismtrace', c_int),
    ('rti_region_fix_file', String),
    ('rti_space_partition', c_int),
    ('rti_tol', struct_bn_tol),
    ('rti_ttol', struct_rt_tess_tol),
    ('rti_max_beam_radius', fastf_t),
    ('mdl_min', point_t),
    ('mdl_max', point_t),
    ('rti_pmin', point_t),
    ('rti_pmax', point_t),
    ('rti_radius', c_double),
    ('rti_dbip', POINTER(struct_db_i)),
    ('needprep', c_int),
    ('Regions', POINTER(POINTER(struct_region))),
    ('HeadRegion', struct_bu_list),
    ('Orca_hash_tbl', POINTER(None)),
    ('delete_regs', struct_bu_ptbl),
    ('nregions', c_size_t),
    ('nsolids', c_size_t),
    ('rti_nrays', c_size_t),
    ('nmiss_model', c_size_t),
    ('nshots', c_size_t),
    ('nmiss', c_size_t),
    ('nhits', c_size_t),
    ('nmiss_tree', c_size_t),
    ('nmiss_solid', c_size_t),
    ('ndup', c_size_t),
    ('nempty_cells', c_size_t),
    ('rti_CutHead', union_cutter),
    ('rti_inf_box', union_cutter),
    ('rti_CutFree', POINTER(union_cutter)),
    ('rti_busy_cutter_nodes', struct_bu_ptbl),
    ('rti_cuts_waiting', struct_bu_ptbl),
    ('rti_cut_maxlen', c_int),
    ('rti_ncut_by_type', c_int * (2 + 1)),
    ('rti_cut_totobj', c_int),
    ('rti_cut_maxdepth', c_int),
    ('rti_sol_by_type', POINTER(POINTER(struct_soltab)) * (46 + 1)),
    ('rti_nsol_by_type', c_int * (46 + 1)),
    ('rti_maxsol_by_type', c_int),
    ('rti_air_discards', c_int),
    ('rti_hist_cellsize', struct_bu_hist),
    ('rti_hist_cell_pieces', struct_bu_hist),
    ('rti_hist_cutdepth', struct_bu_hist),
    ('rti_Solids', POINTER(POINTER(struct_soltab))),
    ('rti_solidheads', struct_bu_list * 8192),
    ('rti_resources', struct_bu_ptbl),
    ('rti_cutlen', c_size_t),
    ('rti_cutdepth', c_size_t),
    ('rti_treetop', String),
    ('rti_uses', c_size_t),
    ('rti_nsolids_with_pieces', c_size_t),
    ('rti_add_to_new_solids_list', c_int),
    ('rti_new_solids', struct_bu_ptbl),
]

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 157
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_new_rti'):
    rt_new_rti = _libs['/opt/brlcad/lib/librt.dylib'].rt_new_rti
    rt_new_rti.argtypes = [POINTER(struct_db_i)]
    rt_new_rti.restype = POINTER(struct_rt_i)

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 158
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_free_rti'):
    rt_free_rti = _libs['/opt/brlcad/lib/librt.dylib'].rt_free_rti
    rt_free_rti.argtypes = [POINTER(struct_rt_i)]
    rt_free_rti.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 159
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_prep'):
    rt_prep = _libs['/opt/brlcad/lib/librt.dylib'].rt_prep
    rt_prep.argtypes = [POINTER(struct_rt_i)]
    rt_prep.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 160
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_prep_parallel'):
    rt_prep_parallel = _libs['/opt/brlcad/lib/librt.dylib'].rt_prep_parallel
    rt_prep_parallel.argtypes = [POINTER(struct_rt_i), c_int]
    rt_prep_parallel.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 176
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gettree'):
    rt_gettree = _libs['/opt/brlcad/lib/librt.dylib'].rt_gettree
    rt_gettree.argtypes = [POINTER(struct_rt_i), String]
    rt_gettree.restype = c_int

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 178
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gettrees'):
    rt_gettrees = _libs['/opt/brlcad/lib/librt.dylib'].rt_gettrees
    rt_gettrees.argtypes = [POINTER(struct_rt_i), c_int, POINTER(POINTER(c_char)), c_int]
    rt_gettrees.restype = c_int

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 200
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gettrees_and_attrs'):
    rt_gettrees_and_attrs = _libs['/opt/brlcad/lib/librt.dylib'].rt_gettrees_and_attrs
    rt_gettrees_and_attrs.argtypes = [POINTER(struct_rt_i), POINTER(POINTER(c_char)), c_int, POINTER(POINTER(c_char)), c_int]
    rt_gettrees_and_attrs.restype = c_int

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 237
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gettrees_muves'):
    rt_gettrees_muves = _libs['/opt/brlcad/lib/librt.dylib'].rt_gettrees_muves
    rt_gettrees_muves.argtypes = [POINTER(struct_rt_i), POINTER(POINTER(c_char)), c_int, POINTER(POINTER(c_char)), c_int]
    rt_gettrees_muves.restype = c_int

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 243
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_load_attrs'):
    rt_load_attrs = _libs['/opt/brlcad/lib/librt.dylib'].rt_load_attrs
    rt_load_attrs.argtypes = [POINTER(struct_rt_i), POINTER(POINTER(c_char))]
    rt_load_attrs.restype = c_int

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 248
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_partitions'):
    rt_pr_partitions = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_partitions
    rt_pr_partitions.argtypes = [POINTER(struct_rt_i), POINTER(struct_partition), String]
    rt_pr_partitions.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 260
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_find_solid'):
    rt_find_solid = _libs['/opt/brlcad/lib/librt.dylib'].rt_find_solid
    rt_find_solid.argtypes = [POINTER(struct_rt_i), String]
    rt_find_solid.restype = POINTER(struct_soltab)

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 279
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_init_resource'):
    rt_init_resource = _libs['/opt/brlcad/lib/librt.dylib'].rt_init_resource
    rt_init_resource.argtypes = [POINTER(struct_resource), c_int, POINTER(struct_rt_i)]
    rt_init_resource.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 282
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_clean_resource'):
    rt_clean_resource = _libs['/opt/brlcad/lib/librt.dylib'].rt_clean_resource
    rt_clean_resource.argtypes = [POINTER(struct_rt_i), POINTER(struct_resource)]
    rt_clean_resource.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 284
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_clean_resource_complete'):
    rt_clean_resource_complete = _libs['/opt/brlcad/lib/librt.dylib'].rt_clean_resource_complete
    rt_clean_resource_complete.argtypes = [POINTER(struct_rt_i), POINTER(struct_resource)]
    rt_clean_resource_complete.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 296
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_clean'):
    rt_clean = _libs['/opt/brlcad/lib/librt.dylib'].rt_clean
    rt_clean.argtypes = [POINTER(struct_rt_i)]
    rt_clean.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 297
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_del_regtree'):
    rt_del_regtree = _libs['/opt/brlcad/lib/librt.dylib'].rt_del_regtree
    rt_del_regtree.argtypes = [POINTER(struct_rt_i), POINTER(struct_region), POINTER(struct_resource)]
    rt_del_regtree.restype = c_int

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 301
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_ck'):
    rt_ck = _libs['/opt/brlcad/lib/librt.dylib'].rt_ck
    rt_ck.argtypes = [POINTER(struct_rt_i)]
    rt_ck.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 304
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_tree_val'):
    rt_pr_tree_val = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_tree_val
    rt_pr_tree_val.argtypes = [POINTER(union_tree), POINTER(struct_partition), c_int, c_int]
    rt_pr_tree_val.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 308
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_pt'):
    rt_pr_pt = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_pt
    rt_pr_pt.argtypes = [POINTER(struct_rt_i), POINTER(struct_partition)]
    rt_pr_pt.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 310
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_pt_vls'):
    rt_pr_pt_vls = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_pt_vls
    rt_pr_pt_vls.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_i), POINTER(struct_partition)]
    rt_pr_pt_vls.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 313
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_pt'):
    rt_pr_pt = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_pt
    rt_pr_pt.argtypes = [POINTER(struct_rt_i), POINTER(struct_partition)]
    rt_pr_pt.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 326
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_cut_it'):
    rt_cut_it = _libs['/opt/brlcad/lib/librt.dylib'].rt_cut_it
    rt_cut_it.argtypes = [POINTER(struct_rt_i), c_int]
    rt_cut_it.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 335
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_fr_cut'):
    rt_fr_cut = _libs['/opt/brlcad/lib/librt.dylib'].rt_fr_cut
    rt_fr_cut.argtypes = [POINTER(struct_rt_i), POINTER(union_cutter)]
    rt_fr_cut.restype = None

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 345
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_regionfix'):
    rt_regionfix = _libs['/opt/brlcad/lib/librt.dylib'].rt_regionfix
    rt_regionfix.argtypes = [POINTER(struct_rt_i)]
    rt_regionfix.restype = None

# /opt/brlcad/include/brlcad/./rt/view.h: 49
class struct_rt_view_info(Structure):
    pass

struct_rt_view_info.__slots__ = [
    'vhead',
    'tol',
    'point_spacing',
    'curve_spacing',
    'bot_threshold',
]
struct_rt_view_info._fields_ = [
    ('vhead', POINTER(struct_bu_list)),
    ('tol', POINTER(struct_bn_tol)),
    ('point_spacing', fastf_t),
    ('curve_spacing', fastf_t),
    ('bot_threshold', c_size_t),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 78
class struct_rt_selection(Structure):
    pass

struct_rt_selection.__slots__ = [
    'obj',
]
struct_rt_selection._fields_ = [
    ('obj', POINTER(None)),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 86
class struct_rt_selection_set(Structure):
    pass

struct_rt_selection_set.__slots__ = [
    'selections',
    'free_selection',
]
struct_rt_selection_set._fields_ = [
    ('selections', struct_bu_ptbl),
    ('free_selection', CFUNCTYPE(UNCHECKED(None), POINTER(struct_rt_selection))),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 104
class struct_rt_object_selections(Structure):
    pass

struct_rt_object_selections.__slots__ = [
    'sets',
]
struct_rt_object_selections._fields_ = [
    ('sets', POINTER(struct_bu_hash_tbl)),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 117
class struct_rt_selection_query(Structure):
    pass

struct_rt_selection_query.__slots__ = [
    'start',
    'dir',
    'sorting',
]
struct_rt_selection_query._fields_ = [
    ('start', point_t),
    ('dir', vect_t),
    ('sorting', c_int),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 132
class struct_rt_selection_translation(Structure):
    pass

struct_rt_selection_translation.__slots__ = [
    'dx',
    'dy',
    'dz',
]
struct_rt_selection_translation._fields_ = [
    ('dx', fastf_t),
    ('dy', fastf_t),
    ('dz', fastf_t),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 148
class union_anon_89(Union):
    pass

union_anon_89.__slots__ = [
    'tran',
]
union_anon_89._fields_ = [
    ('tran', struct_rt_selection_translation),
]

# /opt/brlcad/include/brlcad/./rt/view.h: 144
class struct_rt_selection_operation(Structure):
    pass

struct_rt_selection_operation.__slots__ = [
    'type',
    'parameters',
]
struct_rt_selection_operation._fields_ = [
    ('type', c_int),
    ('parameters', union_anon_89),
]

struct_rt_functab.__slots__ = [
    'magic',
    'ft_name',
    'ft_label',
    'ft_use_rpp',
    'ft_prep',
    'ft_shot',
    'ft_print',
    'ft_norm',
    'ft_piece_shot',
    'ft_piece_hitsegs',
    'ft_uv',
    'ft_curve',
    'ft_classify',
    'ft_free',
    'ft_plot',
    'ft_adaptive_plot',
    'ft_vshot',
    'ft_tessellate',
    'ft_tnurb',
    'ft_brep',
    'ft_import5',
    'ft_export5',
    'ft_import4',
    'ft_export4',
    'ft_ifree',
    'ft_describe',
    'ft_xform',
    'ft_parsetab',
    'ft_internal_size',
    'ft_internal_magic',
    'ft_get',
    'ft_adjust',
    'ft_form',
    'ft_make',
    'ft_params',
    'ft_bbox',
    'ft_volume',
    'ft_surf_area',
    'ft_centroid',
    'ft_oriented_bbox',
    'ft_find_selections',
    'ft_evaluate_selection',
    'ft_process_selection',
    'ft_prep_serialize',
]
struct_rt_functab._fields_ = [
    ('magic', c_uint32),
    ('ft_name', c_char * 17),
    ('ft_label', c_char * 9),
    ('ft_use_rpp', c_int),
    ('ft_prep', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_soltab), POINTER(struct_rt_db_internal), POINTER(struct_rt_i))),
    ('ft_shot', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_soltab), POINTER(struct_xray), POINTER(struct_application), POINTER(struct_seg))),
    ('ft_print', CFUNCTYPE(UNCHECKED(None), POINTER(struct_soltab))),
    ('ft_norm', CFUNCTYPE(UNCHECKED(None), POINTER(struct_hit), POINTER(struct_soltab), POINTER(struct_xray))),
    ('ft_piece_shot', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_piecestate), POINTER(struct_rt_piecelist), c_double, POINTER(struct_xray), POINTER(struct_application), POINTER(struct_seg))),
    ('ft_piece_hitsegs', CFUNCTYPE(UNCHECKED(None), POINTER(struct_rt_piecestate), POINTER(struct_seg), POINTER(struct_application))),
    ('ft_uv', CFUNCTYPE(UNCHECKED(None), POINTER(struct_application), POINTER(struct_soltab), POINTER(struct_hit), POINTER(struct_uvcoord))),
    ('ft_curve', CFUNCTYPE(UNCHECKED(None), POINTER(struct_curvature), POINTER(struct_hit), POINTER(struct_soltab))),
    ('ft_classify', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_soltab), vect_t, vect_t, POINTER(struct_bn_tol))),
    ('ft_free', CFUNCTYPE(UNCHECKED(None), POINTER(struct_soltab))),
    ('ft_plot', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol), POINTER(struct_rt_view_info))),
    ('ft_adaptive_plot', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_db_internal), POINTER(struct_rt_view_info))),
    ('ft_vshot', CFUNCTYPE(UNCHECKED(None), POINTER(POINTER(struct_soltab)), POINTER(POINTER(struct_xray)), POINTER(struct_seg), c_int, POINTER(struct_application))),
    ('ft_tessellate', CFUNCTYPE(UNCHECKED(c_int), POINTER(POINTER(struct_nmgregion)), POINTER(struct_model), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol))),
    ('ft_tnurb', CFUNCTYPE(UNCHECKED(c_int), POINTER(POINTER(struct_nmgregion)), POINTER(struct_model), POINTER(struct_rt_db_internal), POINTER(struct_bn_tol))),
    ('ft_brep', CFUNCTYPE(UNCHECKED(None), POINTER(POINTER(ON_Brep)), POINTER(struct_rt_db_internal), POINTER(struct_bn_tol))),
    ('ft_import5', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_db_internal), POINTER(struct_bu_external), mat_t, POINTER(struct_db_i), POINTER(struct_resource))),
    ('ft_export5', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_external), POINTER(struct_rt_db_internal), c_double, POINTER(struct_db_i), POINTER(struct_resource))),
    ('ft_import4', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_db_internal), POINTER(struct_bu_external), mat_t, POINTER(struct_db_i), POINTER(struct_resource))),
    ('ft_export4', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_external), POINTER(struct_rt_db_internal), c_double, POINTER(struct_db_i), POINTER(struct_resource))),
    ('ft_ifree', CFUNCTYPE(UNCHECKED(None), POINTER(struct_rt_db_internal))),
    ('ft_describe', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), c_int, c_double)),
    ('ft_xform', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_db_internal), mat_t, POINTER(struct_rt_db_internal), c_int, POINTER(struct_db_i))),
    ('ft_parsetab', POINTER(struct_bu_structparse)),
    ('ft_internal_size', c_size_t),
    ('ft_internal_magic', c_uint32),
    ('ft_get', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), String)),
    ('ft_adjust', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), c_int, POINTER(POINTER(c_char)))),
    ('ft_form', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_vls), POINTER(struct_rt_functab))),
    ('ft_make', CFUNCTYPE(UNCHECKED(None), POINTER(struct_rt_functab), POINTER(struct_rt_db_internal))),
    ('ft_params', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_pc_pc_set), POINTER(struct_rt_db_internal))),
    ('ft_bbox', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_db_internal), POINTER(point_t), POINTER(point_t), POINTER(struct_bn_tol))),
    ('ft_volume', CFUNCTYPE(UNCHECKED(None), POINTER(fastf_t), POINTER(struct_rt_db_internal))),
    ('ft_surf_area', CFUNCTYPE(UNCHECKED(None), POINTER(fastf_t), POINTER(struct_rt_db_internal))),
    ('ft_centroid', CFUNCTYPE(UNCHECKED(None), POINTER(point_t), POINTER(struct_rt_db_internal))),
    ('ft_oriented_bbox', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_arb_internal), POINTER(struct_rt_db_internal), fastf_t)),
    ('ft_find_selections', CFUNCTYPE(UNCHECKED(POINTER(struct_rt_selection_set)), POINTER(struct_rt_db_internal), POINTER(struct_rt_selection_query))),
    ('ft_evaluate_selection', CFUNCTYPE(UNCHECKED(POINTER(struct_rt_selection)), POINTER(struct_rt_db_internal), c_int, POINTER(struct_rt_selection), POINTER(struct_rt_selection))),
    ('ft_process_selection', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_rt_db_internal), POINTER(struct_db_i), POINTER(struct_rt_selection), POINTER(struct_rt_selection_operation))),
    ('ft_prep_serialize', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_soltab), POINTER(struct_rt_db_internal), POINTER(struct_bu_external), POINTER(c_size_t))),
]

# /opt/brlcad/include/brlcad/rt/functab.h: 270
try:
    OBJ = (POINTER(struct_rt_functab)).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'OBJ')
except:
    pass

# /opt/brlcad/include/brlcad/rt/functab.h: 274
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_get_functab_by_label'):
    rt_get_functab_by_label = _libs['/opt/brlcad/lib/librt.dylib'].rt_get_functab_by_label
    rt_get_functab_by_label.argtypes = [String]
    rt_get_functab_by_label.restype = POINTER(struct_rt_functab)

# /opt/brlcad/include/brlcad/./rt/func.h: 63
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_prep'):
    rt_obj_prep = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_prep
    rt_obj_prep.argtypes = [POINTER(struct_soltab), POINTER(struct_rt_db_internal), POINTER(struct_rt_i)]
    rt_obj_prep.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 68
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_shot'):
    rt_obj_shot = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_shot
    rt_obj_shot.argtypes = [POINTER(struct_soltab), POINTER(struct_xray), POINTER(struct_application), POINTER(struct_seg)]
    rt_obj_shot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 73
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_obj_piece_shot'):
        continue
    rt_obj_piece_shot = _lib.rt_obj_piece_shot
    rt_obj_piece_shot.argtypes = [POINTER(struct_rt_piecestate), POINTER(struct_rt_piecelist), c_double, POINTER(struct_xray), POINTER(struct_application), POINTER(struct_seg)]
    rt_obj_piece_shot.restype = c_int
    break

# /opt/brlcad/include/brlcad/./rt/func.h: 78
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_obj_piece_hitsegs'):
        continue
    rt_obj_piece_hitsegs = _lib.rt_obj_piece_hitsegs
    rt_obj_piece_hitsegs.argtypes = [POINTER(struct_rt_piecestate), POINTER(struct_seg), POINTER(struct_application)]
    rt_obj_piece_hitsegs.restype = c_int
    break

# /opt/brlcad/include/brlcad/./rt/func.h: 83
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_print'):
    rt_obj_print = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_print
    rt_obj_print.argtypes = [POINTER(struct_soltab)]
    rt_obj_print.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 88
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_norm'):
    rt_obj_norm = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_norm
    rt_obj_norm.argtypes = [POINTER(struct_hit), POINTER(struct_soltab), POINTER(struct_xray)]
    rt_obj_norm.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 93
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_uv'):
    rt_obj_uv = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_uv
    rt_obj_uv.argtypes = [POINTER(struct_application), POINTER(struct_soltab), POINTER(struct_hit), POINTER(struct_uvcoord)]
    rt_obj_uv.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 98
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_curve'):
    rt_obj_curve = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_curve
    rt_obj_curve.argtypes = [POINTER(struct_curvature), POINTER(struct_hit), POINTER(struct_soltab)]
    rt_obj_curve.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 103
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_obj_class'):
        continue
    rt_obj_class = _lib.rt_obj_class
    rt_obj_class.argtypes = []
    rt_obj_class.restype = c_int
    break

# /opt/brlcad/include/brlcad/./rt/func.h: 108
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_free'):
    rt_obj_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_free
    rt_obj_free.argtypes = [POINTER(struct_soltab)]
    rt_obj_free.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 113
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_plot'):
    rt_obj_plot = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_plot
    rt_obj_plot.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol)]
    rt_obj_plot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 118
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_vshot'):
    rt_obj_vshot = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_vshot
    rt_obj_vshot.argtypes = [POINTER(POINTER(struct_soltab)), POINTER(POINTER(struct_xray)), POINTER(struct_seg), c_int, POINTER(struct_application)]
    rt_obj_vshot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 123
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_tess'):
    rt_obj_tess = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_tess
    rt_obj_tess.argtypes = [POINTER(POINTER(struct_nmgregion)), POINTER(struct_model), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol)]
    rt_obj_tess.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 128
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_tnurb'):
    rt_obj_tnurb = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_tnurb
    rt_obj_tnurb.argtypes = [POINTER(POINTER(struct_nmgregion)), POINTER(struct_model), POINTER(struct_rt_db_internal), POINTER(struct_bn_tol)]
    rt_obj_tnurb.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 133
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_import'):
    rt_obj_import = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_import
    rt_obj_import.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_bu_external), mat_t, POINTER(struct_db_i), POINTER(struct_resource)]
    rt_obj_import.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 138
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_export'):
    rt_obj_export = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_export
    rt_obj_export.argtypes = [POINTER(struct_bu_external), POINTER(struct_rt_db_internal), c_double, POINTER(struct_db_i), POINTER(struct_resource)]
    rt_obj_export.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 143
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_ifree'):
    rt_obj_ifree = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_ifree
    rt_obj_ifree.argtypes = [POINTER(struct_rt_db_internal)]
    rt_obj_ifree.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 148
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_get'):
    rt_obj_get = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_get
    rt_obj_get.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), String]
    rt_obj_get.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 153
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_adjust'):
    rt_obj_adjust = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_adjust
    rt_obj_adjust.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), c_int, POINTER(POINTER(c_char))]
    rt_obj_adjust.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 158
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_describe'):
    rt_obj_describe = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_describe
    rt_obj_describe.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), c_int, c_double]
    rt_obj_describe.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 163
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_make'):
    rt_obj_make = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_make
    rt_obj_make.argtypes = [POINTER(struct_rt_functab), POINTER(struct_rt_db_internal)]
    rt_obj_make.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 168
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_xform'):
    rt_obj_xform = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_xform
    rt_obj_xform.argtypes = [POINTER(struct_rt_db_internal), mat_t, POINTER(struct_rt_db_internal), c_int, POINTER(struct_db_i)]
    rt_obj_xform.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 173
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_params'):
    rt_obj_params = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_params
    rt_obj_params.argtypes = [POINTER(struct_pc_pc_set), POINTER(struct_rt_db_internal)]
    rt_obj_params.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 178
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_mirror'):
    rt_obj_mirror = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_mirror
    rt_obj_mirror.argtypes = [POINTER(struct_rt_db_internal), POINTER(plane_t)]
    rt_obj_mirror.restype = c_int

# /opt/brlcad/include/brlcad/./rt/func.h: 183
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_obj_prep_serialize'):
    rt_obj_prep_serialize = _libs['/opt/brlcad/lib/librt.dylib'].rt_obj_prep_serialize
    rt_obj_prep_serialize.argtypes = [POINTER(struct_soltab), POINTER(struct_rt_db_internal), POINTER(struct_bu_external), POINTER(c_size_t)]
    rt_obj_prep_serialize.restype = c_int

# /opt/brlcad/include/brlcad/./rt/private.h: 42
class struct_rt_pt_node(Structure):
    pass

struct_rt_pt_node.__slots__ = [
    'p',
    'next',
]
struct_rt_pt_node._fields_ = [
    ('p', point_t),
    ('next', POINTER(struct_rt_pt_node)),
]

# /opt/brlcad/include/brlcad/./rt/private.h: 51
class struct_rt_shootray_status(Structure):
    pass

struct_rt_shootray_status.__slots__ = [
    'dist_corr',
    'odist_corr',
    'box_start',
    'obox_start',
    'box_end',
    'obox_end',
    'model_start',
    'model_end',
    'newray',
    'ap',
    'resp',
    'inv_dir',
    'abs_inv_dir',
    'rstep',
    'lastcut',
    'lastcell',
    'curcut',
    'curmin',
    'curmax',
    'igrid',
    'tv',
    'out_axis',
    'old_status',
    'box_num',
]
struct_rt_shootray_status._fields_ = [
    ('dist_corr', fastf_t),
    ('odist_corr', fastf_t),
    ('box_start', fastf_t),
    ('obox_start', fastf_t),
    ('box_end', fastf_t),
    ('obox_end', fastf_t),
    ('model_start', fastf_t),
    ('model_end', fastf_t),
    ('newray', struct_xray),
    ('ap', POINTER(struct_application)),
    ('resp', POINTER(struct_resource)),
    ('inv_dir', vect_t),
    ('abs_inv_dir', vect_t),
    ('rstep', c_int * 3),
    ('lastcut', POINTER(union_cutter)),
    ('lastcell', POINTER(union_cutter)),
    ('curcut', POINTER(union_cutter)),
    ('curmin', point_t),
    ('curmax', point_t),
    ('igrid', c_int * 3),
    ('tv', vect_t),
    ('out_axis', c_int),
    ('old_status', POINTER(struct_rt_shootray_status)),
    ('box_num', c_int),
]

# /opt/brlcad/include/brlcad/./rt/overlap.h: 60
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_default_multioverlap'):
    rt_default_multioverlap = _libs['/opt/brlcad/lib/librt.dylib'].rt_default_multioverlap
    rt_default_multioverlap.argtypes = [POINTER(struct_application), POINTER(struct_partition), POINTER(struct_bu_ptbl), POINTER(struct_partition)]
    rt_default_multioverlap.restype = None

# /opt/brlcad/include/brlcad/./rt/overlap.h: 69
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_silent_logoverlap'):
    rt_silent_logoverlap = _libs['/opt/brlcad/lib/librt.dylib'].rt_silent_logoverlap
    rt_silent_logoverlap.argtypes = [POINTER(struct_application), POINTER(struct_partition), POINTER(struct_bu_ptbl), POINTER(struct_partition)]
    rt_silent_logoverlap.restype = None

# /opt/brlcad/include/brlcad/./rt/overlap.h: 80
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_default_logoverlap'):
    rt_default_logoverlap = _libs['/opt/brlcad/lib/librt.dylib'].rt_default_logoverlap
    rt_default_logoverlap.argtypes = [POINTER(struct_application), POINTER(struct_partition), POINTER(struct_bu_ptbl), POINTER(struct_partition)]
    rt_default_logoverlap.restype = None

# /opt/brlcad/include/brlcad/./rt/overlap.h: 89
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_rebuild_overlaps'):
    rt_rebuild_overlaps = _libs['/opt/brlcad/lib/librt.dylib'].rt_rebuild_overlaps
    rt_rebuild_overlaps.argtypes = [POINTER(struct_partition), POINTER(struct_application), c_int]
    rt_rebuild_overlaps.restype = None

# /opt/brlcad/include/brlcad/./rt/overlap.h: 101
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_defoverlap'):
    rt_defoverlap = _libs['/opt/brlcad/lib/librt.dylib'].rt_defoverlap
    rt_defoverlap.argtypes = [POINTER(struct_application), POINTER(struct_partition), POINTER(struct_region), POINTER(struct_region), POINTER(struct_partition)]
    rt_defoverlap.restype = c_int

# /opt/brlcad/include/brlcad/./rt/pattern.h: 45
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_raybundle_maker'):
    rt_raybundle_maker = _libs['/opt/brlcad/lib/librt.dylib'].rt_raybundle_maker
    rt_raybundle_maker.argtypes = [POINTER(struct_xray), c_double, POINTER(fastf_t), POINTER(fastf_t), c_int, c_int]
    rt_raybundle_maker.restype = c_int

enum_anon_90 = c_int # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_RECT_ORTHOGRID = 0 # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_RECT_PERSPGRID = (RT_PATTERN_RECT_ORTHOGRID + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_CIRC_ORTHOGRID = (RT_PATTERN_RECT_PERSPGRID + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_CIRC_PERSPGRID = (RT_PATTERN_CIRC_ORTHOGRID + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_CIRC_SPIRAL = (RT_PATTERN_CIRC_PERSPGRID + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_ELLIPSE_ORTHOGRID = (RT_PATTERN_CIRC_SPIRAL + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_ELLIPSE_PERSPGRID = (RT_PATTERN_ELLIPSE_ORTHOGRID + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_CIRC_LAYERS = (RT_PATTERN_ELLIPSE_PERSPGRID + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_SPH_LAYERS = (RT_PATTERN_CIRC_LAYERS + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_SPH_QRAND = (RT_PATTERN_SPH_LAYERS + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

RT_PATTERN_UNKNOWN = (RT_PATTERN_SPH_QRAND + 1) # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

rt_pattern_t = enum_anon_90 # /opt/brlcad/include/brlcad/./rt/pattern.h: 61

# /opt/brlcad/include/brlcad/./rt/pattern.h: 68
class struct_rt_pattern_data(Structure):
    pass

struct_rt_pattern_data.__slots__ = [
    'rays',
    'ray_cnt',
    'center_pt',
    'center_dir',
    'vn',
    'n_vec',
    'pn',
    'n_p',
]
struct_rt_pattern_data._fields_ = [
    ('rays', POINTER(fastf_t)),
    ('ray_cnt', c_size_t),
    ('center_pt', point_t),
    ('center_dir', vect_t),
    ('vn', c_size_t),
    ('n_vec', POINTER(vect_t)),
    ('pn', c_size_t),
    ('n_p', POINTER(fastf_t)),
]

# /opt/brlcad/include/brlcad/./rt/pattern.h: 224
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pattern'):
    rt_pattern = _libs['/opt/brlcad/lib/librt.dylib'].rt_pattern
    rt_pattern.argtypes = [POINTER(struct_rt_pattern_data), rt_pattern_t]
    rt_pattern.restype = c_int

# /opt/brlcad/include/brlcad/./rt/pattern.h: 235
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gen_elliptical_grid'):
    rt_gen_elliptical_grid = _libs['/opt/brlcad/lib/librt.dylib'].rt_gen_elliptical_grid
    rt_gen_elliptical_grid.argtypes = [POINTER(struct_xrays), POINTER(struct_xray), POINTER(fastf_t), POINTER(fastf_t), fastf_t]
    rt_gen_elliptical_grid.restype = c_int

# /opt/brlcad/include/brlcad/./rt/pattern.h: 248
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gen_circular_grid'):
    rt_gen_circular_grid = _libs['/opt/brlcad/lib/librt.dylib'].rt_gen_circular_grid
    rt_gen_circular_grid.argtypes = [POINTER(struct_xrays), POINTER(struct_xray), fastf_t, POINTER(fastf_t), fastf_t]
    rt_gen_circular_grid.restype = c_int

# /opt/brlcad/include/brlcad/./rt/pattern.h: 262
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gen_conic'):
    rt_gen_conic = _libs['/opt/brlcad/lib/librt.dylib'].rt_gen_conic
    rt_gen_conic.argtypes = [POINTER(struct_xrays), POINTER(struct_xray), fastf_t, vect_t, c_int]
    rt_gen_conic.restype = c_int

# /opt/brlcad/include/brlcad/./rt/pattern.h: 276
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gen_frustum'):
    rt_gen_frustum = _libs['/opt/brlcad/lib/librt.dylib'].rt_gen_frustum
    rt_gen_frustum.argtypes = [POINTER(struct_xrays), POINTER(struct_xray), vect_t, vect_t, fastf_t, fastf_t, fastf_t, fastf_t]
    rt_gen_frustum.restype = c_int

# /opt/brlcad/include/brlcad/./rt/pattern.h: 293
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_gen_rect'):
    rt_gen_rect = _libs['/opt/brlcad/lib/librt.dylib'].rt_gen_rect
    rt_gen_rect.argtypes = [POINTER(struct_xrays), POINTER(struct_xray), vect_t, vect_t, fastf_t, fastf_t]
    rt_gen_rect.restype = c_int

# /opt/brlcad/include/brlcad/./rt/shoot.h: 93
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_shootray'):
    rt_shootray = _libs['/opt/brlcad/lib/librt.dylib'].rt_shootray
    rt_shootray.argtypes = [POINTER(struct_application)]
    rt_shootray.restype = c_int

# /opt/brlcad/include/brlcad/./rt/shoot.h: 122
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_shootrays'):
    rt_shootrays = _libs['/opt/brlcad/lib/librt.dylib'].rt_shootrays
    rt_shootrays.argtypes = [POINTER(struct_application_bundle)]
    rt_shootrays.restype = c_int

# /opt/brlcad/include/brlcad/./rt/shoot.h: 132
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_shootray_simple'):
    rt_shootray_simple = _libs['/opt/brlcad/lib/librt.dylib'].rt_shootray_simple
    rt_shootray_simple.argtypes = [POINTER(struct_application), point_t, vect_t]
    rt_shootray_simple.restype = POINTER(struct_partition)

# /opt/brlcad/include/brlcad/./rt/shoot.h: 141
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_shootray_bundle'):
    rt_shootray_bundle = _libs['/opt/brlcad/lib/librt.dylib'].rt_shootray_bundle
    rt_shootray_bundle.argtypes = [POINTER(struct_application), POINTER(struct_xray), c_int]
    rt_shootray_bundle.restype = c_int

# /opt/brlcad/include/brlcad/./rt/shoot.h: 151
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_add_res_stats'):
    rt_add_res_stats = _libs['/opt/brlcad/lib/librt.dylib'].rt_add_res_stats
    rt_add_res_stats.argtypes = [POINTER(struct_rt_i), POINTER(struct_resource)]
    rt_add_res_stats.restype = None

# /opt/brlcad/include/brlcad/./rt/shoot.h: 154
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_zero_res_stats'):
    rt_zero_res_stats = _libs['/opt/brlcad/lib/librt.dylib'].rt_zero_res_stats
    rt_zero_res_stats.argtypes = [POINTER(struct_resource)]
    rt_zero_res_stats.restype = None

# /opt/brlcad/include/brlcad/./rt/shoot.h: 157
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_res_pieces_clean'):
    rt_res_pieces_clean = _libs['/opt/brlcad/lib/librt.dylib'].rt_res_pieces_clean
    rt_res_pieces_clean.argtypes = [POINTER(struct_resource), POINTER(struct_rt_i)]
    rt_res_pieces_clean.restype = None

# /opt/brlcad/include/brlcad/./rt/shoot.h: 165
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_res_pieces_init'):
    rt_res_pieces_init = _libs['/opt/brlcad/lib/librt.dylib'].rt_res_pieces_init
    rt_res_pieces_init.argtypes = [POINTER(struct_resource), POINTER(struct_rt_i)]
    rt_res_pieces_init.restype = None

# /opt/brlcad/include/brlcad/./rt/shoot.h: 167
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_vstub'):
        continue
    rt_vstub = _lib.rt_vstub
    rt_vstub.argtypes = [POINTER(POINTER(struct_soltab)), POINTER(POINTER(struct_xray)), POINTER(struct_seg), c_int, POINTER(struct_application)]
    rt_vstub.restype = None
    break

# /opt/brlcad/include/brlcad/./rt/timer.h: 60
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_prep_timer'):
    rt_prep_timer = _libs['/opt/brlcad/lib/librt.dylib'].rt_prep_timer
    rt_prep_timer.argtypes = []
    rt_prep_timer.restype = None

# /opt/brlcad/include/brlcad/./rt/timer.h: 68
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_get_timer'):
    rt_get_timer = _libs['/opt/brlcad/lib/librt.dylib'].rt_get_timer
    rt_get_timer.argtypes = [POINTER(struct_bu_vls), POINTER(c_double)]
    rt_get_timer.restype = c_double

# /opt/brlcad/include/brlcad/./rt/timer.h: 74
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_read_timer'):
    rt_read_timer = _libs['/opt/brlcad/lib/librt.dylib'].rt_read_timer
    rt_read_timer.argtypes = [String, c_int]
    rt_read_timer.restype = c_double

# /opt/brlcad/include/brlcad/./rt/boolweave.h: 76
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_boolweave'):
    rt_boolweave = _libs['/opt/brlcad/lib/librt.dylib'].rt_boolweave
    rt_boolweave.argtypes = [POINTER(struct_seg), POINTER(struct_seg), POINTER(struct_partition), POINTER(struct_application)]
    rt_boolweave.restype = None

# /opt/brlcad/include/brlcad/./rt/boolweave.h: 155
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_boolfinal'):
    rt_boolfinal = _libs['/opt/brlcad/lib/librt.dylib'].rt_boolfinal
    rt_boolfinal.argtypes = [POINTER(struct_partition), POINTER(struct_partition), fastf_t, fastf_t, POINTER(struct_bu_ptbl), POINTER(struct_application), POINTER(struct_bu_bitv)]
    rt_boolfinal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/boolweave.h: 170
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bool_growstack'):
    rt_bool_growstack = _libs['/opt/brlcad/lib/librt.dylib'].rt_bool_growstack
    rt_bool_growstack.argtypes = [POINTER(struct_resource)]
    rt_bool_growstack.restype = None

# /opt/brlcad/include/brlcad/./rt/calc.h: 49
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_matrix_transform'):
    rt_matrix_transform = _libs['/opt/brlcad/lib/librt.dylib'].rt_matrix_transform
    rt_matrix_transform.argtypes = [POINTER(struct_rt_db_internal), mat_t, POINTER(struct_rt_db_internal), c_int, POINTER(struct_db_i), POINTER(struct_resource)]
    rt_matrix_transform.restype = c_int

# /opt/brlcad/include/brlcad/./rt/calc.h: 59
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_rpp_region'):
    rt_rpp_region = _libs['/opt/brlcad/lib/librt.dylib'].rt_rpp_region
    rt_rpp_region.argtypes = [POINTER(struct_rt_i), String, POINTER(fastf_t), POINTER(fastf_t)]
    rt_rpp_region.restype = c_int

# /opt/brlcad/include/brlcad/./rt/calc.h: 86
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_in_rpp'):
    rt_in_rpp = _libs['/opt/brlcad/lib/librt.dylib'].rt_in_rpp
    rt_in_rpp.argtypes = [POINTER(struct_xray), POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t)]
    rt_in_rpp.restype = c_int

# /opt/brlcad/include/brlcad/./rt/calc.h: 113
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bound_internal'):
    rt_bound_internal = _libs['/opt/brlcad/lib/librt.dylib'].rt_bound_internal
    rt_bound_internal.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), point_t, point_t]
    rt_bound_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/calc.h: 132
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_shader_mat'):
    rt_shader_mat = _libs['/opt/brlcad/lib/librt.dylib'].rt_shader_mat
    rt_shader_mat.argtypes = [mat_t, POINTER(struct_rt_i), POINTER(struct_region), point_t, point_t, POINTER(struct_resource)]
    rt_shader_mat.restype = c_int

# /opt/brlcad/include/brlcad/./rt/calc.h: 140
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_mirror'):
    rt_mirror = _libs['/opt/brlcad/lib/librt.dylib'].rt_mirror
    rt_mirror.argtypes = [POINTER(struct_db_i), POINTER(struct_rt_db_internal), point_t, vect_t, POINTER(struct_resource)]
    rt_mirror.restype = POINTER(struct_rt_db_internal)

# /opt/brlcad/include/brlcad/./rt/calc.h: 156
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_fallback_angle'):
    rt_pr_fallback_angle = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_fallback_angle
    rt_pr_fallback_angle.argtypes = [POINTER(struct_bu_vls), String, c_double * 5]
    rt_pr_fallback_angle.restype = None

# /opt/brlcad/include/brlcad/./rt/calc.h: 159
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_find_fallback_angle'):
    rt_find_fallback_angle = _libs['/opt/brlcad/lib/librt.dylib'].rt_find_fallback_angle
    rt_find_fallback_angle.argtypes = [c_double * 5, vect_t]
    rt_find_fallback_angle.restype = None

# /opt/brlcad/include/brlcad/./rt/calc.h: 161
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pr_tol'):
    rt_pr_tol = _libs['/opt/brlcad/lib/librt.dylib'].rt_pr_tol
    rt_pr_tol.argtypes = [POINTER(struct_bn_tol)]
    rt_pr_tol.restype = None

# /opt/brlcad/include/brlcad/./rt/calc.h: 177
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_poly_roots'):
    rt_poly_roots = _libs['/opt/brlcad/lib/librt.dylib'].rt_poly_roots
    rt_poly_roots.argtypes = [POINTER(bn_poly_t), POINTER(bn_complex_t), String]
    rt_poly_roots.restype = c_int

# /opt/brlcad/include/brlcad/./rt/cmd.h: 42
class struct_command_tab(Structure):
    pass

struct_command_tab.__slots__ = [
    'ct_cmd',
    'ct_parms',
    'ct_comment',
    'ct_func',
    'ct_min',
    'ct_max',
]
struct_command_tab._fields_ = [
    ('ct_cmd', String),
    ('ct_parms', String),
    ('ct_comment', String),
    ('ct_func', CFUNCTYPE(UNCHECKED(c_int), c_int, POINTER(POINTER(c_char)))),
    ('ct_min', c_int),
    ('ct_max', c_int),
]

# /opt/brlcad/include/brlcad/./rt/cmd.h: 78
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_do_cmd'):
    rt_do_cmd = _libs['/opt/brlcad/lib/librt.dylib'].rt_do_cmd
    rt_do_cmd.argtypes = [POINTER(struct_rt_i), String, POINTER(struct_command_tab)]
    rt_do_cmd.restype = c_int

# /opt/brlcad/include/brlcad/./rt/search.h: 102
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_search'):
    db_search = _libs['/opt/brlcad/lib/librt.dylib'].db_search
    db_search.argtypes = [POINTER(struct_bu_ptbl), c_int, String, c_int, POINTER(POINTER(struct_directory)), POINTER(struct_db_i)]
    db_search.restype = c_int

# /opt/brlcad/include/brlcad/./rt/search.h: 122
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_search_free'):
    db_search_free = _libs['/opt/brlcad/lib/librt.dylib'].db_search_free
    db_search_free.argtypes = [POINTER(struct_bu_ptbl)]
    db_search_free.restype = None

# /opt/brlcad/include/brlcad/./rt/search.h: 140
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_ls'):
    db_ls = _libs['/opt/brlcad/lib/librt.dylib'].db_ls
    db_ls.argtypes = [POINTER(struct_db_i), c_int, String, POINTER(POINTER(POINTER(struct_directory)))]
    db_ls.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/search.h: 163
class struct_db_full_path_list(Structure):
    pass

struct_db_full_path_list.__slots__ = [
    'l',
    'path',
    'local',
]
struct_db_full_path_list._fields_ = [
    ('l', struct_bu_list),
    ('path', POINTER(struct_db_full_path)),
    ('local', c_int),
]

# /opt/brlcad/include/brlcad/./rt/search.h: 168
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_full_path_list_add'):
    db_full_path_list_add = _libs['/opt/brlcad/lib/librt.dylib'].db_full_path_list_add
    db_full_path_list_add.argtypes = [String, c_int, POINTER(struct_db_i), POINTER(struct_db_full_path_list)]
    db_full_path_list_add.restype = c_int

# /opt/brlcad/include/brlcad/./rt/search.h: 169
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_free_full_path_list'):
    db_free_full_path_list = _libs['/opt/brlcad/lib/librt.dylib'].db_free_full_path_list
    db_free_full_path_list.argtypes = [POINTER(struct_db_full_path_list)]
    db_free_full_path_list.restype = None

# /opt/brlcad/include/brlcad/./rt/search.h: 170
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_search_formplan'):
    db_search_formplan = _libs['/opt/brlcad/lib/librt.dylib'].db_search_formplan
    db_search_formplan.argtypes = [POINTER(POINTER(c_char)), POINTER(struct_db_i)]
    db_search_formplan.restype = POINTER(None)

# /opt/brlcad/include/brlcad/./rt/search.h: 172
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_search_freeplan'):
    db_search_freeplan = _libs['/opt/brlcad/lib/librt.dylib'].db_search_freeplan
    db_search_freeplan.argtypes = [POINTER(POINTER(None))]
    db_search_freeplan.restype = None

# /opt/brlcad/include/brlcad/./rt/search.h: 173
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_search_full_paths'):
    db_search_full_paths = _libs['/opt/brlcad/lib/librt.dylib'].db_search_full_paths
    db_search_full_paths.argtypes = [POINTER(None), POINTER(struct_db_full_path_list), POINTER(struct_db_i)]
    db_search_full_paths.restype = POINTER(struct_db_full_path_list)

# /opt/brlcad/include/brlcad/./rt/search.h: 176
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_search_unique_objects'):
    db_search_unique_objects = _libs['/opt/brlcad/lib/librt.dylib'].db_search_unique_objects
    db_search_unique_objects.argtypes = [POINTER(None), POINTER(struct_db_full_path_list), POINTER(struct_db_i)]
    db_search_unique_objects.restype = POINTER(struct_bu_ptbl)

# /opt/brlcad/include/brlcad/./rt/search.h: 180
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_regexp_match_all'):
    db_regexp_match_all = _libs['/opt/brlcad/lib/librt.dylib'].db_regexp_match_all
    db_regexp_match_all.argtypes = [POINTER(struct_bu_vls), POINTER(struct_db_i), String]
    db_regexp_match_all.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 49
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_sync'):
    db_sync = _libs['/opt/brlcad/lib/librt.dylib'].db_sync
    db_sync.argtypes = [POINTER(struct_db_i)]
    db_sync.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 83
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_open'):
    db_open = _libs['/opt/brlcad/lib/librt.dylib'].db_open
    db_open.argtypes = [String, String]
    db_open.restype = POINTER(struct_db_i)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 100
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_create'):
    db_create = _libs['/opt/brlcad/lib/librt.dylib'].db_create
    db_create.argtypes = [String, c_int]
    db_create.restype = POINTER(struct_db_i)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 108
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_close_client'):
    db_close_client = _libs['/opt/brlcad/lib/librt.dylib'].db_close_client
    db_close_client.argtypes = [POINTER(struct_db_i), POINTER(c_long)]
    db_close_client.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 115
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_close'):
    db_close = _libs['/opt/brlcad/lib/librt.dylib'].db_close
    db_close.argtypes = [POINTER(struct_db_i)]
    db_close.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 129
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dump'):
    db_dump = _libs['/opt/brlcad/lib/librt.dylib'].db_dump
    db_dump.argtypes = [POINTER(struct_rt_wdb), POINTER(struct_db_i)]
    db_dump.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 136
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_clone_dbi'):
    db_clone_dbi = _libs['/opt/brlcad/lib/librt.dylib'].db_clone_dbi
    db_clone_dbi.argtypes = [POINTER(struct_db_i), POINTER(c_long)]
    db_clone_dbi.restype = POINTER(struct_db_i)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 152
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_write_free'):
    db5_write_free = _libs['/opt/brlcad/lib/librt.dylib'].db5_write_free
    db5_write_free.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), c_size_t]
    db5_write_free.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 178
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_realloc'):
    db5_realloc = _libs['/opt/brlcad/lib/librt.dylib'].db5_realloc
    db5_realloc.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), POINTER(struct_bu_external)]
    db5_realloc.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 189
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_export_object3'):
    db5_export_object3 = _libs['/opt/brlcad/lib/librt.dylib'].db5_export_object3
    db5_export_object3.argtypes = [POINTER(struct_bu_external), c_int, String, c_ubyte, POINTER(struct_bu_external), POINTER(struct_bu_external), c_int, c_int, c_int, c_int]
    db5_export_object3.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 219
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_cvt_to_external5'):
    rt_db_cvt_to_external5 = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_cvt_to_external5
    rt_db_cvt_to_external5.argtypes = [POINTER(struct_bu_external), String, POINTER(struct_rt_db_internal), c_double, POINTER(struct_db_i), POINTER(struct_resource), c_int]
    rt_db_cvt_to_external5.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 231
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_wrap_v5_external'):
    db_wrap_v5_external = _libs['/opt/brlcad/lib/librt.dylib'].db_wrap_v5_external
    db_wrap_v5_external.argtypes = [POINTER(struct_bu_external), String]
    db_wrap_v5_external.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 246
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_get_internal5'):
    rt_db_get_internal5 = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_get_internal5
    rt_db_get_internal5.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_directory), POINTER(struct_db_i), mat_t, POINTER(struct_resource)]
    rt_db_get_internal5.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 267
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_put_internal5'):
    rt_db_put_internal5 = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_put_internal5
    rt_db_put_internal5.argtypes = [POINTER(struct_directory), POINTER(struct_db_i), POINTER(struct_rt_db_internal), POINTER(struct_resource), c_int]
    rt_db_put_internal5.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 279
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_make_free_object_hdr'):
    db5_make_free_object_hdr = _libs['/opt/brlcad/lib/librt.dylib'].db5_make_free_object_hdr
    db5_make_free_object_hdr.argtypes = [POINTER(struct_bu_external), c_size_t]
    db5_make_free_object_hdr.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 287
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_make_free_object'):
    db5_make_free_object = _libs['/opt/brlcad/lib/librt.dylib'].db5_make_free_object
    db5_make_free_object.argtypes = [POINTER(struct_bu_external), c_size_t]
    db5_make_free_object.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 300
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_decode_signed'):
    db5_decode_signed = _libs['/opt/brlcad/lib/librt.dylib'].db5_decode_signed
    db5_decode_signed.argtypes = [POINTER(c_size_t), POINTER(c_ubyte), c_int]
    db5_decode_signed.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 313
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_decode_length'):
    db5_decode_length = _libs['/opt/brlcad/lib/librt.dylib'].db5_decode_length
    db5_decode_length.argtypes = [POINTER(c_size_t), POINTER(c_ubyte), c_int]
    db5_decode_length.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/db_io.h: 328
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_select_length_encoding'):
    db5_select_length_encoding = _libs['/opt/brlcad/lib/librt.dylib'].db5_select_length_encoding
    db5_select_length_encoding.argtypes = [c_size_t]
    db5_select_length_encoding.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 331
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_import_color_table'):
    db5_import_color_table = _libs['/opt/brlcad/lib/librt.dylib'].db5_import_color_table
    db5_import_color_table.argtypes = [String]
    db5_import_color_table.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 350
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_header_is_valid'):
    db5_header_is_valid = _libs['/opt/brlcad/lib/librt.dylib'].db5_header_is_valid
    db5_header_is_valid.argtypes = [POINTER(c_ubyte)]
    db5_header_is_valid.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 379
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_put_external5'):
    db_put_external5 = _libs['/opt/brlcad/lib/librt.dylib'].db_put_external5
    db_put_external5.argtypes = [POINTER(struct_bu_external), POINTER(struct_directory), POINTER(struct_db_i)]
    db_put_external5.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 388
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_wrap_v4_external'):
    db_wrap_v4_external = _libs['/opt/brlcad/lib/librt.dylib'].db_wrap_v4_external
    db_wrap_v4_external.argtypes = [POINTER(struct_bu_external), String]
    db_wrap_v4_external.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 393
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_write'):
    db_write = _libs['/opt/brlcad/lib/librt.dylib'].db_write
    db_write.argtypes = [POINTER(struct_db_i), POINTER(None), c_size_t, off_t]
    db_write.restype = c_int

# /opt/brlcad/include/brlcad/rt/db4.h: 421
class union_record(Union):
    pass

# /opt/brlcad/include/brlcad/./rt/db_io.h: 435
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_getmrec'):
    db_getmrec = _libs['/opt/brlcad/lib/librt.dylib'].db_getmrec
    db_getmrec.argtypes = [POINTER(struct_db_i), POINTER(struct_directory)]
    db_getmrec.restype = POINTER(union_record)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 447
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_get'):
    db_get = _libs['/opt/brlcad/lib/librt.dylib'].db_get
    db_get.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), POINTER(union_record), off_t, c_size_t]
    db_get.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 462
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_put'):
    db_put = _libs['/opt/brlcad/lib/librt.dylib'].db_put
    db_put.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), POINTER(union_record), off_t, c_size_t]
    db_put.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 481
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_get_external'):
    db_get_external = _libs['/opt/brlcad/lib/librt.dylib'].db_get_external
    db_get_external.argtypes = [POINTER(struct_bu_external), POINTER(struct_directory), POINTER(struct_db_i)]
    db_get_external.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 503
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_put_external'):
    db_put_external = _libs['/opt/brlcad/lib/librt.dylib'].db_put_external
    db_put_external.argtypes = [POINTER(struct_bu_external), POINTER(struct_directory), POINTER(struct_db_i)]
    db_put_external.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 509
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_scan'):
    db_scan = _libs['/opt/brlcad/lib/librt.dylib'].db_scan
    db_scan.argtypes = [POINTER(struct_db_i), CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_db_i), String, off_t, c_size_t, c_int, POINTER(None)), c_int, POINTER(None)]
    db_scan.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 531
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_update_ident'):
    db_update_ident = _libs['/opt/brlcad/lib/librt.dylib'].db_update_ident
    db_update_ident.argtypes = [POINTER(struct_db_i), String, c_double]
    db_update_ident.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 571
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_conversions'):
    db_conversions = _libs['/opt/brlcad/lib/librt.dylib'].db_conversions
    db_conversions.argtypes = [POINTER(struct_db_i), c_int]
    db_conversions.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 583
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_v4_get_units_code'):
    db_v4_get_units_code = _libs['/opt/brlcad/lib/librt.dylib'].db_v4_get_units_code
    db_v4_get_units_code.argtypes = [String]
    db_v4_get_units_code.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 602
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dirbuild'):
    db_dirbuild = _libs['/opt/brlcad/lib/librt.dylib'].db_dirbuild
    db_dirbuild.argtypes = [POINTER(struct_db_i)]
    db_dirbuild.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 603
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_diradd'):
    db5_diradd = _libs['/opt/brlcad/lib/librt.dylib'].db5_diradd
    db5_diradd.argtypes = [POINTER(struct_db_i), POINTER(struct_db5_raw_internal), off_t, POINTER(None)]
    db5_diradd.restype = POINTER(struct_directory)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 615
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_scan'):
    db5_scan = _libs['/opt/brlcad/lib/librt.dylib'].db5_scan
    db5_scan.argtypes = [POINTER(struct_db_i), CFUNCTYPE(UNCHECKED(None), POINTER(struct_db_i), POINTER(struct_db5_raw_internal), off_t, POINTER(None)), POINTER(None)]
    db5_scan.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 627
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_version'):
    db_version = _libs['/opt/brlcad/lib/librt.dylib'].db_version
    db_version.argtypes = [POINTER(struct_db_i)]
    db_version.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 641
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_db_flip_endian'):
    rt_db_flip_endian = _libs['/opt/brlcad/lib/librt.dylib'].rt_db_flip_endian
    rt_db_flip_endian.argtypes = [POINTER(struct_db_i)]
    rt_db_flip_endian.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 649
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_open_inmem'):
    db_open_inmem = _libs['/opt/brlcad/lib/librt.dylib'].db_open_inmem
    db_open_inmem.argtypes = []
    db_open_inmem.restype = POINTER(struct_db_i)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 657
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_create_inmem'):
    db_create_inmem = _libs['/opt/brlcad/lib/librt.dylib'].db_create_inmem
    db_create_inmem.argtypes = []
    db_create_inmem.restype = POINTER(struct_db_i)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 664
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_inmem'):
    db_inmem = _libs['/opt/brlcad/lib/librt.dylib'].db_inmem
    db_inmem.argtypes = [POINTER(struct_directory), POINTER(struct_bu_external), c_int, POINTER(struct_db_i)]
    db_inmem.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 675
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_directory_size'):
    db_directory_size = _libs['/opt/brlcad/lib/librt.dylib'].db_directory_size
    db_directory_size.argtypes = [POINTER(struct_db_i)]
    db_directory_size.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/db_io.h: 681
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_ck_directory'):
    db_ck_directory = _libs['/opt/brlcad/lib/librt.dylib'].db_ck_directory
    db_ck_directory.argtypes = [POINTER(struct_db_i)]
    db_ck_directory.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 689
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_is_directory_non_empty'):
    db_is_directory_non_empty = _libs['/opt/brlcad/lib/librt.dylib'].db_is_directory_non_empty
    db_is_directory_non_empty.argtypes = [POINTER(struct_db_i)]
    db_is_directory_non_empty.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 695
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dirhash'):
    db_dirhash = _libs['/opt/brlcad/lib/librt.dylib'].db_dirhash
    db_dirhash.argtypes = [String]
    db_dirhash.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 716
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dircheck'):
    db_dircheck = _libs['/opt/brlcad/lib/librt.dylib'].db_dircheck
    db_dircheck.argtypes = [POINTER(struct_db_i), POINTER(struct_bu_vls), c_int, POINTER(POINTER(POINTER(struct_directory)))]
    db_dircheck.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 734
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_lookup'):
    db_lookup = _libs['/opt/brlcad/lib/librt.dylib'].db_lookup
    db_lookup.argtypes = [POINTER(struct_db_i), String, c_int]
    db_lookup.restype = POINTER(struct_directory)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 769
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'db_get_name'):
        continue
    db_get_name = _lib.db_get_name
    db_get_name.argtypes = [POINTER(struct_bu_vls), POINTER(struct_db_i), c_int, String, String]
    db_get_name.restype = c_int
    break

# /opt/brlcad/include/brlcad/./rt/db_io.h: 794
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_diradd'):
    db_diradd = _libs['/opt/brlcad/lib/librt.dylib'].db_diradd
    db_diradd.argtypes = [POINTER(struct_db_i), String, off_t, c_size_t, c_int, POINTER(None)]
    db_diradd.restype = POINTER(struct_directory)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 800
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_diradd5'):
    db_diradd5 = _libs['/opt/brlcad/lib/librt.dylib'].db_diradd5
    db_diradd5.argtypes = [POINTER(struct_db_i), String, off_t, c_ubyte, c_ubyte, c_ubyte, c_size_t, POINTER(struct_bu_attribute_value_set)]
    db_diradd5.restype = POINTER(struct_directory)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 822
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_dirdelete'):
    db_dirdelete = _libs['/opt/brlcad/lib/librt.dylib'].db_dirdelete
    db_dirdelete.argtypes = [POINTER(struct_db_i), POINTER(struct_directory)]
    db_dirdelete.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 831
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_pr_dir'):
    db_pr_dir = _libs['/opt/brlcad/lib/librt.dylib'].db_pr_dir
    db_pr_dir.argtypes = [POINTER(struct_db_i)]
    db_pr_dir.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 841
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_rename'):
    db_rename = _libs['/opt/brlcad/lib/librt.dylib'].db_rename
    db_rename.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), String]
    db_rename.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 851
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_update_nref'):
    db_update_nref = _libs['/opt/brlcad/lib/librt.dylib'].db_update_nref
    db_update_nref.argtypes = [POINTER(struct_db_i), POINTER(struct_resource)]
    db_update_nref.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 862
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_flags_internal'):
    db_flags_internal = _libs['/opt/brlcad/lib/librt.dylib'].db_flags_internal
    db_flags_internal.argtypes = [POINTER(struct_rt_db_internal)]
    db_flags_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 871
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_flags_raw_internal'):
    db_flags_raw_internal = _libs['/opt/brlcad/lib/librt.dylib'].db_flags_raw_internal
    db_flags_raw_internal.argtypes = [POINTER(struct_db5_raw_internal)]
    db_flags_raw_internal.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 876
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_alloc'):
    db_alloc = _libs['/opt/brlcad/lib/librt.dylib'].db_alloc
    db_alloc.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), c_size_t]
    db_alloc.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 880
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_delrec'):
    db_delrec = _libs['/opt/brlcad/lib/librt.dylib'].db_delrec
    db_delrec.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), c_int]
    db_delrec.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 884
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_delete'):
    db_delete = _libs['/opt/brlcad/lib/librt.dylib'].db_delete
    db_delete.argtypes = [POINTER(struct_db_i), POINTER(struct_directory)]
    db_delete.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 887
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_zapper'):
    db_zapper = _libs['/opt/brlcad/lib/librt.dylib'].db_zapper
    db_zapper.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), c_size_t]
    db_zapper.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 896
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_alloc_directory_block'):
    db_alloc_directory_block = _libs['/opt/brlcad/lib/librt.dylib'].db_alloc_directory_block
    db_alloc_directory_block.argtypes = [POINTER(struct_resource)]
    db_alloc_directory_block.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 905
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_alloc_seg_block'):
    rt_alloc_seg_block = _libs['/opt/brlcad/lib/librt.dylib'].rt_alloc_seg_block
    rt_alloc_seg_block.argtypes = [POINTER(struct_resource)]
    rt_alloc_seg_block.restype = None

# /opt/brlcad/include/brlcad/./rt/db_io.h: 912
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dirbuild'):
    rt_dirbuild = _libs['/opt/brlcad/lib/librt.dylib'].rt_dirbuild
    rt_dirbuild.argtypes = [String, String, c_int]
    rt_dirbuild.restype = POINTER(struct_rt_i)

# /opt/brlcad/include/brlcad/./rt/db_io.h: 916
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_tag_from_major'):
    db5_type_tag_from_major = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_tag_from_major
    db5_type_tag_from_major.argtypes = [POINTER(POINTER(c_char)), c_int]
    db5_type_tag_from_major.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 919
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_descrip_from_major'):
    db5_type_descrip_from_major = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_descrip_from_major
    db5_type_descrip_from_major.argtypes = [POINTER(POINTER(c_char)), c_int]
    db5_type_descrip_from_major.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 922
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_tag_from_codes'):
    db5_type_tag_from_codes = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_tag_from_codes
    db5_type_tag_from_codes.argtypes = [POINTER(POINTER(c_char)), c_int, c_int]
    db5_type_tag_from_codes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 926
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_descrip_from_codes'):
    db5_type_descrip_from_codes = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_descrip_from_codes
    db5_type_descrip_from_codes.argtypes = [POINTER(POINTER(c_char)), c_int, c_int]
    db5_type_descrip_from_codes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 930
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_codes_from_tag'):
    db5_type_codes_from_tag = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_codes_from_tag
    db5_type_codes_from_tag.argtypes = [POINTER(c_int), POINTER(c_int), String]
    db5_type_codes_from_tag.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 934
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_codes_from_descrip'):
    db5_type_codes_from_descrip = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_codes_from_descrip
    db5_type_codes_from_descrip.argtypes = [POINTER(c_int), POINTER(c_int), String]
    db5_type_codes_from_descrip.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_io.h: 938
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_sizeof_h_binu'):
    db5_type_sizeof_h_binu = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_sizeof_h_binu
    db5_type_sizeof_h_binu.argtypes = [c_int]
    db5_type_sizeof_h_binu.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/db_io.h: 940
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_type_sizeof_n_binu'):
    db5_type_sizeof_n_binu = _libs['/opt/brlcad/lib/librt.dylib'].db5_type_sizeof_n_binu
    db5_type_sizeof_n_binu.argtypes = [c_int]
    db5_type_sizeof_n_binu.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 38
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_get_cgtype'):
    rt_arb_get_cgtype = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_get_cgtype
    rt_arb_get_cgtype.argtypes = [POINTER(c_int), POINTER(struct_rt_arb_internal), POINTER(struct_bn_tol), POINTER(c_int), POINTER(c_int)]
    rt_arb_get_cgtype.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 44
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_std_type'):
    rt_arb_std_type = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_std_type
    rt_arb_std_type.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_bn_tol)]
    rt_arb_std_type.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 46
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_centroid'):
    rt_arb_centroid = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_centroid
    rt_arb_centroid.argtypes = [POINTER(point_t), POINTER(struct_rt_db_internal)]
    rt_arb_centroid.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 48
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_calc_points'):
    rt_arb_calc_points = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_calc_points
    rt_arb_calc_points.argtypes = [POINTER(struct_rt_arb_internal), c_int, plane_t * 6, POINTER(struct_bn_tol)]
    rt_arb_calc_points.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 49
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_check_points'):
    rt_arb_check_points = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_check_points
    rt_arb_check_points.argtypes = [POINTER(struct_rt_arb_internal), c_int, POINTER(struct_bn_tol)]
    rt_arb_check_points.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 52
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_3face_intersect'):
    rt_arb_3face_intersect = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_3face_intersect
    rt_arb_3face_intersect.argtypes = [point_t, plane_t * 6, c_int, c_int]
    rt_arb_3face_intersect.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 56
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_calc_planes'):
    rt_arb_calc_planes = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_calc_planes
    rt_arb_calc_planes.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_arb_internal), c_int, plane_t * 6, POINTER(struct_bn_tol)]
    rt_arb_calc_planes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 61
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_move_edge'):
    rt_arb_move_edge = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_move_edge
    rt_arb_move_edge.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_arb_internal), vect_t, c_int, c_int, c_int, c_int, vect_t, plane_t * 6, POINTER(struct_bn_tol)]
    rt_arb_move_edge.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 71
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_edit'):
    rt_arb_edit = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_edit
    rt_arb_edit.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_arb_internal), c_int, c_int, vect_t, plane_t * 6, POINTER(struct_bn_tol)]
    rt_arb_edit.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/arb8.h: 78
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_arb_find_e_nearest_pt2'):
    rt_arb_find_e_nearest_pt2 = _libs['/opt/brlcad/lib/librt.dylib'].rt_arb_find_e_nearest_pt2
    rt_arb_find_e_nearest_pt2.argtypes = [POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(struct_rt_db_internal), point_t, mat_t, fastf_t]
    rt_arb_find_e_nearest_pt2.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/epa.h: 33
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_ell'):
    rt_ell = _libs['/opt/brlcad/lib/librt.dylib'].rt_ell
    rt_ell.argtypes = [POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), c_int]
    rt_ell.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/pipe.h: 35
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_vls_pipept'):
    rt_vls_pipept = _libs['/opt/brlcad/lib/librt.dylib'].rt_vls_pipept
    rt_vls_pipept.argtypes = [POINTER(struct_bu_vls), c_int, POINTER(struct_rt_db_internal), c_double]
    rt_vls_pipept.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/pipe.h: 39
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pipept_print'):
    rt_pipept_print = _libs['/opt/brlcad/lib/librt.dylib'].rt_pipept_print
    rt_pipept_print.argtypes = [POINTER(struct_wdb_pipept), c_double]
    rt_pipept_print.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/pipe.h: 40
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pipe_ck'):
    rt_pipe_ck = _libs['/opt/brlcad/lib/librt.dylib'].rt_pipe_ck
    rt_pipe_ck.argtypes = [POINTER(struct_bu_list)]
    rt_pipe_ck.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 35
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_vls_metaballpt'):
        continue
    rt_vls_metaballpt = _lib.rt_vls_metaballpt
    rt_vls_metaballpt.argtypes = [POINTER(struct_bu_vls), c_int, POINTER(struct_rt_db_internal), c_double]
    rt_vls_metaballpt.restype = None
    break

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 39
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_metaballpt_print'):
    rt_metaballpt_print = _libs['/opt/brlcad/lib/librt.dylib'].rt_metaballpt_print
    rt_metaballpt_print.argtypes = [POINTER(struct_wdb_metaballpt), c_double]
    rt_metaballpt_print.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 40
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_metaball_ck'):
        continue
    rt_metaball_ck = _lib.rt_metaball_ck
    rt_metaball_ck.argtypes = [POINTER(struct_bu_list)]
    rt_metaball_ck.restype = c_int
    break

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 41
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_metaball_point_value'):
    rt_metaball_point_value = _libs['/opt/brlcad/lib/librt.dylib'].rt_metaball_point_value
    rt_metaball_point_value.argtypes = [POINTER(point_t), POINTER(struct_rt_metaball_internal)]
    rt_metaball_point_value.restype = fastf_t

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 43
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_metaball_point_inside'):
    rt_metaball_point_inside = _libs['/opt/brlcad/lib/librt.dylib'].rt_metaball_point_inside
    rt_metaball_point_inside.argtypes = [POINTER(point_t), POINTER(struct_rt_metaball_internal)]
    rt_metaball_point_inside.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 45
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_metaball_lookup_type_id'):
    rt_metaball_lookup_type_id = _libs['/opt/brlcad/lib/librt.dylib'].rt_metaball_lookup_type_id
    rt_metaball_lookup_type_id.argtypes = [String]
    rt_metaball_lookup_type_id.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 46
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_metaball_lookup_type_name'):
    rt_metaball_lookup_type_name = _libs['/opt/brlcad/lib/librt.dylib'].rt_metaball_lookup_type_name
    rt_metaball_lookup_type_name.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        rt_metaball_lookup_type_name.restype = ReturnString
    else:
        rt_metaball_lookup_type_name.restype = String
        rt_metaball_lookup_type_name.errcheck = ReturnString

# /opt/brlcad/include/brlcad/./rt/primitives/metaball.h: 47
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_metaball_add_point'):
    rt_metaball_add_point = _libs['/opt/brlcad/lib/librt.dylib'].rt_metaball_add_point
    rt_metaball_add_point.argtypes = [POINTER(struct_rt_metaball_internal), POINTER(point_t), fastf_t, fastf_t]
    rt_metaball_add_point.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/rpc.h: 33
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_mk_parabola'):
    rt_mk_parabola = _libs['/opt/brlcad/lib/librt.dylib'].rt_mk_parabola
    rt_mk_parabola.argtypes = [POINTER(struct_rt_pt_node), fastf_t, fastf_t, fastf_t, fastf_t]
    rt_mk_parabola.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/pg.h: 35
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pg_to_bot'):
    rt_pg_to_bot = _libs['/opt/brlcad/lib/librt.dylib'].rt_pg_to_bot
    rt_pg_to_bot.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_bn_tol), POINTER(struct_resource)]
    rt_pg_to_bot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/pg.h: 38
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pg_plot'):
    rt_pg_plot = _libs['/opt/brlcad/lib/librt.dylib'].rt_pg_plot
    rt_pg_plot.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol), POINTER(struct_rt_view_info)]
    rt_pg_plot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/pg.h: 43
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pg_plot_poly'):
    rt_pg_plot_poly = _libs['/opt/brlcad/lib/librt.dylib'].rt_pg_plot_poly
    rt_pg_plot_poly.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol)]
    rt_pg_plot_poly.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/hf.h: 33
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_hf_to_dsp'):
    rt_hf_to_dsp = _libs['/opt/brlcad/lib/librt.dylib'].rt_hf_to_dsp
    rt_hf_to_dsp.argtypes = [POINTER(struct_rt_db_internal)]
    rt_hf_to_dsp.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/dsp.h: 34
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'dsp_pos'):
    dsp_pos = _libs['/opt/brlcad/lib/librt.dylib'].dsp_pos
    dsp_pos.argtypes = [point_t, POINTER(struct_soltab), point_t]
    dsp_pos.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/ell.h: 34
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_ell_16pts'):
    rt_ell_16pts = _libs['/opt/brlcad/lib/librt.dylib'].rt_ell_16pts
    rt_ell_16pts.argtypes = [POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t)]
    rt_ell_16pts.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/tgc.h: 34
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pt_sort'):
    rt_pt_sort = _libs['/opt/brlcad/lib/librt.dylib'].rt_pt_sort
    rt_pt_sort.argtypes = [POINTER(fastf_t), c_int]
    rt_pt_sort.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 36
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'curve_to_vlist'):
    curve_to_vlist = _libs['/opt/brlcad/lib/librt.dylib'].curve_to_vlist
    curve_to_vlist.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_tess_tol), point_t, vect_t, vect_t, POINTER(struct_rt_sketch_internal), POINTER(struct_rt_curve)]
    curve_to_vlist.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 44
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_check_curve'):
    rt_check_curve = _libs['/opt/brlcad/lib/librt.dylib'].rt_check_curve
    rt_check_curve.argtypes = [POINTER(struct_rt_curve), POINTER(struct_rt_sketch_internal), c_int]
    rt_check_curve.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 48
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_curve_reverse_segment'):
    rt_curve_reverse_segment = _libs['/opt/brlcad/lib/librt.dylib'].rt_curve_reverse_segment
    rt_curve_reverse_segment.argtypes = [POINTER(c_uint32)]
    rt_curve_reverse_segment.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 49
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_curve_order_segments'):
    rt_curve_order_segments = _libs['/opt/brlcad/lib/librt.dylib'].rt_curve_order_segments
    rt_curve_order_segments.argtypes = [POINTER(struct_rt_curve)]
    rt_curve_order_segments.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 51
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_copy_curve'):
    rt_copy_curve = _libs['/opt/brlcad/lib/librt.dylib'].rt_copy_curve
    rt_copy_curve.argtypes = [POINTER(struct_rt_curve), POINTER(struct_rt_curve)]
    rt_copy_curve.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 54
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_curve_free'):
    rt_curve_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_curve_free
    rt_curve_free.argtypes = [POINTER(struct_rt_curve)]
    rt_curve_free.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 55
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_copy_curve'):
    rt_copy_curve = _libs['/opt/brlcad/lib/librt.dylib'].rt_copy_curve
    rt_copy_curve.argtypes = [POINTER(struct_rt_curve), POINTER(struct_rt_curve)]
    rt_copy_curve.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 57
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_copy_sketch'):
    rt_copy_sketch = _libs['/opt/brlcad/lib/librt.dylib'].rt_copy_sketch
    rt_copy_sketch.argtypes = [POINTER(struct_rt_sketch_internal)]
    rt_copy_sketch.restype = POINTER(struct_rt_sketch_internal)

# /opt/brlcad/include/brlcad/./rt/primitives/sketch.h: 58
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'curve_to_tcl_list'):
    curve_to_tcl_list = _libs['/opt/brlcad/lib/librt.dylib'].curve_to_tcl_list
    curve_to_tcl_list.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_curve)]
    curve_to_tcl_list.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 36
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_pos_flag'):
    rt_pos_flag = _libs['/opt/brlcad/lib/librt.dylib'].rt_pos_flag
    rt_pos_flag.argtypes = [POINTER(c_int), c_int, c_int]
    rt_pos_flag.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 38
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_check_pos'):
    rt_check_pos = _libs['/opt/brlcad/lib/librt.dylib'].rt_check_pos
    rt_check_pos.argtypes = [POINTER(struct_txt_seg), POINTER(POINTER(c_char))]
    rt_check_pos.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 40
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_check_ant'):
    rt_check_ant = _libs['/opt/brlcad/lib/librt.dylib'].rt_check_ant
    rt_check_ant.argtypes = [POINTER(struct_rt_ant), POINTER(struct_rt_annot_internal), c_int]
    rt_check_ant.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 44
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_copy_ant'):
    rt_copy_ant = _libs['/opt/brlcad/lib/librt.dylib'].rt_copy_ant
    rt_copy_ant.argtypes = [POINTER(struct_rt_ant), POINTER(struct_rt_ant)]
    rt_copy_ant.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 47
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_ant_free'):
    rt_ant_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_ant_free
    rt_ant_free.argtypes = [POINTER(struct_rt_ant)]
    rt_ant_free.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 49
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_copy_annot'):
    rt_copy_annot = _libs['/opt/brlcad/lib/librt.dylib'].rt_copy_annot
    rt_copy_annot.argtypes = [POINTER(struct_rt_annot_internal)]
    rt_copy_annot.restype = POINTER(struct_rt_annot_internal)

# /opt/brlcad/include/brlcad/./rt/primitives/annot.h: 50
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'ant_to_tcl_list'):
    ant_to_tcl_list = _libs['/opt/brlcad/lib/librt.dylib'].ant_to_tcl_list
    ant_to_tcl_list.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_ant)]
    ant_to_tcl_list.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 57
class struct_bot_specific(Structure):
    pass

struct_bot_specific.__slots__ = [
    'bot_mode',
    'bot_orientation',
    'bot_flags',
    'bot_ntri',
    'bot_thickness',
    'bot_facemode',
    'bot_facelist',
    'bot_facearray',
    'bot_tri_per_piece',
    'tie',
]
struct_bot_specific._fields_ = [
    ('bot_mode', c_ubyte),
    ('bot_orientation', c_ubyte),
    ('bot_flags', c_ubyte),
    ('bot_ntri', c_size_t),
    ('bot_thickness', POINTER(fastf_t)),
    ('bot_facemode', POINTER(struct_bu_bitv)),
    ('bot_facelist', POINTER(None)),
    ('bot_facearray', POINTER(POINTER(None))),
    ('bot_tri_per_piece', c_size_t),
    ('tie', POINTER(None)),
]

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 76
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_prep_pieces'):
    rt_bot_prep_pieces = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_prep_pieces
    rt_bot_prep_pieces.argtypes = [POINTER(struct_bot_specific), POINTER(struct_soltab), c_size_t, POINTER(struct_bn_tol)]
    rt_bot_prep_pieces.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 81
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_botface'):
    rt_botface = _libs['/opt/brlcad/lib/librt.dylib'].rt_botface
    rt_botface.argtypes = [POINTER(struct_soltab), POINTER(struct_bot_specific), POINTER(fastf_t), POINTER(fastf_t), POINTER(fastf_t), c_size_t, POINTER(struct_bn_tol)]
    rt_botface.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 91
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_get_edge_list'):
    rt_bot_get_edge_list = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_get_edge_list
    rt_bot_get_edge_list.argtypes = [POINTER(struct_rt_bot_internal), POINTER(POINTER(c_size_t))]
    rt_bot_get_edge_list.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 93
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_edge_in_list'):
    rt_bot_edge_in_list = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_edge_in_list
    rt_bot_edge_in_list.argtypes = [c_size_t, c_size_t, POINTER(c_size_t), c_size_t]
    rt_bot_edge_in_list.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 97
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_plot'):
    rt_bot_plot = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_plot
    rt_bot_plot.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol), POINTER(struct_rt_view_info)]
    rt_bot_plot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 102
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_plot_poly'):
    rt_bot_plot_poly = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_plot_poly
    rt_bot_plot_poly.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol)]
    rt_bot_plot_poly.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 106
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_find_v_nearest_pt2'):
    rt_bot_find_v_nearest_pt2 = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_find_v_nearest_pt2
    rt_bot_find_v_nearest_pt2.argtypes = [POINTER(struct_rt_bot_internal), point_t, mat_t]
    rt_bot_find_v_nearest_pt2.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 109
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_find_e_nearest_pt2'):
    rt_bot_find_e_nearest_pt2 = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_find_e_nearest_pt2
    rt_bot_find_e_nearest_pt2.argtypes = [POINTER(c_int), POINTER(c_int), POINTER(struct_rt_bot_internal), point_t, mat_t]
    rt_bot_find_e_nearest_pt2.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 110
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_propget'):
    rt_bot_propget = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_propget
    rt_bot_propget.argtypes = [POINTER(struct_rt_bot_internal), String]
    rt_bot_propget.restype = fastf_t

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 112
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_vertex_fuse'):
    rt_bot_vertex_fuse = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_vertex_fuse
    rt_bot_vertex_fuse.argtypes = [POINTER(struct_rt_bot_internal), POINTER(struct_bn_tol)]
    rt_bot_vertex_fuse.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 114
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_face_fuse'):
    rt_bot_face_fuse = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_face_fuse
    rt_bot_face_fuse.argtypes = [POINTER(struct_rt_bot_internal)]
    rt_bot_face_fuse.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 115
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_condense'):
    rt_bot_condense = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_condense
    rt_bot_condense.argtypes = [POINTER(struct_rt_bot_internal)]
    rt_bot_condense.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 116
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_smooth'):
    rt_bot_smooth = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_smooth
    rt_bot_smooth.argtypes = [POINTER(struct_rt_bot_internal), String, POINTER(struct_db_i), fastf_t]
    rt_bot_smooth.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 120
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_flip'):
    rt_bot_flip = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_flip
    rt_bot_flip.argtypes = [POINTER(struct_rt_bot_internal)]
    rt_bot_flip.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 121
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_sync'):
    rt_bot_sync = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_sync
    rt_bot_sync.argtypes = [POINTER(struct_rt_bot_internal)]
    rt_bot_sync.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 122
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_split'):
    rt_bot_split = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_split
    rt_bot_split.argtypes = [POINTER(struct_rt_bot_internal)]
    rt_bot_split.restype = POINTER(struct_rt_bot_list)

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 123
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_patches'):
    rt_bot_patches = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_patches
    rt_bot_patches.argtypes = [POINTER(struct_rt_bot_internal)]
    rt_bot_patches.restype = POINTER(struct_rt_bot_list)

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 124
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_list_free'):
    rt_bot_list_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_list_free
    rt_bot_list_free.argtypes = [POINTER(struct_rt_bot_list), c_int]
    rt_bot_list_free.restype = None

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 127
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_same_orientation'):
    rt_bot_same_orientation = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_same_orientation
    rt_bot_same_orientation.argtypes = [POINTER(c_int), POINTER(c_int)]
    rt_bot_same_orientation.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 130
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_tess'):
    rt_bot_tess = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_tess
    rt_bot_tess.argtypes = [POINTER(POINTER(struct_nmgregion)), POINTER(struct_model), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol)]
    rt_bot_tess.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 136
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_merge'):
    rt_bot_merge = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_merge
    rt_bot_merge.argtypes = [c_size_t, POINTER(POINTER(struct_rt_bot_internal))]
    rt_bot_merge.restype = POINTER(struct_rt_bot_internal)

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 141
try:
    rt_bot_minpieces = (c_size_t).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_minpieces')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 142
try:
    rt_bot_tri_per_piece = (c_size_t).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_tri_per_piece')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 143
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_sort_faces'):
    rt_bot_sort_faces = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_sort_faces
    rt_bot_sort_faces.argtypes = [POINTER(struct_rt_bot_internal), c_size_t]
    rt_bot_sort_faces.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 145
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_decimate'):
    rt_bot_decimate = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_decimate
    rt_bot_decimate.argtypes = [POINTER(struct_rt_bot_internal), fastf_t, fastf_t, fastf_t]
    rt_bot_decimate.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 149
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_bot_decimate_gct'):
    rt_bot_decimate_gct = _libs['/opt/brlcad/lib/librt.dylib'].rt_bot_decimate_gct
    rt_bot_decimate_gct.argtypes = [POINTER(struct_rt_bot_internal), fastf_t]
    rt_bot_decimate_gct.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/primitives/brep.h: 36
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_brep_plot'):
    rt_brep_plot = _libs['/opt/brlcad/lib/librt.dylib'].rt_brep_plot
    rt_brep_plot.argtypes = [POINTER(struct_bu_list), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol), POINTER(struct_rt_view_info)]
    rt_brep_plot.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/brep.h: 41
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_brep_plot_poly'):
    rt_brep_plot_poly = _libs['/opt/brlcad/lib/librt.dylib'].rt_brep_plot_poly
    rt_brep_plot_poly.argtypes = [POINTER(struct_bu_list), POINTER(struct_db_full_path), POINTER(struct_rt_db_internal), POINTER(struct_rt_tess_tol), POINTER(struct_bn_tol), POINTER(struct_rt_view_info)]
    rt_brep_plot_poly.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/brep.h: 48
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_brep_valid'):
    rt_brep_valid = _libs['/opt/brlcad/lib/librt.dylib'].rt_brep_valid
    rt_brep_valid.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_bu_vls)]
    rt_brep_valid.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/tor.h: 32
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_num_circular_segments'):
    rt_num_circular_segments = _libs['/opt/brlcad/lib/librt.dylib'].rt_num_circular_segments
    rt_num_circular_segments.argtypes = [c_double, c_double]
    rt_num_circular_segments.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/rhc.h: 34
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_mk_hyperbola'):
    rt_mk_hyperbola = _libs['/opt/brlcad/lib/librt.dylib'].rt_mk_hyperbola
    rt_mk_hyperbola.argtypes = [POINTER(struct_rt_pt_node), fastf_t, fastf_t, fastf_t, fastf_t, fastf_t]
    rt_mk_hyperbola.restype = c_int

# /opt/brlcad/include/brlcad/./rt/primitives/cline.h: 38
try:
    rt_cline_radius = (fastf_t).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_cline_radius')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/comb.h: 38
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_comb_import4'):
    rt_comb_import4 = _libs['/opt/brlcad/lib/librt.dylib'].rt_comb_import4
    rt_comb_import4.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_bu_external), mat_t, POINTER(struct_db_i), POINTER(struct_resource)]
    rt_comb_import4.restype = c_int

# /opt/brlcad/include/brlcad/./rt/comb.h: 44
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_comb_export4'):
    rt_comb_export4 = _libs['/opt/brlcad/lib/librt.dylib'].rt_comb_export4
    rt_comb_export4.argtypes = [POINTER(struct_bu_external), POINTER(struct_rt_db_internal), c_double, POINTER(struct_db_i), POINTER(struct_resource)]
    rt_comb_export4.restype = c_int

# /opt/brlcad/include/brlcad/./rt/comb.h: 51
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_comb_describe'):
    db_comb_describe = _libs['/opt/brlcad/lib/librt.dylib'].db_comb_describe
    db_comb_describe.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_comb_internal), c_int, c_double]
    db_comb_describe.restype = None

# /opt/brlcad/include/brlcad/./rt/comb.h: 59
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_comb_describe'):
    rt_comb_describe = _libs['/opt/brlcad/lib/librt.dylib'].rt_comb_describe
    rt_comb_describe.argtypes = [POINTER(struct_bu_vls), POINTER(struct_rt_db_internal), c_int, c_double]
    rt_comb_describe.restype = c_int

# /opt/brlcad/include/brlcad/./rt/comb.h: 72
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_comb_get_color'):
    rt_comb_get_color = _libs['/opt/brlcad/lib/librt.dylib'].rt_comb_get_color
    rt_comb_get_color.argtypes = [c_ubyte * 3, POINTER(struct_rt_comb_internal)]
    rt_comb_get_color.restype = c_int

# /opt/brlcad/include/brlcad/./rt/comb.h: 82
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_comb_mvall'):
    db_comb_mvall = _libs['/opt/brlcad/lib/librt.dylib'].db_comb_mvall
    db_comb_mvall.argtypes = [POINTER(struct_directory), POINTER(struct_db_i), String, String, POINTER(struct_bu_ptbl)]
    db_comb_mvall.restype = c_int

# /opt/brlcad/include/brlcad/./rt/comb.h: 103
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_comb_import5'):
    rt_comb_import5 = _libs['/opt/brlcad/lib/librt.dylib'].rt_comb_import5
    rt_comb_import5.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_bu_external), mat_t, POINTER(struct_db_i), POINTER(struct_resource)]
    rt_comb_import5.restype = c_int

# /opt/brlcad/include/brlcad/./rt/comb.h: 150
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_comb_children'):
    db_comb_children = _libs['/opt/brlcad/lib/librt.dylib'].db_comb_children
    db_comb_children.argtypes = [POINTER(struct_db_i), POINTER(struct_rt_comb_internal), POINTER(POINTER(POINTER(struct_directory))), POINTER(POINTER(c_int)), POINTER(POINTER(matp_t))]
    db_comb_children.restype = c_int

# /opt/brlcad/include/brlcad/./rt/misc.h: 34
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_find_paths'):
    rt_find_paths = _libs['/opt/brlcad/lib/librt.dylib'].rt_find_paths
    rt_find_paths.argtypes = [POINTER(struct_db_i), POINTER(struct_directory), POINTER(struct_directory), POINTER(struct_bu_ptbl), POINTER(struct_resource)]
    rt_find_paths.restype = c_int

# /opt/brlcad/include/brlcad/./rt/misc.h: 40
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_get_solidbitv'):
    rt_get_solidbitv = _libs['/opt/brlcad/lib/librt.dylib'].rt_get_solidbitv
    rt_get_solidbitv.argtypes = [c_size_t, POINTER(struct_resource)]
    rt_get_solidbitv.restype = POINTER(struct_bu_bitv)

# /opt/brlcad/include/brlcad/./rt/misc.h: 44
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_id_solid'):
    rt_id_solid = _libs['/opt/brlcad/lib/librt.dylib'].rt_id_solid
    rt_id_solid.argtypes = [POINTER(struct_bu_external)]
    rt_id_solid.restype = c_int

# /opt/brlcad/include/brlcad/./rt/misc.h: 52
class struct_rt_point_labels(Structure):
    pass

struct_rt_point_labels.__slots__ = [
    'str',
    'pt',
]
struct_rt_point_labels._fields_ = [
    ('str', c_char * 8),
    ('pt', point_t),
]

# /opt/brlcad/include/brlcad/./rt/misc.h: 60
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'rt_generate_mesh'):
        continue
    rt_generate_mesh = _lib.rt_generate_mesh
    rt_generate_mesh.argtypes = [POINTER(POINTER(c_int)), POINTER(c_int), POINTER(POINTER(point_t)), POINTER(c_int), POINTER(struct_db_i), String, c_int]
    rt_generate_mesh.restype = None
    break

# /opt/brlcad/include/brlcad/./rt/misc.h: 67
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_reduce_obj'):
    rt_reduce_obj = _libs['/opt/brlcad/lib/librt.dylib'].rt_reduce_obj
    rt_reduce_obj.argtypes = [POINTER(struct_rt_db_internal), POINTER(struct_rt_db_internal), fastf_t, c_uint]
    rt_reduce_obj.restype = None

# /opt/brlcad/include/brlcad/./rt/misc.h: 74
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_reduce_db'):
    rt_reduce_db = _libs['/opt/brlcad/lib/librt.dylib'].rt_reduce_db
    rt_reduce_db.argtypes = [POINTER(struct_db_i), c_size_t, POINTER(POINTER(c_char)), POINTER(struct_bu_ptbl)]
    rt_reduce_db.restype = None

# /opt/brlcad/include/brlcad/./rt/misc.h: 78
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_generic_xform'):
    rt_generic_xform = _libs['/opt/brlcad/lib/librt.dylib'].rt_generic_xform
    rt_generic_xform.argtypes = [POINTER(struct_rt_db_internal), mat_t, POINTER(struct_rt_db_internal), c_int, POINTER(struct_db_i)]
    rt_generic_xform.restype = c_int

# /opt/brlcad/include/brlcad/./rt/misc.h: 83
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_generic_make'):
    rt_generic_make = _libs['/opt/brlcad/lib/librt.dylib'].rt_generic_make
    rt_generic_make.argtypes = [POINTER(struct_rt_functab), POINTER(struct_rt_db_internal)]
    rt_generic_make.restype = None

# /opt/brlcad/include/brlcad/./rt/prep.h: 40
class struct_rt_reprep_obj_list(Structure):
    pass

struct_rt_reprep_obj_list.__slots__ = [
    'ntopobjs',
    'topobjs',
    'nunprepped',
    'unprepped',
    'paths',
    'tsp',
    'unprep_regions',
    'old_nsolids',
    'old_nregions',
    'nsolids_unprepped',
    'nregions_unprepped',
]
struct_rt_reprep_obj_list._fields_ = [
    ('ntopobjs', c_size_t),
    ('topobjs', POINTER(POINTER(c_char))),
    ('nunprepped', c_size_t),
    ('unprepped', POINTER(POINTER(c_char))),
    ('paths', struct_bu_ptbl),
    ('tsp', POINTER(POINTER(struct_db_tree_state))),
    ('unprep_regions', struct_bu_ptbl),
    ('old_nsolids', c_size_t),
    ('old_nregions', c_size_t),
    ('nsolids_unprepped', c_size_t),
    ('nregions_unprepped', c_size_t),
]

# /opt/brlcad/include/brlcad/./rt/prep.h: 57
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_unprep'):
    rt_unprep = _libs['/opt/brlcad/lib/librt.dylib'].rt_unprep
    rt_unprep.argtypes = [POINTER(struct_rt_i), POINTER(struct_rt_reprep_obj_list), POINTER(struct_resource)]
    rt_unprep.restype = c_int

# /opt/brlcad/include/brlcad/./rt/prep.h: 60
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_reprep'):
    rt_reprep = _libs['/opt/brlcad/lib/librt.dylib'].rt_reprep
    rt_reprep.argtypes = [POINTER(struct_rt_i), POINTER(struct_rt_reprep_obj_list), POINTER(struct_resource)]
    rt_reprep.restype = c_int

# /opt/brlcad/include/brlcad/./rt/prep.h: 63
for _lib in _libs.itervalues():
    if not hasattr(_lib, 're_prep_solids'):
        continue
    re_prep_solids = _lib.re_prep_solids
    re_prep_solids.argtypes = [POINTER(struct_rt_i), c_int, POINTER(POINTER(c_char)), POINTER(struct_resource)]
    re_prep_solids.restype = c_int
    break

# /opt/brlcad/include/brlcad/./rt/vlist.h: 43
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_vlist_copy'):
    rt_vlist_copy = _libs['/opt/brlcad/lib/librt.dylib'].rt_vlist_copy
    rt_vlist_copy.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list)]
    rt_vlist_copy.restype = None

# /opt/brlcad/include/brlcad/./rt/vlist.h: 45
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_vlist_cleanup'):
    rt_vlist_cleanup = _libs['/opt/brlcad/lib/librt.dylib'].rt_vlist_cleanup
    rt_vlist_cleanup.argtypes = []
    rt_vlist_cleanup.restype = None

# /opt/brlcad/include/brlcad/./rt/vlist.h: 46
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_vlist_import'):
    rt_vlist_import = _libs['/opt/brlcad/lib/librt.dylib'].rt_vlist_import
    rt_vlist_import.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_vls), POINTER(c_ubyte)]
    rt_vlist_import.restype = None

# /opt/brlcad/include/brlcad/./rt/vlist.h: 49
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_vlblock_init'):
    rt_vlblock_init = _libs['/opt/brlcad/lib/librt.dylib'].rt_vlblock_init
    rt_vlblock_init.argtypes = []
    rt_vlblock_init.restype = POINTER(struct_bn_vlblock)

# /opt/brlcad/include/brlcad/./rt/vlist.h: 81
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_label_vlist_verts'):
    rt_label_vlist_verts = _libs['/opt/brlcad/lib/librt.dylib'].rt_label_vlist_verts
    rt_label_vlist_verts.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_bu_list), mat_t, c_double, c_double]
    rt_label_vlist_verts.restype = None

# /opt/brlcad/include/brlcad/./rt/vlist.h: 90
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_label_vlist_faces'):
    rt_label_vlist_faces = _libs['/opt/brlcad/lib/librt.dylib'].rt_label_vlist_faces
    rt_label_vlist_faces.argtypes = [POINTER(struct_bn_vlblock), POINTER(struct_bu_list), mat_t, c_double, c_double]
    rt_label_vlist_faces.restype = None

# /opt/brlcad/include/brlcad/./rt/htbl.h: 35
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_htbl_init'):
    rt_htbl_init = _libs['/opt/brlcad/lib/librt.dylib'].rt_htbl_init
    rt_htbl_init.argtypes = [POINTER(struct_rt_htbl), c_size_t, String]
    rt_htbl_init.restype = None

# /opt/brlcad/include/brlcad/./rt/htbl.h: 40
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_htbl_reset'):
    rt_htbl_reset = _libs['/opt/brlcad/lib/librt.dylib'].rt_htbl_reset
    rt_htbl_reset.argtypes = [POINTER(struct_rt_htbl)]
    rt_htbl_reset.restype = None

# /opt/brlcad/include/brlcad/./rt/htbl.h: 46
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_htbl_free'):
    rt_htbl_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_htbl_free
    rt_htbl_free.argtypes = [POINTER(struct_rt_htbl)]
    rt_htbl_free.restype = None

# /opt/brlcad/include/brlcad/./rt/htbl.h: 51
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_htbl_get'):
    rt_htbl_get = _libs['/opt/brlcad/lib/librt.dylib'].rt_htbl_get
    rt_htbl_get.argtypes = [POINTER(struct_rt_htbl)]
    rt_htbl_get.restype = POINTER(struct_hit)

# /opt/brlcad/include/brlcad/./rt/dspline.h: 34
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dspline_matrix'):
    rt_dspline_matrix = _libs['/opt/brlcad/lib/librt.dylib'].rt_dspline_matrix
    rt_dspline_matrix.argtypes = [mat_t, String, c_double, c_double]
    rt_dspline_matrix.restype = None

# /opt/brlcad/include/brlcad/./rt/dspline.h: 46
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dspline4'):
    rt_dspline4 = _libs['/opt/brlcad/lib/librt.dylib'].rt_dspline4
    rt_dspline4.argtypes = [mat_t, c_double, c_double, c_double, c_double, c_double]
    rt_dspline4.restype = c_double

# /opt/brlcad/include/brlcad/./rt/dspline.h: 63
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dspline4v'):
    rt_dspline4v = _libs['/opt/brlcad/lib/librt.dylib'].rt_dspline4v
    rt_dspline4v.argtypes = [POINTER(c_double), mat_t, POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double), c_int, c_double]
    rt_dspline4v.restype = None

# /opt/brlcad/include/brlcad/./rt/dspline.h: 97
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dspline_n'):
    rt_dspline_n = _libs['/opt/brlcad/lib/librt.dylib'].rt_dspline_n
    rt_dspline_n.argtypes = [POINTER(c_double), mat_t, POINTER(c_double), c_int, c_int, c_double]
    rt_dspline_n.restype = None

enum_anon_91 = c_int # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_REGION = 0 # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_REGION_ID = (ATTR_REGION + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_MATERIAL_ID = (ATTR_REGION_ID + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_AIR = (ATTR_MATERIAL_ID + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_LOS = (ATTR_AIR + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_COLOR = (ATTR_LOS + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_SHADER = (ATTR_COLOR + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_INHERIT = (ATTR_SHADER + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_TIMESTAMP = (ATTR_INHERIT + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

ATTR_NULL = (ATTR_TIMESTAMP + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 44

enum_anon_92 = c_int # /opt/brlcad/include/brlcad/./rt/db_attr.h: 58

ATTR_STANDARD = 0 # /opt/brlcad/include/brlcad/./rt/db_attr.h: 58

ATTR_USER_DEFINED = (ATTR_STANDARD + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 58

ATTR_UNKNOWN_ORIGIN = (ATTR_USER_DEFINED + 1) # /opt/brlcad/include/brlcad/./rt/db_attr.h: 58

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 64
class struct_db5_attr_ctype(Structure):
    pass

struct_db5_attr_ctype.__slots__ = [
    'attr_type',
    'is_binary',
    'attr_subtype',
    'name',
    'description',
    'examples',
    'aliases',
    'property',
    'long_description',
]
struct_db5_attr_ctype._fields_ = [
    ('attr_type', c_int),
    ('is_binary', c_int),
    ('attr_subtype', c_int),
    ('name', String),
    ('description', String),
    ('examples', String),
    ('aliases', String),
    ('property', String),
    ('long_description', String),
]

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 83
try:
    db5_attr_std = (POINTER(struct_db5_attr_ctype)).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_std')
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 86
class struct_db5_registry(Structure):
    pass

struct_db5_registry.__slots__ = [
    'internal',
]
struct_db5_registry._fields_ = [
    ('internal', POINTER(None)),
]

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 96
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_registry_init'):
    db5_attr_registry_init = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_registry_init
    db5_attr_registry_init.argtypes = [POINTER(struct_db5_registry)]
    db5_attr_registry_init.restype = None

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 104
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_registry_free'):
    db5_attr_registry_free = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_registry_free
    db5_attr_registry_free.argtypes = [POINTER(struct_db5_registry)]
    db5_attr_registry_free.restype = None

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 112
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_create'):
    db5_attr_create = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_create
    db5_attr_create.argtypes = [POINTER(struct_db5_registry), c_int, c_int, c_int, String, String, String, String, String, String]
    db5_attr_create.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 129
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_register'):
    db5_attr_register = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_register
    db5_attr_register.argtypes = [POINTER(struct_db5_registry), POINTER(struct_db5_attr_ctype)]
    db5_attr_register.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 138
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_deregister'):
    db5_attr_deregister = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_deregister
    db5_attr_deregister.argtypes = [POINTER(struct_db5_registry), String]
    db5_attr_deregister.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 147
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_get'):
    db5_attr_get = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_get
    db5_attr_get.argtypes = [POINTER(struct_db5_registry), String]
    db5_attr_get.restype = POINTER(struct_db5_attr_ctype)

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 156
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_attr_dump'):
    db5_attr_dump = _libs['/opt/brlcad/lib/librt.dylib'].db5_attr_dump
    db5_attr_dump.argtypes = [POINTER(struct_db5_registry)]
    db5_attr_dump.restype = POINTER(POINTER(struct_db5_attr_ctype))

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 169
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_standard_attribute'):
    db5_standard_attribute = _libs['/opt/brlcad/lib/librt.dylib'].db5_standard_attribute
    db5_standard_attribute.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        db5_standard_attribute.restype = ReturnString
    else:
        db5_standard_attribute.restype = String
        db5_standard_attribute.errcheck = ReturnString

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 183
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'db5_standard_attribute_def'):
        continue
    db5_standard_attribute_def = _lib.db5_standard_attribute_def
    db5_standard_attribute_def.argtypes = [c_int]
    if sizeof(c_int) == sizeof(c_void_p):
        db5_standard_attribute_def.restype = ReturnString
    else:
        db5_standard_attribute_def.restype = String
        db5_standard_attribute_def.errcheck = ReturnString
    break

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 194
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_is_standard_attribute'):
    db5_is_standard_attribute = _libs['/opt/brlcad/lib/librt.dylib'].db5_is_standard_attribute
    db5_is_standard_attribute.argtypes = [String]
    db5_is_standard_attribute.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 209
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_standardize_avs'):
    db5_standardize_avs = _libs['/opt/brlcad/lib/librt.dylib'].db5_standardize_avs
    db5_standardize_avs.argtypes = [POINTER(struct_bu_attribute_value_set)]
    db5_standardize_avs.restype = c_size_t

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 215
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_standardize_attribute'):
    db5_standardize_attribute = _libs['/opt/brlcad/lib/librt.dylib'].db5_standardize_attribute
    db5_standardize_attribute.argtypes = [String]
    db5_standardize_attribute.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 220
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_sync_attr_to_comb'):
    db5_sync_attr_to_comb = _libs['/opt/brlcad/lib/librt.dylib'].db5_sync_attr_to_comb
    db5_sync_attr_to_comb.argtypes = [POINTER(struct_rt_comb_internal), POINTER(struct_bu_attribute_value_set), POINTER(struct_directory)]
    db5_sync_attr_to_comb.restype = None

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 225
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_sync_comb_to_attr'):
    db5_sync_comb_to_attr = _libs['/opt/brlcad/lib/librt.dylib'].db5_sync_comb_to_attr
    db5_sync_comb_to_attr.argtypes = [POINTER(struct_bu_attribute_value_set), POINTER(struct_rt_comb_internal)]
    db5_sync_comb_to_attr.restype = None

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 247
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_import_attributes'):
    db5_import_attributes = _libs['/opt/brlcad/lib/librt.dylib'].db5_import_attributes
    db5_import_attributes.argtypes = [POINTER(struct_bu_attribute_value_set), POINTER(struct_bu_external)]
    db5_import_attributes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 265
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_export_attributes'):
    db5_export_attributes = _libs['/opt/brlcad/lib/librt.dylib'].db5_export_attributes
    db5_export_attributes.argtypes = [POINTER(struct_bu_external), POINTER(struct_bu_attribute_value_set)]
    db5_export_attributes.restype = None

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 291
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_lookup_by_attr'):
    db_lookup_by_attr = _libs['/opt/brlcad/lib/librt.dylib'].db_lookup_by_attr
    db_lookup_by_attr.argtypes = [POINTER(struct_db_i), c_int, POINTER(struct_bu_attribute_value_set), c_int]
    db_lookup_by_attr.restype = POINTER(struct_bu_ptbl)

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 303
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_put_color_table'):
    db5_put_color_table = _libs['/opt/brlcad/lib/librt.dylib'].db5_put_color_table
    db5_put_color_table.argtypes = [POINTER(struct_db_i)]
    db5_put_color_table.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 304
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_update_ident'):
    db5_update_ident = _libs['/opt/brlcad/lib/librt.dylib'].db5_update_ident
    db5_update_ident.argtypes = [POINTER(struct_db_i), String, c_double]
    db5_update_ident.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 321
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_update_attributes'):
    db5_update_attributes = _libs['/opt/brlcad/lib/librt.dylib'].db5_update_attributes
    db5_update_attributes.argtypes = [POINTER(struct_directory), POINTER(struct_bu_attribute_value_set), POINTER(struct_db_i)]
    db5_update_attributes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 332
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_update_attribute'):
    db5_update_attribute = _libs['/opt/brlcad/lib/librt.dylib'].db5_update_attribute
    db5_update_attribute.argtypes = [String, String, String, POINTER(struct_db_i)]
    db5_update_attribute.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 348
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_replace_attributes'):
    db5_replace_attributes = _libs['/opt/brlcad/lib/librt.dylib'].db5_replace_attributes
    db5_replace_attributes.argtypes = [POINTER(struct_directory), POINTER(struct_bu_attribute_value_set), POINTER(struct_db_i)]
    db5_replace_attributes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 360
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db5_get_attributes'):
    db5_get_attributes = _libs['/opt/brlcad/lib/librt.dylib'].db5_get_attributes
    db5_get_attributes.argtypes = [POINTER(struct_db_i), POINTER(struct_bu_attribute_value_set), POINTER(struct_directory)]
    db5_get_attributes.restype = c_int

# /opt/brlcad/include/brlcad/./rt/binunif.h: 35
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_mk_binunif'):
    rt_mk_binunif = _libs['/opt/brlcad/lib/librt.dylib'].rt_mk_binunif
    rt_mk_binunif.argtypes = [POINTER(struct_rt_wdb), String, String, c_uint, c_size_t]
    rt_mk_binunif.restype = c_int

# /opt/brlcad/include/brlcad/./rt/binunif.h: 47
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_binunif_free'):
    rt_binunif_free = _libs['/opt/brlcad/lib/librt.dylib'].rt_binunif_free
    rt_binunif_free.argtypes = [POINTER(struct_rt_binunif_internal)]
    rt_binunif_free.restype = None

# /opt/brlcad/include/brlcad/./rt/binunif.h: 52
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_binunif_dump'):
    rt_binunif_dump = _libs['/opt/brlcad/lib/librt.dylib'].rt_binunif_dump
    rt_binunif_dump.argtypes = [POINTER(struct_rt_binunif_internal)]
    rt_binunif_dump.restype = None

# /opt/brlcad/include/brlcad/./rt/version.h: 37
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_version'):
    rt_version = _libs['/opt/brlcad/lib/librt.dylib'].rt_version
    rt_version.argtypes = []
    if sizeof(c_int) == sizeof(c_void_p):
        rt_version.restype = ReturnString
    else:
        rt_version.restype = String
        rt_version.errcheck = ReturnString

# /opt/brlcad/include/brlcad/rt/solid.h: 38
class struct_solid(Structure):
    pass

struct_solid.__slots__ = [
    'l',
    's_size',
    's_csize',
    's_center',
    's_vlist',
    's_vlen',
    's_fullpath',
    's_flag',
    's_iflag',
    's_soldash',
    's_Eflag',
    's_uflag',
    's_dflag',
    's_cflag',
    's_wflag',
    's_basecolor',
    's_color',
    's_regionid',
    's_dlist',
    's_transparency',
    's_dmode',
    's_hiddenLine',
    's_mat',
]
struct_solid._fields_ = [
    ('l', struct_bu_list),
    ('s_size', fastf_t),
    ('s_csize', fastf_t),
    ('s_center', vect_t),
    ('s_vlist', struct_bu_list),
    ('s_vlen', c_int),
    ('s_fullpath', struct_db_full_path),
    ('s_flag', c_char),
    ('s_iflag', c_char),
    ('s_soldash', c_char),
    ('s_Eflag', c_char),
    ('s_uflag', c_char),
    ('s_dflag', c_char),
    ('s_cflag', c_char),
    ('s_wflag', c_char),
    ('s_basecolor', c_ubyte * 3),
    ('s_color', c_ubyte * 3),
    ('s_regionid', c_short),
    ('s_dlist', c_uint),
    ('s_transparency', fastf_t),
    ('s_dmode', c_int),
    ('s_hiddenLine', c_int),
    ('s_mat', mat_t),
]

# /opt/brlcad/include/brlcad/rt/db_diff.h: 51
class struct_diff_avp(Structure):
    pass

struct_diff_avp.__slots__ = [
    'name',
    'state',
    'left_value',
    'ancestor_value',
    'right_value',
]
struct_diff_avp._fields_ = [
    ('name', String),
    ('state', c_int),
    ('left_value', String),
    ('ancestor_value', String),
    ('right_value', String),
]

# /opt/brlcad/include/brlcad/rt/db_diff.h: 58
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'diff_init_avp'):
    diff_init_avp = _libs['/opt/brlcad/lib/librt.dylib'].diff_init_avp
    diff_init_avp.argtypes = [POINTER(struct_diff_avp)]
    diff_init_avp.restype = None

# /opt/brlcad/include/brlcad/rt/db_diff.h: 59
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'diff_free_avp'):
    diff_free_avp = _libs['/opt/brlcad/lib/librt.dylib'].diff_free_avp
    diff_free_avp.argtypes = [POINTER(struct_diff_avp)]
    diff_free_avp.restype = None

# /opt/brlcad/include/brlcad/rt/db_diff.h: 60
class struct_diff_result(Structure):
    pass

struct_diff_result.__slots__ = [
    'obj_name',
    'diff_tol',
    'dp_left',
    'dp_ancestor',
    'dp_right',
    'param_state',
    'attr_state',
    'param_diffs',
    'attr_diffs',
]
struct_diff_result._fields_ = [
    ('obj_name', String),
    ('diff_tol', POINTER(struct_bn_tol)),
    ('dp_left', POINTER(struct_directory)),
    ('dp_ancestor', POINTER(struct_directory)),
    ('dp_right', POINTER(struct_directory)),
    ('param_state', c_int),
    ('attr_state', c_int),
    ('param_diffs', POINTER(struct_bu_ptbl)),
    ('attr_diffs', POINTER(struct_bu_ptbl)),
]

# /opt/brlcad/include/brlcad/rt/db_diff.h: 71
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'diff_init_result'):
    diff_init_result = _libs['/opt/brlcad/lib/librt.dylib'].diff_init_result
    diff_init_result.argtypes = [POINTER(struct_diff_result), POINTER(struct_bn_tol), String]
    diff_init_result.restype = None

# /opt/brlcad/include/brlcad/rt/db_diff.h: 72
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'diff_free_result'):
    diff_free_result = _libs['/opt/brlcad/lib/librt.dylib'].diff_free_result
    diff_free_result.argtypes = [POINTER(struct_diff_result)]
    diff_free_result.restype = None

enum_anon_93 = c_int # /opt/brlcad/include/brlcad/rt/db_diff.h: 84

DB_COMPARE_ALL = 0 # /opt/brlcad/include/brlcad/rt/db_diff.h: 84

DB_COMPARE_PARAM = 1 # /opt/brlcad/include/brlcad/rt/db_diff.h: 84

DB_COMPARE_ATTRS = 2 # /opt/brlcad/include/brlcad/rt/db_diff.h: 84

db_compare_criteria_t = enum_anon_93 # /opt/brlcad/include/brlcad/rt/db_diff.h: 84

# /opt/brlcad/include/brlcad/rt/db_diff.h: 92
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_avs_diff'):
    db_avs_diff = _libs['/opt/brlcad/lib/librt.dylib'].db_avs_diff
    db_avs_diff.argtypes = [POINTER(struct_bu_attribute_value_set), POINTER(struct_bu_attribute_value_set), POINTER(struct_bn_tol), CFUNCTYPE(UNCHECKED(c_int), String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, POINTER(None)), POINTER(None)]
    db_avs_diff.restype = c_int

# /opt/brlcad/include/brlcad/rt/db_diff.h: 105
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_avs_diff3'):
    db_avs_diff3 = _libs['/opt/brlcad/lib/librt.dylib'].db_avs_diff3
    db_avs_diff3.argtypes = [POINTER(struct_bu_attribute_value_set), POINTER(struct_bu_attribute_value_set), POINTER(struct_bu_attribute_value_set), POINTER(struct_bn_tol), CFUNCTYPE(UNCHECKED(c_int), String, String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, String, String, POINTER(None)), CFUNCTYPE(UNCHECKED(c_int), String, String, POINTER(None)), POINTER(None)]
    db_avs_diff3.restype = c_int

# /opt/brlcad/include/brlcad/rt/db_diff.h: 157
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_diff_dp'):
    db_diff_dp = _libs['/opt/brlcad/lib/librt.dylib'].db_diff_dp
    db_diff_dp.argtypes = [POINTER(struct_db_i), POINTER(struct_db_i), POINTER(struct_directory), POINTER(struct_directory), POINTER(struct_bn_tol), db_compare_criteria_t, POINTER(struct_diff_result)]
    db_diff_dp.restype = c_int

# /opt/brlcad/include/brlcad/rt/db_diff.h: 185
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_diff3_dp'):
    db_diff3_dp = _libs['/opt/brlcad/lib/librt.dylib'].db_diff3_dp
    db_diff3_dp.argtypes = [POINTER(struct_db_i), POINTER(struct_db_i), POINTER(struct_db_i), POINTER(struct_directory), POINTER(struct_directory), POINTER(struct_directory), POINTER(struct_bn_tol), db_compare_criteria_t, POINTER(struct_diff_result)]
    db_diff3_dp.restype = c_int

# /opt/brlcad/include/brlcad/rt/db_diff.h: 214
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_diff'):
    db_diff = _libs['/opt/brlcad/lib/librt.dylib'].db_diff
    db_diff.argtypes = [POINTER(struct_db_i), POINTER(struct_db_i), POINTER(struct_bn_tol), db_compare_criteria_t, POINTER(struct_bu_ptbl)]
    db_diff.restype = c_int

# /opt/brlcad/include/brlcad/rt/db_diff.h: 234
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'db_diff3'):
    db_diff3 = _libs['/opt/brlcad/lib/librt.dylib'].db_diff3
    db_diff3.argtypes = [POINTER(struct_db_i), POINTER(struct_db_i), POINTER(struct_db_i), POINTER(struct_bn_tol), db_compare_criteria_t, POINTER(struct_bu_ptbl)]
    db_diff3.restype = c_int

TFLOAT = c_double # /opt/brlcad/include/brlcad/rt/tie.h: 65

# /opt/brlcad/include/brlcad/rt/tie.h: 78
class struct_TIE_3_s(Structure):
    pass

struct_TIE_3_s.__slots__ = [
    'v',
]
struct_TIE_3_s._fields_ = [
    ('v', TFLOAT * 3),
]

TIE_3 = struct_TIE_3_s # /opt/brlcad/include/brlcad/rt/tie.h: 78

# /opt/brlcad/include/brlcad/rt/tie.h: 80
class struct_tie_ray_s(Structure):
    pass

struct_tie_ray_s.__slots__ = [
    'pos',
    'dir',
    'depth',
    'kdtree_depth',
]
struct_tie_ray_s._fields_ = [
    ('pos', point_t),
    ('dir', vect_t),
    ('depth', c_short),
    ('kdtree_depth', c_short),
]

# /opt/brlcad/include/brlcad/rt/tie.h: 87
class struct_tie_id_s(Structure):
    pass

struct_tie_id_s.__slots__ = [
    'pos',
    'norm',
    'dist',
    'alpha',
    'beta',
]
struct_tie_id_s._fields_ = [
    ('pos', point_t),
    ('norm', vect_t),
    ('dist', fastf_t),
    ('alpha', fastf_t),
    ('beta', fastf_t),
]

# /opt/brlcad/include/brlcad/rt/tie.h: 95
class struct_tie_tri_s(Structure):
    pass

struct_tie_tri_s.__slots__ = [
    'data',
    'v',
    'ptr',
    'b',
]
struct_tie_tri_s._fields_ = [
    ('data', TIE_3 * 3),
    ('v', TFLOAT * 2),
    ('ptr', POINTER(None)),
    ('b', c_uint32),
]

# /opt/brlcad/include/brlcad/rt/tie.h: 107
class struct_tie_kdtree_s(Structure):
    pass

struct_tie_kdtree_s.__slots__ = [
    'axis',
    'b',
    'data',
]
struct_tie_kdtree_s._fields_ = [
    ('axis', c_float),
    ('b', c_uint32),
    ('data', POINTER(None)),
]

# /opt/brlcad/include/brlcad/rt/tie.h: 114
class struct_tie_s(Structure):
    pass

struct_tie_s.__slots__ = [
    'rays_fired',
    'kdtree',
    'max_depth',
    'tri_num',
    'tri_num_alloc',
    'tri_list',
    'stat',
    'kdmethod',
    'min',
    'max',
    'amin',
    'amax',
    'mid',
    'radius',
]
struct_tie_s._fields_ = [
    ('rays_fired', c_uint64),
    ('kdtree', POINTER(struct_tie_kdtree_s)),
    ('max_depth', c_uint),
    ('tri_num', c_uint),
    ('tri_num_alloc', c_uint),
    ('tri_list', POINTER(struct_tie_tri_s)),
    ('stat', c_int),
    ('kdmethod', c_uint),
    ('min', point_t),
    ('max', point_t),
    ('amin', vect_t),
    ('amax', vect_t),
    ('mid', vect_t),
    ('radius', fastf_t),
]

# /opt/brlcad/include/brlcad/rt/tie.h: 128
try:
    tie_check_degenerate = (c_int).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_check_degenerate')
except:
    pass

# /opt/brlcad/include/brlcad/rt/tie.h: 129
try:
    TIE_PREC = (fastf_t).in_dll(_libs['/opt/brlcad/lib/librt.dylib'], 'TIE_PREC')
except:
    pass

# /opt/brlcad/include/brlcad/rt/tie.h: 139
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_init_double'):
    tie_init_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_init_double
    tie_init_double.argtypes = [POINTER(struct_tie_s), c_uint, c_uint]
    tie_init_double.restype = None

# /opt/brlcad/include/brlcad/rt/tie.h: 140
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_free_double'):
    tie_free_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_free_double
    tie_free_double.argtypes = [POINTER(struct_tie_s)]
    tie_free_double.restype = None

# /opt/brlcad/include/brlcad/rt/tie.h: 141
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_prep_double'):
    tie_prep_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_prep_double
    tie_prep_double.argtypes = [POINTER(struct_tie_s)]
    tie_prep_double.restype = None

# /opt/brlcad/include/brlcad/rt/tie.h: 142
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_work_double'):
    tie_work_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_work_double
    tie_work_double.argtypes = [POINTER(struct_tie_s), POINTER(struct_tie_ray_s), POINTER(struct_tie_id_s), CFUNCTYPE(UNCHECKED(POINTER(None)), POINTER(struct_tie_ray_s), POINTER(struct_tie_id_s), POINTER(struct_tie_tri_s), POINTER(None)), POINTER(None)]
    tie_work_double.restype = POINTER(None)

# /opt/brlcad/include/brlcad/rt/tie.h: 143
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_push_double'):
    tie_push_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_push_double
    tie_push_double.argtypes = [POINTER(struct_tie_s), POINTER(POINTER(TIE_3)), c_uint, POINTER(None), c_uint]
    tie_push_double.restype = None

# /opt/brlcad/include/brlcad/rt/tie.h: 144
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_kdtree_free_double'):
    tie_kdtree_free_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_kdtree_free_double
    tie_kdtree_free_double.argtypes = [POINTER(struct_tie_s)]
    tie_kdtree_free_double.restype = None

# /opt/brlcad/include/brlcad/rt/tie.h: 145
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'tie_kdtree_prep_double'):
    tie_kdtree_prep_double = _libs['/opt/brlcad/lib/librt.dylib'].tie_kdtree_prep_double
    tie_kdtree_prep_double.argtypes = [POINTER(struct_tie_s)]
    tie_kdtree_prep_double.restype = None

dbfloat_t = c_float # /opt/brlcad/include/brlcad/rt/db4.h: 83

# /opt/brlcad/include/brlcad/rt/db4.h: 88
class struct_ident(Structure):
    pass

struct_ident.__slots__ = [
    'i_id',
    'i_units',
    'i_version',
    'i_title',
    'i_byteorder',
    'i_floattype',
]
struct_ident._fields_ = [
    ('i_id', c_char),
    ('i_units', c_char),
    ('i_version', c_char * 6),
    ('i_title', c_char * 72),
    ('i_byteorder', c_char),
    ('i_floattype', c_char),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 119
class struct_solidrec(Structure):
    pass

struct_solidrec.__slots__ = [
    's_id',
    's_type',
    's_name',
    's_cgtype',
    's_values',
]
struct_solidrec._fields_ = [
    ('s_id', c_char),
    ('s_type', c_char),
    ('s_name', c_char * 16),
    ('s_cgtype', c_short),
    ('s_values', dbfloat_t * 24),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 194
class struct_combination(Structure):
    pass

struct_combination.__slots__ = [
    'c_id',
    'c_flags',
    'c_name',
    'c_regionid',
    'c_aircode',
    'c_pad1',
    'c_pad2',
    'c_material',
    'c_los',
    'c_override',
    'c_rgb',
    'c_matname',
    'c_matparm',
    'c_inherit',
]
struct_combination._fields_ = [
    ('c_id', c_char),
    ('c_flags', c_char),
    ('c_name', c_char * 16),
    ('c_regionid', c_short),
    ('c_aircode', c_short),
    ('c_pad1', c_short),
    ('c_pad2', c_short),
    ('c_material', c_short),
    ('c_los', c_short),
    ('c_override', c_char),
    ('c_rgb', c_ubyte * 3),
    ('c_matname', c_char * 32),
    ('c_matparm', c_char * 60),
    ('c_inherit', c_char),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 218
class struct_member(Structure):
    pass

struct_member.__slots__ = [
    'm_id',
    'm_relation',
    'm_brname',
    'm_instname',
    'm_pad1',
    'm_mat',
    'm_pad2',
]
struct_member._fields_ = [
    ('m_id', c_char),
    ('m_relation', c_char),
    ('m_brname', c_char * 16),
    ('m_instname', c_char * 16),
    ('m_pad1', c_short),
    ('m_mat', dbfloat_t * 16),
    ('m_pad2', c_short),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 228
class struct_material_rec(Structure):
    pass

struct_material_rec.__slots__ = [
    'md_id',
    'md_flags',
    'md_low',
    'md_hi',
    'md_r',
    'md_g',
    'md_b',
    'md_material',
]
struct_material_rec._fields_ = [
    ('md_id', c_char),
    ('md_flags', c_char),
    ('md_low', c_short),
    ('md_hi', c_short),
    ('md_r', c_ubyte),
    ('md_g', c_ubyte),
    ('md_b', c_ubyte),
    ('md_material', c_char * 100),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 239
class struct_B_solid(Structure):
    pass

struct_B_solid.__slots__ = [
    'B_id',
    'B_pad',
    'B_name',
    'B_nsurf',
    'B_unused',
]
struct_B_solid._fields_ = [
    ('B_id', c_char),
    ('B_pad', c_char),
    ('B_name', c_char * 16),
    ('B_nsurf', c_short),
    ('B_unused', dbfloat_t),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 247
class struct_b_surf(Structure):
    pass

struct_b_surf.__slots__ = [
    'd_id',
    'd_order',
    'd_kv_size',
    'd_ctl_size',
    'd_geom_type',
    'd_nknots',
    'd_nctls',
]
struct_b_surf._fields_ = [
    ('d_id', c_char),
    ('d_order', c_short * 2),
    ('d_kv_size', c_short * 2),
    ('d_ctl_size', c_short * 2),
    ('d_geom_type', c_short),
    ('d_nknots', c_short),
    ('d_nctls', c_short),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 257
class struct_polyhead(Structure):
    pass

struct_polyhead.__slots__ = [
    'p_id',
    'p_pad1',
    'p_name',
]
struct_polyhead._fields_ = [
    ('p_id', c_char),
    ('p_pad1', c_char),
    ('p_name', c_char * 16),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 263
class struct_polydata(Structure):
    pass

struct_polydata.__slots__ = [
    'q_id',
    'q_count',
    'q_verts',
    'q_norms',
]
struct_polydata._fields_ = [
    ('q_id', c_char),
    ('q_count', c_char),
    ('q_verts', (dbfloat_t * 3) * 5),
    ('q_norms', (dbfloat_t * 3) * 5),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 270
class struct_ars_rec(Structure):
    pass

struct_ars_rec.__slots__ = [
    'a_id',
    'a_type',
    'a_name',
    'a_m',
    'a_n',
    'a_curlen',
    'a_totlen',
    'a_pad',
    'a_xmax',
    'a_xmin',
    'a_ymax',
    'a_ymin',
    'a_zmax',
    'a_zmin',
]
struct_ars_rec._fields_ = [
    ('a_id', c_char),
    ('a_type', c_char),
    ('a_name', c_char * 16),
    ('a_m', c_short),
    ('a_n', c_short),
    ('a_curlen', c_short),
    ('a_totlen', c_short),
    ('a_pad', c_short),
    ('a_xmax', dbfloat_t),
    ('a_xmin', dbfloat_t),
    ('a_ymax', dbfloat_t),
    ('a_ymin', dbfloat_t),
    ('a_zmax', dbfloat_t),
    ('a_zmin', dbfloat_t),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 289
class struct_ars_ext(Structure):
    pass

struct_ars_ext.__slots__ = [
    'b_id',
    'b_type',
    'b_n',
    'b_ngranule',
    'b_pad',
    'b_values',
]
struct_ars_ext._fields_ = [
    ('b_id', c_char),
    ('b_type', c_char),
    ('b_n', c_short),
    ('b_ngranule', c_short),
    ('b_pad', c_short),
    ('b_values', dbfloat_t * (8 * 3)),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 298
class struct_strsol(Structure):
    pass

struct_strsol.__slots__ = [
    'ss_id',
    'ss_pad',
    'ss_name',
    'ss_keyword',
    'ss_args',
]
struct_strsol._fields_ = [
    ('ss_id', c_char),
    ('ss_pad', c_char),
    ('ss_name', c_char * 16),
    ('ss_keyword', c_char * 16),
    ('ss_args', c_char * 4),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 308
class struct_arbn_rec(Structure):
    pass

struct_arbn_rec.__slots__ = [
    'n_id',
    'n_pad',
    'n_name',
    'n_neqn',
    'n_grans',
]
struct_arbn_rec._fields_ = [
    ('n_id', c_char),
    ('n_pad', c_char),
    ('n_name', c_char * 16),
    ('n_neqn', c_ubyte * 4),
    ('n_grans', c_ubyte * 4),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 317
class struct_exported_pipept(Structure):
    pass

struct_exported_pipept.__slots__ = [
    'epp_coord',
    'epp_bendradius',
    'epp_id',
    'epp_od',
]
struct_exported_pipept._fields_ = [
    ('epp_coord', c_ubyte * (8 * 3)),
    ('epp_bendradius', c_ubyte * 8),
    ('epp_id', c_ubyte * 8),
    ('epp_od', c_ubyte * 8),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 324
class struct_pipewire_rec(Structure):
    pass

struct_pipewire_rec.__slots__ = [
    'pwr_id',
    'pwr_pad',
    'pwr_name',
    'pwr_pt_count',
    'pwr_count',
    'pwr_data',
]
struct_pipewire_rec._fields_ = [
    ('pwr_id', c_char),
    ('pwr_pad', c_char),
    ('pwr_name', c_char * 16),
    ('pwr_pt_count', c_ubyte * 4),
    ('pwr_count', c_ubyte * 4),
    ('pwr_data', struct_exported_pipept * 1),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 333
class struct_particle_rec(Structure):
    pass

struct_particle_rec.__slots__ = [
    'p_id',
    'p_pad',
    'p_name',
    'p_v',
    'p_h',
    'p_vrad',
    'p_hrad',
]
struct_particle_rec._fields_ = [
    ('p_id', c_char),
    ('p_pad', c_char),
    ('p_name', c_char * 16),
    ('p_v', c_ubyte * (8 * 3)),
    ('p_h', c_ubyte * (8 * 3)),
    ('p_vrad', c_ubyte * 8),
    ('p_hrad', c_ubyte * 8),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 343
class struct_nmg_rec(Structure):
    pass

struct_nmg_rec.__slots__ = [
    'N_id',
    'N_version',
    'N_name',
    'N_pad2',
    'N_count',
    'N_structs',
]
struct_nmg_rec._fields_ = [
    ('N_id', c_char),
    ('N_version', c_char),
    ('N_name', c_char * 16),
    ('N_pad2', c_char * 2),
    ('N_count', c_ubyte * 4),
    ('N_structs', c_ubyte * (26 * 4)),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 352
class struct_extr_rec(Structure):
    pass

struct_extr_rec.__slots__ = [
    'ex_id',
    'ex_pad',
    'ex_name',
    'ex_V',
    'ex_h',
    'ex_uvec',
    'ex_vvec',
    'ex_key',
    'ex_count',
]
struct_extr_rec._fields_ = [
    ('ex_id', c_char),
    ('ex_pad', c_char),
    ('ex_name', c_char * 16),
    ('ex_V', c_ubyte * (8 * 3)),
    ('ex_h', c_ubyte * (8 * 3)),
    ('ex_uvec', c_ubyte * (8 * 3)),
    ('ex_vvec', c_ubyte * (8 * 3)),
    ('ex_key', c_ubyte * 4),
    ('ex_count', c_ubyte * 4),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 365
class struct_sketch_rec(Structure):
    pass

struct_sketch_rec.__slots__ = [
    'skt_id',
    'skt_pad',
    'skt_name',
    'skt_V',
    'skt_uvec',
    'skt_vvec',
    'skt_vert_count',
    'skt_seg_count',
    'skt_count',
]
struct_sketch_rec._fields_ = [
    ('skt_id', c_char),
    ('skt_pad', c_char),
    ('skt_name', c_char * 16),
    ('skt_V', c_ubyte * (8 * 3)),
    ('skt_uvec', c_ubyte * (8 * 3)),
    ('skt_vvec', c_ubyte * (8 * 3)),
    ('skt_vert_count', c_ubyte * 4),
    ('skt_seg_count', c_ubyte * 4),
    ('skt_count', c_ubyte * 4),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 377
class struct_annot_rec(Structure):
    pass

struct_annot_rec.__slots__ = [
    'ant_id',
    'ant_pad',
    'ant_name',
    'ant_V',
    'ant_vert_count',
    'ant_seg_count',
    'ant_count',
]
struct_annot_rec._fields_ = [
    ('ant_id', c_char),
    ('ant_pad', c_char),
    ('ant_name', c_char * 16),
    ('ant_V', c_ubyte * (8 * 3)),
    ('ant_vert_count', c_ubyte * 4),
    ('ant_seg_count', c_ubyte * 4),
    ('ant_count', c_ubyte * 4),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 387
class struct_script_rec(Structure):
    pass

struct_script_rec.__slots__ = [
    'script_id',
    'script_pad',
    'script_name',
]
struct_script_rec._fields_ = [
    ('script_id', c_char),
    ('script_pad', c_char),
    ('script_name', c_char * 16),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 393
class struct_cline_rec(Structure):
    pass

struct_cline_rec.__slots__ = [
    'cli_id',
    'cli_pad',
    'cli_name',
    'cli_V',
    'cli_h',
    'cli_radius',
    'cli_thick',
]
struct_cline_rec._fields_ = [
    ('cli_id', c_char),
    ('cli_pad', c_char),
    ('cli_name', c_char * 16),
    ('cli_V', c_ubyte * (8 * 3)),
    ('cli_h', c_ubyte * (8 * 3)),
    ('cli_radius', c_ubyte * 8),
    ('cli_thick', c_ubyte * 8),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 403
class struct_bot_rec(Structure):
    pass

struct_bot_rec.__slots__ = [
    'bot_id',
    'bot_pad',
    'bot_name',
    'bot_nrec',
    'bot_orientation',
    'bot_mode',
    'bot_err_mode',
    'bot_num_verts',
    'bot_num_triangles',
    'bot_data',
]
struct_bot_rec._fields_ = [
    ('bot_id', c_char),
    ('bot_pad', c_char),
    ('bot_name', c_char * 16),
    ('bot_nrec', c_ubyte * 4),
    ('bot_orientation', c_ubyte),
    ('bot_mode', c_ubyte),
    ('bot_err_mode', c_ubyte),
    ('bot_num_verts', c_ubyte * 4),
    ('bot_num_triangles', c_ubyte * 4),
    ('bot_data', c_ubyte * 1),
]

union_record.__slots__ = [
    'u_id',
    'u_size',
    'i',
    's',
    'c',
    'M',
    'md',
    'B',
    'd',
    'p',
    'q',
    'a',
    'b',
    'ss',
    'n',
    'pwr',
    'part',
    'nmg',
    'extr',
    'skt',
    'ant',
    'scr',
    'cli',
    'bot',
]
union_record._fields_ = [
    ('u_id', c_char),
    ('u_size', c_char * 128),
    ('i', struct_ident),
    ('s', struct_solidrec),
    ('c', struct_combination),
    ('M', struct_member),
    ('md', struct_material_rec),
    ('B', struct_B_solid),
    ('d', struct_b_surf),
    ('p', struct_polyhead),
    ('q', struct_polydata),
    ('a', struct_ars_rec),
    ('b', struct_ars_ext),
    ('ss', struct_strsol),
    ('n', struct_arbn_rec),
    ('pwr', struct_pipewire_rec),
    ('part', struct_particle_rec),
    ('nmg', struct_nmg_rec),
    ('extr', struct_extr_rec),
    ('skt', struct_sketch_rec),
    ('ant', struct_annot_rec),
    ('scr', struct_script_rec),
    ('cli', struct_cline_rec),
    ('bot', struct_bot_rec),
]

# /opt/brlcad/include/brlcad/rt/db4.h: 505
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_fastf_float'):
    rt_fastf_float = _libs['/opt/brlcad/lib/librt.dylib'].rt_fastf_float
    rt_fastf_float.argtypes = [POINTER(fastf_t), POINTER(dbfloat_t), c_int, c_int]
    rt_fastf_float.restype = None

# /opt/brlcad/include/brlcad/rt/db4.h: 508
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_mat_dbmat'):
    rt_mat_dbmat = _libs['/opt/brlcad/lib/librt.dylib'].rt_mat_dbmat
    rt_mat_dbmat.argtypes = [POINTER(fastf_t), POINTER(dbfloat_t), c_int]
    rt_mat_dbmat.restype = None

# /opt/brlcad/include/brlcad/rt/db4.h: 511
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'rt_dbmat_mat'):
    rt_dbmat_mat = _libs['/opt/brlcad/lib/librt.dylib'].rt_dbmat_mat
    rt_dbmat_mat.argtypes = [POINTER(dbfloat_t), POINTER(fastf_t)]
    rt_dbmat_mat.restype = None

# /opt/brlcad/include/brlcad/rt/arb_edit.h: 382
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'ext4to6'):
    ext4to6 = _libs['/opt/brlcad/lib/librt.dylib'].ext4to6
    ext4to6.argtypes = [c_int, c_int, c_int, POINTER(struct_rt_arb_internal), (fastf_t * 4) * 7]
    ext4to6.restype = None

# /opt/brlcad/include/brlcad/rt/arb_edit.h: 393
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'mv_edge'):
    mv_edge = _libs['/opt/brlcad/lib/librt.dylib'].mv_edge
    mv_edge.argtypes = [POINTER(struct_rt_arb_internal), vect_t, c_int, c_int, c_int, c_int, vect_t, POINTER(struct_bn_tol), (fastf_t * 4) * 7]
    mv_edge.restype = c_int

# /opt/brlcad/include/brlcad/rt/arb_edit.h: 403
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'arb_extrude'):
    arb_extrude = _libs['/opt/brlcad/lib/librt.dylib'].arb_extrude
    arb_extrude.argtypes = [POINTER(struct_rt_arb_internal), c_int, fastf_t, POINTER(struct_bn_tol), (fastf_t * 4) * 7]
    arb_extrude.restype = c_int

# /opt/brlcad/include/brlcad/rt/arb_edit.h: 424
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'arb_permute'):
    arb_permute = _libs['/opt/brlcad/lib/librt.dylib'].arb_permute
    arb_permute.argtypes = [POINTER(struct_rt_arb_internal), String, POINTER(struct_bn_tol)]
    arb_permute.restype = c_int

# /opt/brlcad/include/brlcad/rt/arb_edit.h: 429
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'arb_mirror_face_axis'):
    arb_mirror_face_axis = _libs['/opt/brlcad/lib/librt.dylib'].arb_mirror_face_axis
    arb_mirror_face_axis.argtypes = [POINTER(struct_rt_arb_internal), (fastf_t * 4) * 7, c_int, String, POINTER(struct_bn_tol)]
    arb_mirror_face_axis.restype = c_int

# /opt/brlcad/include/brlcad/rt/arb_edit.h: 439
if hasattr(_libs['/opt/brlcad/lib/librt.dylib'], 'arb_edit'):
    arb_edit = _libs['/opt/brlcad/lib/librt.dylib'].arb_edit
    arb_edit.argtypes = [POINTER(struct_rt_arb_internal), (fastf_t * 4) * 7, c_int, c_int, vect_t, POINTER(struct_bn_tol)]
    arb_edit.restype = c_int

# /usr/include/sys/syslimits.h: 91
try:
    PATH_MAX = 1024
except:
    pass

# /opt/brlcad/include/brlcad/bu/defines.h: 50
try:
    BRLCAD_OK = 0
except:
    pass

# /opt/brlcad/include/brlcad/bu/defines.h: 51
try:
    BRLCAD_ERROR = 1
except:
    pass

# /opt/brlcad/include/brlcad/bu/defines.h: 66
try:
    BU_DIR_SEPARATOR = '/'
except:
    pass

# /opt/brlcad/include/brlcad/bu/defines.h: 77
try:
    MAXPATHLEN = PATH_MAX
except:
    pass

# /opt/brlcad/include/brlcad/bu/defines.h: 96
try:
    BU_PATH_SEPARATOR = ':'
except:
    pass

# /usr/include/sys/resource.h: 100
try:
    PRIO_PROCESS = 0
except:
    pass

# /usr/include/sys/resource.h: 101
try:
    PRIO_PGRP = 1
except:
    pass

# /usr/include/sys/resource.h: 102
try:
    PRIO_USER = 2
except:
    pass

# /usr/include/sys/resource.h: 105
try:
    PRIO_DARWIN_THREAD = 3
except:
    pass

# /usr/include/sys/resource.h: 106
try:
    PRIO_DARWIN_PROCESS = 4
except:
    pass

# /usr/include/sys/resource.h: 112
try:
    PRIO_MIN = (-20)
except:
    pass

# /usr/include/sys/resource.h: 113
try:
    PRIO_MAX = 20
except:
    pass

# /usr/include/sys/resource.h: 120
try:
    PRIO_DARWIN_BG = 4096
except:
    pass

# /usr/include/sys/resource.h: 126
try:
    PRIO_DARWIN_NONUI = 4097
except:
    pass

# /usr/include/sys/resource.h: 140
try:
    RUSAGE_SELF = 0
except:
    pass

# /usr/include/sys/resource.h: 141
try:
    RUSAGE_CHILDREN = (-1)
except:
    pass

# /usr/include/sys/resource.h: 186
try:
    RUSAGE_INFO_V0 = 0
except:
    pass

# /usr/include/sys/resource.h: 187
try:
    RUSAGE_INFO_V1 = 1
except:
    pass

# /usr/include/sys/resource.h: 188
try:
    RUSAGE_INFO_V2 = 2
except:
    pass

# /usr/include/sys/resource.h: 189
try:
    RUSAGE_INFO_V3 = 3
except:
    pass

# /usr/include/sys/resource.h: 190
try:
    RUSAGE_INFO_CURRENT = RUSAGE_INFO_V3
except:
    pass

# /usr/include/sys/resource.h: 304
try:
    RLIMIT_CPU = 0
except:
    pass

# /usr/include/sys/resource.h: 305
try:
    RLIMIT_FSIZE = 1
except:
    pass

# /usr/include/sys/resource.h: 306
try:
    RLIMIT_DATA = 2
except:
    pass

# /usr/include/sys/resource.h: 307
try:
    RLIMIT_STACK = 3
except:
    pass

# /usr/include/sys/resource.h: 308
try:
    RLIMIT_CORE = 4
except:
    pass

# /usr/include/sys/resource.h: 309
try:
    RLIMIT_AS = 5
except:
    pass

# /usr/include/sys/resource.h: 311
try:
    RLIMIT_RSS = RLIMIT_AS
except:
    pass

# /usr/include/sys/resource.h: 312
try:
    RLIMIT_MEMLOCK = 6
except:
    pass

# /usr/include/sys/resource.h: 313
try:
    RLIMIT_NPROC = 7
except:
    pass

# /usr/include/sys/resource.h: 315
try:
    RLIMIT_NOFILE = 8
except:
    pass

# /usr/include/sys/resource.h: 317
try:
    RLIM_NLIMITS = 9
except:
    pass

# /usr/include/sys/resource.h: 319
try:
    _RLIMIT_POSIX_FLAG = 4096
except:
    pass

# /usr/include/sys/resource.h: 336
try:
    RLIMIT_WAKEUPS_MONITOR = 1
except:
    pass

# /usr/include/sys/resource.h: 337
try:
    RLIMIT_CPU_USAGE_MONITOR = 2
except:
    pass

# /usr/include/sys/resource.h: 338
try:
    RLIMIT_THREAD_CPULIMITS = 3
except:
    pass

# /usr/include/sys/resource.h: 343
try:
    WAKEMON_ENABLE = 1
except:
    pass

# /usr/include/sys/resource.h: 344
try:
    WAKEMON_DISABLE = 2
except:
    pass

# /usr/include/sys/resource.h: 345
try:
    WAKEMON_GET_PARAMS = 4
except:
    pass

# /usr/include/sys/resource.h: 346
try:
    WAKEMON_SET_DEFAULTS = 8
except:
    pass

# /usr/include/sys/resource.h: 347
try:
    WAKEMON_MAKE_FATAL = 16
except:
    pass

# /usr/include/sys/resource.h: 351
try:
    CPUMON_MAKE_FATAL = 4096
except:
    pass

# /usr/include/sys/resource.h: 361
try:
    IOPOL_TYPE_DISK = 0
except:
    pass

# /usr/include/sys/resource.h: 364
try:
    IOPOL_SCOPE_PROCESS = 0
except:
    pass

# /usr/include/sys/resource.h: 365
try:
    IOPOL_SCOPE_THREAD = 1
except:
    pass

# /usr/include/sys/resource.h: 366
try:
    IOPOL_SCOPE_DARWIN_BG = 2
except:
    pass

# /usr/include/sys/resource.h: 369
try:
    IOPOL_DEFAULT = 0
except:
    pass

# /usr/include/sys/resource.h: 370
try:
    IOPOL_IMPORTANT = 1
except:
    pass

# /usr/include/sys/resource.h: 371
try:
    IOPOL_PASSIVE = 2
except:
    pass

# /usr/include/sys/resource.h: 372
try:
    IOPOL_THROTTLE = 3
except:
    pass

# /usr/include/sys/resource.h: 373
try:
    IOPOL_UTILITY = 4
except:
    pass

# /usr/include/sys/resource.h: 374
try:
    IOPOL_STANDARD = 5
except:
    pass

# /usr/include/sys/resource.h: 377
try:
    IOPOL_APPLICATION = IOPOL_STANDARD
except:
    pass

# /usr/include/sys/resource.h: 378
try:
    IOPOL_NORMAL = IOPOL_IMPORTANT
except:
    pass

# /opt/brlcad/include/brlcad/bu/parallel.h: 216
try:
    BU_SEM_DATETIME = 6
except:
    pass

# /opt/brlcad/include/brlcad/bu/parallel.h: 217
try:
    BU_SEM_LAST = (BU_SEM_DATETIME + 1)
except:
    pass

# /opt/brlcad/include/brlcad/bn/defines.h: 45
try:
    BN_AZIMUTH = 0
except:
    pass

# /opt/brlcad/include/brlcad/bn/defines.h: 46
try:
    BN_ELEVATION = 1
except:
    pass

# /opt/brlcad/include/brlcad/bn/defines.h: 47
try:
    BN_TWIST = 2
except:
    pass

# /opt/brlcad/include/brlcad/bn/tol.h: 105
def BN_TOL_IS_INITIALIZED(_p):
    return ((_p != None) and (LIKELY ((((_p.contents.magic).value) == BN_TOL_MAGIC))))

# /opt/brlcad/include/brlcad/bn/tol.h: 110
try:
    BN_TOL_DIST = 0.0005
except:
    pass

# /opt/brlcad/include/brlcad/bn/tol.h: 116
def BN_VECT_ARE_PARALLEL(_dot, _tol):
    return (_dot <= (-SMALL_FASTF)) and (NEAR_EQUAL (_dot, (-1.0), (_tol.contents.perp))) or (NEAR_EQUAL (_dot, 1.0, (_tol.contents.perp)))

# /opt/brlcad/include/brlcad/bn/tol.h: 123
def BN_VECT_ARE_PERP(_dot, _tol):
    return (_dot < 0) and ((-_dot) <= ((_tol.contents.perp).value)) or (_dot <= ((_tol.contents.perp).value))

# /opt/brlcad/include/brlcad/bn/anim.h: 47
try:
    ANIM_STEER_NEW = 0
except:
    pass

# /opt/brlcad/include/brlcad/bn/anim.h: 48
try:
    ANIM_STEER_END = 1
except:
    pass

# /opt/brlcad/include/brlcad/bn/anim.h: 55
def VSCAN(a):
    return (scanf ('%lf %lf %lf', a, (a + 1), (a + 2)))

# /opt/brlcad/include/brlcad/bn/anim.h: 56
def VPRINTS(t, a):
    return (printf ('%s %f %f %f ', t, (a [0]), (a [1]), (a [2])))

# /opt/brlcad/include/brlcad/bn/anim.h: 57
def VPRINTN(t, a):
    return (printf ('%s %f %f %f\n', t, (a [0]), (a [1]), (a [2])))

# /opt/brlcad/include/brlcad/bn/vlist.h: 65
try:
    BN_VLIST_CHUNK = 35
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 73
try:
    BN_VLIST_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 78
try:
    BN_VLIST_LINE_MOVE = 0
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 79
try:
    BN_VLIST_LINE_DRAW = 1
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 80
try:
    BN_VLIST_POLY_START = 2
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 81
try:
    BN_VLIST_POLY_MOVE = 3
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 82
try:
    BN_VLIST_POLY_DRAW = 4
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 83
try:
    BN_VLIST_POLY_END = 5
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 84
try:
    BN_VLIST_POLY_VERTNORM = 6
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 85
try:
    BN_VLIST_TRI_START = 7
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 86
try:
    BN_VLIST_TRI_MOVE = 8
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 87
try:
    BN_VLIST_TRI_DRAW = 9
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 88
try:
    BN_VLIST_TRI_END = 10
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 89
try:
    BN_VLIST_TRI_VERTNORM = 11
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 90
try:
    BN_VLIST_POINT_DRAW = 12
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 91
try:
    BN_VLIST_POINT_SIZE = 13
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 92
try:
    BN_VLIST_LINE_WIDTH = 14
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 93
try:
    BN_VLIST_DISPLAY_MAT = 15
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 94
try:
    BN_VLIST_MODEL_MAT = 16
except:
    pass

# /opt/brlcad/include/brlcad/bn/vlist.h: 95
try:
    BN_VLIST_CMD_MAX = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 73
try:
    ID_NULL = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 74
try:
    ID_TOR = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 75
try:
    ID_TGC = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 76
try:
    ID_ELL = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 77
try:
    ID_ARB8 = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 78
try:
    ID_ARS = 5
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 79
try:
    ID_HALF = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 80
try:
    ID_REC = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 81
try:
    ID_POLY = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 82
try:
    ID_BSPLINE = 9
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 83
try:
    ID_SPH = 10
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 84
try:
    ID_NMG = 11
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 85
try:
    ID_EBM = 12
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 86
try:
    ID_VOL = 13
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 87
try:
    ID_ARBN = 14
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 88
try:
    ID_PIPE = 15
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 89
try:
    ID_PARTICLE = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 90
try:
    ID_RPC = 17
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 91
try:
    ID_RHC = 18
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 92
try:
    ID_EPA = 19
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 93
try:
    ID_EHY = 20
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 94
try:
    ID_ETO = 21
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 95
try:
    ID_GRIP = 22
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 96
try:
    ID_JOINT = 23
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 97
try:
    ID_HF = 24
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 98
try:
    ID_DSP = 25
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 99
try:
    ID_SKETCH = 26
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 100
try:
    ID_EXTRUDE = 27
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 101
try:
    ID_SUBMODEL = 28
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 102
try:
    ID_CLINE = 29
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 103
try:
    ID_BOT = 30
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 109
try:
    ID_MAX_SOLID = 46
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 114
try:
    ID_COMBINATION = 31
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 115
try:
    ID_UNUSED1 = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 116
try:
    ID_BINUNIF = 33
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 117
try:
    ID_UNUSED2 = 34
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 118
try:
    ID_CONSTRAINT = 39
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 122
try:
    ID_SUPERELL = 35
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 123
try:
    ID_METABALL = 36
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 124
try:
    ID_BREP = 37
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 125
try:
    ID_HYP = 38
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 126
try:
    ID_REVOLVE = 40
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 127
try:
    ID_PNTS = 41
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 128
try:
    ID_ANNOT = 42
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 129
try:
    ID_HRT = 43
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 130
try:
    ID_DATUM = 44
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 131
try:
    ID_SCRIPT = 45
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 132
try:
    ID_MAXIMUM = 46
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 144
try:
    RT_DBNHASH = 8192
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 162
def RT_DBHASH(sum):
    return (sum & (RT_DBNHASH - 1))

# /opt/brlcad/include/brlcad/./rt/defines.h: 166
try:
    RT_DEFAULT_MINPIECES = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 167
try:
    RT_DEFAULT_TRIS_PER_PIECE = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 168
try:
    RT_DEFAULT_MINTIE = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 179
try:
    RT_G_DEBUG = (RTG.debug)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 187
try:
    RT_SEM_TREE0 = BU_SEM_LAST
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 188
try:
    RT_SEM_TREE1 = (RT_SEM_TREE0 + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 189
try:
    RT_SEM_TREE2 = (RT_SEM_TREE1 + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 190
try:
    RT_SEM_TREE3 = (RT_SEM_TREE2 + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 191
try:
    RT_SEM_WORKER = (RT_SEM_TREE3 + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 192
try:
    RT_SEM_STATS = (RT_SEM_WORKER + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 193
try:
    RT_SEM_RESULTS = (RT_SEM_STATS + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 194
try:
    RT_SEM_MODEL = (RT_SEM_RESULTS + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 196
try:
    RT_SEM_LAST = (RT_SEM_MODEL + 1)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 199
try:
    BACKING_DIST = (-2.0)
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 200
try:
    OFFSET_DIST = 0.01
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 205
def RT_BADNUM(n):
    return (not ((n >= (-INFINITY)) and (n <= INFINITY)))

# /opt/brlcad/include/brlcad/./rt/defines.h: 206
def RT_BADVEC(v):
    return (((RT_BADNUM ((v [X]))) or (RT_BADNUM ((v [Y])))) or (RT_BADNUM ((v [Z]))))

# /opt/brlcad/include/brlcad/./rt/defines.h: 209
try:
    RT_MAXLINE = 10240
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 211
try:
    RT_PART_NUBSPT = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/defines.h: 220
def VPRINT(a, b):
    return (bu_log ('%s (%g, %g, %g)\n', a, (b [0]), (b [1]), (b [2])))

# /opt/brlcad/include/brlcad/./rt/defines.h: 221
def HPRINT(a, b):
    return (bu_log ('%s (%g, %g, %g, %g)\n', a, (b [0]), (b [1]), (b [2]), (b [3])))

# /opt/brlcad/include/brlcad/./rt/op.h: 36
def MKOP(x):
    return x

# /opt/brlcad/include/brlcad/./rt/op.h: 38
try:
    OP_SOLID = (MKOP (1))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 39
try:
    OP_UNION = (MKOP (2))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 40
try:
    OP_INTERSECT = (MKOP (3))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 41
try:
    OP_SUBTRACT = (MKOP (4))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 42
try:
    OP_XOR = (MKOP (5))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 43
try:
    OP_REGION = (MKOP (6))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 44
try:
    OP_NOP = (MKOP (7))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 46
try:
    OP_NOT = (MKOP (8))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 47
try:
    OP_GUARD = (MKOP (9))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 48
try:
    OP_XNOP = (MKOP (10))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 49
try:
    OP_NMG_TESS = (MKOP (11))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 51
try:
    OP_DB_LEAF = (MKOP (12))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/op.h: 52
try:
    OP_FREE = (MKOP (13))
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 67
try:
    DB5HDR_MAGIC1 = 118
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 68
try:
    DB5HDR_MAGIC2 = 53
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 71
try:
    DB5HDR_HFLAGS_DLI_MASK = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 72
try:
    DB5HDR_HFLAGS_DLI_APPLICATION_DATA_OBJECT = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 73
try:
    DB5HDR_HFLAGS_DLI_HEADER_OBJECT = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 74
try:
    DB5HDR_HFLAGS_DLI_FREE_STORAGE = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 75
try:
    DB5HDR_HFLAGS_HIDDEN_OBJECT = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 76
try:
    DB5HDR_HFLAGS_NAME_PRESENT = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 77
try:
    DB5HDR_HFLAGS_OBJECT_WIDTH_MASK = 192
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 78
try:
    DB5HDR_HFLAGS_OBJECT_WIDTH_SHIFT = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 79
try:
    DB5HDR_HFLAGS_NAME_WIDTH_MASK = 24
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 80
try:
    DB5HDR_HFLAGS_NAME_WIDTH_SHIFT = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 82
try:
    DB5HDR_WIDTHCODE_8BIT = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 83
try:
    DB5HDR_WIDTHCODE_16BIT = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 84
try:
    DB5HDR_WIDTHCODE_32BIT = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 85
try:
    DB5HDR_WIDTHCODE_64BIT = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 88
try:
    DB5HDR_AFLAGS_ZZZ_MASK = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 89
try:
    DB5HDR_AFLAGS_PRESENT = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 90
try:
    DB5HDR_AFLAGS_WIDTH_MASK = 192
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 91
try:
    DB5HDR_AFLAGS_WIDTH_SHIFT = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 94
try:
    DB5HDR_BFLAGS_ZZZ_MASK = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 95
try:
    DB5HDR_BFLAGS_PRESENT = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 96
try:
    DB5HDR_BFLAGS_WIDTH_MASK = 192
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 97
try:
    DB5HDR_BFLAGS_WIDTH_SHIFT = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 108
try:
    DB5_GLOBAL_OBJECT_NAME = '_GLOBAL'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 111
try:
    DB5_ZZZ_UNCOMPRESSED = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 112
try:
    DB5_ZZZ_GNU_GZIP = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 113
try:
    DB5_ZZZ_BURROUGHS_WHEELER = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 117
try:
    DB5_MAJORTYPE_RESERVED = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 118
try:
    DB5_MAJORTYPE_BRLCAD = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 119
try:
    DB5_MAJORTYPE_ATTRIBUTE_ONLY = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 120
try:
    DB5_MAJORTYPE_BINARY_MASK = 24
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 121
try:
    DB5_MAJORTYPE_BINARY_UNIF = 9
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 122
try:
    DB5_MAJORTYPE_BINARY_MIME = 10
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 128
try:
    DB5_MINORTYPE_RESERVED = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 129
try:
    DB5_MINORTYPE_BRLCAD_TOR = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 130
try:
    DB5_MINORTYPE_BRLCAD_TGC = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 131
try:
    DB5_MINORTYPE_BRLCAD_ELL = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 132
try:
    DB5_MINORTYPE_BRLCAD_ARB8 = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 133
try:
    DB5_MINORTYPE_BRLCAD_ARS = 5
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 134
try:
    DB5_MINORTYPE_BRLCAD_HALF = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 135
try:
    DB5_MINORTYPE_BRLCAD_REC = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 136
try:
    DB5_MINORTYPE_BRLCAD_POLY = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 137
try:
    DB5_MINORTYPE_BRLCAD_BSPLINE = 9
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 138
try:
    DB5_MINORTYPE_BRLCAD_SPH = 10
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 139
try:
    DB5_MINORTYPE_BRLCAD_NMG = 11
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 140
try:
    DB5_MINORTYPE_BRLCAD_EBM = 12
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 141
try:
    DB5_MINORTYPE_BRLCAD_VOL = 13
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 142
try:
    DB5_MINORTYPE_BRLCAD_ARBN = 14
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 143
try:
    DB5_MINORTYPE_BRLCAD_PIPE = 15
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 144
try:
    DB5_MINORTYPE_BRLCAD_PARTICLE = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 145
try:
    DB5_MINORTYPE_BRLCAD_RPC = 17
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 146
try:
    DB5_MINORTYPE_BRLCAD_RHC = 18
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 147
try:
    DB5_MINORTYPE_BRLCAD_EPA = 19
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 148
try:
    DB5_MINORTYPE_BRLCAD_EHY = 20
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 149
try:
    DB5_MINORTYPE_BRLCAD_ETO = 21
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 150
try:
    DB5_MINORTYPE_BRLCAD_GRIP = 22
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 151
try:
    DB5_MINORTYPE_BRLCAD_JOINT = 23
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 152
try:
    DB5_MINORTYPE_BRLCAD_HF = 24
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 153
try:
    DB5_MINORTYPE_BRLCAD_DSP = 25
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 154
try:
    DB5_MINORTYPE_BRLCAD_SKETCH = 26
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 155
try:
    DB5_MINORTYPE_BRLCAD_EXTRUDE = 27
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 156
try:
    DB5_MINORTYPE_BRLCAD_SUBMODEL = 28
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 157
try:
    DB5_MINORTYPE_BRLCAD_CLINE = 29
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 158
try:
    DB5_MINORTYPE_BRLCAD_BOT = 30
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 159
try:
    DB5_MINORTYPE_BRLCAD_COMBINATION = 31
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 163
try:
    DB5_MINORTYPE_BRLCAD_SUPERELL = 35
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 164
try:
    DB5_MINORTYPE_BRLCAD_METABALL = 36
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 165
try:
    DB5_MINORTYPE_BRLCAD_BREP = 37
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 166
try:
    DB5_MINORTYPE_BRLCAD_HYP = 38
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 168
try:
    DB5_MINORTYPE_BRLCAD_CONSTRAINT = 39
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 170
try:
    DB5_MINORTYPE_BRLCAD_REVOLVE = 40
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 171
try:
    DB5_MINORTYPE_BRLCAD_PNTS = 41
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 172
try:
    DB5_MINORTYPE_BRLCAD_ANNOT = 42
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 173
try:
    DB5_MINORTYPE_BRLCAD_HRT = 43
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 174
try:
    DB5_MINORTYPE_BRLCAD_DATUM = 44
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 175
try:
    DB5_MINORTYPE_BRLCAD_SCRIPT = 45
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 178
try:
    DB5_MINORTYPE_BINU_WID_MASK = 48
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 179
try:
    DB5_MINORTYPE_BINU_SGN_MASK = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 180
try:
    DB5_MINORTYPE_BINU_ATM_MASK = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 181
try:
    DB5_MINORTYPE_BINU_FLOAT = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 182
try:
    DB5_MINORTYPE_BINU_DOUBLE = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 183
try:
    DB5_MINORTYPE_BINU_8BITINT_U = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 184
try:
    DB5_MINORTYPE_BINU_16BITINT_U = 5
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 185
try:
    DB5_MINORTYPE_BINU_32BITINT_U = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 186
try:
    DB5_MINORTYPE_BINU_64BITINT_U = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 187
try:
    DB5_MINORTYPE_BINU_8BITINT = 12
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 188
try:
    DB5_MINORTYPE_BINU_16BITINT = 13
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 189
try:
    DB5_MINORTYPE_BINU_32BITINT = 14
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 190
try:
    DB5_MINORTYPE_BINU_64BITINT = 15
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db5.h: 227
def DB5_ENC_LEN(len):
    return (1 << len)

# /opt/brlcad/include/brlcad/nmg.h: 100
try:
    DEBUG_PL_ANIM = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 101
try:
    DEBUG_PL_SLOW = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 102
try:
    DEBUG_GRAPHCL = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 103
try:
    DEBUG_PL_LOOP = 8
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 104
try:
    DEBUG_PLOTEM = 16
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 105
try:
    DEBUG_POLYSECT = 32
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 106
try:
    DEBUG_VERIFY = 64
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 107
try:
    DEBUG_BOOL = 128
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 108
try:
    DEBUG_CLASSIFY = 256
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 109
try:
    DEBUG_BOOLEVAL = 512
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 110
try:
    DEBUG_BASIC = 1024
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 111
try:
    DEBUG_MESH = 2048
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 112
try:
    DEBUG_MESH_EU = 4096
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 113
try:
    DEBUG_POLYTO = 8192
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 114
try:
    DEBUG_LABEL_PTS = 16384
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 115
try:
    NMG_DEBUG_UNUSED1 = 32768
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 116
try:
    DEBUG_NMGRT = 65536
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 117
try:
    DEBUG_FINDEU = 131072
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 118
try:
    DEBUG_CMFACE = 262144
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 119
try:
    DEBUG_CUTLOOP = 524288
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 120
try:
    DEBUG_VU_SORT = 1048576
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 121
try:
    DEBUG_FCUT = 2097152
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 122
try:
    DEBUG_RT_SEGS = 4194304
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 123
try:
    DEBUG_RT_ISECT = 8388608
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 124
try:
    DEBUG_TRI = 16777216
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 125
try:
    DEBUG_PT_FU = 33554432
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 126
try:
    DEBUG_MANIF = 67108864
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 127
try:
    NMG_DEBUG_UNUSED2 = 134217728
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 128
try:
    NMG_DEBUG_UNUSED3 = 268435456
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 129
try:
    NMG_DEBUG_UNUSED4 = 536870912
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 130
try:
    NMG_DEBUG_UNUSED5 = 1073741824
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 131
try:
    NMG_DEBUG_UNUSED6 = 2147483648
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 132
try:
    NMG_DEBUG_FORMAT = '\x10\x1bMANIF\x1aPTFU\x19TRIANG\x18RT_ISECT\x17RT_SEGS\x16FCUT\x15VU_SORT\x14CUTLOOP\x13CMFACE\x12FINDEU\x11RT_ISECT\x10(FREE)\x0fLABEL_PTS\x0ePOLYTO\rMESH_EU\x0cMESH\x0bBASIC\nBOOLEVAL\tCLASSIFY\x08BOOL\x07VERIFY\x06POLYSECT\x05PLOTEM\x04PL_LOOP\x03GRAPHCL\x02PL_SLOW\x01PL_ANIM'
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 139
try:
    NMG_BOOL_SUB = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 140
try:
    NMG_BOOL_ADD = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 141
try:
    NMG_BOOL_ISECT = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 144
try:
    NMG_CLASS_Unknown = (-1)
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 145
try:
    NMG_CLASS_AinB = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 146
try:
    NMG_CLASS_AonBshared = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 147
try:
    NMG_CLASS_AonBanti = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 148
try:
    NMG_CLASS_AoutB = 3
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 149
try:
    NMG_CLASS_BinA = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 150
try:
    NMG_CLASS_BonAshared = 5
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 151
try:
    NMG_CLASS_BonAanti = 6
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 152
try:
    NMG_CLASS_BoutA = 7
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 155
try:
    OT_NONE = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 156
try:
    OT_SAME = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 157
try:
    OT_OPPOSITE = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 158
try:
    OT_UNSPEC = 3
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 159
try:
    OT_BOOLPLACE = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 650
def NMG_ARE_EUS_ADJACENT(_eu1, _eu2):
    return (((((((_eu1.contents.vu_p).value).contents.v_p).value) == ((((_eu2.contents.vu_p).value).contents.v_p).value)) and (((((((_eu1.contents.eumate_p).value).contents.vu_p).value).contents.v_p).value) == ((((((_eu2.contents.eumate_p).value).contents.vu_p).value).contents.v_p).value))) or ((((((_eu1.contents.vu_p).value).contents.v_p).value) == ((((((_eu2.contents.eumate_p).value).contents.vu_p).value).contents.v_p).value)) and (((((((_eu1.contents.eumate_p).value).contents.vu_p).value).contents.v_p).value) == ((((_eu2.contents.vu_p).value).contents.v_p).value))))

# /opt/brlcad/include/brlcad/nmg.h: 657
def EDGESADJ(_e1, _e2):
    return (NMG_ARE_EUS_ADJACENT (_e1, _e2))

# /opt/brlcad/include/brlcad/nmg.h: 660
def PLPRINT(_s, _pl):
    return (bu_log ('%s %gx + %gy + %gz = %g\n', _s, (_pl [0]), (_pl [1]), (_pl [2]), (_pl [3])))

# /opt/brlcad/include/brlcad/nmg.h: 665
try:
    NMG_FPI_FIRST = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 668
try:
    NMG_FPI_PERGEOM = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 672
try:
    NMG_FPI_PERUSE = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 689
try:
    PREEXIST = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 690
try:
    NEWEXIST = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 749
def NMG_INDEX_VALUE(_tab, _index):
    return (_tab [_index])

# /opt/brlcad/include/brlcad/nmg.h: 750
def NMG_INDEX_TEST(_tab, _p):
    return (_tab [(_p.contents.index)])

# /opt/brlcad/include/brlcad/nmg.h: 753
def NMG_INDEX_TEST_AND_SET(_tab, _p):
    return ((_tab [((_p.contents.index).value)]) == 0) and 1 or 0

# /opt/brlcad/include/brlcad/nmg.h: 754
def NMG_INDEX_IS_SET(_tab, _p):
    return (NMG_INDEX_TEST (_tab, _p))

# /opt/brlcad/include/brlcad/nmg.h: 755
def NMG_INDEX_FIRST_TIME(_tab, _p):
    return (NMG_INDEX_TEST_AND_SET (_tab, _p))

# /opt/brlcad/include/brlcad/nmg.h: 757
def NMG_INDEX_GET(_tab, _p):
    return (_tab [(_p.contents.index)])

# /opt/brlcad/include/brlcad/nmg.h: 767
try:
    NMG_0MANIFOLD = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 768
try:
    NMG_1MANIFOLD = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 769
try:
    NMG_2MANIFOLD = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 770
try:
    NMG_DANGLING = 8
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 771
try:
    NMG_3MANIFOLD = 16
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 774
def NMG_MANIFOLDS(_t, _p):
    return (NMG_INDEX_VALUE (_t, (_p.contents.index)))

# /opt/brlcad/include/brlcad/nmg.h: 780
try:
    NMG_VLIST_STYLE_VECTOR = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 781
try:
    NMG_VLIST_STYLE_POLYGON = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 782
try:
    NMG_VLIST_STYLE_VISUALIZE_NORMALS = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 783
try:
    NMG_VLIST_STYLE_USE_VU_NORMALS = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 784
try:
    NMG_VLIST_STYLE_NO_SURFACES = 8
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 882
try:
    RT_NURB_SPLIT_ROW = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 883
try:
    RT_NURB_SPLIT_COL = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 884
try:
    RT_NURB_SPLIT_FLAT = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 901
try:
    RT_NURB_PT_XY = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 902
try:
    RT_NURB_PT_XYZ = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 903
try:
    RT_NURB_PT_UV = 3
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 904
try:
    RT_NURB_PT_DATA = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 905
try:
    RT_NURB_PT_PROJ = 5
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 907
try:
    RT_NURB_PT_RATIONAL = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 908
try:
    RT_NURB_PT_NONRAT = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 910
def RT_NURB_MAKE_PT_TYPE(n, t, h):
    return (((n << 5) | (t << 1)) | h)

# /opt/brlcad/include/brlcad/nmg.h: 911
def RT_NURB_EXTRACT_COORDS(pt):
    return (pt >> 5)

# /opt/brlcad/include/brlcad/nmg.h: 912
def RT_NURB_EXTRACT_PT_TYPE(pt):
    return ((pt >> 1) & 15)

# /opt/brlcad/include/brlcad/nmg.h: 913
def RT_NURB_IS_PT_RATIONAL(pt):
    return (pt & 1)

# /opt/brlcad/include/brlcad/nmg.h: 914
def RT_NURB_STRIDE(pt):
    return (((RT_NURB_EXTRACT_COORDS (pt)).value) * sizeof(fastf_t))

# /opt/brlcad/include/brlcad/nmg.h: 916
try:
    DEBUG_NMG_SPLINE = 256
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 995
try:
    NMG_HIT_LIST = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 996
try:
    NMG_MISS_LIST = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1001
def HMG_INBOUND_STATE(_hm):
    return ((((_hm.contents.in_out).value) & 240) >> 4)

# /opt/brlcad/include/brlcad/nmg.h: 1002
def HMG_OUTBOUND_STATE(_hm):
    return (((_hm.contents.in_out).value) & 15)

# /opt/brlcad/include/brlcad/nmg.h: 1005
try:
    NMG_RAY_STATE_INSIDE = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1006
try:
    NMG_RAY_STATE_ON = 2
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1007
try:
    NMG_RAY_STATE_OUTSIDE = 4
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1008
try:
    NMG_RAY_STATE_ANY = 8
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1010
try:
    HMG_HIT_IN_IN = 17
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1011
try:
    HMG_HIT_IN_OUT = 20
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1012
try:
    HMG_HIT_OUT_IN = 65
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1013
try:
    HMG_HIT_OUT_OUT = 68
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1014
try:
    HMG_HIT_IN_ON = 18
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1015
try:
    HMG_HIT_ON_IN = 33
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1016
try:
    HMG_HIT_ON_ON = 34
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1017
try:
    HMG_HIT_OUT_ON = 66
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1018
try:
    HMG_HIT_ON_OUT = 36
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1019
try:
    HMG_HIT_ANY_ANY = 136
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1021
try:
    NMG_VERT_ENTER = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1022
try:
    NMG_VERT_ENTER_LEAVE = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1023
try:
    NMG_VERT_LEAVE = (-1)
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1024
try:
    NMG_VERT_UNKNOWN = (-2)
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1026
try:
    NMG_HITMISS_SEG_IN = 6909440
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1027
try:
    NMG_HITMISS_SEG_OUT = 1869968384
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1102
try:
    HIT = 1
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 1103
try:
    MISS = 0
except:
    pass

# /opt/brlcad/include/brlcad/nmg.h: 2402
def nmg_mev(_v, _u):
    return (nmg_me (_v, NULL, _u))

# /opt/brlcad/include/brlcad/brep/defines.h: 58
try:
    BREP_MAX_ITERATIONS = 100
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 61
try:
    BREP_INTERSECTION_ROOT_EPSILON = 1e-06
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 64
try:
    BREP_INTERSECTION_ROOT_SETTLE = 0.01
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 69
try:
    BREP_GRAZING_DOT_TOL = 1.7453e-05
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 72
try:
    DO_VECTOR = 1
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 75
try:
    BREP_MAX_FT_DEPTH = 8
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 76
try:
    BREP_MAX_LN_DEPTH = 20
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 78
def SIGN(x):
    return (x >= 0) and 1 or (-1)

# /opt/brlcad/include/brlcad/brep/defines.h: 81
try:
    BREP_SURFACE_FLATNESS = 0.85
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 82
try:
    BREP_SURFACE_STRAIGHTNESS = 0.75
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 85
try:
    BREP_MAX_FCP_ITERATIONS = 50
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 88
try:
    BREP_FCP_ROOT_EPSILON = 1e-05
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 93
try:
    BREP_BB_CRV_PNT_CNT = 10
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 95
try:
    BREP_CURVE_FLATNESS = 0.95
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 98
try:
    BREP_SURF_SUB_FACTOR = 1
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 99
try:
    BREP_TRIM_SUB_FACTOR = 1
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 110
try:
    BREP_EDGE_MISS_TOLERANCE = 0.005
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 112
try:
    BREP_SAME_POINT_TOLERANCE = 1e-06
except:
    pass

# /opt/brlcad/include/brlcad/brep/defines.h: 115
def ON_PRINT4(p):
    return (((((((('[' << (p [0])) << ', ') << (p [1])) << ', ') << (p [2])) << ', ') << (p [3])) << ']')

# /opt/brlcad/include/brlcad/brep/defines.h: 116
def ON_PRINT3(p):
    return (((((('(' << (p [0])) << ', ') << (p [1])) << ', ') << (p [2])) << ')')

# /opt/brlcad/include/brlcad/brep/defines.h: 117
def ON_PRINT2(p):
    return (((('(' << (p [0])) << ', ') << (p [1])) << ')')

# /opt/brlcad/include/brlcad/brep/defines.h: 118
def PT(p):
    return (ON_PRINT3 (p))

# /opt/brlcad/include/brlcad/brep/defines.h: 119
def PT2(p):
    return (ON_PRINT2 (p))

# /opt/brlcad/include/brlcad/brep/defines.h: 120
def IVAL(_ival):
    return (((('[' << (((_ival.m_t).value) [0])) << ', ') << (((_ival.m_t).value) [1])) << ']')

# /opt/brlcad/include/brlcad/./rt/geom.h: 52
try:
    NAMELEN = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 158
try:
    METABALL_METABALL = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 159
try:
    METABALL_ISOPOTENTIAL = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 160
try:
    METABALL_BLOB = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 176
try:
    WDB_METABALLPT_TYPE_POINT = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 177
try:
    WDB_METABALLPT_TYPE_LINE = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 178
try:
    WDB_METABALLPT_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 289
def RT_NURB_GET_CONTROL_POINT(_s, _u, _v):
    return ((_s.contents.ctl_points) [(((_v * (((_s.contents.s_size).value) [0])) + _u) * ((RT_NURB_EXTRACT_COORDS (((_s.contents.pt_type).value))).value))])

# /opt/brlcad/include/brlcad/./rt/geom.h: 304
def RT_BREP_TEST_MAGIC(_p):
    return (_p and ((_p[0]) == RT_BREP_INTERNAL_MAGIC))

# /opt/brlcad/include/brlcad/./rt/geom.h: 321
try:
    RT_EBM_NAME_LEN = 256
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 343
try:
    RT_VOL_NAME_LEN = 128
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 444
try:
    RT_PARTICLE_TYPE_SPHERE = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 445
try:
    RT_PARTICLE_TYPE_CYLINDER = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 446
try:
    RT_PARTICLE_TYPE_CONE = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 550
try:
    DSP_NAME_LEN = 128
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 562
try:
    DSP_CUT_DIR_ADAPT = 'a'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 563
try:
    DSP_CUT_DIR_llUR = 'l'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 564
try:
    DSP_CUT_DIR_ULlr = 'L'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 574
try:
    RT_DSP_SRC_V4_FILE = '4'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 575
try:
    RT_DSP_SRC_FILE = 'f'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 576
try:
    RT_DSP_SRC_OBJ = 'o'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 645
try:
    SKETCH_NAME_LEN = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 808
try:
    RT_BOT_UNORIENTED = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 809
try:
    RT_BOT_CCW = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 810
try:
    RT_BOT_CW = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 813
try:
    RT_BOT_SURFACE = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 814
try:
    RT_BOT_SOLID = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 821
try:
    RT_BOT_PLATE = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 827
try:
    RT_BOT_PLATE_NOCOS = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 830
try:
    RT_BOT_HAS_SURFACE_NORMALS = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 831
try:
    RT_BOT_USE_NORMALS = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 832
try:
    RT_BOT_USE_FLOATS = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 966
try:
    RT_ANNOT_POS_BL = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 967
try:
    RT_ANNOT_POS_BC = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 968
try:
    RT_ANNOT_POS_BR = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 969
try:
    RT_ANNOT_POS_ML = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 970
try:
    RT_ANNOT_POS_MC = 5
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 971
try:
    RT_ANNOT_POS_MR = 6
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 972
try:
    RT_ANNOT_POS_TL = 7
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 973
try:
    RT_ANNOT_POS_TC = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/geom.h: 974
try:
    RT_ANNOT_POS_TR = 9
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 58
def DB_FULL_PATH_POP(_pp):
    return (((_pp.contents.fp_len).value) > 0) and (((_pp.contents.fp_len).value) - 1) or (_pp.contents.fp_len)

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 60
def DB_FULL_PATH_CUR_DIR(_pp):
    return ((_pp.contents.fp_names) [(((_pp.contents.fp_len).value) - 1)])

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 61
def DB_FULL_PATH_CUR_BOOL(_pp):
    return ((_pp.contents.fp_bool) [(((_pp.contents.fp_len).value) - 1)])

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 62
def DB_FULL_PATH_SET_CUR_BOOL(_pp, _i):
    return _i

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 63
def DB_FULL_PATH_ROOT_DIR(_pp):
    return ((_pp.contents.fp_names) [0])

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 64
def DB_FULL_PATH_GET(_pp, _i):
    return ((_pp.contents.fp_names) [_i])

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 65
def DB_FULL_PATH_GET_BOOL(_pp, _i):
    return ((_pp.contents.fp_bool) [_i])

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 66
def DB_FULL_PATH_SET_BOOL(_pp, _i, _j):
    return _j

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 116
try:
    DB_FP_PRINT_BOOL = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 117
try:
    DB_FP_PRINT_TYPE = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 118
try:
    DB_FP_PRINT_MATRIX = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 42
try:
    DEBUG_OFF = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 47
try:
    DEBUG_ALLRAYS = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 48
try:
    DEBUG_ALLHITS = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 49
try:
    DEBUG_SHOOT = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 50
try:
    DEBUG_INSTANCE = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 53
try:
    DEBUG_DB = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 54
try:
    DEBUG_SOLIDS = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 55
try:
    DEBUG_REGIONS = 64
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 56
try:
    DEBUG_ARB8 = 128
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 58
try:
    DEBUG_SPLINE = 256
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 59
try:
    DEBUG_ANIM = 512
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 60
try:
    DEBUG_ANIM_FULL = 1024
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 61
try:
    DEBUG_VOL = 2048
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 64
try:
    DEBUG_ROOTS = 4096
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 65
try:
    DEBUG_PARTITION = 8192
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 66
try:
    DEBUG_CUT = 16384
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 67
try:
    DEBUG_BOXING = 32768
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 69
try:
    DEBUG_MEM = 65536
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 70
try:
    DEBUG_UNUSED_0 = 131072
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 71
try:
    DEBUG_FDIFF = 262144
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 72
try:
    DEBUG_PARALLEL = 524288
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 74
try:
    DEBUG_CUTDETAIL = 1048576
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 75
try:
    DEBUG_TREEWALK = 2097152
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 76
try:
    DEBUG_TESTING = 4194304
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 77
try:
    DEBUG_ADVANCE = 8388608
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 79
try:
    DEBUG_MATH = 16777216
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 82
try:
    DEBUG_EBM = 33554432
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 83
try:
    DEBUG_HF = 67108864
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 85
try:
    DEBUG_UNUSED_1 = 134217728
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 86
try:
    DEBUG_UNUSED_2 = 268435456
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 87
try:
    DEBUG_UNUSED_3 = 536870912
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 90
try:
    DEBUG_PL_SOLIDS = 1073741824
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 91
try:
    DEBUG_PL_BOX = 2147483648
except:
    pass

# /opt/brlcad/include/brlcad/./rt/debug.h: 94
try:
    DEBUG_FORMAT = '\x10 PLOTBOX\x1fPLOTSOLIDS\x1bHF\x1aEBM\x19MATH\x18ADVANCE\x17TESTING\x16TREEWALK\x15CUTDETAIL\x14PARALLEL\x13FDIFF\x11MEM\x10BOXING\x0fCUTTING\x0ePARTITION\rROOTS\x0cVOL\x0bANIM_FULL\nANIM\tSPLINE\x08ARB8\x07REGIONS\x06SOLIDS\x05DB\x04INSTANCE\x03SHOOT\x02ALLHITS\x01ALLRAYS'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/tol.h: 77
try:
    RT_LEN_TOL = 1e-08
except:
    pass

# /opt/brlcad/include/brlcad/./rt/tol.h: 78
try:
    RT_DOT_TOL = 0.001
except:
    pass

# /opt/brlcad/include/brlcad/./rt/tol.h: 79
try:
    RT_PCOEF_TOL = 1e-10
except:
    pass

# /opt/brlcad/include/brlcad/./rt/tol.h: 80
try:
    RT_ROOT_TOL = 1e-05
except:
    pass

# /opt/brlcad/include/brlcad/rt/mem.h: 42
try:
    MAP_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/mater.h: 59
try:
    MATER_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/mater.h: 60
try:
    MATER_NO_ADDR = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 56
try:
    ANM_RSTACK = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 57
try:
    ANM_RARC = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 58
try:
    ANM_LMUL = 3
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 59
try:
    ANM_RMUL = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 60
try:
    ANM_RBOTH = 5
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 67
try:
    RT_ANP_REPLACE = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 68
try:
    RT_ANP_APPEND = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 88
try:
    RT_AN_MATRIX = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 89
try:
    RT_AN_MATERIAL = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 90
try:
    RT_AN_COLOR = 3
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 91
try:
    RT_AN_SOLID = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 92
try:
    RT_AN_TEMPERATURE = 5
except:
    pass

# /opt/brlcad/include/brlcad/rt/anim.h: 94
try:
    ANIM_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 78
try:
    RT_DIR_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 82
try:
    RT_DIR_PHONY_ADDR = (-1)
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 85
try:
    RT_DIR_SOLID = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 86
try:
    RT_DIR_COMB = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 87
try:
    RT_DIR_REGION = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 88
try:
    RT_DIR_HIDDEN = 8
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 89
try:
    RT_DIR_NON_GEOM = 16
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 90
try:
    RT_DIR_USED = 128
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 91
try:
    RT_DIR_INMEM = 256
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 94
try:
    LOOKUP_NOISY = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/directory.h: 95
try:
    LOOKUP_QUIET = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/db_instance.h: 90
try:
    DBI_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/region.h: 60
try:
    REGION_NON_FASTGEN = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/region.h: 61
try:
    REGION_FASTGEN_PLATE = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/region.h: 62
try:
    REGION_FASTGEN_VOLUME = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/region.h: 65
try:
    REGION_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/soltab.h: 80
try:
    RT_SOLTAB_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/soltab.h: 81
try:
    SOLTAB_NULL = RT_SOLTAB_NULL
except:
    pass

# /opt/brlcad/include/brlcad/rt/xray.h: 34
try:
    CORNER_PTS = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/xray.h: 49
try:
    RAY_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/hit.h: 71
try:
    HIT_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/hit.h: 123
try:
    CURVE_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/seg.h: 65
try:
    RT_SEG_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/ray_partition.h: 68
try:
    PT_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/ray_partition.h: 78
def RT_PT_MIDDLE_LEN(p):
    return (pointer(((p.contents.RT_PT_MIDDLE_END).value)) - pointer(((p.contents.RT_PT_MIDDLE_START).value)))

# /opt/brlcad/include/brlcad/rt/application.h: 190
try:
    RT_APPLICATION_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/application.h: 191
try:
    RT_AFN_NULL = NULL
except:
    pass

# /opt/brlcad/include/brlcad/./rt/nmg.h: 127
try:
    NMG_PCA_EDGE = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/nmg.h: 128
try:
    NMG_PCA_EDGE_VERTEX = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/nmg.h: 129
try:
    NMG_PCA_VERTEX = 3
except:
    pass

# /opt/brlcad/include/brlcad/rt/tree.h: 98
try:
    TS_SOFAR_MINUS = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/tree.h: 99
try:
    TS_SOFAR_INTER = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/tree.h: 100
try:
    TS_SOFAR_REGION = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/tree.h: 186
try:
    TREE_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/tree.h: 233
try:
    TREE_LIST_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/resource.h: 110
try:
    RESOURCE_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 67
try:
    CUT_CUTNODE = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 68
try:
    CUT_BOXNODE = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 69
try:
    CUT_MAXIMUM = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/space_partition.h: 78
try:
    CUTTER_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 79
try:
    RT_WDB_NULL = NULL
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 80
try:
    RT_WDB_TYPE_DB_DISK = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 81
try:
    RT_WDB_TYPE_DB_DISK_APPEND_ONLY = 3
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 82
try:
    RT_WDB_TYPE_DB_INMEM = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/wdb.h: 83
try:
    RT_WDB_TYPE_DB_INMEM_APPEND_ONLY = 5
except:
    pass

# /opt/brlcad/include/brlcad/./rt/rt_instance.h: 132
try:
    RTI_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/./rt/view.h: 36
try:
    RT_MINVIEWSIZE = 0.0001
except:
    pass

# /opt/brlcad/include/brlcad/./rt/view.h: 37
try:
    RT_MINVIEWSCALE = 5e-05
except:
    pass

# /opt/brlcad/include/brlcad/./rt/view.h: 121
try:
    RT_SORT_UNSORTED = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/view.h: 122
try:
    RT_SORT_CLOSEST_TO_START = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/view.h: 145
try:
    RT_SELECTION_NOP = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/view.h: 146
try:
    RT_SELECTION_TRANSLATION = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/functab.h: 79
def RTFUNCTAB_FUNC_PREP_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 85
def RTFUNCTAB_FUNC_SHOT_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 88
def RTFUNCTAB_FUNC_PRINT_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 93
def RTFUNCTAB_FUNC_NORM_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 101
def RTFUNCTAB_FUNC_PIECE_SHOT_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 106
def RTFUNCTAB_FUNC_PIECE_HITSEGS_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 112
def RTFUNCTAB_FUNC_UV_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 117
def RTFUNCTAB_FUNC_CURVE_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 120
def RTFUNCTAB_FUNC_CLASS_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 123
def RTFUNCTAB_FUNC_FREE_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 130
def RTFUNCTAB_FUNC_PLOT_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 134
def RTFUNCTAB_FUNC_ADAPTIVE_PLOT_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 141
def RTFUNCTAB_FUNC_VSHOT_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 148
def RTFUNCTAB_FUNC_TESS_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 153
def RTFUNCTAB_FUNC_TNURB_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 158
def RTFUNCTAB_FUNC_BREP_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 165
def RTFUNCTAB_FUNC_IMPORT5_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 172
def RTFUNCTAB_FUNC_EXPORT5_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 179
def RTFUNCTAB_FUNC_IMPORT4_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 186
def RTFUNCTAB_FUNC_EXPORT4_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 189
def RTFUNCTAB_FUNC_IFREE_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 195
def RTFUNCTAB_FUNC_DESCRIBE_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 200
def RTFUNCTAB_FUNC_XFORM_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 207
def RTFUNCTAB_FUNC_GET_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 210
def RTFUNCTAB_FUNC_ADJUST_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 213
def RTFUNCTAB_FUNC_FORM_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 216
def RTFUNCTAB_FUNC_MAKE_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 219
def RTFUNCTAB_FUNC_PARAMS_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 226
def RTFUNCTAB_FUNC_BBOX_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 229
def RTFUNCTAB_FUNC_VOLUME_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 232
def RTFUNCTAB_FUNC_SURF_AREA_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 235
def RTFUNCTAB_FUNC_CENTROID_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 240
def RTFUNCTAB_FUNC_ORIENTED_BBOX_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 245
def RTFUNCTAB_FUNC_FIND_SELECTIONS_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 255
def RTFUNCTAB_FUNC_EVALUATE_SELECTION_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 262
def RTFUNCTAB_FUNC_PROCESS_SELECTION_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/rt/functab.h: 266
def RTFUNCTAB_FUNC_PREP_SERIALIZE_CAST(_func):
    return _func

# /opt/brlcad/include/brlcad/./rt/search.h: 111
try:
    DB_SEARCH_TREE = 0
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 112
try:
    DB_SEARCH_FLAT = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 113
try:
    DB_SEARCH_HIDDEN = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 114
try:
    DB_SEARCH_RETURN_UNIQ_DP = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 115
try:
    DB_SEARCH_QUIET = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 146
try:
    DB_LS_PRIM = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 147
try:
    DB_LS_COMB = 2
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 148
try:
    DB_LS_REGION = 4
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 149
try:
    DB_LS_HIDDEN = 8
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 150
try:
    DB_LS_NON_GEOM = 16
except:
    pass

# /opt/brlcad/include/brlcad/./rt/search.h: 151
try:
    DB_LS_TOPS = 32
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_io.h: 55
try:
    DB_OPEN_READONLY = 'r'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_io.h: 60
try:
    DB_OPEN_READWRITE = 'rw'
except:
    pass

# /opt/brlcad/include/brlcad/./rt/misc.h: 69
try:
    RT_REDUCE_OBJ_PRESERVE_VOLUME = 1
except:
    pass

# /opt/brlcad/include/brlcad/./rt/db_attr.h: 228
def ATTR_STD(attr):
    return (db5_standard_attribute ((db5_standardize_attribute (attr))))

# /opt/brlcad/include/brlcad/rt/solid.h: 68
try:
    SOLID_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/rt/solid.h: 86
def LAST_SOLID(_sp):
    return (DB_FULL_PATH_CUR_DIR (pointer((_sp.contents.s_fullpath))))

# /opt/brlcad/include/brlcad/rt/solid.h: 87
def FIRST_SOLID(_sp):
    return (((_sp.contents.s_fullpath).fp_names) [0])

# /opt/brlcad/include/brlcad/rt/db_diff.h: 40
try:
    DIFF_EMPTY = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/db_diff.h: 41
try:
    DIFF_UNCHANGED = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db_diff.h: 42
try:
    DIFF_REMOVED = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/db_diff.h: 43
try:
    DIFF_ADDED = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/db_diff.h: 44
try:
    DIFF_CHANGED = 8
except:
    pass

# /opt/brlcad/include/brlcad/rt/db_diff.h: 45
try:
    DIFF_CONFLICT = 16
except:
    pass

# /opt/brlcad/include/brlcad/rt/tie.h: 52
try:
    TIE_PRECISION = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/tie.h: 55
try:
    TIE_CHECK_DEGENERATE = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/tie.h: 57
try:
    TIE_KDTREE_FAST = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/tie.h: 58
try:
    TIE_KDTREE_OPTIMAL = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 73
try:
    NAMESIZE = 16
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 85
try:
    DB_MINREC = 128
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 92
try:
    ID_NO_UNIT = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 93
try:
    ID_MM_UNIT = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 94
try:
    ID_CM_UNIT = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 95
try:
    ID_M_UNIT = 3
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 96
try:
    ID_IN_UNIT = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 97
try:
    ID_FT_UNIT = 5
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 99
try:
    ID_UM_UNIT = 6
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 100
try:
    ID_KM_UNIT = 7
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 101
try:
    ID_YD_UNIT = 8
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 102
try:
    ID_MI_UNIT = 9
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 104
try:
    ID_VERSION = 'v4'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 108
try:
    ID_BY_UNKNOWN = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 109
try:
    ID_BY_VAX = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 110
try:
    ED_BY_IBM = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 112
try:
    ID_FT_UNKNOWN = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 113
try:
    ID_FT_VAX = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 114
try:
    ID_FT_IBM = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 115
try:
    ID_FT_IEEE = 3
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 116
try:
    ID_FT_CRAY = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 122
try:
    RPP = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 123
try:
    BOX = 2
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 124
try:
    RAW = 3
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 125
try:
    ARB4 = 4
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 126
try:
    ARB5 = 5
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 127
try:
    ARB6 = 6
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 128
try:
    ARB7 = 7
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 129
try:
    ARB8 = 8
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 130
try:
    ELL = 9
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 131
try:
    ELL1 = 10
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 132
try:
    SPH = 11
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 133
try:
    RCC = 12
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 134
try:
    REC = 13
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 135
try:
    TRC = 14
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 136
try:
    TEC = 15
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 137
try:
    TOR = 16
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 138
try:
    TGC = 17
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 139
try:
    GENTGC = 18
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 140
try:
    GENELL = 19
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 141
try:
    GENARB8 = 20
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 142
try:
    ARS = 21
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 143
try:
    ARSCONT = 22
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 144
try:
    ELLG = 23
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 145
try:
    HALFSPACE = 24
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 146
try:
    SPLINE = 25
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 147
try:
    RPC = 26
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 148
try:
    RHC = 27
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 149
try:
    EPA = 28
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 150
try:
    EHY = 29
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 151
try:
    ETO = 30
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 152
try:
    GRP = 31
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 153
try:
    SUPERELL = 32
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 154
try:
    HYP = 33
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 197
try:
    DBV4_NON_REGION = ' '
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 198
try:
    DBV4_NON_REGION_NULL = '\\0'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 199
try:
    DBV4_REGION = 'R'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 200
try:
    DBV4_REGION_FASTGEN_PLATE = 'P'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 201
try:
    DBV4_REGION_FASTGEN_VOLUME = 'V'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 214
try:
    DB_INH_LOWER = 0
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 215
try:
    DB_INH_HIGHER = 1
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 302
try:
    DB_SS_NGRAN = 8
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 303
try:
    DB_SS_LEN = (((DB_SS_NGRAN * DB_MINREC) - (2 * NAMESIZE)) - 2)
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 424
try:
    ID_IDENT = 'I'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 425
try:
    ID_SOLID = 'S'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 426
try:
    ID_COMB = 'C'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 427
try:
    ID_MEMB = 'M'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 428
try:
    ID_ARS_A = 'A'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 429
try:
    ID_ARS_B = 'B'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 430
try:
    ID_FREE = 'F'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 431
try:
    ID_P_HEAD = 'P'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 432
try:
    ID_P_DATA = 'Q'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 433
try:
    ID_BSOLID = 'b'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 434
try:
    ID_BSURF = 'D'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 435
try:
    ID_MATERIAL = 'm'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 436
try:
    DBID_STRSOL = 's'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 437
try:
    DBID_ARBN = 'n'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 438
try:
    DBID_PIPE = 'w'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 439
try:
    DBID_PARTICLE = 'p'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 440
try:
    DBID_NMG = 'N'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 441
try:
    DBID_SKETCH = 'd'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 442
try:
    DBID_ANNOT = 'a'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 443
try:
    DBID_EXTR = 'e'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 444
try:
    DBID_CLINE = 'c'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 445
try:
    DBID_BOT = 't'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 446
try:
    DBID_SCRIPT = 'T'
except:
    pass

# /opt/brlcad/include/brlcad/rt/db4.h: 501
try:
    DB_RECORD_NULL = None
except:
    pass

rusage = struct_rusage # /usr/include/sys/resource.h: 152

rusage_info_v0 = struct_rusage_info_v0 # /usr/include/sys/resource.h: 194

rusage_info_v1 = struct_rusage_info_v1 # /usr/include/sys/resource.h: 208

rusage_info_v2 = struct_rusage_info_v2 # /usr/include/sys/resource.h: 228

rusage_info_v3 = struct_rusage_info_v3 # /usr/include/sys/resource.h: 250

rlimit = struct_rlimit # /usr/include/sys/resource.h: 325

proc_rlimit_control_wakeupmon = struct_proc_rlimit_control_wakeupmon # /usr/include/sys/resource.h: 353

bn_tol = struct_bn_tol # /opt/brlcad/include/brlcad/bn/tol.h: 72

bn_vlist = struct_bn_vlist # /opt/brlcad/include/brlcad/bn/vlist.h: 67

bn_vlblock = struct_bn_vlblock # /opt/brlcad/include/brlcad/bn/vlist.h: 193

db5_ondisk_header = struct_db5_ondisk_header # /opt/brlcad/include/brlcad/./rt/db5.h: 56

db5_raw_internal = struct_db5_raw_internal # /opt/brlcad/include/brlcad/./rt/db5.h: 200

knot_vector = struct_knot_vector # /opt/brlcad/include/brlcad/nmg.h: 221

model = struct_model # /opt/brlcad/include/brlcad/nmg.h: 245

nmgregion_a = struct_nmgregion_a # /opt/brlcad/include/brlcad/nmg.h: 261

nmgregion = struct_nmgregion # /opt/brlcad/include/brlcad/nmg.h: 253

shell_a = struct_shell_a # /opt/brlcad/include/brlcad/nmg.h: 297

vertexuse = struct_vertexuse # /opt/brlcad/include/brlcad/nmg.h: 545

shell = struct_shell # /opt/brlcad/include/brlcad/nmg.h: 285

faceuse = struct_faceuse # /opt/brlcad/include/brlcad/nmg.h: 352

face_g_plane = struct_face_g_plane # /opt/brlcad/include/brlcad/nmg.h: 324

face_g_snurb = struct_face_g_snurb # /opt/brlcad/include/brlcad/nmg.h: 331

face = struct_face # /opt/brlcad/include/brlcad/nmg.h: 308

loopuse = struct_loopuse # /opt/brlcad/include/brlcad/nmg.h: 432

loop_g = struct_loop_g # /opt/brlcad/include/brlcad/nmg.h: 425

loop = struct_loop # /opt/brlcad/include/brlcad/nmg.h: 418

edgeuse = struct_edgeuse # /opt/brlcad/include/brlcad/nmg.h: 504

edge = struct_edge # /opt/brlcad/include/brlcad/nmg.h: 464

edge_g_lseg = struct_edge_g_lseg # /opt/brlcad/include/brlcad/nmg.h: 476

edge_g_cnurb = struct_edge_g_cnurb # /opt/brlcad/include/brlcad/nmg.h: 492

vertex_g = struct_vertex_g # /opt/brlcad/include/brlcad/nmg.h: 539

vertex = struct_vertex # /opt/brlcad/include/brlcad/nmg.h: 532

vertexuse_a_plane = struct_vertexuse_a_plane # /opt/brlcad/include/brlcad/nmg.h: 562

vertexuse_a_cnurb = struct_vertexuse_a_cnurb # /opt/brlcad/include/brlcad/nmg.h: 568

nmg_boolstruct = struct_nmg_boolstruct # /opt/brlcad/include/brlcad/nmg.h: 678

nmg_struct_counts = struct_nmg_struct_counts # /opt/brlcad/include/brlcad/nmg.h: 700

nmg_visit_handlers = struct_nmg_visit_handlers # /opt/brlcad/include/brlcad/nmg.h: 800

nmg_radial = struct_nmg_radial # /opt/brlcad/include/brlcad/nmg.h: 840

nmg_inter_struct = struct_nmg_inter_struct # /opt/brlcad/include/brlcad/nmg.h: 853

nmg_nurb_poly = struct_nmg_nurb_poly # /opt/brlcad/include/brlcad/nmg.h: 941

nmg_nurb_uv_hit = struct_nmg_nurb_uv_hit # /opt/brlcad/include/brlcad/nmg.h: 947

oslo_mat = struct_oslo_mat # /opt/brlcad/include/brlcad/nmg.h: 955

bezier_2d_list = struct_bezier_2d_list # /opt/brlcad/include/brlcad/nmg.h: 964

nmg_ray = struct_nmg_ray # /opt/brlcad/include/brlcad/nmg.h: 1106

nmg_hit = struct_nmg_hit # /opt/brlcad/include/brlcad/nmg.h: 1114

nmg_seg = struct_nmg_seg # /opt/brlcad/include/brlcad/nmg.h: 1125

nmg_hitmiss = struct_nmg_hitmiss # /opt/brlcad/include/brlcad/nmg.h: 1132

nmg_ray_data = struct_nmg_ray_data # /opt/brlcad/include/brlcad/nmg.h: 1169

nmg_curvature = struct_nmg_curvature # /opt/brlcad/include/brlcad/nmg.h: 2690

_on_brep_placeholder = struct__on_brep_placeholder # /opt/brlcad/include/brlcad/brep/defines.h: 54

rt_tor_internal = struct_rt_tor_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 59

rt_tgc_internal = struct_rt_tgc_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 78

rt_ell_internal = struct_rt_ell_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 95

rt_superell_internal = struct_rt_superell_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 110

rt_metaball_internal = struct_rt_metaball_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 155

wdb_metaballpt = struct_wdb_metaballpt # /opt/brlcad/include/brlcad/./rt/geom.h: 168

rt_arb_internal = struct_rt_arb_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 190

rt_ars_internal = struct_rt_ars_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 202

rt_half_internal = struct_rt_half_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 216

rt_grip_internal = struct_rt_grip_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 228

rt_joint_internal = struct_rt_joint_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 243

rt_pg_face_internal = struct_rt_pg_face_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 262

rt_pg_internal = struct_rt_pg_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 267

rt_nurb_internal = struct_rt_nurb_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 280

rt_brep_internal = struct_rt_brep_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 296

rt_ebm_internal = struct_rt_ebm_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 322

rt_vol_internal = struct_rt_vol_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 344

rt_hf_internal = struct_rt_hf_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 368

rt_arbn_internal = struct_rt_arbn_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 398

rt_pipe_internal = struct_rt_pipe_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 411

wdb_pipept = struct_wdb_pipept # /opt/brlcad/include/brlcad/./rt/geom.h: 418

rt_part_internal = struct_rt_part_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 433

rt_rpc_internal = struct_rt_rpc_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 454

rt_rhc_internal = struct_rt_rhc_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 469

rt_epa_internal = struct_rt_epa_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 485

rt_ehy_internal = struct_rt_ehy_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 501

rt_hyp_internal = struct_rt_hyp_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 518

rt_eto_internal = struct_rt_eto_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 534

rt_db_internal = struct_rt_db_internal # /opt/brlcad/include/brlcad/./rt/db_internal.h: 46

rt_dsp_internal = struct_rt_dsp_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 551

rt_curve = struct_rt_curve # /opt/brlcad/include/brlcad/./rt/geom.h: 592

line_seg = struct_line_seg # /opt/brlcad/include/brlcad/./rt/geom.h: 604

carc_seg = struct_carc_seg # /opt/brlcad/include/brlcad/./rt/geom.h: 611

nurb_seg = struct_nurb_seg # /opt/brlcad/include/brlcad/./rt/geom.h: 625

bezier_seg = struct_bezier_seg # /opt/brlcad/include/brlcad/./rt/geom.h: 637

rt_sketch_internal = struct_rt_sketch_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 646

db_i = struct_db_i # /opt/brlcad/include/brlcad/./rt/geom.h: 679

rt_submodel_internal = struct_rt_submodel_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 671

rt_extrude_internal = struct_rt_extrude_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 690

rt_revolve_internal = struct_rt_revolve_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 715

rt_cline_internal = struct_rt_cline_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 739

rt_bot_internal = struct_rt_bot_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 756

rt_bot_list = struct_rt_bot_list # /opt/brlcad/include/brlcad/./rt/geom.h: 801

pnt = struct_pnt # /opt/brlcad/include/brlcad/./rt/geom.h: 868

pnt_color = struct_pnt_color # /opt/brlcad/include/brlcad/./rt/geom.h: 872

pnt_scale = struct_pnt_scale # /opt/brlcad/include/brlcad/./rt/geom.h: 877

pnt_normal = struct_pnt_normal # /opt/brlcad/include/brlcad/./rt/geom.h: 882

pnt_color_scale = struct_pnt_color_scale # /opt/brlcad/include/brlcad/./rt/geom.h: 887

pnt_color_normal = struct_pnt_color_normal # /opt/brlcad/include/brlcad/./rt/geom.h: 893

pnt_scale_normal = struct_pnt_scale_normal # /opt/brlcad/include/brlcad/./rt/geom.h: 899

pnt_color_scale_normal = struct_pnt_color_scale_normal # /opt/brlcad/include/brlcad/./rt/geom.h: 905

rt_pnts_internal = struct_rt_pnts_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 914

rt_ant = struct_rt_ant # /opt/brlcad/include/brlcad/./rt/geom.h: 935

txt_seg = struct_txt_seg # /opt/brlcad/include/brlcad/./rt/geom.h: 946

rt_annot_internal = struct_rt_annot_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 953

rt_datum_internal = struct_rt_datum_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 1010

rt_hrt_internal = struct_rt_hrt_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 1029

rt_script_internal = struct_rt_script_internal # /opt/brlcad/include/brlcad/./rt/geom.h: 1043

resource = struct_resource # /opt/brlcad/include/brlcad/rt/resource.h: 61

directory = struct_directory # /opt/brlcad/include/brlcad/rt/directory.h: 59

db_full_path = struct_db_full_path # /opt/brlcad/include/brlcad/./rt/db_fullpath.h: 51

rt_tess_tol = struct_rt_tess_tol # /opt/brlcad/include/brlcad/./rt/tol.h: 86

mem_map = struct_mem_map # /opt/brlcad/include/brlcad/rt/mem.h: 37

region = struct_region # /opt/brlcad/include/brlcad/rt/region.h: 44

mater_info = struct_mater_info # /opt/brlcad/include/brlcad/rt/mater.h: 38

mater = struct_mater # /opt/brlcad/include/brlcad/rt/mater.h: 50

anim_mat = struct_anim_mat # /opt/brlcad/include/brlcad/rt/anim.h: 52

rt_anim_property = struct_rt_anim_property # /opt/brlcad/include/brlcad/rt/anim.h: 62

rt_anim_color = struct_rt_anim_color # /opt/brlcad/include/brlcad/rt/anim.h: 71

animate = struct_animate # /opt/brlcad/include/brlcad/rt/anim.h: 76

animate_specific = union_animate_specific # /opt/brlcad/include/brlcad/rt/anim.h: 81

rt_wdb = struct_rt_wdb # /opt/brlcad/include/brlcad/./rt/wdb.h: 49

tree = union_tree # /opt/brlcad/include/brlcad/rt/tree.h: 147

bound_rpp = struct_bound_rpp # /opt/brlcad/include/brlcad/rt/soltab.h: 43

rt_functab = struct_rt_functab # /opt/brlcad/include/brlcad/rt/functab.h: 69

rt_i = struct_rt_i # /opt/brlcad/include/brlcad/./rt/rt_instance.h: 61

soltab = struct_soltab # /opt/brlcad/include/brlcad/rt/soltab.h: 56

xray = struct_xray # /opt/brlcad/include/brlcad/rt/xray.h: 41

xrays = struct_xrays # /opt/brlcad/include/brlcad/rt/xray.h: 57

pixel_ext = struct_pixel_ext # /opt/brlcad/include/brlcad/rt/xray.h: 74

hit = struct_hit # /opt/brlcad/include/brlcad/rt/hit.h: 61

curvature = struct_curvature # /opt/brlcad/include/brlcad/rt/hit.h: 118

uvcoord = struct_uvcoord # /opt/brlcad/include/brlcad/rt/hit.h: 152

seg = struct_seg # /opt/brlcad/include/brlcad/rt/seg.h: 59

partition = struct_partition # /opt/brlcad/include/brlcad/rt/ray_partition.h: 53

application = struct_application # /opt/brlcad/include/brlcad/rt/application.h: 99

partition_list = struct_partition_list # /opt/brlcad/include/brlcad/rt/ray_partition.h: 136

partition_bundle = struct_partition_bundle # /opt/brlcad/include/brlcad/rt/ray_partition.h: 149

application_bundle = struct_application_bundle # /opt/brlcad/include/brlcad/rt/application.h: 176

hitmiss = struct_hitmiss # /opt/brlcad/include/brlcad/./rt/nmg.h: 42

ray_data = struct_ray_data # /opt/brlcad/include/brlcad/./rt/nmg.h: 81

db_tree_state = struct_db_tree_state # /opt/brlcad/include/brlcad/rt/tree.h: 56

rt_comb_internal = struct_rt_comb_internal # /opt/brlcad/include/brlcad/./rt/nongeom.h: 41

db_traverse = struct_db_traverse # /opt/brlcad/include/brlcad/rt/tree.h: 115

combined_tree_state = struct_combined_tree_state # /opt/brlcad/include/brlcad/rt/tree.h: 140

tree_node = struct_tree_node # /opt/brlcad/include/brlcad/rt/tree.h: 150

tree_leaf = struct_tree_leaf # /opt/brlcad/include/brlcad/rt/tree.h: 157

tree_cts = struct_tree_cts # /opt/brlcad/include/brlcad/rt/tree.h: 163

tree_nmgregion = struct_tree_nmgregion # /opt/brlcad/include/brlcad/rt/tree.h: 169

tree_db_leaf = struct_tree_db_leaf # /opt/brlcad/include/brlcad/rt/tree.h: 175

rt_tree_array = struct_rt_tree_array # /opt/brlcad/include/brlcad/rt/tree.h: 227

rt_piecestate = struct_rt_piecestate # /opt/brlcad/include/brlcad/./rt/piece.h: 57

rt_piecelist = struct_rt_piecelist # /opt/brlcad/include/brlcad/./rt/piece.h: 84

cutter = union_cutter # /opt/brlcad/include/brlcad/./rt/space_partition.h: 70

cutnode = struct_cutnode # /opt/brlcad/include/brlcad/./rt/space_partition.h: 46

boxnode = struct_boxnode # /opt/brlcad/include/brlcad/./rt/space_partition.h: 54

bvh_build_node = struct_bvh_build_node # /opt/brlcad/include/brlcad/./rt/space_partition.h: 103

rt_binunif_internal = struct_rt_binunif_internal # /opt/brlcad/include/brlcad/./rt/nongeom.h: 103

rt_constraint_internal = struct_rt_constraint_internal # /opt/brlcad/include/brlcad/./rt/nongeom.h: 127

rt_htbl = struct_rt_htbl # /opt/brlcad/include/brlcad/./rt/piece.h: 41

rt_g = struct_rt_g # /opt/brlcad/include/brlcad/./rt/global.h: 39

rt_view_info = struct_rt_view_info # /opt/brlcad/include/brlcad/./rt/view.h: 49

rt_selection = struct_rt_selection # /opt/brlcad/include/brlcad/./rt/view.h: 78

rt_selection_set = struct_rt_selection_set # /opt/brlcad/include/brlcad/./rt/view.h: 86

rt_object_selections = struct_rt_object_selections # /opt/brlcad/include/brlcad/./rt/view.h: 104

rt_selection_query = struct_rt_selection_query # /opt/brlcad/include/brlcad/./rt/view.h: 117

rt_selection_translation = struct_rt_selection_translation # /opt/brlcad/include/brlcad/./rt/view.h: 132

rt_selection_operation = struct_rt_selection_operation # /opt/brlcad/include/brlcad/./rt/view.h: 144

rt_pt_node = struct_rt_pt_node # /opt/brlcad/include/brlcad/./rt/private.h: 42

rt_shootray_status = struct_rt_shootray_status # /opt/brlcad/include/brlcad/./rt/private.h: 51

rt_pattern_data = struct_rt_pattern_data # /opt/brlcad/include/brlcad/./rt/pattern.h: 68

command_tab = struct_command_tab # /opt/brlcad/include/brlcad/./rt/cmd.h: 42

db_full_path_list = struct_db_full_path_list # /opt/brlcad/include/brlcad/./rt/search.h: 163

record = union_record # /opt/brlcad/include/brlcad/rt/db4.h: 421

bot_specific = struct_bot_specific # /opt/brlcad/include/brlcad/./rt/primitives/bot.h: 57

rt_point_labels = struct_rt_point_labels # /opt/brlcad/include/brlcad/./rt/misc.h: 52

rt_reprep_obj_list = struct_rt_reprep_obj_list # /opt/brlcad/include/brlcad/./rt/prep.h: 40

db5_attr_ctype = struct_db5_attr_ctype # /opt/brlcad/include/brlcad/./rt/db_attr.h: 64

db5_registry = struct_db5_registry # /opt/brlcad/include/brlcad/./rt/db_attr.h: 86

solid = struct_solid # /opt/brlcad/include/brlcad/rt/solid.h: 38

diff_avp = struct_diff_avp # /opt/brlcad/include/brlcad/rt/db_diff.h: 51

diff_result = struct_diff_result # /opt/brlcad/include/brlcad/rt/db_diff.h: 60

TIE_3_s = struct_TIE_3_s # /opt/brlcad/include/brlcad/rt/tie.h: 78

tie_ray_s = struct_tie_ray_s # /opt/brlcad/include/brlcad/rt/tie.h: 80

tie_id_s = struct_tie_id_s # /opt/brlcad/include/brlcad/rt/tie.h: 87

tie_tri_s = struct_tie_tri_s # /opt/brlcad/include/brlcad/rt/tie.h: 95

tie_kdtree_s = struct_tie_kdtree_s # /opt/brlcad/include/brlcad/rt/tie.h: 107

tie_s = struct_tie_s # /opt/brlcad/include/brlcad/rt/tie.h: 114

ident = struct_ident # /opt/brlcad/include/brlcad/rt/db4.h: 88

solidrec = struct_solidrec # /opt/brlcad/include/brlcad/rt/db4.h: 119

combination = struct_combination # /opt/brlcad/include/brlcad/rt/db4.h: 194

member = struct_member # /opt/brlcad/include/brlcad/rt/db4.h: 218

material_rec = struct_material_rec # /opt/brlcad/include/brlcad/rt/db4.h: 228

B_solid = struct_B_solid # /opt/brlcad/include/brlcad/rt/db4.h: 239

b_surf = struct_b_surf # /opt/brlcad/include/brlcad/rt/db4.h: 247

polyhead = struct_polyhead # /opt/brlcad/include/brlcad/rt/db4.h: 257

polydata = struct_polydata # /opt/brlcad/include/brlcad/rt/db4.h: 263

ars_rec = struct_ars_rec # /opt/brlcad/include/brlcad/rt/db4.h: 270

ars_ext = struct_ars_ext # /opt/brlcad/include/brlcad/rt/db4.h: 289

strsol = struct_strsol # /opt/brlcad/include/brlcad/rt/db4.h: 298

arbn_rec = struct_arbn_rec # /opt/brlcad/include/brlcad/rt/db4.h: 308

exported_pipept = struct_exported_pipept # /opt/brlcad/include/brlcad/rt/db4.h: 317

pipewire_rec = struct_pipewire_rec # /opt/brlcad/include/brlcad/rt/db4.h: 324

particle_rec = struct_particle_rec # /opt/brlcad/include/brlcad/rt/db4.h: 333

nmg_rec = struct_nmg_rec # /opt/brlcad/include/brlcad/rt/db4.h: 343

extr_rec = struct_extr_rec # /opt/brlcad/include/brlcad/rt/db4.h: 352

sketch_rec = struct_sketch_rec # /opt/brlcad/include/brlcad/rt/db4.h: 365

annot_rec = struct_annot_rec # /opt/brlcad/include/brlcad/rt/db4.h: 377

script_rec = struct_script_rec # /opt/brlcad/include/brlcad/rt/db4.h: 387

cline_rec = struct_cline_rec # /opt/brlcad/include/brlcad/rt/db4.h: 393

bot_rec = struct_bot_rec # /opt/brlcad/include/brlcad/rt/db4.h: 403

# No inserted files

