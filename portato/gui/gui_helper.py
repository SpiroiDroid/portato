# -*- coding: utf-8 -*-
#
# File: portato/gui/gui_helper.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

# some backend things
from portato import backend
from portato.backend import flags
from portato.helper import *

# parser
from portato.config_parser import ConfigParser

# the wrapper
from wrapper import Console, Tree

# some stuff needed
from subprocess import Popen, PIPE, STDOUT
from threading import Thread
import pty
import time
import os
import signal

class Config:
	"""Wrapper around a ConfigParser and for additional local configurations."""
	const = {
			"main_sec" : "Main",
			"usePerVersion_opt" : "usePerVersion",
			"useFile_opt" : "usefile",
			"maskFile_opt" : "maskfile",
			"maskPerVersion_opt" : "maskPerVersion",
			"testingFile_opt" : "keywordfile",
			"testingPerVersion_opt" : "keywordperversion",
			"debug_opt" : "debug",
			"oneshot_opt" : "oneshot",
			"deep_opt" : "deep",
			"newuse_opt" : "newuse",
			"syncCmd_opt" : "synccommand"
			}
	
	def __init__ (self, cfgFile):
		"""Constructor.

		@param cfgFile: path to config file
		@type cfgFile: string"""

		# init ConfigParser
		self._cfg = ConfigParser(cfgFile)
		
		# read config
		self._cfg.parse()

		# local configs
		self.local = {}

	def get(self, name, section=const["main_sec"], constName = True):
		"""Gets an option.
		
		@param name: name of the option
		@type name: string
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean
		@return: the option's value
		@rtype: string"""

		if constName:
			name = self.const[name]

		return self._cfg.get(name, section)

	def get_boolean(self, name, section=const["main_sec"], constName = True):
		"""Gets a boolean option.
			
		@param name: name of the option
		@type name: string
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean
		@return: the option's value
		@rtype: boolean"""

		if constName:
			name = self.const[name]

		return self._cfg.get_boolean(name, section)

	def modify_flags_config (self):
		"""Sets the internal config of the L{flags}-module.
		@see: L{flags.set_config()}"""

		flagCfg = {
				"usefile": self.get("useFile_opt"), 
				"usePerVersion" : self.get_boolean("usePerVersion_opt"),
				"maskfile" : self.get("maskFile_opt"),
				"maskPerVersion" : self.get_boolean("maskPerVersion_opt"),
				"testingfile" : self.get("testingFile_opt"),
				"testingPerVersion" : self.get_boolean("testingPerVersion_opt")}
		flags.set_config(flagCfg)

	def modify_debug_config (self):
		"""Sets the external debug-config.
		@see: L{helper.set_debug()}"""
		set_debug(self.get_boolean("debug_opt"))

	def modify_external_configs (self):
		"""Convenience function setting all external configs."""
		self.modify_debug_config()
		self.modify_flags_config()

	def set_local(self, cpv, name, val):
		"""Sets some local config.

		@param cpv: the cpv describing the package for which to set this option
		@type cpv: string (cpv)
		@param name: the option's name
		@type name: string
		@param val: the value to set
		@type val: any"""
		
		if not cpv in self.local:
			self.local[cpv] = {}

		self.local[cpv].update({name:val})

	def get_local(self, cpv, name):
		"""Returns something out of the local config.

		@param cpv: the cpv describing the package from which to get this option
		@type cpv: string (cpv)
		@param name: the option's name
		@type name: string
		@return: value stored for the cpv and name or None if not found
		@rtype: any"""

		if not cpv in self.local:
			return None
		if not name in self.local[cpv]:
			return None

		return self.local[cpv][name]

	def set(self, name, val, section=const["main_sec"], constName = True):
		"""Sets an option.
		
		@param name: name of the option
		@type name: string
		@param val: value to set the option to
		@type val: string
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean"""

		if constName:
			name = self.const[name]

		self._cfg.set(name, val, section)

	def set_boolean (self, name, val, section=const["main_sec"], constName = True):
		"""Sets a boolean option.
		
		@param name: name of the option
		@type name: string
		@param val: value to set the option to
		@type val: boolean
		@param section: section to look in; default is Main-Section
		@type section: string
		@param constName: If True (the default), the option names are first looked up in the const-dict.
		@type constName: boolean"""

		if constName:
			name = self.const[name]

		self._cfg.set_boolean(name, val, section)

	def write(self):
		"""Writes to the config file and modify any external configs."""
		self._cfg.write()
		self.modify_external_configs()

