#
# File: geneticone/gui/gui_helper.py
# This file is part of the Genetic/One-Project, a graphical portage-frontend.
#
# Copyright (C) 2006 Necoro d.M.
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by Necoro d.M. <necoro@necoro.net>

from geneticone import backend
from geneticone.backend import flags
from geneticone.helper import *
import dialogs

from subprocess import Popen, PIPE, STDOUT
from threading import Thread
from ConfigParser import SafeConfigParser

import pty
import vte

class Config:
	const = {
			"main_sec" : "Main",
			"usePerVersion_opt" : "usePerVersion",
			"useFile_opt" : "usefile",
			"maskFile_opt" : "maskfile",
			"maskPerVersion_opt" : "maskPerVersion",
			"testingFile_opt" : "keywordfile",
			"testingPerVersion_opt" : "keywordperversion",
			"debug_opt" : "debug",
			"oneshot_opt" : "oneshot"
			}
	
	def __init__ (self, cfgFile):
		self._cfg = SafeConfigParser()
		if not isinstance(cfgFile, file):
			self._file = open(cfgFile) # assume string
		elif cfgFile.closed:
			self._file = open(cfgFile.name)
		else:
			self._file = cfgFile

		self._cfg.readfp(self._file)
		self._file.close()

		self.local = {}

	def get(self, name, section=const["main_sec"]):
		return self._cfg.get(section, name)

	def get_boolean(self, name, section=const["main_sec"]):
		return self._cfg.getboolean(section, name)

	def modify_flags_config (self):
		flagCfg = {
				"usefile": self.get(self.const["useFile_opt"]), 
				"usePerVersion" : self.get_boolean(self.const["usePerVersion_opt"]),
				"maskfile" : self.get(self.const["maskFile_opt"]),
				"maskPerVersion" : self.get_boolean(self.const["maskPerVersion_opt"]),
				"testingfile" : self.get(self.const["testingFile_opt"]),
				"testingPerVersion" : self.get_boolean(self.const["testingPerVersion_opt"])}
		flags.set_config(flagCfg)

	def modify_debug_config (self):
		set_debug(self.get_boolean(self.const["debug_opt"]))

	def set_local(self, cpv, name, val):
		if not cpv in self.local:
			self.local[cpv] = {}

		self.local[cpv].update({name:val})

	def get_local(self, cpv, name):
		if not cpv in self.local:
			return None
		if not name in self.local[cpv]:
			return None

		return self.local[cpv][name]

	def set(self, name, val, section=const["main_sec"]):
		self._cfg.set(section, name, val)

	def write(self):
		self._file = open(self._file.name,"w")
		self._cfg.write(self._file)
		self.modify_flags_config()
		self.modify_debug_config()

class Database:
	"""An internal database which holds a simple dictionary cat -> [package_list]."""

	def __init__ (self):
		"""Constructor."""
		self.db = {}

	def populate (self, category = None):
		"""Populates the database.
		@param category: An optional category - so only packages of this category are inserted.
		@type category: string"""
		packages = backend.find_all_packages(name = category, withVersion = False)
		installed = backend.find_all_installed_packages(name = category, withVersion = False)
		for p in packages:
			list = p.split("/")
			cat = list[0]
			pkg = list[1]
			if p in installed:
				pkg += "*"
			if not cat in self.db: self.db[cat] = []
			self.db[cat].append(pkg)

		for key in self.db:
			self.db[key].sort(cmp=cmp, key=str.lower)

	def get_cat (self, cat):
		"""Returns the packages in the category.
		@param cat: category to return the packages from
		@type cat: string
		@return: list of packages or []
		@rtype: list of strings"""
		try:
			return self.db[cat]
		except KeyError: # cat is in category list - but not in portage
			debug("Catched KeyError =>", cat, "seems not to be an available category. Have you played with rsync-excludes?")
			return []

	def reload (self, cat):
		"""Reloads the given category.
		@param cat: category
		@type cat: string"""

		del self.db[cat]
		self.populate(cat+"/")

