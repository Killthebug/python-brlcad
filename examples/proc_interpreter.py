"""
Procedure interpreter for the script parser.

Procedural geometry, as the name suggests reusing certain procedures to
create geometry. These procedures are embedded in the script as "functions".

proc_interpreter.py is responsible for interpreting procedures and working
with them when invoked.

A sample procedure might look like :
-------------------------------------------------------------
proc right {a b} {
	set old $x
	set x [expr {$old + $b}]
	in rcc.$a rcc $old $y $z [exp{$x - $old}] 0 0 $radius
	in sph.$a sph $x $y $z $radius
}

right 100 $i 					#Procedure call
-------------------------------------------------------------

Currently the proc_interpreter can
** _do nothing_
**
**
**
**
"""

import sys
import re
import os

class Procedure():
	"""
	Common class for all procedures.
	Each unique procedure is an instance of this class
	"""

	def __init__(self, proc_name, proc_args, global_vars, element):
		self.name = proc_name
		self.args = proc_args
		self.global_vars = global_vars
		self.proc_string = element