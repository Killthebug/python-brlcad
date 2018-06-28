'''
This is a python module that deals with tcl scripts to create procedural geometry

Usage :
		python script.py <<script_name>>.tcl <<database_name>>.g

Assumptions :
** Global vars are all defined before all commands
** There are no undefined varaibles referenced anywhere in the script
** All global variables are defined the first proc definition
** 

How the script parser works :
** Read script
** Parse global variables
** Parse proc (procedures)
	** Every proc is an object of the procedure class (proc_interpreter.py)
	** Intialization takes place with proc_name and global vars passed to the object
** Parse in commands and proc calls in parallel
** Proc calls:
	** Substitue value of of global vars in commands in procs
	** Calculate value of local variables
		** Value of local variables can depend on global variables or passed arguments
	** Replace all variables in the proc with their constant values
	** Return a list of commands (Eg : in sph.s sph ...) from the prob objects
** In a serial order draw all the shapes as required from this script module.
'''

import argparse
import errno
import sys
import os
import brlcad.wdb as wdb
from brlcad.primitives import *

global_vars = {}
script_procedures  = {}

def index_containing_substring(the_list, substring):
	for i, s in enumerate(the_list):
		if substring in s:
			  return i
	return -1

def parse_var(command):
	var_name = "$"+str(command[1])
	var_val  = float(command[2])
	global_vars[var_name] = var_val
	return

def check_vars(command):
	'''
	The +3 here is to account for the first three words in a tcl command
	Eg : 
	set i 1
	set j 5
	in ball.s sph i 2 j 0.75

	would return
	in ball.s sph 1 2 5 0.75
	'''
	for iterator in range(len(command[3:])):
		if str(command[iterator+3]) in global_vars:
			command[iterator+3] = global_vars[str(command[iterator+3])]

def initalize_global_vars(commands):
	first_proc_line = index_containing_substring(commands, "proc")
	for iterator in range(0, first_proc_line):
		element = commands[iterator]
		element = element.split()
		if element == []:			#Blank line
			continue
		command_type = element[0]
		if command_type == "set": 
			switcher[command_type](element)
	print(global_vars)				#debug

def create_proc_objects(proc_list):
	for element in proc_list:
		temp_list = element.split("\n")[0]
		proc_name = temp_list.split()[1]
		proc_args = temp_list.split("{")[1].split('}')[0].split()
		print(proc_args)											#debug
		script_procedures[proc_name] = Procedure(proc_name, proc_args, global_vars)

def parse_procs(commands, proc_line_position):
	proc_list = []
	print(proc_line_position)
	for iterator in range(len(proc_line_position)):
		proc_start = proc_line_position[iterator]

		if iterator != len(proc_line_position) - 1 :  #Checking if this is the last proc defintion
			proc_end = proc_line_position[iterator + 1]
			proc_span = commands[proc_start : proc_end]
		else :
			proc_end = -1
			proc_span = commands[proc_start:]

		proc_string = " ".join(proc_span)
		print(proc_string.strip())				#debug
		proc_list.append(proc_string.strip())
	return proc_list

def initialize_procs(commands):
	"""
	Here we iterate over the script based on line numbers
	because we're uncertain about how big/small a proc is
	and we'll need to be skipping multiple lines after we
	parse each proc
	"""
	proc_line_position = []  		#Keeps tracks of lines numbers of proc definiton
	
	for iterator in range(len(commands)):
		element = commands[iterator].split()
		if element == []:			#Blank line
			continue
		command_type = element[0]
		if command_type == "proc":
			proc_line_position.append(iterator)

	proc_list = parse_procs(commands, proc_line_position)
	create_proc_objects(proc_list)

def parse_combination():
	return

def argument_check():
	return

def primitive_union():
	return

def read_file(filename):
	if not os.path.isfile(filename):
		raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
	file = open(filename).readlines()
	return file


def parse_primitive(command):
	primitive_name = command[1]
	primitive_type = command[2]
	check_vars(command)					#Replace any variables with constants
	print(command)
	'''
	Further functionality to parse variables will be included before this
	step. To the draw_primitive function, only pure arguments will be
	send, not variable
	'''
	primitive_map[primitive_type](primitive_name, command[3:])


def parse_script(database_name, units, commands):
	initalize_global_vars(commands)
	initialize_procs(commands)
	exit()

	for element in commands:
		element = element.split()
		command_type = element[0]
		switcher[command_type](element)

def draw_sphere(primitive_name, arguments):
	center = [float(x) for x in arguments[:3]]
	radius = float(arguments[3])
	brl_db.sphere(primitive_name, center, radius)
	return

def draw_rpp(primitive_name, arguments):
	pmin = [float(x) for x in arguments[:3]]
	pmax = [float(x) for x in arguments[3:]]
	brl_db.rpp(primitive_name, pmin, pmax)
	return

def draw_wedge(primitive_name, arguments):
	vertex = [float(x) for x in arguments[:3]]
	x_dir  = [float(x) for x in arguments[3:6]]
	z_dir  = [float(x) for x in arguments[6:9]]
	x_len, y_len, z_len, x_top_len = arguments[9:]
	brl_db.wedge(primitive_name, vertex, x_dir, z_dir,
				 x_len, y_len, z_len, x_top_len)
	return

def draw_arb4(primitive_name, arguments):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:]]
	brl_db.arb4(primitive_name, v1, v2, v3, v4)
	return

def draw_arb5(primitive_name, arguments):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:]]
	brl_db.arb5(primitive_name, v1, v2, v3, v4, v5)
	return

def draw_arb6(primitive_name, arguments):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:15]]
	v6 = [float(x) for x in arguments[15:]]
	brl_db.arb6(primitive_name, v1, v2, v3, v4, v5, v6)
	return

