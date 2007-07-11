# -*- coding: utf-8 -*-
#
# File: portato/helper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net> et.al.

"""
Some nice functions used in the program.

@var DEBUG: Boolean controlling whether to printout debug messages.
@type DEBUG: boolean
"""

import traceback, os.path, sys, types
import os, signal

DEBUG = True

def set_debug (d):
	"""Sets the global DEBUG variable. Do not set it by your own - always use this function.

	@param d: True to enable debugging; False otherwise
	@type d: boolean"""

	global DEBUG
	DEBUG = d

def debug(*args, **kwargs):
	"""Prints a debug message including filename and lineno.
	A variable number of positional arguments are allowed.

	If debug(obj0, obj1, obj2) is called, the text part of the output 
	looks like the output from print obj0, obj1, obj2.
	
	@keyword name: Use the given name instead the correct function name.
	@keyword file: Output file to use.
	@keyword minus: The value given is the amount of frames to ignore in the stack to return the correct function call.
	This should be used if you are wrapping the debug call.
	@keyword warn: Prints the message as a warning. Value of DEBUG is ignored.
	@keyword error: Prints the message as an error. Value of DEBUG is ignored."""

	if not DEBUG and not ("warn" in kwargs or "error" in kwargs): return
	
	stack = traceback.extract_stack()
	minus = -2
	if "minus" in kwargs:
		minus = minus - kwargs["minus"]
	a, b, c, d = stack[minus]
	a = os.path.basename(a)
	out = []
	for obj in args:
		out.append(str(obj))
	text = ' '.join(out)
	if "name" in kwargs:
		text = 'In %s (%s:%s): %s' % (kwargs["name"], a, b, text)
	else:
		text = 'In %s (%s:%s): %s' % (c, a, b, text)
	
	outfile = sys.stdout
	surround = "DEBUG"

	if "warn" in kwargs:
		outfile = sys.stderr
		surround = "WARNING"
	elif "error" in kwargs:
		outfile = sys.stderr
		surround = "ERROR"

	text = ("***%s*** %s ***%s***" % (surround, text, surround))
	
	if "file" in kwargs:
		f = open(kwargs["file"], "a+")
		f.write(text+"\n")
		f.close()
	else:
		print >> outfile, text

def send_signal_to_group (sig):
	"""Sends a signal to all processes of our process group (w/o ourselves).
	
	@param sig: signal number to send
	@type sig: int"""

	def handler (sig, stack):
		"""Ignores the signal exactly one time and then restores the default."""
		signal.signal(sig, signal.SIG_DFL)
	
	signal.signal(sig, handler)
	
	pgid = os.getpgrp()
	os.killpg(pgid, sig)

def am_i_root ():
	"""Returns True if the current user is root, False otherwise.
	@rtype: boolean"""

	from plugin import hook

	@hook("am_i_root")
	def __am_i_root():
		if os.getuid() == 0:
			return True
		else:
			return False
	
	return __am_i_root()

def flatten (listOfLists):
	"""Flattens the given list of lists.

	@param listOfLists: the list of lists to flatten
	@type listOfLists: list of lists
	@returns: flattend list
	@rtype: list"""

	if type(listOfLists) != types.ListType:
		return [listOfLists]

	ret = []
	for r in listOfLists:
		ret.extend(flatten(r))

	return ret

def unique_array(s):
	"""Stolen from portage_utils:
	lifted from python cookbook, credit: Tim Peters
	Return a list of the elements in s in arbitrary order, sans duplicates"""
	n = len(s)
	# assume all elements are hashable, if so, it's linear
	try:
		return list(set(s))
	except TypeError:
		pass

	# so much for linear.  abuse sort.
	try:
		t = list(s)
		t.sort()
	except TypeError:
		pass
	else:
		assert n > 0
		last = t[0]
		lasti = i = 1
		while i < n:
			if t[i] != last:
				t[lasti] = last = t[i]
				lasti += 1
			i += 1
		return t[:lasti]

	# blah.	 back to original portage.unique_array
	u = []
	for x in s:
		if x not in u:
			u.append(x)
	return u