class Database:
	"""An internal database which holds a simple dictionary cat -> [package_list]."""

	def __init__ (self):
		"""Constructor."""
		self._db = {}

	def populate (self, category = None):
		"""Populates the database.
		
		@param category: An optional category - so only packages of this category are inserted.
		@type category: string"""
		
		# get the lists
		packages = backend.find_all_packages(name = category, withVersion = False)
		installed = backend.find_all_installed_packages(name = category, withVersion = False)
		
		# cycle through packages
		for p in packages:
			list = p.split("/")
			cat = list[0]
			pkg = list[1]
			if p in installed:
				pkg += "*"
			if not cat in self._db: self._db[cat] = []
			self._db[cat].append(pkg)

		for key in self._db: # sort alphabetically
			self._db[key].sort(cmp=cmp, key=str.lower)

	def get_cat (self, cat):
		"""Returns the packages in the category.
		
		@param cat: category to return the packages from
		@type cat: string
		@return: list of packages or []
		@rtype: string[]"""

		try:
			return self._db[cat]
		except KeyError: # cat is in category list - but not in portage
			debug("Catched KeyError =>", cat, "seems not to be an available category. Have you played with rsync-excludes?")
			return []

	def reload (self, cat):
		"""Reloads the given category.
		
		@param cat: category
		@type cat: string"""

		del self._db[cat]
		self.populate(cat+"/")

