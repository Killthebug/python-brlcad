'''Wrapper for ged.h

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

_libs["/opt/brlcad/lib/libged.dylib"] = load_library("/opt/brlcad/lib/libged.dylib")

# 1 libraries
# End libraries

# Begin modules

from libbu import *
from libbn import *
from librt import *

# 3 modules
# End modules

# /opt/brlcad/include/brlcad/dm/bview.h: 51
class struct_display_list(Structure):
    pass

struct_display_list.__slots__ = [
    'l',
    'dl_dp',
    'dl_path',
    'dl_headSolid',
    'dl_wflag',
]
struct_display_list._fields_ = [
    ('l', struct_bu_list),
    ('dl_dp', POINTER(None)),
    ('dl_path', struct_bu_vls),
    ('dl_headSolid', struct_bu_list),
    ('dl_wflag', c_int),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 59
class struct_bview_adc_state(Structure):
    pass

struct_bview_adc_state.__slots__ = [
    'draw',
    'dv_x',
    'dv_y',
    'dv_a1',
    'dv_a2',
    'dv_dist',
    'pos_model',
    'pos_view',
    'pos_grid',
    'a1',
    'a2',
    'dst',
    'anchor_pos',
    'anchor_a1',
    'anchor_a2',
    'anchor_dst',
    'anchor_pt_a1',
    'anchor_pt_a2',
    'anchor_pt_dst',
    'line_color',
    'tick_color',
    'line_width',
]
struct_bview_adc_state._fields_ = [
    ('draw', c_int),
    ('dv_x', c_int),
    ('dv_y', c_int),
    ('dv_a1', c_int),
    ('dv_a2', c_int),
    ('dv_dist', c_int),
    ('pos_model', fastf_t * 3),
    ('pos_view', fastf_t * 3),
    ('pos_grid', fastf_t * 3),
    ('a1', fastf_t),
    ('a2', fastf_t),
    ('dst', fastf_t),
    ('anchor_pos', c_int),
    ('anchor_a1', c_int),
    ('anchor_a2', c_int),
    ('anchor_dst', c_int),
    ('anchor_pt_a1', fastf_t * 3),
    ('anchor_pt_a2', fastf_t * 3),
    ('anchor_pt_dst', fastf_t * 3),
    ('line_color', c_int * 3),
    ('tick_color', c_int * 3),
    ('line_width', c_int),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 84
class struct_bview_axes_state(Structure):
    pass

struct_bview_axes_state.__slots__ = [
    'draw',
    'axes_pos',
    'axes_size',
    'line_width',
    'pos_only',
    'axes_color',
    'label_color',
    'triple_color',
    'tick_enabled',
    'tick_length',
    'tick_major_length',
    'tick_interval',
    'ticks_per_major',
    'tick_threshold',
    'tick_color',
    'tick_major_color',
]
struct_bview_axes_state._fields_ = [
    ('draw', c_int),
    ('axes_pos', point_t),
    ('axes_size', fastf_t),
    ('line_width', c_int),
    ('pos_only', c_int),
    ('axes_color', c_int * 3),
    ('label_color', c_int * 3),
    ('triple_color', c_int),
    ('tick_enabled', c_int),
    ('tick_length', c_int),
    ('tick_major_length', c_int),
    ('tick_interval', fastf_t),
    ('ticks_per_major', c_int),
    ('tick_threshold', c_int),
    ('tick_color', c_int * 3),
    ('tick_major_color', c_int * 3),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 103
class struct_bview_data_axes_state(Structure):
    pass

struct_bview_data_axes_state.__slots__ = [
    'draw',
    'color',
    'line_width',
    'size',
    'num_points',
    'points',
]
struct_bview_data_axes_state._fields_ = [
    ('draw', c_int),
    ('color', c_int * 3),
    ('line_width', c_int),
    ('size', fastf_t),
    ('num_points', c_int),
    ('points', POINTER(point_t)),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 112
class struct_bview_grid_state(Structure):
    pass

struct_bview_grid_state.__slots__ = [
    'draw',
    'snap',
    'anchor',
    'res_h',
    'res_v',
    'res_major_h',
    'res_major_v',
    'color',
]
struct_bview_grid_state._fields_ = [
    ('draw', c_int),
    ('snap', c_int),
    ('anchor', fastf_t * 3),
    ('res_h', fastf_t),
    ('res_v', fastf_t),
    ('res_major_h', c_int),
    ('res_major_v', c_int),
    ('color', c_int * 3),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 123
class struct_bview_interactive_rect_state(Structure):
    pass

struct_bview_interactive_rect_state.__slots__ = [
    'active',
    'draw',
    'line_width',
    'line_style',
    'pos',
    'dim',
    'x',
    'y',
    'width',
    'height',
    'bg',
    'color',
    'cdim',
    'aspect',
]
struct_bview_interactive_rect_state._fields_ = [
    ('active', c_int),
    ('draw', c_int),
    ('line_width', c_int),
    ('line_style', c_int),
    ('pos', c_int * 2),
    ('dim', c_int * 2),
    ('x', fastf_t),
    ('y', fastf_t),
    ('width', fastf_t),
    ('height', fastf_t),
    ('bg', c_int * 3),
    ('color', c_int * 3),
    ('cdim', c_int * 2),
    ('aspect', fastf_t),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 141
class struct_bview_data_arrow_state(Structure):
    pass

struct_bview_data_arrow_state.__slots__ = [
    'gdas_draw',
    'gdas_color',
    'gdas_line_width',
    'gdas_tip_length',
    'gdas_tip_width',
    'gdas_num_points',
    'gdas_points',
]
struct_bview_data_arrow_state._fields_ = [
    ('gdas_draw', c_int),
    ('gdas_color', c_int * 3),
    ('gdas_line_width', c_int),
    ('gdas_tip_length', c_int),
    ('gdas_tip_width', c_int),
    ('gdas_num_points', c_int),
    ('gdas_points', POINTER(point_t)),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 151
class struct_bview_data_label_state(Structure):
    pass

struct_bview_data_label_state.__slots__ = [
    'gdls_draw',
    'gdls_color',
    'gdls_num_labels',
    'gdls_size',
    'gdls_labels',
    'gdls_points',
]
struct_bview_data_label_state._fields_ = [
    ('gdls_draw', c_int),
    ('gdls_color', c_int * 3),
    ('gdls_num_labels', c_int),
    ('gdls_size', c_int),
    ('gdls_labels', POINTER(POINTER(c_char))),
    ('gdls_points', POINTER(point_t)),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 160
class struct_bview_data_line_state(Structure):
    pass

struct_bview_data_line_state.__slots__ = [
    'gdls_draw',
    'gdls_color',
    'gdls_line_width',
    'gdls_num_points',
    'gdls_points',
]
struct_bview_data_line_state._fields_ = [
    ('gdls_draw', c_int),
    ('gdls_color', c_int * 3),
    ('gdls_line_width', c_int),
    ('gdls_num_points', c_int),
    ('gdls_points', POINTER(point_t)),
]

enum_anon_138 = c_int # /opt/brlcad/include/brlcad/dm/bview.h: 168

ClipType = enum_anon_138 # /opt/brlcad/include/brlcad/dm/bview.h: 168

# /opt/brlcad/include/brlcad/dm/bview.h: 173
class struct_anon_139(Structure):
    pass

struct_anon_139.__slots__ = [
    'gpc_num_points',
    'gpc_point',
]
struct_anon_139._fields_ = [
    ('gpc_num_points', c_size_t),
    ('gpc_point', POINTER(point_t)),
]

bview_poly_contour = struct_anon_139 # /opt/brlcad/include/brlcad/dm/bview.h: 173

# /opt/brlcad/include/brlcad/dm/bview.h: 182
class struct_anon_140(Structure):
    pass

struct_anon_140.__slots__ = [
    'gp_num_contours',
    'gp_color',
    'gp_line_width',
    'gp_line_style',
    'gp_hole',
    'gp_contour',
]
struct_anon_140._fields_ = [
    ('gp_num_contours', c_size_t),
    ('gp_color', c_int * 3),
    ('gp_line_width', c_int),
    ('gp_line_style', c_int),
    ('gp_hole', POINTER(c_int)),
    ('gp_contour', POINTER(bview_poly_contour)),
]

bview_polygon = struct_anon_140 # /opt/brlcad/include/brlcad/dm/bview.h: 182

# /opt/brlcad/include/brlcad/dm/bview.h: 187
class struct_anon_141(Structure):
    pass

struct_anon_141.__slots__ = [
    'gp_num_polygons',
    'gp_polygon',
]
struct_anon_141._fields_ = [
    ('gp_num_polygons', c_size_t),
    ('gp_polygon', POINTER(bview_polygon)),
]

bview_polygons = struct_anon_141 # /opt/brlcad/include/brlcad/dm/bview.h: 187

# /opt/brlcad/include/brlcad/dm/bview.h: 208
class struct_anon_142(Structure):
    pass

struct_anon_142.__slots__ = [
    'gdps_draw',
    'gdps_moveAll',
    'gdps_color',
    'gdps_line_width',
    'gdps_line_style',
    'gdps_cflag',
    'gdps_target_polygon_i',
    'gdps_curr_polygon_i',
    'gdps_curr_point_i',
    'gdps_prev_point',
    'gdps_clip_type',
    'gdps_scale',
    'gdps_origin',
    'gdps_rotation',
    'gdps_view2model',
    'gdps_model2view',
    'gdps_polygons',
    'gdps_data_vZ',
]
struct_anon_142._fields_ = [
    ('gdps_draw', c_int),
    ('gdps_moveAll', c_int),
    ('gdps_color', c_int * 3),
    ('gdps_line_width', c_int),
    ('gdps_line_style', c_int),
    ('gdps_cflag', c_int),
    ('gdps_target_polygon_i', c_size_t),
    ('gdps_curr_polygon_i', c_size_t),
    ('gdps_curr_point_i', c_size_t),
    ('gdps_prev_point', point_t),
    ('gdps_clip_type', ClipType),
    ('gdps_scale', fastf_t),
    ('gdps_origin', point_t),
    ('gdps_rotation', mat_t),
    ('gdps_view2model', mat_t),
    ('gdps_model2view', mat_t),
    ('gdps_polygons', bview_polygons),
    ('gdps_data_vZ', fastf_t),
]

bview_data_polygon_state = struct_anon_142 # /opt/brlcad/include/brlcad/dm/bview.h: 208

# /opt/brlcad/include/brlcad/dm/bview.h: 210
class struct_bview_other_state(Structure):
    pass

struct_bview_other_state.__slots__ = [
    'gos_draw',
    'gos_line_color',
    'gos_text_color',
]
struct_bview_other_state._fields_ = [
    ('gos_draw', c_int),
    ('gos_line_color', c_int * 3),
    ('gos_text_color', c_int * 3),
]

# /opt/brlcad/include/brlcad/dm/bview.h: 216
class struct_bview(Structure):
    pass

struct_bview.__slots__ = [
    'l',
    'gv_scale',
    'gv_size',
    'gv_isize',
    'gv_perspective',
    'gv_aet',
    'gv_eye_pos',
    'gv_keypoint',
    'gv_coord',
    'gv_rotate_about',
    'gv_rotation',
    'gv_center',
    'gv_model2view',
    'gv_pmodel2view',
    'gv_view2model',
    'gv_pmat',
    'gv_callback',
    'gv_clientData',
    'gv_prevMouseX',
    'gv_prevMouseY',
    'gv_minMouseDelta',
    'gv_maxMouseDelta',
    'gv_rscale',
    'gv_sscale',
    'gv_mode',
    'gv_zclip',
    'gv_adc',
    'gv_model_axes',
    'gv_view_axes',
    'gv_data_arrows',
    'gv_data_axes',
    'gv_data_labels',
    'gv_data_lines',
    'gv_data_polygons',
    'gv_sdata_arrows',
    'gv_sdata_axes',
    'gv_sdata_labels',
    'gv_sdata_lines',
    'gv_sdata_polygons',
    'gv_grid',
    'gv_center_dot',
    'gv_prim_labels',
    'gv_view_params',
    'gv_view_scale',
    'gv_rect',
    'gv_adaptive_plot',
    'gv_redraw_on_zoom',
    'gv_x_samples',
    'gv_y_samples',
    'gv_point_scale',
    'gv_curve_scale',
    'gv_data_vZ',
    'gv_bot_threshold',
]
struct_bview._fields_ = [
    ('l', struct_bu_list),
    ('gv_scale', fastf_t),
    ('gv_size', fastf_t),
    ('gv_isize', fastf_t),
    ('gv_perspective', fastf_t),
    ('gv_aet', vect_t),
    ('gv_eye_pos', vect_t),
    ('gv_keypoint', vect_t),
    ('gv_coord', c_char),
    ('gv_rotate_about', c_char),
    ('gv_rotation', mat_t),
    ('gv_center', mat_t),
    ('gv_model2view', mat_t),
    ('gv_pmodel2view', mat_t),
    ('gv_view2model', mat_t),
    ('gv_pmat', mat_t),
    ('gv_callback', CFUNCTYPE(UNCHECKED(None), )),
    ('gv_clientData', POINTER(None)),
    ('gv_prevMouseX', fastf_t),
    ('gv_prevMouseY', fastf_t),
    ('gv_minMouseDelta', fastf_t),
    ('gv_maxMouseDelta', fastf_t),
    ('gv_rscale', fastf_t),
    ('gv_sscale', fastf_t),
    ('gv_mode', c_int),
    ('gv_zclip', c_int),
    ('gv_adc', struct_bview_adc_state),
    ('gv_model_axes', struct_bview_axes_state),
    ('gv_view_axes', struct_bview_axes_state),
    ('gv_data_arrows', struct_bview_data_arrow_state),
    ('gv_data_axes', struct_bview_data_axes_state),
    ('gv_data_labels', struct_bview_data_label_state),
    ('gv_data_lines', struct_bview_data_line_state),
    ('gv_data_polygons', bview_data_polygon_state),
    ('gv_sdata_arrows', struct_bview_data_arrow_state),
    ('gv_sdata_axes', struct_bview_data_axes_state),
    ('gv_sdata_labels', struct_bview_data_label_state),
    ('gv_sdata_lines', struct_bview_data_line_state),
    ('gv_sdata_polygons', bview_data_polygon_state),
    ('gv_grid', struct_bview_grid_state),
    ('gv_center_dot', struct_bview_other_state),
    ('gv_prim_labels', struct_bview_other_state),
    ('gv_view_params', struct_bview_other_state),
    ('gv_view_scale', struct_bview_other_state),
    ('gv_rect', struct_bview_interactive_rect_state),
    ('gv_adaptive_plot', c_int),
    ('gv_redraw_on_zoom', c_int),
    ('gv_x_samples', c_int),
    ('gv_y_samples', c_int),
    ('gv_point_scale', fastf_t),
    ('gv_curve_scale', fastf_t),
    ('gv_data_vZ', fastf_t),
    ('gv_bot_threshold', c_size_t),
]

# /opt/brlcad/include/brlcad/ged/defines.h: 116
class struct_ged_run_rt(Structure):
    pass

struct_ged_run_rt.__slots__ = [
    'l',
    'fd',
    'pid',
    'aborted',
]
struct_ged_run_rt._fields_ = [
    ('l', struct_bu_list),
    ('fd', c_int),
    ('pid', c_int),
    ('aborted', c_int),
]

# /opt/brlcad/include/brlcad/ged/defines.h: 133
class struct_ged_qray_color(Structure):
    pass

struct_ged_qray_color.__slots__ = [
    'r',
    'g',
    'b',
]
struct_ged_qray_color._fields_ = [
    ('r', c_ubyte),
    ('g', c_ubyte),
    ('b', c_ubyte),
]

# /opt/brlcad/include/brlcad/ged/defines.h: 140
class struct_ged_qray_fmt(Structure):
    pass

struct_ged_qray_fmt.__slots__ = [
    'type',
    'fmt',
]
struct_ged_qray_fmt._fields_ = [
    ('type', c_char),
    ('fmt', struct_bu_vls),
]

# /opt/brlcad/include/brlcad/ged/defines.h: 145
class struct_vd_curve(Structure):
    pass

struct_vd_curve.__slots__ = [
    'l',
    'vdc_name',
    'vdc_rgb',
    'vdc_vhd',
]
struct_vd_curve._fields_ = [
    ('l', struct_bu_list),
    ('vdc_name', c_char * (31 + 1)),
    ('vdc_rgb', c_long),
    ('vdc_vhd', struct_bu_list),
]

# /opt/brlcad/include/brlcad/ged/defines.h: 154
class struct_ged_drawable(Structure):
    pass

struct_ged_drawable.__slots__ = [
    'l',
    'gd_headDisplay',
    'gd_headVDraw',
    'gd_currVHead',
    'gd_freeSolids',
    'gd_rt_cmd',
    'gd_rt_cmd_len',
    'gd_headRunRt',
    'gd_rtCmdNotify',
    'gd_uplotOutputMode',
    'gd_qray_basename',
    'gd_qray_script',
    'gd_qray_effects',
    'gd_qray_cmd_echo',
    'gd_qray_fmts',
    'gd_qray_odd_color',
    'gd_qray_even_color',
    'gd_qray_void_color',
    'gd_qray_overlap_color',
    'gd_shaded_mode',
]
struct_ged_drawable._fields_ = [
    ('l', struct_bu_list),
    ('gd_headDisplay', POINTER(struct_bu_list)),
    ('gd_headVDraw', POINTER(struct_bu_list)),
    ('gd_currVHead', POINTER(struct_vd_curve)),
    ('gd_freeSolids', POINTER(struct_solid)),
    ('gd_rt_cmd', POINTER(POINTER(c_char))),
    ('gd_rt_cmd_len', c_int),
    ('gd_headRunRt', struct_ged_run_rt),
    ('gd_rtCmdNotify', CFUNCTYPE(UNCHECKED(None), c_int)),
    ('gd_uplotOutputMode', c_int),
    ('gd_qray_basename', struct_bu_vls),
    ('gd_qray_script', struct_bu_vls),
    ('gd_qray_effects', c_char),
    ('gd_qray_cmd_echo', c_int),
    ('gd_qray_fmts', POINTER(struct_ged_qray_fmt)),
    ('gd_qray_odd_color', struct_ged_qray_color),
    ('gd_qray_even_color', struct_ged_qray_color),
    ('gd_qray_void_color', struct_ged_qray_color),
    ('gd_qray_overlap_color', struct_ged_qray_color),
    ('gd_shaded_mode', c_int),
]

# /opt/brlcad/include/brlcad/ged/defines.h: 252
class struct_ged_cmd(Structure):
    pass

# /opt/brlcad/include/brlcad/ged/defines.h: 185
class struct_ged_results(Structure):
    pass

# /opt/brlcad/include/brlcad/fb.h: 288
class struct_fbserv_obj(Structure):
    pass

# /opt/brlcad/include/brlcad/ged/defines.h: 187
class struct_ged(Structure):
    pass

struct_ged.__slots__ = [
    'l',
    'ged_wdbp',
    'ged_log',
    'freesolid',
    'ged_result_str',
    'ged_results',
    'ged_gdp',
    'ged_gvp',
    'ged_fbsp',
    'ged_selections',
    'ged_dmp',
    'ged_refresh_clientdata',
    'ged_refresh_handler',
    'ged_output_handler',
    'ged_output_script',
    'ged_create_vlist_solid_callback',
    'ged_create_vlist_callback',
    'ged_free_vlist_callback',
    'ged_internal_call',
    'cmds',
    'add',
    '_del',
    'run',
    'ged_interp',
    'ged_dm_width',
    'ged_dm_height',
    'ged_dmp_is_null',
    'ged_dm_get_display_image',
]
struct_ged._fields_ = [
    ('l', struct_bu_list),
    ('ged_wdbp', POINTER(struct_rt_wdb)),
    ('ged_log', POINTER(struct_bu_vls)),
    ('freesolid', POINTER(struct_solid)),
    ('ged_result_str', POINTER(struct_bu_vls)),
    ('ged_results', POINTER(struct_ged_results)),
    ('ged_gdp', POINTER(struct_ged_drawable)),
    ('ged_gvp', POINTER(struct_bview)),
    ('ged_fbsp', POINTER(struct_fbserv_obj)),
    ('ged_selections', POINTER(struct_bu_hash_tbl)),
    ('ged_dmp', POINTER(None)),
    ('ged_refresh_clientdata', POINTER(None)),
    ('ged_refresh_handler', CFUNCTYPE(UNCHECKED(None), POINTER(None))),
    ('ged_output_handler', CFUNCTYPE(UNCHECKED(None), POINTER(struct_ged), String)),
    ('ged_output_script', String),
    ('ged_create_vlist_solid_callback', CFUNCTYPE(UNCHECKED(None), POINTER(struct_solid))),
    ('ged_create_vlist_callback', CFUNCTYPE(UNCHECKED(None), POINTER(struct_display_list))),
    ('ged_free_vlist_callback', CFUNCTYPE(UNCHECKED(None), c_uint, c_int)),
    ('ged_internal_call', c_int),
    ('cmds', POINTER(struct_ged_cmd)),
    ('add', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_ged), POINTER(struct_ged_cmd))),
    ('_del', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_ged), String)),
    ('run', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_ged), c_int, POINTER(POINTER(c_char)))),
    ('ged_interp', POINTER(None)),
    ('ged_dm_width', c_int),
    ('ged_dm_height', c_int),
    ('ged_dmp_is_null', c_int),
    ('ged_dm_get_display_image', CFUNCTYPE(UNCHECKED(None), POINTER(struct_ged), POINTER(POINTER(c_ubyte)))),
]

struct_ged_cmd.__slots__ = [
    'l',
    'name',
    'description',
    'manpage',
    'load',
    'unload',
    '_exec',
]
struct_ged_cmd._fields_ = [
    ('l', struct_bu_list),
    ('name', String),
    ('description', c_char * 80),
    ('manpage', String),
    ('load', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_ged))),
    ('unload', CFUNCTYPE(UNCHECKED(None), POINTER(struct_ged))),
    ('_exec', CFUNCTYPE(UNCHECKED(c_int), POINTER(struct_ged), c_int, POINTER(POINTER(c_char)))),
]

# /opt/brlcad/include/tcl.h: 480
class struct_Tcl_Interp(Structure):
    pass

struct_Tcl_Interp.__slots__ = [
    'result',
    'freeProc',
    'errorLine',
]
struct_Tcl_Interp._fields_ = [
    ('result', String),
    ('freeProc', CFUNCTYPE(UNCHECKED(None), String)),
    ('errorLine', c_int),
]

Tcl_Interp = struct_Tcl_Interp # /opt/brlcad/include/tcl.h: 480

# /opt/brlcad/include/brlcad/pkg.h: 81
class struct_pkg_conn(Structure):
    pass

pkg_callback = CFUNCTYPE(UNCHECKED(None), POINTER(struct_pkg_conn), String) # /opt/brlcad/include/brlcad/pkg.h: 56

pkg_errlog = CFUNCTYPE(UNCHECKED(None), String) # /opt/brlcad/include/brlcad/pkg.h: 57

# /opt/brlcad/include/brlcad/pkg.h: 59
class struct_pkg_switch(Structure):
    pass

struct_pkg_switch.__slots__ = [
    'pks_type',
    'pks_handler',
    'pks_title',
    'pks_user_data',
]
struct_pkg_switch._fields_ = [
    ('pks_type', c_ushort),
    ('pks_handler', pkg_callback),
    ('pks_title', String),
    ('pks_user_data', POINTER(None)),
]

# /opt/brlcad/include/brlcad/pkg.h: 74
class struct_pkg_header(Structure):
    pass

struct_pkg_header.__slots__ = [
    'pkh_magic',
    'pkh_type',
    'pkh_len',
]
struct_pkg_header._fields_ = [
    ('pkh_magic', c_ubyte * 2),
    ('pkh_type', c_ubyte * 2),
    ('pkh_len', c_ubyte * 4),
]

struct_pkg_conn.__slots__ = [
    'pkc_fd',
    'pkc_switch',
    'pkc_errlog',
    'pkc_hdr',
    'pkc_len',
    'pkc_type',
    'pkc_user_data',
    'pkc_stream',
    'pkc_magic',
    'pkc_strpos',
    'pkc_inbuf',
    'pkc_incur',
    'pkc_inend',
    'pkc_inlen',
    'pkc_left',
    'pkc_buf',
    'pkc_curpos',
    'pkc_server_data',
]
struct_pkg_conn._fields_ = [
    ('pkc_fd', c_int),
    ('pkc_switch', POINTER(struct_pkg_switch)),
    ('pkc_errlog', pkg_errlog),
    ('pkc_hdr', struct_pkg_header),
    ('pkc_len', c_size_t),
    ('pkc_type', c_ushort),
    ('pkc_user_data', POINTER(None)),
    ('pkc_stream', c_char * (32 * 1024)),
    ('pkc_magic', c_uint),
    ('pkc_strpos', c_int),
    ('pkc_inbuf', String),
    ('pkc_incur', c_int),
    ('pkc_inend', c_int),
    ('pkc_inlen', c_int),
    ('pkc_left', c_int),
    ('pkc_buf', String),
    ('pkc_curpos', String),
    ('pkc_server_data', POINTER(None)),
]

# /opt/brlcad/include/brlcad/fb.h: 94
class struct_fb_internal(Structure):
    pass

fb = struct_fb_internal # /opt/brlcad/include/brlcad/fb.h: 94

# /opt/brlcad/include/brlcad/fb.h: 266
class struct_fbserv_listener(Structure):
    pass

struct_fbserv_listener.__slots__ = [
    'fbsl_fd',
    'fbsl_port',
    'fbsl_listen',
    'fbsl_fbsp',
]
struct_fbserv_listener._fields_ = [
    ('fbsl_fd', c_int),
    ('fbsl_port', c_int),
    ('fbsl_listen', c_int),
    ('fbsl_fbsp', POINTER(struct_fbserv_obj)),
]

# /opt/brlcad/include/brlcad/fb.h: 277
class struct_fbserv_client(Structure):
    pass

struct_fbserv_client.__slots__ = [
    'fbsc_fd',
    'fbsc_pkg',
    'fbsc_fbsp',
]
struct_fbserv_client._fields_ = [
    ('fbsc_fd', c_int),
    ('fbsc_pkg', POINTER(struct_pkg_conn)),
    ('fbsc_fbsp', POINTER(struct_fbserv_obj)),
]

struct_fbserv_obj.__slots__ = [
    'fbs_fbp',
    'fbs_interp',
    'fbs_listener',
    'fbs_clients',
    'fbs_callback',
    'fbs_clientData',
    'fbs_mode',
]
struct_fbserv_obj._fields_ = [
    ('fbs_fbp', POINTER(fb)),
    ('fbs_interp', POINTER(Tcl_Interp)),
    ('fbs_listener', struct_fbserv_listener),
    ('fbs_clients', struct_fbserv_client * 32),
    ('fbs_callback', CFUNCTYPE(UNCHECKED(None), POINTER(None))),
    ('fbs_clientData', POINTER(None)),
    ('fbs_mode', c_int),
]

# /opt/brlcad/include/brlcad/ged.h: 54
if hasattr(_libs['/opt/brlcad/lib/libged.dylib'], 'ged_delay'):
    ged_delay = _libs['/opt/brlcad/lib/libged.dylib'].ged_delay
    ged_delay.argtypes = [POINTER(struct_ged), c_int, POINTER(POINTER(c_char))]
    ged_delay.restype = c_int

# /opt/brlcad/include/brlcad/ged.h: 59
if hasattr(_libs['/opt/brlcad/lib/libged.dylib'], 'ged_echo'):
    ged_echo = _libs['/opt/brlcad/lib/libged.dylib'].ged_echo
    ged_echo.argtypes = [POINTER(struct_ged), c_int, POINTER(POINTER(c_char))]
    ged_echo.restype = c_int

# /opt/brlcad/include/brlcad/ged.h: 64
if hasattr(_libs['/opt/brlcad/lib/libged.dylib'], 'ged_graph'):
    ged_graph = _libs['/opt/brlcad/lib/libged.dylib'].ged_graph
    ged_graph.argtypes = [POINTER(struct_ged), c_int, POINTER(POINTER(c_char))]
    ged_graph.restype = c_int

# No inserted files