def draw_arb7(primitive_name, arguments):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:15]]
	v6 = [float(x) for x in arguments[15:18]]
	v7 = [float(x) for x in arguments[18:]]	
	brl_db.arb7(primitive_name, v1, v2, v3, v4, v5, v6, v7)
	return

def draw_arb8(primitive_name, arguments):
	v1 = [float(x) for x in arguments[:3]]
	v2 = [float(x) for x in arguments[3:6]]
	v3 = [float(x) for x in arguments[6:9]]
	v4 = [float(x) for x in arguments[9:12]]
	v5 = [float(x) for x in arguments[12:15]]
	v6 = [float(x) for x in arguments[15:18]]
	v7 = [float(x) for x in arguments[18:21]]
	v8 = [float(x) for x in arguments[21:]]
	brl_db.arb8(primitive_name, v1, v2, v3, v4, v5, v6, v7, v8)
	return

def draw_ellipsoid(primitive_name, arguments):
	center = [float(x) for x in arguments[:3]]
	a	  = [float(x) for x in arguments[3:6]]
	b	  = [float(x) for x in arguments[6:9]]
	c	  = [float(x) for x in arguments[9:]]
	brl_db.ellipsoid(primitive_name, center, a, b, c)
	return

def draw_torus(primitive_name, arguments):
	center = [float(x) for x in arguments[:3]]
	n	  = [float(x) for x in arguments[3:6]]
	r_revolution = float(arguments[6])
	r_cross	  = float(arguments[7])
	brl_db.torus(primitive_name, center, n,
				 r_revolution, r_cross)
	return

def draw_rcc(primitive_name, arguments):
	base   = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	radius = arguments[6]
	brl_db.rcc(primitive_name, base, height, radius)
	return

def draw_tgc(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	a = [float(x) for x in arguments[6:9]]
	b = [float(x) for x in arguments[9:12]]
	c = [float(x) for x in arguments[12:15]]
	d = [float(x) for x in arguments[15:]]
	brl_db.tgc(primitive_name, base, height, a, b, c, d)
	return

def draw_cone(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	n	= [float(x) for x in arguments[3:6]]
	h, r_base, r_top = [float(x) for x in arguments[6:]]
	brl_db.cone(primitive_name, base, n, h, r_base, r_top)
	return

def draw_trc(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	r_base, r_top = [float(x) for x in arguments[6:]]
	brl_db.trc(primitive_name, base, height, r_base, r_top)
	return

def draw_rpc(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	breadth = [float(x) for x in arguments[6:9]]
	half_width = arguments[9]
	brl_db.rpc(primitive_name, base, height, breadth, half_width)
	return

def draw_rhc(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	breadth = [float(x) for x in arguments[6:9]]
	half_width, asymptote = [float(x) for x in arguments[9:]]
	brl_db.rhc(primitive_name, base, height, breadth, half_width, asymptote)
	return

def draw_epa(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	n_major = [float(x) for x in arguments[6:9]]
	r_major, r_minor = [float(x) for x in arguments[9:]]
	brl_db.epa(primitive_name, base, height, n_major, r_major, r_minor)
	return

def draw_ehy(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	n_major = [float(x) for x in arguments[6:9]]
	r_major, r_minor, asymptote = [float(x) for x in arguments[9:]]
	brl_db.ehy(primitive_name, base, height, n_major,
			   r_major, r_minor, asymptote)
	return

def draw_hyperboloid(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	a = [float(x) for x in arguments[6:9]]
	b_mag, base_neck_ratio = [float(x) for x in arguments[9:]]
	brl_db.hyperboloid(primitive_name, base, height, a,
					   b_mag, base_neck_ratio)
	return

def draw_eto(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	n = [float(x) for x in arguments[3:6]]
	s_major = [float(x) for x in arguments[6:9]]
	r_revolution, r_minor = [float(x) for x in arguments[9:]]
	brl_db.eto(primitive_name, base, n, s_major,
			   r_revolution, r_minor)
	return

def draw_arbn(primitive_name, arguments):
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

def draw_particle(primitive_name, arguments):
	base = [float(x) for x in arguments[:3]]
	height = [float(x) for x in arguments[3:6]]
	r_base, r_end = arguments[6:]
	brl_db.particle(primitive_name, base, height, r_base, r_end)
	return

def draw_pipe(primitive_name, arguments):
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

switcher = {"set" : parse_var,
			"in"  : parse_primitive,
			"u"	  : primitive_union,
			"proc": parse_procs,
			"comb": parse_combination}

primitive_map = {"sph"   : draw_sphere,
				 "rpp"   : draw_rpp,
				 "wedge" : draw_wedge,
				 "arb4"  : draw_arb4,
				 "arb5"  : draw_arb5,
				 "arb6"  : draw_arb6,
				 "arb7"  : draw_arb7,
				 "arb8"  : draw_arb8,
				 "ell"   : draw_ellipsoid,
				 "tor"   : draw_torus,
				 "rcc"   : draw_rcc,
				 "tgc"   : draw_tgc,
				 "cone"  : draw_cone,
				 "trc"   : draw_trc,
				 "rpc"   : draw_rpc,
				 "rhc"   : draw_rhc,
				 "epa"   : draw_epa,
				 "ehy"   : draw_ehy,
				 "hyp"   : draw_hyperboloid,
				 "eto"   : draw_eto,
				 "arbn"  : draw_arbn,
				 "part"  : draw_particle,
				 "pipe"  : draw_pipe}	


if __name__ == "__main__":
	argv = sys.argv
	commands = read_file(argv[1])
	database_name = ' '.join(commands[0].split()[1:])
	units = commands[1].split()[1]
	commands = commands[2:]
	brl_db = wdb.WDB(database_name, "db.g")
	parse_script(database_name, units, commands)

