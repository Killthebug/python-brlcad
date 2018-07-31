from brlcad.procedural import *
import brlcad.geometry as geometry

def main():
	'''
	Given below are examples of drawing primitives using the abstract method

	All the draw_primitive function follow a similar syntax :

		draw_primitveName(primitive_name, [list_of_arguments], db_name)

	'''

	draw_sphere('sph.s', [1, 2, 3, 0.75], brl_db)
	
	draw_rpp('rpp.s', [0, 0, 0, 2, 4, 2.5], brl_db)
	
	draw_wedge('wedge.s', [0, 0, 3.5, 
						   0, 1, 0, 
						   0, 0, 1, 
						   4, 2, 1, 
						   3], brl_db)
	
	draw_arb4('arb4.s', [-1, -5, 3, 
						  1, -5, 3, 
						  1, -3, 4, 
						  0, -4, 5], brl_db)

	draw_arb5('arb5.s', [-1, -5, 0, 
						  1, -5, 0, 
						  1, -3, 0, 
						  -1, -3, 0, 
						  0, -4, 3], brl_db)
	
	draw_arb6('arb6.s', [-1, -2.5, 0, 1, 
						-2.5, 0, 1, -0.5, 
						0, -1, -0.5, 0, 
						0, -2.5, 2.5, 
						0, -0.5, 2.5], brl_db)
	
	draw_arb7('arb7.s', [-1, -2.5, 3, 
						  1, -2.5, 3, 
						  1, -0.5, 3, 
						  -1, -1.5, 3, 
						  -1, -2.5, 5,
						  1, -2.5, 5,
						  1, -1.5, 5], brl_db)
	
	draw_arb8('arb8.s', [-1, -1, 5, 
						  1, -1, 5, 
						  1, 1, 5, 
						  -1, 1, 5,
                		  -0.5, -0.5, 6.5, 
                		  0.5, -0.5, 6.5, 
                		  0.5, 0.5, 6.5, 
                		  -0.5, 0.5, 6.5], brl_db)
	
	draw_ellipsoid('ellipsoid.s', [0, -4, 6,
								   0.75, 0, 0,
								   0, 1, 0,
								   0, 0, 0.5], brl_db)
	
	draw_torus('torus.s', [0, -2, 6,
						   0, 0, 1, 
						   1, 0.25], brl_db)

	draw_rcc('rcc.s', [1, 2, 5,
					   0, 0, 1,
					   1], brl_db)
	
	draw_tgc('tgc.s', [0, -5, 7,
					   0, 0, 1,
					   0.5, 0, 0,
					   0, 1, 0,
					   1, 0, 0,
					   0, 0.5, 0], brl_db)

	draw_cone('cone.s', [0, -2, 7,
						 0, 0, 2,
						 0.5, 1.25, 0.75], brl_db)

	draw_trc('trc.s', [0, -2, 7.5,
					   0, 0, 0.5,
					   0.75, 1.25], brl_db)
	
	draw_rpc('rpc.s', [0, -2, 8.5,
					   0, 0, 0.5,
					   0.25, 0.25, 0,
					   0.75], brl_db)
	
	draw_rhc('rhc.s',[0, -2, 9,
					  0, 0, 0.5,
					  0.25, 0.25, 0,
					  0.75, 0.1], brl_db)
	
	draw_epa('epa.s', [1, 2, 7,
					   0, 0, -1,
					   1, 0, 0,
					   1, 0.5], brl_db)
	
	draw_ehy('ehy.s', [1, 2, 7,
					   0, 0, 1,
					   1, 0, 0,
					   1, 0.5, 0.1], brl_db)
	
	draw_hyperboloid('hyperbolid.s', [0, 0, 6.75,
									  0, 0, 0.75,
									  1, 0, 0,
									  0.5, 0.3], brl_db)
	
	draw_eto('eto.s', [1, 2, 8.5,
					   0, 0, 1,
					   0.5, 0, 0.5,
					   1, 0.25], brl_db)
	
	draw_arbn('arbn.s', [0, 0, -1, -8,
						 0, 0, 1, 9,
						 -1, 0, 0, 0.5,
						 1, 0, 0, 0.5,
						 0, -1, 0, 0.5,
						 0, 1, 0, 0.5], brl_db)
	
	draw_particle('particle.s', [0, -5, 8.5,
								 0, 0, 0.75,
								 0.25, 0.5], brl_db)
	
	draw_pipe('pips.s',[0.55, 4, 5.45, 0.1, 0, 0.45,
                0.55, 3.55, 5.4875, 0.1, 0, 0.45,
                1.45, 3.55, 5.5625, 0.1, 0, 0.45,
                1.45, 4.45, 5.6375, 0.1, 0, 0.45,
                0.55, 4.45, 5.7125, 0.1, 0, 0.45,
                0.55, 3.55, 5.7875, 0.1, 0, 0.45,
                1.45, 3.55, 5.8625, 0.1, 0, 0.45,
                1.45, 4.45, 5.9375, 0.1, 0, 0.45,
                0.55, 4.45, 6.0125, 0.1, 0, 0.45,
                0.55, 4, 6.05, 0.1, 0, 0.45], brl_db)

	draw_half('half.s', [0, 1, 0, 0], brl_db)

	return

if __name__ == '__main__':
	argv = sys.argv
	database_name = argv[1]
	brl_db = geometry.Database(database_name, "SGI.g")
	main()