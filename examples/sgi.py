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
    union_list = []
    database_name = argv[1]
    # cube dimensions
    i, j, radius = 1000, 800, 100
    # starting position
    x, y, z = 0, 0, 0
    brl_db = wdb.WDB(database_name, "SGI.g")
    forward_list, back_list = [100, 107, 114], [105, 109, 116]
    up_list, down_list      = [104, 111, 115], [102, 106, 113]
    right_list, left_list   = [103, 110, 117], [101, 108, 112]

    for iterator in range (100, 118):
        rcc_name, sph_name = "rcc." + str(iterator), "sph." + str(iterator)
        union_list.extend((rcc_name, sph_name))
        if iterator in forward_list:
            forward(iterator, i, rcc_name, sph_name)
        if iterator in back_list:
            back(iterator, i, rcc_name, sph_name)
        if iterator in up_list:
            up(iterator, i, rcc_name, sph_name)
        if iterator in down_list:
            down(iterator, i, rcc_name, sph_name)
        if iterator in right_list:
            right(iterator, i, rcc_name, sph_name)
        if iterator in left_list:
            left(iterator, i, rcc_name, sph_name)

    brl_db.combination(
            "cube.r",
            is_region=True,
            tree=union(union_list),
            shader="plastic {di=.8 sp=.2}",
            rgb_color=(64, 180, 96)
        )