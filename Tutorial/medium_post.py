from brlcad.vmath import Transform
from brlcad.geometry import Database
from brlcad import primitives
from brlcad.primitives.sketch import *

def main():
	brl_db = Database("test_wdb.g", "Test BRLCAD DB file")
	brl_db.sphere("sph1.s", center=(0.5, 5, 8), radius=0.75)
	brl_db.region(
            'sph.r',
            region_id = 16,
            tree = 'sph1.s',
            shader="plastic {di .9 sp .4}",
            rgb_color=(153,0,0)
            )


if __name__ == "__main__":
	main()