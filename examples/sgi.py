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

def right(a, b, rcc_name, sph_name):
    global x
    old = x
    x = old + b
    draw_rcc(rcc_name, [old, y, z, x-old, 0, 0, radius], brl_db)
    draw_sphere(sph_name, [x, y, z, radius], brl_db)

def left(a, b, rcc_name, sph_name):
    global x
    old = x
    x = old - b
    draw_rcc(rcc_name, [old, y, z, x - old, 0, 0, radius], brl_db)
    draw_sphere(sph_name, [x, y, z, radius], brl_db)

def forward(a, b, rcc_name, sph_name):
    global y
    old = y
    y = old + b
    draw_rcc(rcc_name, [x, old, z, 0, y - old, 0, radius], brl_db)
    draw_sphere(sph_name, [x, y, z, radius], brl_db)

def back(a, b, rcc_name, sph_name):
    global y
    old = y
    y = old - b
    draw_rcc(rcc_name, [x, old, z, 0, y - old, 0, radius], brl_db)
    draw_sphere(sph_name, [x, y, z, radius], brl_db)

def up(a, b, rcc_name, sph_name):
    global z
    old = z
    z = old + b
    draw_rcc(rcc_name, [x, y, old, 0, 0, z - old, radius], brl_db)
    draw_sphere(sph_name, [x, y, z, radius], brl_db)

def down(a, b, rcc_name, sph_name):
    global z
    old = z
    z = old - b
    draw_rcc(rcc_name, [x, y, old, 0, 0, z - old, radius], brl_db)
    draw_sphere(sph_name, [x, y, z, radius], brl_db)

if __name__ == "__main__":
    argv = sys.argv
    database_name = argv[1]
    # cube dimensions
    i, j, radius = 1000, 800, 100
    # starting position
    x, y, z = 0, 0, 0
    brl_db = wdb.WDB(database_name, "SGI.g")
    rcc_name_list, sph_name_list, union_list = [], [], []

    for iterator in range (100, 118):
        rcc_name, sph_name = "rcc." + str(iterator), "sph." + str(iterator)
        rcc_name_list.append(rcc_name)
        sph_name_list.append(sph_name)
        union_list.extend((rcc_name, sph_name))

    forward(100, i, rcc_name_list[0], sph_name_list[0])
    left(101, j, rcc_name_list[1], sph_name_list[1])
    down(102, i, rcc_name_list[2], sph_name_list[2])
    right(103, i, rcc_name_list[3], sph_name_list[3])
    up(104, j, rcc_name_list[4], sph_name_list[4])
    back(105, i, rcc_name_list[5], sph_name_list[5])
    down(106, i, rcc_name_list[6], sph_name_list[6])
    forward(107, i, rcc_name_list[7], sph_name_list[7])
    left(108, i, rcc_name_list[8], sph_name_list[8])
    back(109, i, rcc_name_list[9], sph_name_list[9])
    right(110, j, rcc_name_list[10], sph_name_list[10])
    up(111, i, rcc_name_list[11], sph_name_list[11])
    left(112, i, rcc_name_list[12], sph_name_list[12])
    down(113, j, rcc_name_list[13], sph_name_list[13])
    forward(114, i, rcc_name_list[14], sph_name_list[14])
    up(115, i, rcc_name_list[15], sph_name_list[15])
    back(116, j, rcc_name_list[16], sph_name_list[16])
    right(117, i, rcc_name_list[17], sph_name_list[17])

    brl_db.combination(
            "cube.r",
            is_region=True,
            tree=union(union_list),
            shader="plastic {di=.8 sp=.2}",
            rgb_color=(64, 180, 96)
        )