class EmergeQueue:
	"""This class manages the emerge queue."""
	
	def __init__ (self, tree = None, console = None, db = None, title_update = None):
		"""Constructor.
		
		@param tree: Tree to append all the items to.
		@type tree: Tree
		@param console: Output is shown here.
		@type console: Console
		@param db: A database instance.
		@type db: Database"""
		
		# the different queues
		self.mergequeue = [] # for emerge
		self.unmergequeue = [] # for emerge -C
		self.oneshotmerge = [] # for emerge --oneshot
		
		# dictionaries with data about the packages in the queue
		self.iters = {} # iterator in the tree
		self.deps = {} # all the deps of the package
		
		# member vars
		self.tree = tree
		if self.tree and not isinstance(self.tree, Tree): raise TypeError, "tree passed is not a Tree-object"
		
		self.console = console
		if self.console and not isinstance(self.console, Console): raise TypeError, "console passed is not a Console-object"
		
		self.db = db
		self.title_update = title_update
		
		# our iterators pointing at the toplevels; they are set to None if we do not have a tree
		if self.tree: 
			self.emergeIt = self.tree.get_emerge_it()
			self.unmergeIt = self.tree.get_unmerge_it()
		else:
			self.emergeIt = self.unmergeIt = None

	def _get_pkg_from_cpv (self, cpv, unmask = False):
		"""Gets a L{backend.Package}-object from a cpv.

		@param cpv: the cpv to get the package for
		@type cpv: string (cpv)
		@param unmask: if True we will look for masked packages if we cannot find unmasked ones
		@type unmask: boolean
		@return: created package
		@rtype: backend.Package
		
		@raises backend.PackageNotFoundException: If no package could be found - normally it is existing but masked."""

		# for the beginning: let us create a package object - but it is not guaranteed, that it actually exists in portage
		pkg = backend.Package(cpv)
		masked = not (pkg.is_masked() or pkg.is_testing(allowed=True)) # we are setting this to True in case we have unmasked it already, but portage does not know this
		
		# and now try to find it in portage
		pkg = backend.find_packages("="+cpv, masked = masked)
		
		if pkg: # gotcha
			pkg = pkg[0]

		elif unmask: # no pkg returned, but we are allowed to unmask it
			pkg = backend.find_packages("="+cpv, masked = True)[0]
			if pkg.is_testing(allowed = True):
				pkg.set_testing(True)
			if pkg.is_masked():
				pkg.set_masked()
		
		else: # no pkg returned - and we are not allowed to unmask
			raise backend.PackageNotFoundException(cpv)
		
		return pkg
	
	def update_tree (self, it, cpv, unmask = False, oneshot = False):
		"""This updates the tree recursivly, or? Isn't it? Bjorn!

		@param it: iterator where to append
		@type it: Iterator
		@param cpv: The package to append.
		@type cpv: string (cat/pkg-ver)
		@param unmask: True if we are allowed to look for masked packages
		@type unmask: boolean
		@param oneshot: True if we want to emerge is oneshot
		@type oneshot: boolean
		
		@raises backend.BlockedException: When occured during dependency-calculation.
		@raises backend.PackageNotFoundException: If no package could be found - normally it is existing but masked."""
		
		if cpv in self.deps:
			return # in list already and therefore it's already in the tree too	
		
		update = False
		uVersion = None
		try:
			pkg = self._get_pkg_from_cpv(cpv, unmask)
			if not pkg.is_installed():
				old = backend.find_installed_packages(pkg.get_slot_cp())
				if old: 
					old = old[0] # assume we have only one there; FIXME: slotted packages
					update = True
					uVersion = old.get_version()

		except backend.PackageNotFoundException, e: # package not found / package is masked -> delete current tree and re-raise the exception
			if self.tree.iter_has_parent(it):
				while self.tree.iter_has_parent(it):
					it = self.tree.parent_iter(it)
				self.remove_with_children(it)
			raise e

		# add iter
		subIt = self.tree.append(it, self.tree.build_append_value(cpv, oneshot = oneshot, update = update, version = uVersion))
		self.iters.update({cpv: subIt})
		
		# get dependencies
		deps = pkg.get_dep_packages() # this might raise a BlockedException
		self.deps.update({cpv : deps})
		
		# recursive call
		for d in deps:
			try:
				self.update_tree(subIt, d, unmask)
			except backend.BlockedException, e: # BlockedException occured -> delete current tree and re-raise exception
				debug("Something blocked:", e[0])
				self.remove_with_children(subIt)
				raise e
		
	def append (self, cpv, unmerge = False, update = False, forceUpdate = False, unmask = False, oneshot = False):
		"""Appends a cpv either to the merge queue or to the unmerge-queue.
		Also updates the tree-view.
		
		@param cpv: Package to add
		@type cpv: string (cat/pkg-ver)
		@param unmerge: Set to True if you want to unmerge this package - else False.
		@type unmerge: boolean		
		@param update: Set to True if a package is going to be updated (e.g. if the use-flags changed).
		@type update: boolean
		@param forceUpdate: Set to True if the update should be forced.
		@type forceUpdate: boolean
		@param unmask: True if we are allowed to look for masked packages
		@type unmask: boolean
		@param oneshot: True if this package should not be added to the world-file.
		@type oneshot: boolean
		
		@raises portato.backend.PackageNotFoundException: if trying to add a package which does not exist"""
		
		if not unmerge: # emerge
			# insert dependencies
			pkg = self._get_pkg_from_cpv(cpv, unmask)
			deps = pkg.get_dep_packages()
			
			if update:
				if not forceUpdate and deps == self.deps[cpv]:
					return # nothing changed - return
				else:
					hasBeenInQueue = (cpv in self.mergequeue or cpv in self.oneshotmerge)
					parentIt = self.tree.parent_iter(self.iters[cpv])

					# delete it out of the tree - but NOT the changed flags
					self.remove_with_children(self.iters[cpv], removeNewFlags = False)
					
					if hasBeenInQueue: # package has been in queue before
						self._queue_append(cpv, oneshot)
					
					self.update_tree(parentIt, cpv, unmask, oneshot = oneshot)
			else: # not update
				self._queue_append(cpv, oneshot)
				if self.emergeIt: 
					self.update_tree(self.emergeIt, cpv, unmask, oneshot = oneshot)
			
		else: # unmerge
			self.unmergequeue.append(cpv)
			if self.unmergeIt: # update tree
				self.tree.append(self.unmergeIt, self.tree.build_append_value(cpv))

	def _queue_append (self, cpv, oneshot = False):
		"""Convenience function appending a cpv either to self.mergequeue or to self.oneshotmerge.

		@param cpv: cpv to add
		@type cpv: string (cpv)
		@param oneshot: True if this package should not be added to the world-file.
		@type oneshot: boolean"""

		if not oneshot:
			self.mergequeue.append(cpv)
		else:
			self.oneshotmerge.append(cpv)
	
	def _update_packages(self, packages, process = None):
		"""This updates the packages-list. It simply makes the db to rebuild the specific category.
		
		@param packages: The packages which we emerged.
		@type packages: list of cpvs
		@param process: The process we have to wait for before we can do our work.
		@type process: subprocess.Popen"""
		
		old_title = self.console.get_window_title()
		if process: 
			while process.poll() == None:
				if self.title_update : 
					title = self.console.get_window_title()
					if title != old_title:
						self.title_update(title)
					time.sleep(0.5)

		if self.title_update: self.title_update(None)

		for p in packages:
			if p in ["world", "system"]: continue
			cat = backend.split_package_name(p)[0] # get category
			self.db.reload(cat)
			debug("Category %s refreshed" % cat)

	def _emerge (self, options, packages, it, command = ["/usr/bin/python","/usr/bin/emerge"]):
		"""Calls emerge and updates the terminal.
		
		@param options: options to send to emerge
		@type options: list
		@param packages: packages to emerge
		@type packages: list
		@param it: Iterators which point to these entries whose children will be removed after completion.
		@type it: Iterator[]
		@param command: the command to execute - default is "/usr/bin/python /usr/bin/emerge"
		@type command: string[]"""

		# open tty
		(master, slave) = pty.openpty()
		self.console.set_pty(master)
		
		# start emerge
		self.process = Popen(command+options+packages, stdout = slave, stderr = STDOUT, shell = False)
		
		# start thread waiting for the stop of emerge
		Thread(name="Emerge-Thread", target=self._update_packages, args=(packages+self.deps.keys(), self.process)).start()
		
		# remove
		for i in it:
			self.remove_with_children(i)

	def emerge (self, force = False):
		"""Emerges everything in the merge-queue.
		
		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean"""
		
		def prepare(queue):
			"""Prepares the list of iterators and the list of packages."""
			list = []
			its = []
			for k in queue:
				list += ["="+k]
				its.append(self.iters[k])

			return list, its

		# oneshot-queue
		if len(self.oneshotmerge) != 0:
			# prepare package-list for oneshot
			list, its = prepare(self.oneshotmerge)
			
			s = ["--oneshot"]
			if not force: s += ["--verbose", "--pretend"]
			
			self._emerge(s, list, its)
		
		# normal queue
		if len(self.mergequeue) != 0:
			# prepare package-list
			list, its = prepare(self.mergequeue)

			s = []
			if not force: s = ["--verbose", "--pretend"]
		
			self._emerge(s, list, its)

	def unmerge (self, force = False):
		"""Unmerges everything in the umerge-queue.

		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean"""
		
		if len(self.unmergequeue) == 0: return # nothing in queue

		list = self.unmergequeue[:] # copy the unmerge-queue
		
		# set options
		s = ["-C"]
		if not force: s += ["-pv"]
		
		self._emerge(s,list, [self.unmergeIt])

	def update_world(self, force = False, newuse = False, deep = False):
		"""Does an update world. newuse and deep are the arguments handed to emerge.

		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean"""

		options = ["--update"]

		if newuse: options += ["--newuse"]
		if deep: options += ["--deep"]
		if not force: options += ["-pv"]

		self._emerge(options, ["world"], [self.emergeIt])

	def sync (self, command = None):
		"""Calls "emerge --sync".
		
		@param command: command to execute to sync. If None "emerge --sync" is taken.
		@type command: string[]"""

		if command == None:
			self._emerge(["--sync"], [], [])
		else:
			self._emerge([],[],[], command = command)

	def kill_emerge (self):
		"""Kills the emerge process."""
		try:
			os.kill(self.process.pid, signal.SIGTERM)
			debug("Process should be killed")
		except AttributeError:
			debug("AttributeError occured ==> process not exisiting - ignore")
		except OSError:
			debug("OSError occured ==> process already stopped - ignore")

	def remove_with_children (self, it, removeNewFlags = True):
		"""Convenience function which removes all children of an iterator and than the iterator itself.

		@param it: The iter which to remove.
		@type it: Iterator
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""

		self.remove_children(it, removeNewFlags)
		self.remove(it, removeNewFlags)

	def remove_children (self, parentIt, removeNewFlags = True):
		"""Removes all children of a given parent TreeIter recursivly.
		
		@param parentIt: The iter from which to remove all children.
		@type parentIt: Iterator
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""

		childIt = self.tree.first_child_iter(parentIt)

		while childIt:
			if (self.tree.iter_has_children(childIt)): # recursive call
				self.remove_children(childIt, removeNewFlags)
			temp = childIt
			childIt = self.tree.next_iter(childIt)
			self.remove(temp, removeNewFlags)

	def remove (self, it, removeNewFlags = True):
		"""Removes a specific item in the tree. This does not remove the top-entries.
		
		@param it: Iterator which points to the entry we are going to remove.
		@type it: Iterator
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""
		
		if self.tree.iter_has_parent(it): # NEVER remove our top stuff
			cpv = self.tree.get_value(it, self.tree.get_cpv_column())
			if self.tree.is_in_emerge(it): # Emerge
				del self.iters[cpv]
				try:
					del self.deps[cpv]
				except KeyError: # this seems to be removed due to a BlockedException - so no deps here atm ;)
					debug("Catched KeyError =>", cpv, "seems not to be in self.deps. Should be no harm in normal cases.")
				try:
					self.mergequeue.remove(cpv)
				except ValueError: # this is a dependency - ignore
					try:
						self.oneshotmerge.remove(cpv)
					except ValueError:
						debug("Catched ValueError =>", cpv, "seems not to be in merge-queue. Should be no harm.")
				
				if removeNewFlags: # remove the changed flags
					flags.remove_new_use_flags(cpv)
					flags.remove_new_masked(cpv)
					flags.remove_new_testing(cpv)
			
			else: # in Unmerge
				self.unmergequeue.remove(cpv)
			
			self.tree.remove(it)