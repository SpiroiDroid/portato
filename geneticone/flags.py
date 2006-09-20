#!/usr/bin/python

#
# File: geneticone/flags.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

import os
import os.path
from subprocess import Popen, PIPE

from geneticone import *
from portage_util import unique_array

### GENERAL PART ###

def grep (p, path):
	"""Grep runs "egrep" on a given path and looks for occurences of a given package."""
	if not isinstance(p, Package):
		p = Package(p) # assume it is a cpv or a gentoolkit.Package

	command = "egrep -x -n -r -H '^[<>!=~]{0,2}%s(-[0-9].*)?[[:space:]].*$' %s"
	return Popen((command % (p.get_cp(), path)), shell = True, stdout = PIPE).communicate()[0].splitlines()

def get_data(pkg):
	"""This splits up the data of grep() and builds tuples in the format (file,line,criterion,list_of_flags)."""
	flags = []

	# do grep
	list = grep(pkg, USE_PATH)
	
	for i in range(len(list)):
		file, line, fl = tuple(list[i].split(":")) # get file, line and flag-list
		fl = fl.split()
		crit = fl[0]
		fl = fl[1:]
		# stop after first comment
		for i in range(len(fl)):
			if fl[i][0] == "#": #comment - stop here
				fl = fl[:i]
				break
		flags.append((file,line,crit,fl))

	return flags

### USE FLAG PART ###
USE_PATH = os.path.join(portage.USER_CONFIG_PATH,"package.use")
USE_PATH_IS_DIR = os.path.isdir(USE_PATH)
useFlags = {} # useFlags in the file
newUseFlags = [] # useFlags as we want them to be: format: (cpv, file, line, useflag, (true if removed from list / false if added))

def set_use_flag (pkg, flag):
	"""Sets the useflag for a given package."""
	global useFlags, newUseFlags

	def invert_flag (_flag):
		if _flag[0] == "-":
			return _flag[1:]
		else:
			return "-"+_flag

	if not isinstance(pkg, Package):
		pkg = Package(pkg) # assume cpv or gentoolkit.Package

	cpv = pkg.get_cpv()
	invFlag = invert_flag(flag)
	
	# if not saved in useFlags, get it by calling get_data() which calls grep()
	data = None
	if not cpv in useFlags:
		data = get_data(pkg)
		useFlags[cpv] = data
	else:
		data = useFlags[cpv]

	print "data: "+str(data)
	# add a useflag / delete one
	added = False
	for file, line, crit, flags in data:
		if pkg.matches(crit):
			
			# we have the inverted flag in the uselist/newuselist --> delete it
			if invFlag in flags or (cpv, file, line, invFlag, False) in newUseFlags or (cpv, file, line, flag, True) in newUseFlags:
				if added: del newUseFlags[-1] # we currently added it as an extra option - delete it
				added = True
				jumpOut = False
				for t in [(cpv, file, line, invFlag, False),(cpv, file, line, flag, True)]:
					if t in newUseFlags:
						newUseFlags.remove(t)
						jumpOut = True
						break
				if not jumpOut:	newUseFlags.append((cpv, file, line, invFlag, True))
				break
			
			# we want to duplicate the flag --> ignore
			elif flag in flags:
				added = True # emulate adding
				break

			# add as an extra flag
			else:
				if not added: newUseFlags.append((cpv, file, line, flag, False))
				added = True
	
	# create a new line
	if not added:
		path = USE_PATH
		if USE_PATH_IS_DIR:
			path = os.path.join(USE_PATH,"geneticone")
		
		try:
			newUseFlags.remove((cpv, path, -1, invFlag, False))
		except ValueError: # not in UseFlags
			newUseFlags.append((cpv, path, -1, flag, False))

	newUseFlags = unique_array(newUseFlags)
	print "newUseFlags: "+str(newUseFlags)

def write_use_flags ():
	"""This writes our changed useflags into the file."""
	global newUseFlags, useFlags

	def insert (flag, list):
		"""Shortcut for inserting a new flag right after the package-name."""
		list.insert(1,flag)
	
	def remove (flag, list):
		"""Removes a flag."""
		try:
			list.remove(flag)
		except ValueError: # flag is given as flag\n
			list.remove(flag+"\n")
			list.append("\n") #re-insert the newline

		# no more flags there - comment it out
		if len(list) == 1 or list[1][0] in ("#","\n"):
			list[0] = "#"+list[0]
			insert("#removed by geneticone#",list)

	file_cache = {} # cache for having to read the file only once: name->[lines]
	for cpv, file, line, flag, delete in newUseFlags:
		line = int(line) # it is saved as a string so far!
		
		# add new line
		if line == -1:
			msg = "\n#geneticone update#\n=%s %s" % (cpv, flag)
			if not file in file_cache:
				f = open(file, "a")
				f.write(msg)
				f.close()
			else:
				file_cache[file].append(msg)
		# change a line
		else:
			if not file in file_cache:
				# read file
				f = open(file, "r")
				lines = []
				i = 1
				while i < line: # stop at the given line
					lines.append(f.readline())
					i = i+1
				l = f.readline().split(" ")
				# delete or insert
				if delete:
					remove(flag,l)
				else:
					insert(flag,l)
				lines.append(" ".join(l))
				
				# read the rest
				lines.extend(f.readlines())
				
				file_cache[file] = lines
				f.close()
			else: # in cache
				l = file_cache[file][line-1].split(" ")
				if delete:
					remove(flag,l)
				else:
					insert(flag,l)
				file_cache[file][line-1] = " ".join(l)
	
	# write to disk
	for file in file_cache.keys():
		f = open(file, "w")
		f.writelines(file_cache[file])
		f.close()
	# reset
	useFlags = {}
	newUseFlags = []