import sys
from brlcad.primitives import union

def draw_sphere(primitive_name, arguments, brl_db):
	center = [float(x) for x in arguments[:3]]
	radius = float(arguments[3])
	brl_db.sphere(primitive_name, center, radius)
	return

def draw_rpp(primitive_name, arguments, brl_db):
	pmin = [float(x) for x in arguments[:3]]
	pmax = [float(x) for x in arguments[3:]]
	brl_db.rpp(primitive_name, pmin, pmax)
	return

def draw_wedge(primitive_name, arguments, brl_db):
	vertex = [float(x) for x in arguments[:3]]
	x_dir  = [float(x) for x in arguments[3:6]]
	z_dir  = [float(x) for x in arguments[6:9]]
	x_len, y_len, z_len, x_top_len = arguments[9:]
	brl_db.wedge(primitive_name, vertex, x_dir, z_dir,
				 x_len, y_len, z_len, x_top_len)
	return

def draw_arb4(primitive_name, arguments, brl_db):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:]]
	brl_db.arb4(primitive_name, [v1, v2, v3, v4])
	return

def draw_arb5(primitive_name, arguments, brl_db):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:]]
	brl_db.arb5(primitive_name, [v1, v2, v3, v4, v5])
	return

def draw_arb6(primitive_name, arguments, brl_db):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:15]]
	v6 = [float(x) for x in arguments[15:]]
	brl_db.arb6(primitive_name, [v1, v2, v3, v4, v5, v6])
	return

def draw_arb7(primitive_name, arguments, brl_db):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:15]]
	v6 = [float(x) for x in arguments[15:18]]
	v7 = [float(x) for x in arguments[18:]]	
	brl_db.arb7(primitive_name, [v1, v2, v3, v4, v5, v6, v7])
	return

def draw_arb8(primitive_name, arguments, brl_db):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:15]]
	v6 = [float(x) for x in arguments[15:18]]
	v7 = [float(x) for x in arguments[18:21]]
	v8 = [float(x) for x in arguments[21:]]
	brl_db.arb8(primitive_name, [v1, v2, v3, v4, v5, v6, v7, v8])
	return

def draw_ellipsoid(primitive_name, arguments, brl_db):
	center = [float(x) for x in arguments[:3]]
	a	  = [float(x) for x in arguments[3:6]]
	b	  = [float(x) for x in arguments[6:9]]
	c	  = [float(x) for x in arguments[9:]]
	brl_db.ellipsoid(primitive_name, center, a, b, c)
	return

def draw_torus(primitive_name, arguments, brl_db):
	center = [float(x) for x in arguments[:3]]
	n	  = [float(x) for x in arguments[3:6]]
	r_revolution = float(arguments[6])
	r_cross	  = float(arguments[7])
	brl_db.torus(primitive_name, center, n,
				 r_revolution, r_cross)
	return

def draw_rcc(primitive_name, arguments, brl_db):
	base   = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	radius = arguments[6]
	brl_db.rcc(primitive_name, base, height, radius)
	return

