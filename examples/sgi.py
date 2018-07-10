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

import brlcad.wdb as wdb

def right(a, b):
    global x
    old = x
    x = old + b
    rcc_name, sph_name = "rcc." + str(a), "sph." + str(a)
    name_tracker.extend((rcc_name, sph_name))
    brl_db.rcc(rcc_name, base = (old, y, z), height = (x - old, 0, 0), radius = radius)
    brl_db.sphere(sph_name, center = (x, y, z), radius = radius)

def left(a, b):
    global x
    old = x
    x = old - b
    rcc_name, sph_name = "rcc." + str(a), "sph." + str(a)
    name_tracker.extend((rcc_name, sph_name))
    brl_db.rcc(rcc_name, base = (old, y, z), height = (x - old, 0, 0), radius = radius)
    brl_db.sphere(sph_name, center = (x, y, z), radius = radius)
    return

def forward(a, b):
    global y
    old = y
    y = old + b
    rcc_name, sph_name = "rcc." + str(a), "sph." + str(a)
    name_tracker.extend((rcc_name, sph_name))
    brl_db.rcc(rcc_name, base = (x, old, z), height = (0, y - old, 0), radius = radius)
    brl_db.sphere(sph_name, center = (x, y, z), radius = radius)
    return

def back(a, b):
    global y
    old = y
    y = old - b
    rcc_name, sph_name = "rcc." + str(a), "sph." + str(a)
    name_tracker.extend((rcc_name, sph_name))
    brl_db.rcc(rcc_name, base = (x, old, z), height = (0, y - old, 0), radius = radius)
    brl_db.sphere(sph_name, center = (x, y, z), radius = radius)
    return

def up(a, b):
    global z
    old = z
    z = old + b
    rcc_name, sph_name = "rcc." + str(a), "sph." + str(a)
    name_tracker.extend((rcc_name, sph_name))
    brl_db.rcc(rcc_name, base = (x, y, old), height = (0, 0, z - old), radius = radius)
    brl_db.sphere(sph_name, center = (x, y, z), radius = radius)
    return

def down(a, b):
    global z
    old = z
    z = old - b
    rcc_name, sph_name = "rcc." + str(a), "sph." + str(a)
    name_tracker.extend((rcc_name, sph_name))
    brl_db.rcc(rcc_name, base = (x, y, old), height = (0, 0, z - old), radius = radius)
    brl_db.sphere(sph_name, center = (x, y, z), radius = radius)
    return

if __name__ == "__main__":
    argv = sys.argv
    database_name = argv[1]
    name_tracker = []
    
    # cube dimensions
    i, j, radius = 1000, 800, 100

    # starting position
    x, y, z = 0, 0, 0
    
    brl_db = wdb.WDB(database_name, "SGI.g")

    forward(100, i)
    left(101, j)
    down(102, i)
    right(103, i)
    up(104, j)
    back(105, i)
    down(106, i)
    forward(107, i)
    left(108, i)
    back(109, i)
    right(110, j)
    up(111, i)
    left(112, i)
    down(113, j)
    forward(114, i)
    up(115, i)
    back(116, j)
    right(117, i)

    print(name_tracker)

    union_list = []

    for element in name_tracker:
        if "rcc" in element or "sph" in element:
            union_list.append(element)

    brl_db.combination(
            "cube.r",
            is_region=True,
            tree=union(union_list),
            shader="cook {re=.8 di=2 sp=1 ri=10}",
            rgb_color=(250, 250, 250)
        )
