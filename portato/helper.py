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
"""

import os, signal, logging, grp

debug 		= logging.getLogger("portatoLogger").debug
info 		= logging.getLogger("portatoLogger").info
warning 	= logging.getLogger("portatoLogger").warning
error 		= logging.getLogger("portatoLogger").error
critical 	= logging.getLogger("portatoLogger").critical

def N_ (s):
	return s

def set_log_level (lvl):
	logging.getLogger("portatoLogger").setLevel(lvl)

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

def flatten (listOfLists):
	"""Flattens the given list of lists.

	@param listOfLists: the list of lists to flatten
	@type listOfLists: list of lists
	@returns: flattend list
	@rtype: list"""

	if not isinstance(listOfLists, list):
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
