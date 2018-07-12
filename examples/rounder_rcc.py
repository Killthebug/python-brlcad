"""
This is the python version of sgi.sh using the python-brlcad module.

usage:
    python sgi.py sgi.g
To Render : 
    rtedge -s 1024 -F output.pix sgi.g cube.r
    pix-png -s 1024 < output.pix > output.png
"""

import sys
from brlcad.primitives import union
from draw_primitive import *
import brlcad.wdb as wdb

def rounder_rcc(c_radius, c_length, rounding_radius):
    origin = (0, 0, 0)
    base   = (0, 0, rounding_radius)
    filler = (0, 0, c_length)
    top_tor = (0, 0, c_length - rounding_radius)
    height = (0, 0, c_length - 2 * rounding_radius)
    neg_z_dir, pos_z_dir = (0, 0, -1), (0, 0, 1)
    brl_db.rcc("cylinder.rcc", base, height, c_radius)
    brl_db.rcc("fillend.rcc", origin, filler, c_radius - rounding_radius)
    brl_db.torus("bottom.tor", base, neg_z_dir, c_radius - rounding_radius, rounding_radius)
    brl_db.torus("top.tor", top_tor, pos_z_dir, c_radius - rounding_radius, rounding_radius)
    union_list = ["cylinder.rcc", "fillend.rcc", "top.tor", "bottom.tor"]
    brl_db.combination(
        "cube.r",
        is_region=False,
        tree=union(union_list)
    )

   
if __name__ == "__main__":
    argv = sys.argv
    union_list = []
    database_name = argv[1]
    brl_db = wdb.WDB(database_name, "fml.g")
    rounder_rcc(40, 100, 10)
