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
		#print(self.commands)

	def find_between(self, s, first, last):
		try:
			start = s.index( first ) + len( first )
			end = s.index( last, start )
			return s[start:end]
		except ValueError:
			return ""

	def replace_vars(self, my_string):
		'''
		In replacement global vars are substituted first and then local vars
		In case of having two variables with the same name, the local vars
		are given precedence.
		'''
		print(my_string)
		x = my_string
		for variable in self.global_vars:
			x = x.replace(variable, str(self.global_vars[variable]))
			print(x)
		print(self.local_vars)
		for variable_name in self.local_vars:
			x = x.replace(variable, str(self.local_vars[variable]))
			print(x)
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

	def evaluate_exp(self, command, index):
		calculated_value = 0.0
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
				my_string = self.find_between(element, "exp", "]")
				text 	  = self.replace_vars(my_string)
				result    = self.calculate_value(text)
				to_replace = "[" + element
				command   = command.replace(to_replace.strip(), str(result))
				calculated_value = float(result)
				self.commands[index] = command
				print(command)
		return calculated_value

	def set_var_value(self, command, index):
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
			value = self.evaluate_exp(command[2], index)
			self.local_vars[variable_name] = float(value)

		return

	def calculate_vars(self):
		for line_num, command in enumerate(self.commands):
			element = command
			element = element.split()
			if element == []:			#Blank line
				continue
			command_type = element[0]
			if command_type == "set": 
				self.set_var_value(command, line_num)
		return

	def evaluate_in(self, command, index):
		print(self.local_vars)
		self.evaluate_exp(command, index)
		print(elements)
		return

	def execute_in(self):
		for line_num, command in enumerate(self.commands):
			element = command.split()
			if element == []:
				continue
			command_type = element[0]
			if command_type == "in":
				self.evaluate_in(command, line_num)

	def execute(self, arguments):
		print(arguments)
		for x in zip(self.args, arguments):
			var = '$' + str(x[0])
			value = float(x[1])
			print(var, value)
			self.local_vars[var] = value
		self.calculate_vars()
		self.execute_in()


