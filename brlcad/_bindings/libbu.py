'''Wrapper for bu.h

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

_libs["/opt/brlcad/lib/libbu.dylib"] = load_library("/opt/brlcad/lib/libbu.dylib")

# 1 libraries
# End libraries

# No modules

__int64_t = c_longlong # /usr/include/i386/_types.h: 46

__darwin_off_t = __int64_t # /usr/include/sys/_types.h: 71

off_t = __darwin_off_t # /usr/include/sys/_types/_off_t.h: 30

# /opt/brlcad/include/brlcad/bu/magic.h: 253
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_badmagic'):
    bu_badmagic = _libs['/opt/brlcad/lib/libbu.dylib'].bu_badmagic
    bu_badmagic.argtypes = [POINTER(c_uint32), c_uint32, String, String, c_int]
    bu_badmagic.restype = None

# /opt/brlcad/include/brlcad/bu/magic.h: 265
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_identify_magic'):
    bu_identify_magic = _libs['/opt/brlcad/lib/libbu.dylib'].bu_identify_magic
    bu_identify_magic.argtypes = [c_uint32]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_identify_magic.restype = ReturnString
    else:
        bu_identify_magic.restype = String
        bu_identify_magic.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 53
class struct_bu_vls(Structure):
    pass

struct_bu_vls.__slots__ = [
    'vls_magic',
    'vls_str',
    'vls_offset',
    'vls_len',
    'vls_max',
]
struct_bu_vls._fields_ = [
    ('vls_magic', c_uint32),
    ('vls_str', String),
    ('vls_offset', c_size_t),
    ('vls_len', c_size_t),
    ('vls_max', c_size_t),
]

bu_vls_t = struct_bu_vls # /opt/brlcad/include/brlcad/bu/vls.h: 60

# /opt/brlcad/include/brlcad/bu/vls.h: 95
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_init'):
    bu_vls_init = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_init
    bu_vls_init.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_init.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 103
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_init_if_uninit'):
    bu_vls_init_if_uninit = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_init_if_uninit
    bu_vls_init_if_uninit.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_init_if_uninit.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 110
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_vlsinit'):
    bu_vls_vlsinit = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_vlsinit
    bu_vls_vlsinit.argtypes = []
    bu_vls_vlsinit.restype = POINTER(struct_bu_vls)

# /opt/brlcad/include/brlcad/bu/vls.h: 116
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_addr'):
    bu_vls_addr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_addr
    bu_vls_addr.argtypes = [POINTER(struct_bu_vls)]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_vls_addr.restype = ReturnString
    else:
        bu_vls_addr.restype = String
        bu_vls_addr.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 124
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_cstr'):
    bu_vls_cstr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_cstr
    bu_vls_cstr.argtypes = [POINTER(struct_bu_vls)]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_vls_cstr.restype = ReturnString
    else:
        bu_vls_cstr.restype = String
        bu_vls_cstr.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 131
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_extend'):
    bu_vls_extend = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_extend
    bu_vls_extend.argtypes = [POINTER(struct_bu_vls), c_size_t]
    bu_vls_extend.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 144
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_setlen'):
    bu_vls_setlen = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_setlen
    bu_vls_setlen.argtypes = [POINTER(struct_bu_vls), c_size_t]
    bu_vls_setlen.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 150
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strlen'):
    bu_vls_strlen = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strlen
    bu_vls_strlen.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_strlen.restype = c_size_t

# /opt/brlcad/include/brlcad/bu/vls.h: 158
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_trunc'):
    bu_vls_trunc = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_trunc
    bu_vls_trunc.argtypes = [POINTER(struct_bu_vls), c_int]
    bu_vls_trunc.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 168
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_nibble'):
    bu_vls_nibble = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_nibble
    bu_vls_nibble.argtypes = [POINTER(struct_bu_vls), off_t]
    bu_vls_nibble.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 174
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_free'):
    bu_vls_free = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_free
    bu_vls_free.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_free.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 180
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_vlsfree'):
    bu_vls_vlsfree = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_vlsfree
    bu_vls_vlsfree.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_vlsfree.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 186
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strdup'):
    bu_vls_strdup = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strdup
    bu_vls_strdup.argtypes = [POINTER(struct_bu_vls)]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_vls_strdup.restype = ReturnString
    else:
        bu_vls_strdup.restype = String
        bu_vls_strdup.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 197
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strgrab'):
    bu_vls_strgrab = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strgrab
    bu_vls_strgrab.argtypes = [POINTER(struct_bu_vls)]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_vls_strgrab.restype = ReturnString
    else:
        bu_vls_strgrab.restype = String
        bu_vls_strgrab.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 202
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strcpy'):
    bu_vls_strcpy = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strcpy
    bu_vls_strcpy.argtypes = [POINTER(struct_bu_vls), String]
    bu_vls_strcpy.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 209
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strncpy'):
    bu_vls_strncpy = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strncpy
    bu_vls_strncpy.argtypes = [POINTER(struct_bu_vls), String, c_size_t]
    bu_vls_strncpy.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 216
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strcat'):
    bu_vls_strcat = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strcat
    bu_vls_strcat.argtypes = [POINTER(struct_bu_vls), String]
    bu_vls_strcat.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 222
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strncat'):
    bu_vls_strncat = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strncat
    bu_vls_strncat.argtypes = [POINTER(struct_bu_vls), String, c_size_t]
    bu_vls_strncat.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 230
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_vlscat'):
    bu_vls_vlscat = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_vlscat
    bu_vls_vlscat.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_vls)]
    bu_vls_vlscat.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 237
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_vlscatzap'):
    bu_vls_vlscatzap = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_vlscatzap
    bu_vls_vlscatzap.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_vls)]
    bu_vls_vlscatzap.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 245
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strcmp'):
    bu_vls_strcmp = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strcmp
    bu_vls_strcmp.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_vls)]
    bu_vls_strcmp.restype = c_int

# /opt/brlcad/include/brlcad/bu/vls.h: 254
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_strncmp'):
    bu_vls_strncmp = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_strncmp
    bu_vls_strncmp.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_vls), c_size_t]
    bu_vls_strncmp.restype = c_int

# /opt/brlcad/include/brlcad/bu/vls.h: 262
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_from_argv'):
    bu_vls_from_argv = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_from_argv
    bu_vls_from_argv.argtypes = [POINTER(struct_bu_vls), c_int, POINTER(POINTER(c_char))]
    bu_vls_from_argv.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 275
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_write'):
    bu_vls_write = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_write
    bu_vls_write.argtypes = [c_int, POINTER(struct_bu_vls)]
    bu_vls_write.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 286
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_read'):
    bu_vls_read = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_read
    bu_vls_read.argtypes = [POINTER(struct_bu_vls), c_int]
    bu_vls_read.restype = c_int

# /opt/brlcad/include/brlcad/bu/vls.h: 307
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_putc'):
    bu_vls_putc = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_putc
    bu_vls_putc.argtypes = [POINTER(struct_bu_vls), c_int]
    bu_vls_putc.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 313
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_trimspace'):
    bu_vls_trimspace = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_trimspace
    bu_vls_trimspace.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_trimspace.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 328
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_printf'):
    _func = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_printf
    _restype = None
    _argtypes = [POINTER(struct_bu_vls), String]
    bu_vls_printf = _variadic_function(_func,_restype,_argtypes)

# /opt/brlcad/include/brlcad/bu/vls.h: 340
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_sprintf'):
    _func = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_sprintf
    _restype = None
    _argtypes = [POINTER(struct_bu_vls), String]
    bu_vls_sprintf = _variadic_function(_func,_restype,_argtypes)

# /opt/brlcad/include/brlcad/bu/vls.h: 346
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_spaces'):
    bu_vls_spaces = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_spaces
    bu_vls_spaces.argtypes = [POINTER(struct_bu_vls), c_size_t]
    bu_vls_spaces.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 361
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_print_positions_used'):
    bu_vls_print_positions_used = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_print_positions_used
    bu_vls_print_positions_used.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_print_positions_used.restype = c_size_t

# /opt/brlcad/include/brlcad/bu/vls.h: 368
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_detab'):
    bu_vls_detab = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_detab
    bu_vls_detab.argtypes = [POINTER(struct_bu_vls)]
    bu_vls_detab.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 374
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_prepend'):
    bu_vls_prepend = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_prepend
    bu_vls_prepend.argtypes = [POINTER(struct_bu_vls), String]
    bu_vls_prepend.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 388
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_substr'):
    bu_vls_substr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_substr
    bu_vls_substr.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_vls), c_size_t, c_size_t]
    bu_vls_substr.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 404
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_vprintf'):
    bu_vls_vprintf = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_vprintf
    bu_vls_vprintf.argtypes = [POINTER(struct_bu_vls), String, c_void_p]
    bu_vls_vprintf.restype = None

# /opt/brlcad/include/brlcad/bu/vls.h: 449
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_encode'):
    bu_vls_encode = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_encode
    bu_vls_encode.argtypes = [POINTER(struct_bu_vls), String]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_vls_encode.restype = ReturnString
    else:
        bu_vls_encode.restype = String
        bu_vls_encode.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 462
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_decode'):
    bu_vls_decode = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_decode
    bu_vls_decode.argtypes = [POINTER(struct_bu_vls), String]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_vls_decode.restype = ReturnString
    else:
        bu_vls_decode.restype = String
        bu_vls_decode.errcheck = ReturnString

# /opt/brlcad/include/brlcad/bu/vls.h: 501
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_simplify'):
    bu_vls_simplify = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_simplify
    bu_vls_simplify.argtypes = [POINTER(struct_bu_vls), String, String, String]
    bu_vls_simplify.restype = c_int

bu_vls_uniq_t = CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_bu_vls), POINTER(None)) # /opt/brlcad/include/brlcad/bu/vls.h: 507

# /opt/brlcad/include/brlcad/bu/vls.h: 656
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_incr'):
    bu_vls_incr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_incr
    bu_vls_incr.argtypes = [POINTER(struct_bu_vls), String, String, bu_vls_uniq_t, POINTER(None)]
    bu_vls_incr.restype = c_int

# /opt/brlcad/include/brlcad/bu/list.h: 130
class struct_bu_list(Structure):
    pass

struct_bu_list.__slots__ = [
    'magic',
    'forw',
    'back',
]
struct_bu_list._fields_ = [
    ('magic', c_uint32),
    ('forw', POINTER(struct_bu_list)),
    ('back', POINTER(struct_bu_list)),
]

bu_list_t = struct_bu_list # /opt/brlcad/include/brlcad/bu/list.h: 135

# /opt/brlcad/include/brlcad/bu/list.h: 489
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_new'):
    bu_list_new = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_new
    bu_list_new.argtypes = []
    bu_list_new.restype = POINTER(struct_bu_list)

# /opt/brlcad/include/brlcad/bu/list.h: 494
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_pop'):
    bu_list_pop = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_pop
    bu_list_pop.argtypes = [POINTER(struct_bu_list)]
    bu_list_pop.restype = POINTER(struct_bu_list)

# /opt/brlcad/include/brlcad/bu/list.h: 499
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_len'):
    bu_list_len = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_len
    bu_list_len.argtypes = [POINTER(struct_bu_list)]
    bu_list_len.restype = c_int

# /opt/brlcad/include/brlcad/bu/list.h: 504
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_reverse'):
    bu_list_reverse = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_reverse
    bu_list_reverse.argtypes = [POINTER(struct_bu_list)]
    bu_list_reverse.restype = None

# /opt/brlcad/include/brlcad/bu/list.h: 512
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_free'):
    bu_list_free = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_free
    bu_list_free.argtypes = [POINTER(struct_bu_list)]
    bu_list_free.restype = None

# /opt/brlcad/include/brlcad/bu/list.h: 522
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_parallel_append'):
    bu_list_parallel_append = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_parallel_append
    bu_list_parallel_append.argtypes = [POINTER(struct_bu_list), POINTER(struct_bu_list)]
    bu_list_parallel_append.restype = None

# /opt/brlcad/include/brlcad/bu/list.h: 535
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_list_parallel_dequeue'):
    bu_list_parallel_dequeue = _libs['/opt/brlcad/lib/libbu.dylib'].bu_list_parallel_dequeue
    bu_list_parallel_dequeue.argtypes = [POINTER(struct_bu_list)]
    bu_list_parallel_dequeue.restype = POINTER(struct_bu_list)

# /opt/brlcad/include/brlcad/bu/list.h: 540
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_ck_list'):
    bu_ck_list = _libs['/opt/brlcad/lib/libbu.dylib'].bu_ck_list
    bu_ck_list.argtypes = [POINTER(struct_bu_list), String]
    bu_ck_list.restype = None

# /opt/brlcad/include/brlcad/bu/list.h: 547
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_ck_list_magic'):
    bu_ck_list_magic = _libs['/opt/brlcad/lib/libbu.dylib'].bu_ck_list_magic
    bu_ck_list_magic.argtypes = [POINTER(struct_bu_list), String, c_uint32]
    bu_ck_list_magic.restype = None

bitv_t = c_ubyte # /opt/brlcad/include/brlcad/./bu/bitv.h: 62

# /opt/brlcad/include/brlcad/./bu/bitv.h: 108
class struct_bu_bitv(Structure):
    pass

struct_bu_bitv.__slots__ = [
    'l',
    'nbits',
    'bits',
]
struct_bu_bitv._fields_ = [
    ('l', struct_bu_list),
    ('nbits', c_size_t),
    ('bits', bitv_t * 2),
]

bu_bitv_t = struct_bu_bitv # /opt/brlcad/include/brlcad/./bu/bitv.h: 113

# /opt/brlcad/include/brlcad/./bu/bitv.h: 149
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_shift'):
    bu_bitv_shift = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_shift
    bu_bitv_shift.argtypes = []
    bu_bitv_shift.restype = c_size_t

# /opt/brlcad/include/brlcad/./bu/bitv.h: 276
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_new'):
    bu_bitv_new = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_new
    bu_bitv_new.argtypes = [c_size_t]
    bu_bitv_new.restype = POINTER(struct_bu_bitv)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 285
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_free'):
    bu_bitv_free = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_free
    bu_bitv_free.argtypes = [POINTER(struct_bu_bitv)]
    bu_bitv_free.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 293
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_clear'):
    bu_bitv_clear = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_clear
    bu_bitv_clear.argtypes = [POINTER(struct_bu_bitv)]
    bu_bitv_clear.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 298
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_or'):
    bu_bitv_or = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_or
    bu_bitv_or.argtypes = [POINTER(struct_bu_bitv), POINTER(struct_bu_bitv)]
    bu_bitv_or.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 303
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_and'):
    bu_bitv_and = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_and
    bu_bitv_and.argtypes = [POINTER(struct_bu_bitv), POINTER(struct_bu_bitv)]
    bu_bitv_and.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 308
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_vls'):
    bu_bitv_vls = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_vls
    bu_bitv_vls.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_bitv)]
    bu_bitv_vls.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 314
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_pr_bitv'):
    bu_pr_bitv = _libs['/opt/brlcad/lib/libbu.dylib'].bu_pr_bitv
    bu_pr_bitv.argtypes = [String, POINTER(struct_bu_bitv)]
    bu_pr_bitv.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 320
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_to_hex'):
    bu_bitv_to_hex = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_to_hex
    bu_bitv_to_hex.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_bitv)]
    bu_bitv_to_hex.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 326
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_hex_to_bitv'):
    bu_hex_to_bitv = _libs['/opt/brlcad/lib/libbu.dylib'].bu_hex_to_bitv
    bu_hex_to_bitv.argtypes = [String]
    bu_hex_to_bitv.restype = POINTER(struct_bu_bitv)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 332
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_to_binary'):
    bu_bitv_to_binary = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_to_binary
    bu_bitv_to_binary.argtypes = [POINTER(struct_bu_vls), POINTER(struct_bu_bitv)]
    bu_bitv_to_binary.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 338
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_binary_to_bitv'):
    bu_binary_to_bitv = _libs['/opt/brlcad/lib/libbu.dylib'].bu_binary_to_bitv
    bu_binary_to_bitv.argtypes = [String]
    bu_binary_to_bitv.restype = POINTER(struct_bu_bitv)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 345
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_binary_to_bitv2'):
    bu_binary_to_bitv2 = _libs['/opt/brlcad/lib/libbu.dylib'].bu_binary_to_bitv2
    bu_binary_to_bitv2.argtypes = [String, c_int]
    bu_binary_to_bitv2.restype = POINTER(struct_bu_bitv)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 352
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_compare_equal'):
    bu_bitv_compare_equal = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_compare_equal
    bu_bitv_compare_equal.argtypes = [POINTER(struct_bu_bitv), POINTER(struct_bu_bitv)]
    bu_bitv_compare_equal.restype = c_int

# /opt/brlcad/include/brlcad/./bu/bitv.h: 360
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_compare_equal2'):
    bu_bitv_compare_equal2 = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_compare_equal2
    bu_bitv_compare_equal2.argtypes = [POINTER(struct_bu_bitv), POINTER(struct_bu_bitv)]
    bu_bitv_compare_equal2.restype = c_int

# /opt/brlcad/include/brlcad/./bu/bitv.h: 365
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_bitv_dup'):
    bu_bitv_dup = _libs['/opt/brlcad/lib/libbu.dylib'].bu_bitv_dup
    bu_bitv_dup.argtypes = [POINTER(struct_bu_bitv)]
    bu_bitv_dup.restype = POINTER(struct_bu_bitv)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 381
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_hexstr_to_binstr'):
    bu_hexstr_to_binstr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_hexstr_to_binstr
    bu_hexstr_to_binstr.argtypes = [String, POINTER(struct_bu_vls)]
    bu_hexstr_to_binstr.restype = c_int

# /opt/brlcad/include/brlcad/./bu/bitv.h: 398
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_binstr_to_hexstr'):
    bu_binstr_to_hexstr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_binstr_to_hexstr
    bu_binstr_to_hexstr.argtypes = [String, POINTER(struct_bu_vls)]
    bu_binstr_to_hexstr.restype = c_int

# /opt/brlcad/include/brlcad/./bu/bitv.h: 415
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_vls_printb'):
    bu_vls_printb = _libs['/opt/brlcad/lib/libbu.dylib'].bu_vls_printb
    bu_vls_printb.argtypes = [POINTER(struct_bu_vls), String, c_ulong, String]
    bu_vls_printb.restype = None

# /opt/brlcad/include/brlcad/./bu/bitv.h: 422
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_printb'):
    bu_printb = _libs['/opt/brlcad/lib/libbu.dylib'].bu_printb
    bu_printb.argtypes = [String, c_ulong, String]
    bu_printb.restype = None

# /opt/brlcad/include/brlcad/./bu/malloc.h: 48
try:
    bu_n_malloc = (c_size_t).in_dll(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_n_malloc')
except:
    pass

# /opt/brlcad/include/brlcad/./bu/malloc.h: 49
try:
    bu_n_realloc = (c_size_t).in_dll(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_n_realloc')
except:
    pass

# /opt/brlcad/include/brlcad/./bu/malloc.h: 50
try:
    bu_n_free = (c_size_t).in_dll(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_n_free')
except:
    pass

# /opt/brlcad/include/brlcad/./bu/malloc.h: 57
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_malloc'):
    bu_malloc = _libs['/opt/brlcad/lib/libbu.dylib'].bu_malloc
    bu_malloc.argtypes = [c_size_t, String]
    bu_malloc.restype = POINTER(None)

# /opt/brlcad/include/brlcad/./bu/malloc.h: 65
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_calloc'):
    bu_calloc = _libs['/opt/brlcad/lib/libbu.dylib'].bu_calloc
    bu_calloc.argtypes = [c_size_t, c_size_t, String]
    bu_calloc.restype = POINTER(None)

# /opt/brlcad/include/brlcad/./bu/malloc.h: 69
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_free'):
    bu_free = _libs['/opt/brlcad/lib/libbu.dylib'].bu_free
    bu_free.argtypes = [POINTER(None), String]
    bu_free.restype = None

# /opt/brlcad/include/brlcad/./bu/malloc.h: 84
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_realloc'):
    bu_realloc = _libs['/opt/brlcad/lib/libbu.dylib'].bu_realloc
    bu_realloc.argtypes = [POINTER(None), c_size_t, String]
    bu_realloc.restype = POINTER(None)

# /opt/brlcad/include/brlcad/./bu/malloc.h: 91
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_prmem'):
    bu_prmem = _libs['/opt/brlcad/lib/libbu.dylib'].bu_prmem
    bu_prmem.argtypes = [String]
    bu_prmem.restype = None

# /opt/brlcad/include/brlcad/./bu/malloc.h: 108
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_malloc_len_roundup'):
    bu_malloc_len_roundup = _libs['/opt/brlcad/lib/libbu.dylib'].bu_malloc_len_roundup
    bu_malloc_len_roundup.argtypes = [c_int]
    bu_malloc_len_roundup.restype = c_int

# /opt/brlcad/include/brlcad/./bu/malloc.h: 113
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_ck_malloc_ptr'):
    bu_ck_malloc_ptr = _libs['/opt/brlcad/lib/libbu.dylib'].bu_ck_malloc_ptr
    bu_ck_malloc_ptr.argtypes = [POINTER(None), String]
    bu_ck_malloc_ptr.restype = None

# /opt/brlcad/include/brlcad/./bu/malloc.h: 118
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_mem_barriercheck'):
    bu_mem_barriercheck = _libs['/opt/brlcad/lib/libbu.dylib'].bu_mem_barriercheck
    bu_mem_barriercheck.argtypes = []
    bu_mem_barriercheck.restype = c_int

# /opt/brlcad/include/brlcad/./bu/malloc.h: 131
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_heap_get'):
    bu_heap_get = _libs['/opt/brlcad/lib/libbu.dylib'].bu_heap_get
    bu_heap_get.argtypes = [c_size_t]
    bu_heap_get.restype = POINTER(None)

# /opt/brlcad/include/brlcad/./bu/malloc.h: 141
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_heap_put'):
    bu_heap_put = _libs['/opt/brlcad/lib/libbu.dylib'].bu_heap_put
    bu_heap_put.argtypes = [POINTER(None), c_size_t]
    bu_heap_put.restype = None

bu_heap_func_t = CFUNCTYPE(UNCHECKED(c_int), String) # /opt/brlcad/include/brlcad/./bu/malloc.h: 147

# /opt/brlcad/include/brlcad/./bu/malloc.h: 157
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_heap_log'):
    bu_heap_log = _libs['/opt/brlcad/lib/libbu.dylib'].bu_heap_log
    bu_heap_log.argtypes = [bu_heap_func_t]
    bu_heap_log.restype = bu_heap_func_t

# /opt/brlcad/include/brlcad/./bu/malloc.h: 164
class struct_bu_pool(Structure):
    pass

struct_bu_pool.__slots__ = [
    'block_size',
    'block_pos',
    'alloc_size',
    'block',
]
struct_bu_pool._fields_ = [
    ('block_size', c_size_t),
    ('block_pos', c_size_t),
    ('alloc_size', c_size_t),
    ('block', POINTER(c_uint8)),
]

# /opt/brlcad/include/brlcad/./bu/malloc.h: 171
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_pool_create'):
    bu_pool_create = _libs['/opt/brlcad/lib/libbu.dylib'].bu_pool_create
    bu_pool_create.argtypes = [c_size_t]
    bu_pool_create.restype = POINTER(struct_bu_pool)

# /opt/brlcad/include/brlcad/./bu/malloc.h: 173
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_pool_alloc'):
    bu_pool_alloc = _libs['/opt/brlcad/lib/libbu.dylib'].bu_pool_alloc
    bu_pool_alloc.argtypes = [POINTER(struct_bu_pool), c_size_t, c_size_t]
    bu_pool_alloc.restype = POINTER(None)

# /opt/brlcad/include/brlcad/./bu/malloc.h: 175
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_pool_delete'):
    bu_pool_delete = _libs['/opt/brlcad/lib/libbu.dylib'].bu_pool_delete
    bu_pool_delete.argtypes = [POINTER(struct_bu_pool)]
    bu_pool_delete.restype = None

# /opt/brlcad/include/brlcad/./bu/malloc.h: 183
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_shmget'):
    bu_shmget = _libs['/opt/brlcad/lib/libbu.dylib'].bu_shmget
    bu_shmget.argtypes = [POINTER(c_int), POINTER(POINTER(c_char)), c_int, c_size_t]
    bu_shmget.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 46
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strlcatm'):
    bu_strlcatm = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strlcatm
    bu_strlcatm.argtypes = [String, String, c_size_t, String]
    bu_strlcatm.restype = c_size_t

# /opt/brlcad/include/brlcad/./bu/str.h: 56
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strlcpym'):
    bu_strlcpym = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strlcpym
    bu_strlcpym.argtypes = [String, String, c_size_t, String]
    bu_strlcpym.restype = c_size_t

# /opt/brlcad/include/brlcad/./bu/str.h: 67
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strdupm'):
    bu_strdupm = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strdupm
    bu_strdupm.argtypes = [String, String]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_strdupm.restype = ReturnString
    else:
        bu_strdupm.restype = String
        bu_strdupm.errcheck = ReturnString

# /opt/brlcad/include/brlcad/./bu/str.h: 77
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strcmp'):
    bu_strcmp = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strcmp
    bu_strcmp.argtypes = [String, String]
    bu_strcmp.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 87
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strncmp'):
    bu_strncmp = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strncmp
    bu_strncmp.argtypes = [String, String, c_size_t]
    bu_strncmp.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 97
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strcasecmp'):
    bu_strcasecmp = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strcasecmp
    bu_strcasecmp.argtypes = [String, String]
    bu_strcasecmp.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 108
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_strncasecmp'):
    bu_strncasecmp = _libs['/opt/brlcad/lib/libbu.dylib'].bu_strncasecmp
    bu_strncasecmp.argtypes = [String, String, c_size_t]
    bu_strncasecmp.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 208
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_str_escape'):
    bu_str_escape = _libs['/opt/brlcad/lib/libbu.dylib'].bu_str_escape
    bu_str_escape.argtypes = [String, String, String, c_size_t]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_str_escape.restype = ReturnString
    else:
        bu_str_escape.restype = String
        bu_str_escape.errcheck = ReturnString

# /opt/brlcad/include/brlcad/./bu/str.h: 238
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_str_unescape'):
    bu_str_unescape = _libs['/opt/brlcad/lib/libbu.dylib'].bu_str_unescape
    bu_str_unescape.argtypes = [String, String, c_size_t]
    if sizeof(c_int) == sizeof(c_void_p):
        bu_str_unescape.restype = ReturnString
    else:
        bu_str_unescape.restype = String
        bu_str_unescape.errcheck = ReturnString

# /opt/brlcad/include/brlcad/./bu/str.h: 243
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_str_isprint'):
    bu_str_isprint = _libs['/opt/brlcad/lib/libbu.dylib'].bu_str_isprint
    bu_str_isprint.argtypes = [String]
    bu_str_isprint.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 261
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_str_true'):
    bu_str_true = _libs['/opt/brlcad/lib/libbu.dylib'].bu_str_true
    bu_str_true.argtypes = [String]
    bu_str_true.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 272
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_str_false'):
    bu_str_false = _libs['/opt/brlcad/lib/libbu.dylib'].bu_str_false
    bu_str_false.argtypes = [String]
    bu_str_false.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 296
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_argv_from_string'):
    bu_argv_from_string = _libs['/opt/brlcad/lib/libbu.dylib'].bu_argv_from_string
    bu_argv_from_string.argtypes = [POINTER(POINTER(c_char)), c_size_t, String]
    bu_argv_from_string.restype = c_size_t

# /opt/brlcad/include/brlcad/./bu/str.h: 305
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_argv_from_tcl_list'):
    bu_argv_from_tcl_list = _libs['/opt/brlcad/lib/libbu.dylib'].bu_argv_from_tcl_list
    bu_argv_from_tcl_list.argtypes = [String, POINTER(c_int), POINTER(POINTER(POINTER(c_char)))]
    bu_argv_from_tcl_list.restype = c_int

# /opt/brlcad/include/brlcad/./bu/str.h: 315
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_argv_free'):
    bu_argv_free = _libs['/opt/brlcad/lib/libbu.dylib'].bu_argv_free
    bu_argv_free.argtypes = [c_size_t, POINTER(POINTER(c_char))]
    bu_argv_free.restype = None

# /opt/brlcad/include/brlcad/./bu/str.h: 321
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_free_args'):
    bu_free_args = _libs['/opt/brlcad/lib/libbu.dylib'].bu_free_args
    bu_free_args.argtypes = [c_size_t, POINTER(POINTER(c_char)), String]
    bu_free_args.restype = None

# /opt/brlcad/include/brlcad/./bu/str.h: 331
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_argv_dup'):
    bu_argv_dup = _libs['/opt/brlcad/lib/libbu.dylib'].bu_argv_dup
    bu_argv_dup.argtypes = [c_size_t, POINTER(POINTER(c_char))]
    bu_argv_dup.restype = POINTER(POINTER(c_char))

# /opt/brlcad/include/brlcad/./bu/str.h: 343
if hasattr(_libs['/opt/brlcad/lib/libbu.dylib'], 'bu_argv_dupinsert'):
    bu_argv_dupinsert = _libs['/opt/brlcad/lib/libbu.dylib'].bu_argv_dupinsert
    bu_argv_dupinsert.argtypes = [c_int, c_size_t, POINTER(POINTER(c_char)), c_size_t, POINTER(POINTER(c_char))]
    bu_argv_dupinsert.restype = POINTER(POINTER(c_char))

# /opt/brlcad/include/brlcad/common.h: 305
def LIKELY(expression):
    return expression

# /opt/brlcad/include/brlcad/bu/magic.h: 55
try:
    BU_AVS_MAGIC = 1098273569
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 56
try:
    BU_BITV_MAGIC = 1651078262
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 57
try:
    BU_COLOR_MAGIC = 1651860332
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 58
try:
    BU_EXTERNAL_MAGIC = 1989000144
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 59
try:
    BU_HASH_ENTRY_MAGIC = 1212501588
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 60
try:
    BU_HASH_RECORD_MAGIC = 1751217000
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 61
try:
    BU_HASH_TBL_MAGIC = 1212240712
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 62
try:
    BU_HIST_MAGIC = 1214870388
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 63
try:
    BU_HOOK_LIST_MAGIC = 2429935277
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 64
try:
    BU_IMAGE_FILE_MAGIC = 1651074669
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 65
try:
    BU_LIST_HEAD_MAGIC = 16868736
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 66
try:
    BU_MAPPED_FILE_MAGIC = 1298231398
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 67
try:
    BU_OBSERVER_MAGIC = 1702454643
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 68
try:
    BU_PTBL_MAGIC = 1886675564
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 69
try:
    BU_RB_LIST_MAGIC = 1919052915
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 70
try:
    BU_RB_NODE_MAGIC = 1919053423
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 71
try:
    BU_RB_PKG_MAGIC = 1919053931
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 72
try:
    BU_RB_TREE_MAGIC = 1919054962
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 73
try:
    BU_VLB_MAGIC = 1599491138
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 74
try:
    BU_VLS_MAGIC = 2301836219
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 78
try:
    BN_GAUSS_MAGIC = 512256128
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 79
try:
    BN_POLY_MAGIC = 1349471353
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 80
try:
    BN_SPM_MAGIC = 1093109368
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 81
try:
    BN_TABDATA_MAGIC = 1400073584
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 82
try:
    BN_TABLE_MAGIC = 1399874420
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 83
try:
    BN_TOL_MAGIC = 2563191995
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 84
try:
    BN_UNIF_MAGIC = 12481632
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 85
try:
    BN_VERT_TREE_MAGIC = 1447383636
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 86
try:
    BN_VLBLOCK_MAGIC = 2551959826
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 87
try:
    BN_VLIST_MAGIC = 2552460404
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 91
try:
    RT_ARBN_INTERNAL_MAGIC = 404972641
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 92
try:
    RT_ARB_INTERNAL_MAGIC = 2616184848
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 93
try:
    RT_ARS_INTERNAL_MAGIC = 2011020259
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 94
try:
    RT_BINUNIF_INTERNAL_MAGIC = 1114205781
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 95
try:
    RT_BOT_INTERNAL_MAGIC = 1651471474
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 96
try:
    RT_BREP_INTERNAL_MAGIC = 1112687952
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 97
try:
    RT_CLINE_INTERNAL_MAGIC = 1131836280
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 98
try:
    RT_DATUM_INTERNAL_MAGIC = 1684108397
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 99
try:
    RT_DSP_INTERNAL_MAGIC = 3558
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 100
try:
    RT_EBM_INTERNAL_MAGIC = 4177637937
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 101
try:
    RT_EHY_INTERNAL_MAGIC = 2865557137
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 102
try:
    RT_ELL_INTERNAL_MAGIC = 2478515199
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 103
try:
    RT_EPA_INTERNAL_MAGIC = 2865557136
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 104
try:
    RT_ETO_INTERNAL_MAGIC = 2865557138
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 105
try:
    RT_EXTRUDE_INTERNAL_MAGIC = 1702392946
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 106
try:
    RT_GRIP_INTERNAL_MAGIC = 823747077
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 107
try:
    RT_HALF_INTERNAL_MAGIC = 2861022173
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 108
try:
    RT_HF_INTERNAL_MAGIC = 1212565837
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 109
try:
    RT_HYP_INTERNAL_MAGIC = 1752789093
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 110
try:
    RT_JOINT_INTERNAL_MAGIC = 1248815470
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 111
try:
    RT_METABALL_INTERNAL_MAGIC = 1650551916
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 112
try:
    RT_NURB_INTERNAL_MAGIC = 2829277
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 113
try:
    RT_PART_INTERNAL_MAGIC = 2865557127
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 114
try:
    RT_PG_INTERNAL_MAGIC = 2617170055
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 115
try:
    RT_PIPE_INTERNAL_MAGIC = 2111290174
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 116
try:
    RT_REVOLVE_INTERNAL_MAGIC = 1919252076
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 117
try:
    RT_RHC_INTERNAL_MAGIC = 2865557129
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 118
try:
    RT_RPC_INTERNAL_MAGIC = 2865557128
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 119
try:
    RT_SKETCH_INTERNAL_MAGIC = 1936418164
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 120
try:
    RT_SUBMODEL_INTERNAL_MAGIC = 1937072749
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 121
try:
    RT_SUPERELL_INTERNAL_MAGIC = 4287871779
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 122
try:
    RT_TGC_INTERNAL_MAGIC = 2864438663
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 123
try:
    RT_TOR_INTERNAL_MAGIC = 2617240967
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 124
try:
    RT_VOL_INTERNAL_MAGIC = 2558239184
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 125
try:
    RT_PNTS_INTERNAL_MAGIC = 1886286963
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 126
try:
    RT_ANNOT_INTERNAL_MAGIC = 1634627183
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 127
try:
    RT_HRT_INTERNAL_MAGIC = 1752331327
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 128
try:
    RT_SCRIPT_INTERNAL_MAGIC = 1935897193
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 132
try:
    NMG_EDGEUSE2_MAGIC = 2442236305
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 133
try:
    NMG_EDGEUSE_MAGIC = 2425393296
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 134
try:
    NMG_EDGE_G_CNURB_MAGIC = 1668182626
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 135
try:
    NMG_EDGE_G_LSEG_MAGIC = 1818847080
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 136
try:
    NMG_EDGE_MAGIC = 858993459
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 137
try:
    NMG_FACEUSE_MAGIC = 1448498774
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 138
try:
    NMG_FACE_G_PLANE_MAGIC = 1919643237
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 139
try:
    NMG_FACE_G_SNURB_MAGIC = 1936618082
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 140
try:
    NMG_FACE_MAGIC = 1162167621
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 141
try:
    NMG_INTER_STRUCT_MAGIC = 2576425248
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 142
try:
    NMG_KNOT_VECTOR_MAGIC = 1802399604
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 143
try:
    NMG_LOOPUSE_MAGIC = 2021161080
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 144
try:
    NMG_LOOP_G_MAGIC = 1679827532
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 145
try:
    NMG_LOOP_MAGIC = 1734829927
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 146
try:
    NMG_MODEL_MAGIC = 303174162
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 147
try:
    NMG_RADIAL_MAGIC = 1382106145
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 148
try:
    NMG_RAY_DATA_MAGIC = 23402353
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 149
try:
    NMG_REGION_A_MAGIC = 1768843040
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 150
try:
    NMG_REGION_MAGIC = 589505315
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 151
try:
    NMG_RT_HIT_MAGIC = 1214870528
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 152
try:
    NMG_RT_HIT_SUB_MAGIC = 1214868736
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 153
try:
    NMG_RT_MISS_MAGIC = 1298756352
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 154
try:
    NMG_SHELL_A_MAGIC = 1696626529
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 155
try:
    NMG_SHELL_MAGIC = 1896313669
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 156
try:
    NMG_VERTEXUSE_A_CNURB_MAGIC = 541159012
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 157
try:
    NMG_VERTEXUSE_A_PLANE_MAGIC = 1768384628
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 158
try:
    NMG_VERTEXUSE_MAGIC = 305402420
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 159
try:
    NMG_VERTEX_G_MAGIC = 1920169735
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 160
try:
    NMG_VERTEX_MAGIC = 1192227
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 164
try:
    RT_ANP_MAGIC = 1095791216
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 165
try:
    RT_AP_MAGIC = 1097887852
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 166
try:
    RT_COMB_MAGIC = 1131375945
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 167
try:
    RT_CONSTRAINT_MAGIC = 1885563245
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 168
try:
    RT_CTS_MAGIC = 2560135459
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 169
try:
    RT_DB_TRAVERSE_MAGIC = 1684173938
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 170
try:
    RT_DBTS_MAGIC = 1684173939
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 171
try:
    RT_DB_INTERNAL_MAGIC = 230414439
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 172
try:
    RT_DIR_MAGIC = 89461266
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 173
try:
    RT_FUNCTAB_MAGIC = 1182092899
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 174
try:
    RT_HIT_MAGIC = 543713652
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 175
try:
    RT_HTBL_MAGIC = 1752457836
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 176
try:
    RT_PIECELIST_MAGIC = 1885564019
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 177
try:
    RT_PIECESTATE_MAGIC = 1885565812
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 178
try:
    RT_RAY_MAGIC = 2020761977
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 179
try:
    RT_REGION_MAGIC = 3757801473
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 180
try:
    RT_SEG_MAGIC = 2562514673
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 181
try:
    RT_SOLTAB2_MAGIC = 2462043618
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 182
try:
    RT_SOLTAB_MAGIC = 2462043616
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 183
try:
    RT_TESS_TOL_MAGIC = 3104378283
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 184
try:
    RT_TREE_MAGIC = 2434339217
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 185
try:
    RT_WDB_MAGIC = 1599562850
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 189
try:
    GED_CMD_MAGIC = 1702389091
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 193
try:
    FB_MAGIC = 4227531003
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 194
try:
    FB_WGL_MAGIC = 1464813122
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 195
try:
    FB_OGL_MAGIC = 1481590338
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 196
try:
    FB_X24_MAGIC = 1479689794
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 197
try:
    FB_TK_MAGIC = 1414219330
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 198
try:
    FB_QT_MAGIC = 1364477506
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 199
try:
    FB_DEBUG_MAGIC = 1145194050
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 200
try:
    FB_DISK_MAGIC = 1145652802
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 201
try:
    FB_STK_MAGIC = 1398031938
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 202
try:
    FB_MEMORY_MAGIC = 1296385602
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 203
try:
    FB_REMOTE_MAGIC = 1380795970
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 204
try:
    FB_NULL_MAGIC = 1314211394
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 205
try:
    FB_OSGL_MAGIC = 1330071106
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 209
try:
    ANIMATE_MAGIC = 1095649635
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 210
try:
    CURVE_BEZIER_MAGIC = 1650817641
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 211
try:
    CURVE_CARC_MAGIC = 1667330659
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 212
try:
    CURVE_LSEG_MAGIC = 1819501927
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 213
try:
    CURVE_NURB_MAGIC = 1853190754
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 214
try:
    ANN_TSEG_MAGIC = 1953719655
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 215
try:
    DB5_RAW_INTERNAL_MAGIC = 1681224297
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 216
try:
    DBI_MAGIC = 1461732225
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 217
try:
    DB_FULL_PATH_MAGIC = 1684170352
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 218
try:
    LIGHT_MAGIC = 3688742327
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 219
try:
    MF_MAGIC = 1435926616
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 220
try:
    PIXEL_EXT_MAGIC = 1350071296
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 221
try:
    PL_MAGIC = 200208397
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 222
try:
    PT_HD_MAGIC = 2271770240
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 223
try:
    PT_MAGIC = 2271770241
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 224
try:
    RESOURCE_MAGIC = 2204440629
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 225
try:
    RTI_MAGIC = 2567968344
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 226
try:
    WDB_METABALLPT_MAGIC = 1835167860
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 227
try:
    WDB_PIPESEG_MAGIC = 2535718895
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 228
try:
    WMEMBER_MAGIC = 1125288210
except:
    pass

# /opt/brlcad/include/brlcad/bu/magic.h: 229
try:
    ICV_IMAGE_MAGIC = 1651074669
except:
    pass

# /opt/brlcad/include/brlcad/bu/vls.h: 61
try:
    BU_VLS_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/bu/vls.h: 89
def BU_VLS_IS_INITIALIZED(_vp):
    return ((_vp != BU_VLS_NULL) and (((_vp.contents.vls_magic).value) == BU_VLS_MAGIC))

# /opt/brlcad/include/brlcad/bu/list.h: 136
try:
    BU_LIST_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/bu/list.h: 147
def BU_LIST_MAGIC_EQUAL(_l, _magic):
    return (((_l.contents.magic).value) == _magic)

# /opt/brlcad/include/brlcad/bu/list.h: 188
def BU_LIST_IS_INITIALIZED(_headp):
    return ((_headp != BU_LIST_NULL) and (LIKELY ((((_headp.contents.forw).value) != BU_LIST_NULL))))

# /opt/brlcad/include/brlcad/bu/list.h: 308
def BU_LIST_IS_EMPTY(headp):
    return (((headp.contents.forw).value) == headp)

# /opt/brlcad/include/brlcad/bu/list.h: 309
def BU_LIST_NON_EMPTY(headp):
    return (((headp.contents.forw).value) != headp)

# /opt/brlcad/include/brlcad/bu/list.h: 312
def BU_LIST_IS_CLEAR(headp):
    return (((((headp.contents.magic).value) == 0) and (((headp.contents.forw).value) == BU_LIST_NULL)) and (((headp.contents.back).value) == BU_LIST_NULL))

# /opt/brlcad/include/brlcad/bu/list.h: 335
def BU_LIST_IS_HEAD(p, headp):
    return (p == headp)

# /opt/brlcad/include/brlcad/bu/list.h: 337
def BU_LIST_NOT_HEAD(p, headp):
    return (not (BU_LIST_IS_HEAD (p, headp)))

# /opt/brlcad/include/brlcad/bu/list.h: 343
def BU_LIST_PREV_IS_HEAD(p, headp):
    return (((p.contents.back).value) == headp)

# /opt/brlcad/include/brlcad/bu/list.h: 345
def BU_LIST_PREV_NOT_HEAD(p, headp):
    return (not (BU_LIST_PREV_IS_HEAD (p, headp)))

# /opt/brlcad/include/brlcad/bu/list.h: 351
def BU_LIST_NEXT_IS_HEAD(p, headp):
    return (((p.contents.forw).value) == headp)

# /opt/brlcad/include/brlcad/bu/list.h: 353
def BU_LIST_NEXT_NOT_HEAD(p, headp):
    return (not (BU_LIST_NEXT_IS_HEAD (p, headp)))

# /opt/brlcad/include/brlcad/bu/list.h: 429
def BU_LIST_FIRST_MAGIC(headp):
    return ((headp.contents.forw).contents.magic)

# /opt/brlcad/include/brlcad/bu/list.h: 430
def BU_LIST_LAST_MAGIC(headp):
    return ((headp.contents.back).contents.magic)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 77
try:
    BU_BITV_SHIFT = 3
except:
    pass

# /opt/brlcad/include/brlcad/./bu/bitv.h: 90
try:
    BU_BITV_MASK = ((1 << BU_BITV_SHIFT) - 1)
except:
    pass

# /opt/brlcad/include/brlcad/./bu/bitv.h: 114
try:
    BU_BITV_NULL = None
except:
    pass

# /opt/brlcad/include/brlcad/./bu/bitv.h: 141
def BU_BITV_IS_INITIALIZED(_bp):
    return ((_bp != BU_BITV_NULL) and (LIKELY ((((((_bp.contents.l).value).magic).value) == BU_BITV_MAGIC))))

# /opt/brlcad/include/brlcad/./bu/bitv.h: 155
def BU_WORDS2BITS(_nw):
    return (((_nw > 0) and _nw or 0 * sizeof(bitv_t)) * 8)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 161
def BU_BITS2WORDS(_nb):
    return (((_nb > 0) and _nb or 0 + BU_BITV_MASK) >> BU_BITV_SHIFT)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 167
def BU_BITS2BYTES(_nb):
    return (((BU_BITS2WORDS (_nb)).value) * sizeof(bitv_t))

# /opt/brlcad/include/brlcad/./bu/bitv.h: 171
def BU_BITTEST(_bv, bit):
    return (((((_bv.contents.bits).value) [(bit >> BU_BITV_SHIFT)]) & (1 << (bit & BU_BITV_MASK))) != 0)

# /opt/brlcad/include/brlcad/./bu/bitv.h: 186
def BU_BITSET(_bv, bit):
    return (((_bv.contents.bits) [(bit >> BU_BITV_SHIFT)]) | (1 << (bit & BU_BITV_MASK)))

# /opt/brlcad/include/brlcad/./bu/bitv.h: 188
def BU_BITCLR(_bv, bit):
    return (((_bv.contents.bits) [(bit >> BU_BITV_SHIFT)]) & (~(1 << (bit & BU_BITV_MASK))))

# /opt/brlcad/include/brlcad/./bu/str.h: 114
def BU_STR_EMPTY(s):
    return (((bu_strcmp (s, '')).value) == 0)

# /opt/brlcad/include/brlcad/./bu/str.h: 123
def BU_STR_EQUAL(s1, s2):
    return (((bu_strcmp (s1, s2)).value) == 0)

# /opt/brlcad/include/brlcad/./bu/str.h: 132
def BU_STR_EQUIV(s1, s2):
    return (((bu_strcasecmp (s1, s2)).value) == 0)

bu_vls = struct_bu_vls # /opt/brlcad/include/brlcad/bu/vls.h: 53

bu_list = struct_bu_list # /opt/brlcad/include/brlcad/bu/list.h: 130

bu_bitv = struct_bu_bitv # /opt/brlcad/include/brlcad/./bu/bitv.h: 108

bu_pool = struct_bu_pool # /opt/brlcad/include/brlcad/./bu/malloc.h: 164

# No inserted files

