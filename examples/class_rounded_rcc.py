"""
Run : python rounded_rcc.py <<db>>.g
"""

import sys
from brlcad.primitives import union
from draw_primitive import *
import brlcad.wdb as wdb

class rounded_rcc():
    def __init__(self, brl_db, inmem):
        '''
        Here is where we could deal with inmem db.
        inmem could be true or false
        '''
        self.brl_db = brl_db
        self.inmem  = inmem

    def sanity_check(self, c_radius, c_length, rounding_radius):
        if rounding_radius > c_radius/2:
            raise ValueError("Rounding Radius cannot be larger than 0.5 * Cylinder Radius")
            exit()
        if rounding_radius > c_length/2:
            raise ValueError("Rounding Radius cannot be larger than 0.5 * Cylinder Height")
            exit()

    def create(self, c_radius, c_length, rounding_radius):
        self.sanity_check(c_radius, c_length, rounding_radius)
        origin = (0, 0, 0)
        base   = (0, 0, rounding_radius)
        filler = (0, 0, c_length)
        top_tor = (0, 0, c_length - rounding_radius)
        height = (0, 0, c_length - 2 * rounding_radius)
        neg_z_dir, pos_z_dir = (0, 0, -1), (0, 0, 1)
        self.brl_db.rcc("cylinder.rcc", base, height, c_radius)
        self.brl_db.rcc("fillend.rcc", origin, filler, c_radius - rounding_radius)
        self.brl_db.torus("bottom.tor", base, neg_z_dir, c_radius - rounding_radius, rounding_radius)
        self.brl_db.torus("top.tor", top_tor, pos_z_dir, c_radius - rounding_radius, rounding_radius)
        union_list = ["cylinder.rcc", "fillend.rcc", "top.tor", "bottom.tor"]
        self.brl_db.combination(
            "cylinder3.r",
            is_region=False,
            tree=union(union_list)
        )

   
if __name__ == "__main__":
    argv = sys.argv
    union_list = []
    database_name = argv[1]
    brl_db = wdb.WDB(database_name, "fml.g")
    myObject = rounded_rcc(brl_db)
    myObject.create(50, 220, 21)