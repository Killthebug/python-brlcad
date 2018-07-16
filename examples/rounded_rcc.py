"""
Run : python rounded_rcc.py <<db>>.g
"""

import sys
from brlcad.primitives import union
from draw_primitive import *
import brlcad.wdb as wdb

def sanity_check(c_radius, c_length, rounding_radius):
    if rounding_radius > c_radius/2:
        raise ValueError("Rounding Radius cannot be larger than 0.5 * Cylinder Radius")
        exit()
    if rounding_radius > c_length/2:
        raise ValueError("Rounding Radius cannot be larger than 0.5 * Cylinder Height")
        exit()

def rounder_rcc(c_radius, c_length, rounding_radius):
    sanity_check(c_radius, c_length, rounding_radius)
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
        "cylinder3.r",
        is_region=False,
        tree=union(union_list)
    )

   
if __name__ == "__main__":
    argv = sys.argv
    union_list = []
    database_name = argv[1]
    brl_db = wdb.WDB(database_name, "fml.g")
    rounder_rcc(40, 100, 21)