def draw_tgc(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	a = [float(x) for x in arguments[6:9]]
	b = [float(x) for x in arguments[9:12]]
	c = [float(x) for x in arguments[12:15]]
	d = [float(x) for x in arguments[15:]]
	brl_db.tgc(primitive_name, base, height, a, b, c, d)
	return

def draw_cone(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	n	= [float(x) for x in arguments[3:6]]
	h, r_base, r_top = [float(x) for x in arguments[6:]]
	brl_db.cone(primitive_name, base, n, h, r_base, r_top)
	return

def draw_trc(primitive_name, arguments, brl_db):
	print(arguments)
	print(len(arguments))
	print("DEBUG")
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	r_base, r_top = [float(x) for x in arguments[6:]]
	brl_db.trc(primitive_name, base, height, r_base, r_top)
	return

def draw_rpc(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	breadth = [float(x) for x in arguments[6:9]]
	half_width = arguments[9]
	brl_db.rpc(primitive_name, base, height, breadth, half_width)
	return

def draw_rhc(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	breadth = [float(x) for x in arguments[6:9]]
	half_width, asymptote = [float(x) for x in arguments[9:]]
	brl_db.rhc(primitive_name, base, height, breadth, half_width, asymptote)
	return

def draw_epa(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	n_major = [float(x) for x in arguments[6:9]]
	r_major, r_minor = [float(x) for x in arguments[9:]]
	brl_db.epa(primitive_name, base, height, n_major, r_major, r_minor)
	return

def draw_ehy(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	n_major = [float(x) for x in arguments[6:9]]
	r_major, r_minor, asymptote = [float(x) for x in arguments[9:]]
	brl_db.ehy(primitive_name, base, height, n_major,
			   r_major, r_minor, asymptote)
	return

def draw_hyperboloid(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	a = [float(x) for x in arguments[6:9]]
	b_mag, base_neck_ratio = [float(x) for x in arguments[9:]]
	brl_db.hyperboloid(primitive_name, base, height, a,
					   b_mag, base_neck_ratio)
	return

def draw_eto(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	n = [float(x) for x in arguments[3:6]]
	s_major = [float(x) for x in arguments[6:9]]
	r_revolution, r_minor = [float(x) for x in arguments[9:]]
	brl_db.eto(primitive_name, base, n, s_major,
			   r_revolution, r_minor)
	return

def draw_arbn(primitive_name, arguments, brl_db):
	plane_1 = [tuple([float(x) for x in arguments[:3]])]
	plane_1.append(float(arguments[3]))
	plane_2 = [tuple([float(x) for x in arguments[4:7]])]
	plane_2.append(float(arguments[7]))
	plane_3 = [tuple([float(x) for x in arguments[8:11]])]
	plane_3.append(float(arguments[11]))
	plane_4 = [tuple([float(x) for x in arguments[12:15]])]
	plane_4.append(float(arguments[15]))
	plane_5 = [tuple([float(x) for x in arguments[16:19]])]
	plane_5.append(float(arguments[19]))
	plane_6 = [tuple([float(x) for x in arguments[20:23]])]
	plane_6.append(float(arguments[23]))
	planes = [plane_1, plane_2, plane_3, plane_4, plane_5, plane_6]
	brl_db.arbn(primitive_name, planes)
	return

def draw_particle(primitive_name, arguments, brl_db):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	r_base, r_end = arguments[6:]
	brl_db.particle(primitive_name, base, height, r_base, r_end)
	return

def draw_half(primitive_name, arguments, brl_db):
	normal = [float(x) for x in arguments[:3]]
	distance = float(arguments[3])
	brl_db.half(primitive_name, normal, distance)
	return

def draw_pipe(primitive_name, arguments, brl_db):
	point_1 = [tuple(float(x) for x in arguments[:3])]
	for y in range(3):
		point_1.append(float(arguments[3+y]))
	point_2 = [tuple(float(x) for x in arguments[6:9])]
	for y in range(3):
		point_2.append(float(arguments[9+y]))
	point_3 = [tuple(float(x) for x in arguments[12:15])]
	for y in range(3):
		point_3.append(float(arguments[15+y]))
	point_4 = [tuple(float(x) for x in arguments[18:21])]
	for y in range(3):
		point_4.append(float(arguments[21+y]))
	point_5 = [tuple(float(x) for x in arguments[24:27])]
	for y in range(3):
		point_5.append(float(arguments[27+y]))
	point_6 = [tuple(float(x) for x in arguments[30:33])]
	for y in range(3):
		point_6.append(float(arguments[33+y]))
	point_7 = [tuple(float(x) for x in arguments[36:39])]
	for y in range(3):
		point_7.append(float(arguments[39+y]))
	point_8 = [tuple(float(x) for x in arguments[42:45])]
	for y in range(3):
		point_8.append(float(arguments[45+y]))
	point_9 = [tuple(float(x) for x in arguments[48:51])]
	for y in range(3):
		point_9.append(float(arguments[51+y]))
	point_10 = [tuple(float(x) for x in arguments[54:57])]
	for y in range(3):
		point_10.append(float(arguments[57+y]))

	points = [point_1, point_2, point_3, point_4, point_5, 
			  point_6, point_7, point_8, point_9, point_10]

	brl_db.pipe(primitive_name, points)