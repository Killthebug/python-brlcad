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
		self.local_vars = {}
		self.commands = self.proc_string.strip().split("\n")
		print(self.commands)

	def replace_vars(self, my_string):
		'''
		In replacement global vars are substituted first and then local vars
		In case of having two variables with the same name, the local vars
		are given precedence.
		'''
		x = my_string
		for variable in global_vars:
			x = x.replace(variable, str(global_vars[variable]))
		for variable_name in self.local_vars:
			x = x.replace(variable, str(self.local_vars[variable]))
		return x

	def calculate_value(self, text):
		'''
		Helper functino for evaluate_exp()
		'''
		text = text.replace("{", "(")
		text = text.replace("}", ")")
		text = text.strip()
		lexer = Lexer(text)
		interpreter = Interpreter(lexer)
		result = interpreter.expr()
		return float(result)

	def evaluate_exp(self, command):
		broken = command.split("[")
		mystring = ""
		'''
		We iterate over any every command after its split at "["
		and evaluate any expressions that might be present.
		Because that's how expressions are meant to be written

		mystring now holds the the text contained within an expression
		Eg : 
		> [exp{$j - $i}]
		> mystring = {$j - $i}
		'''
		print('here')
		for element in broken:
			if "exp" in element:
				my_string = find_between(element, "exp", "]")
				text 	  = replace_vars(my_string)
				result    = calculate_value(text)
				to_replace = "[" + element
				command   = command.replace(to_replace.strip(), str(result))
				self.commands[index] = command
		return

	def set_var_value(self, command):
		split_command = command.split()
		variable_name = '$' + command[1]
		if command[2].isdigit():
			self.local_vars[variable_name] = float(command[2])
		elif command[2].startswith("$"):
			if command[2] in global_vars:
				self.local_vars[variable_name] = float(global_vars[command[2]])
			else:
				self.local_vars[variable_name] = float(self.local_vars[command[2]])
		else:
			value = evaluate_exp(command[2])
			self.local_vars[variable_name] = float(value)

		return

	def calculate_vars(self):
		for line_num, command in emumerate(self.commands):
			element = command
			element = element.split()
			if element == []:			#Blank line
				continue
			command_type = element[0]
			if command_type == "set": 
				set_var_value(command)
		return

	def execute(self, arguments):
		for x in zip(self.args, arguments):
			var = '$' + str(x[0])
			value = float(x[1])
			self.local_vars[var] = value
		self.calculate_vars()
		#self.evaluate_exp()
		#self.execute_maps()