class EmergeQueue:
	"""This class manages the emerge queue."""
	
	def __init__ (self, tree = None, console = None, db = None):
		"""Constructor.
		
		@param tree: Tree to append all the items to. Default: None.
		@type tree: gtk.TreeStore
		@param console: Output is shown here. Default: None
		@type console: vte.Terminal
		@param db: A database instance.
		@type db: Database"""
		
		self.mergequeue = []
		self.unmergequeue = []
		self.oneshotmerge = []
		self.iters = {}
		self.deps = {}
		self.tree = tree
		self.console = console
		self.db = db

		if self.tree: 
			self.emergeIt = self.tree.append(None, ["Emerge", ""])
			self.unmergeIt = self.tree.append(None, ["Unmerge", ""])
		else:
			self.emergeIt = self.unmergeIt = None

	def _get_pkg_from_cpv (self, cpv, unmask = False):
		pkg = backend.Package(cpv)
		if not pkg.is_masked() and not pkg.is_testing(allowed=True):
			masked = True
		else:
			masked = False
		pkg = backend.find_packages("="+cpv, masked = masked)
		if pkg:
			pkg = pkg[0]
		elif unmask:
			pkg = backend.find_packages("="+cpv, masked = True)[0]
			if pkg.is_testing(allowed = True):
				pkg.set_testing(True)
			if pkg.is_masked():
				pkg.set_masked()
		else:
			raise backend.PackageNotFoundException(cpv)
		return pkg
	
	def update_tree (self, it, cpv, unmask = False, options = ""):
		"""This updates the tree recursivly, or? Isn't it? Bjorn!

		@param it: iterator where to append
		@type it: gtk.TreeIter
		@param cpv: The package to append.
		@type cpv: string (cat/pkg-ver)
		
		@raise geneticone.backend.BlockedException: When occured during dependency-calculation."""
		
		# get dependencies
		if cpv in self.deps:
			return # in list already
		
		try:
			pkg = self._get_pkg_from_cpv(cpv, unmask)
		except backend.PackageNotFoundException, e:
			if self.tree.iter_parent(it):
				while self.tree.iter_parent(it):
					it = self.tree.iter_parent(it)
				self.remove_with_children(it)
			raise e

		# add iter
		subIt = self.tree.append(it, [cpv, "<i>"+options+"</i>"])
		self.iters.update({cpv: subIt})
		
		deps = pkg.get_dep_packages()
		self.deps.update({cpv : deps})
		
		# recursive call
		for d in deps:
			try:
				self.update_tree(subIt, d, unmask)
			except backend.BlockedException, e:
				debug("Something blocked:", e[0])
				self.remove_with_children(subIt)
				raise e
		
	def append (self, cpv, unmerge = False, update = False, unmask = False, oneshot = False, forceUpdate = False):
		"""Appends a cpv either to the merge queue or to the unmerge-queue.
		Also updates the tree-view.
		
		@param cpv: Package to add
		@type cpv: string (cat/pkg-ver)
		@param unmerge: Set to True if you want to unmerge this package - else False. Default: False
		@type unmerge: boolean
		@param update: Set to True if a package is going to be updated (e.g. if the use-flags changed). Default: False
		@type update: boolean
		@raises geneticone.backend.PackageNotFoundException: if trying to add a package which does not exist"""
		
		if not unmerge:
			try:
				# insert dependencies
				pkg = self._get_pkg_from_cpv(cpv, unmask)
				deps = pkg.get_dep_packages()
				
				if update:
					if not forceUpdate and deps == self.deps[cpv]:
						return # nothing changed - return
					else:
						hasBeenInQueue = (cpv in self.mergequeue or cpv in self.oneshotmerge)
						parentIt = self.tree.iter_parent(self.iters[cpv])
						options = ""
						self.remove_with_children(self.iters[cpv], False) # this is needed to def delete everything
						if hasBeenInQueue:
							if not oneshot:
								self.mergequeue.append(cpv)
							else:
								self.oneshotmerge.append(cpv)
								options="oneshot"

						self.update_tree(parentIt, cpv, unmask, options = options)
				else: # not update
					options = ""
					if not oneshot: self.mergequeue.append(cpv)
					else: 
						self.oneshotmerge.append(cpv)
						options = "oneshot"
					if self.emergeIt: self.update_tree(self.emergeIt, cpv, unmask, options)
			
			except backend.BlockedException, e : # there is sth blocked --> call blocked_dialog
				blocks = e[0]
				dialogs.blocked_dialog(cpv, blocks)
				return
		else: # unmerge
			self.unmergequeue.append(cpv)
			if self.unmergeIt: # update tree
				self.tree.append(self.unmergeIt, [cpv])
	
	def _update_packages(self, packages, process = None):
		"""This updates the packages-list. It simply makes the db to rebuild the specific category.
		
		@param packages: The packages which we emerged.
		@type packages: list of cpvs
		@param process: The process we have to wait for before we can do our work. Default: None.
		@type process: subprocess.Popen"""

		if process: process.wait()
		for p in packages:
			cat = backend.split_package_name(p)[0] # get category
			while cat[0] in ["=",">","<","!"]:
				cat = cat[1:]
			self.db.reload(cat)
			debug("Category %s refreshed" % cat)

	def _emerge (self, options, packages, it):
		"""Calls emerge and updates the terminal.
		
		@param options: options to send to emerge
		@type options: list
		@param packages: packages to emerge
		@type packages: list
		@param it: Iterators which point to these entries whose children will be removed after completion.
		@type it: list of gtk.TreeIter"""

		# open tty
		(master, slave) = pty.openpty()
		self.console.set_pty(master)
		
		# start emerge
		process = Popen(["/usr/bin/python","/usr/bin/emerge"]+options+packages, stdout = slave, stderr = STDOUT, shell = False)
		Thread(target=self._update_packages, args=(packages, process)).start()
		
		# remove
		for i in it:
			self.remove_with_children(i)

	def emerge (self, force = False):
		"""Emerges everything in the merge-queue.
		
		@param force: If False, '-pv' is send to emerge. Default: False.
		@type force: boolean"""

		if len(self.oneshotmerge) != 0:
			# prepare package-list for oneshot
			list = []
			its = []
			for k in self.oneshotmerge:
				list += ["="+k]
				its.append(self.iters[k])

			s = ["--oneshot"]
			if not force: s += ["--verbose", "--pretend"]
			self._emerge(s, list, its)
		
		if len(self.mergequeue) != 0:
			# prepare package-list
			list = []
			its = []
			for k in self.mergequeue:
				list += ["="+k]
				its.append(self.iters[k])
		
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
		if not force: s = ["-Cpv"]
		
		self._emerge(s,list, [self.unmergeIt])

	def remove_with_children (self, it, removeNewFlags = True):
		self.remove_children(it, removeNewFlags)
		self.remove(it, removeNewFlags)

	def remove_children (self, parentIt, removeNewFlags = True):
		"""Removes all children of a given parent TreeIter recursivly.
		
		@param parentIt: The iter from which to remove all children.
		@type parentIt: gtk.TreeIter
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""

		childIt = self.tree.iter_children(parentIt)

		while childIt:
			if (self.tree.iter_has_child(childIt)): # recursive call
				self.remove_children(childIt, removeNewFlags)
			temp = childIt
			childIt = self.tree.iter_next(childIt)
			self.remove(temp, removeNewFlags)

	def remove (self, it, removeNewFlags = True):
		"""Removes a specific item in the tree. This does not remove the top-entries.
		
		@param it: Iterator which points to the entry we are going to remove.
		@type it: gtk.TreeIter
		@param removeNewFlags: True if new flags should be removed; False otherwise. Default: True.
		@type removeNewFlags: boolean"""
		
		if self.tree.iter_parent(it): # NEVER remove our top stuff
			cpv = self.tree.get_value(it,0)
			if self.tree.get_string_from_iter(it).split(":")[0] == self.tree.get_string_from_iter(self.emergeIt): # in Emerge
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
				
				if removeNewFlags: 
					flags.remove_new_use_flags(cpv)
					flags.remove_new_masked(cpv)
					flags.remove_new_testing(cpv)
			
			else: # in Unmerge
				self.unmergequeue.remove(cpv)
			
			self.tree.remove(it)
