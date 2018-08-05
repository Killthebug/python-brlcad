from brlcad.procedural import *
import brlcad.geometry as geometry

def main():
	draw_tgc('tgc1.s', [0, -7, 7,
					   0, 0, 1,
					   0.5, 0, 0,
					   0, 1, 0,
					   1, 0, 0,
					   0, 0.5, 0], brl_db)

	draw_tgc('tgc2.s', [0, -10.5, 7,
					   0, 0, 1,
					   1, 0, 0,
					   0, 1, 0,
					   1, 0, 0,
					   0, 1, 0], brl_db)

	draw_tgc('tgc3.s', [0, -8.5, 10,
					   0, 0, 3,
					   1, 0, 0,
					   0, 0.5, 0,
					   1, 0, 0,
					   0, 0.5, 0], brl_db)

	draw_tgc('tgc4.s', [0, -12, 10,
					   0, 0, 3,
					   1, 0, 0,
					   0, 0.5, 0,
					   3, 0, 0,
					   0, 0.5, 0], brl_db)

	draw_rcc('rcc1.s', [-2, -2, 0,
					   0, 0, 5,
					   1], brl_db)

	draw_rcc('rcc2.s', [1, 5, 5,
					   0, 0, 10,
					   0.1], brl_db)

	draw_rcc('rcc3.s', [1, 7, 5,
					   0, 0, 0.5,
					   1], brl_db)

	draw_rhc('rhc.s', [0, -10, -5,
					  0, 0, 0.5,
					  0.25, 0.25, 0,
					  0.75, 0.1], brl_db)

	draw_rhc('rhc.s', [0, -10, -5,
					  0, 0, 0.5,
					  0.25, 0.25, 0,
					  0.75, 0.1], brl_db)

	draw_rhc('rhc2.s', [0, -13, -5,
					  0, 0, 5,
					  0.9, 0.1, 0,
					  1, 0.1], brl_db)

	draw_rhc('rhc3.s', [0, -16, -5,
					  0, 1, 0,
					  0.9, 0, 1,
					  1, 0.5], brl_db)

	draw_rhc('rhc4.s', [0, -13, -8,
					  0, 0, 1,
					  0.9, 0.1, 0,
					  5, 0.1], brl_db)



if __name__ == '__main__':
	argv = sys.argv
	database_name = argv[1]
	brl_db = geometry.Database(database_name, "SGI.g")
	main()