# -*- coding: utf-8 -*-
#
# File: portato/backend/portage/package.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..package import Package
from .. import flags
from .. import system
from ..exceptions import BlockedException, PackageNotFoundException
from ...helper import debug, unique_array

import portage, portage_dep
from portage_util import unique_array

import os.path
from gettext import lgettext as _

class PortagePackage (Package):
	"""This is a class abstracting a normal package which can be installed for the portage-system."""

	def __init__ (self, cpv):
		"""Constructor.

		@param cpv: The cpv which describes the package to create.
		@type cpv: string (cat/pkg-ver)"""

		Package.__init__(self, cpv)
		self._settings = system.settings
		self._settingslock = system.settings.settingslock

		self._trees = system.settings.trees

		self.forced_flags = set()
		self.forced_flags.update(self._settings.settings.usemask)
		self.forced_flags.update(self._settings.settings.useforce)
		
		try:
			self._status = portage.getmaskingstatus(self.get_cpv(), settings = self._settings.settings)
		except KeyError: # package is not located in the system
			self._status = None
		
		if self._status and len(self._status) == 1 and self._status[0] == "corrupted":
			self._status = None
	
	def is_installed(self):
		return self._settings.vartree.dbapi.cpv_exists(self._cpv)

	def is_overlay(self):
		dir,ovl = self._settings.porttree.dbapi.findname2(self._cpv)
		return ovl != self._settings.settings["PORTDIR"] and str(ovl) != "0"

	def get_overlay_path (self):
		dir,ovl = self._settings.porttree.dbapi.findname2(self._cpv)
		return ovl

	def is_in_system (self):
		return (self._status != None)

	def is_missing_keyword(self):
		if self._status and "missing keyword" in self._status:
			return True
		return False

	def is_testing(self, use_keywords = False):
		testArch = "~" + self.get_global_settings("ARCH")
		if not use_keywords: # keywords are NOT taken into account
			if testArch in self.get_package_settings("KEYWORDS").split():
				return True
			return False
		
		else: # keywords are taken into account
			status = flags.new_testing_status(self.get_cpv())
			if status is None: # we haven't changed it in any way
				if self._status and testArch+" keyword" in self._status:
					return True
				return False
			else:
				return status
	
	def is_masked (self, use_changed = True):
		
		if use_changed:
			status = flags.new_masking_status(self.get_cpv())
			if status != None: # we have locally changed it
				if status == "masked": return True
				elif status == "unmasked": return False
				else:
					error(_("BUG in flags.new_masking_status. It returns \'%s\'"), status)
			else: # we have not touched the status
				if self._status and ("profile" in self._status or "package.mask" in self._status):
					return True
				return False
		else: # we want the original portage value XXX: bug if masked by user AND by system
			
			# get the normal masked ones
			if self._status and ("profile" in self._status or "package.mask" in self._status):
				if not flags.is_locally_masked(self, changes = False): # assume that if it is locally masked, it is not masked by the system
					return True
			else: # more difficult: get the ones we unmasked, but are masked by the system
				try:
					masked = self._settings.settings.pmaskdict[self.get_cp()]
				except KeyError: # key error: not masked
					return False

				for cpv in masked:
					if self.matches(cpv):
						if not flags.is_locally_masked(self, changes = False): # assume that if it is locally masked, it is not masked by the system
							return True
						else:
							return False

			return False

	def get_masking_reason(self):
		reason = portage.getmaskingreason(self.get_cpv(), settings = self._settings.settings)

		if reason:
			return reason[:-1] # strip of last \n
		else:
			return reason

	def get_iuse_flags (self, installed = False):
		if installed or not self.is_in_system():
			tree = self._settings.vartree
		else:
			tree = self._settings.porttree
		
		return list(set(self.get_package_settings("IUSE", tree = tree).split()).difference(self.forced_flags))

	def get_matched_dep_packages (self, depvar):
		# change the useflags, because we have internally changed some, but not made them visible for portage
		actual = self.get_actual_use_flags()
		
		depstring = ""
		try:
			for d in depvar:
				depstring += self.get_package_settings(d, tree = self._settings.porttree)+" "
		except KeyError: # not found in porttree - use vartree
			depstring = ""
			for d in depvar:
				depstring += self.get_package_settings(d, tree = self._settings.vartree)+" "

		deps = portage.dep_check(depstring, None, self._settings.settings, myuse = actual, trees = self._trees)

		if not deps: # FIXME: what is the difference to [1, []] ?
			return [] 

		if deps[0] == 0: # error
			raise DependencyCalcError, deps[1]
		
		deps = deps[1]

		retlist = []
		
		for d in deps:
			if not d[0] == "!":
				retlist.append(d)

		return retlist

	def get_dep_packages (self, depvar = ["RDEPEND", "PDEPEND", "DEPEND"], with_criterions = False):
		dep_pkgs = [] # the package list
		
		# change the useflags, because we have internally changed some, but not made them visible for portage
		actual = self.get_actual_use_flags()

		depstring = ""
		for d in depvar:
			depstring += self.get_package_settings(d, tree=self._settings.porttree)+" "

		# let portage do the main stuff ;)
		# pay attention to any changes here
		deps = portage.dep_check (depstring, self._settings.vartree.dbapi, self._settings.settings, myuse = actual, trees = self._trees)
		
		if not deps: # FIXME: what is the difference to [1, []] ?
			return [] 

		if deps[0] == 0: # error
			raise DependencyCalcError, deps[1]
		
		deps = deps[1]

		def create_dep_pkgs_data (dep, pkg):
			"""Returns the data to enter into the dep_pkgs list, which is either the package cpv or a tuple
			consisting of the cpv and the criterion."""
			if with_criterions:
				return (pkg.get_cpv(), dep)
			else:
				return pkg.get_cpv()

		for dep in deps:
			if dep[0] == '!': # blocking sth
				dep = dep[1:]
				if dep != self.get_cp(): # not cpv, because a version might explicitly block another one
					blocked = system.find_installed_packages(dep)
					if blocked != []:
						raise BlockedException, (self.get_cpv(), blocked[0].get_cpv())
				continue # finished with the blocking one -> next

			pkg = system.find_best_match(dep)
			if not pkg: # try to find masked ones
				list = system.find_packages(dep, masked = True)
				if not list:
					raise PackageNotFoundException, dep

				list = system.sort_package_list(list)
				done = False
				for i in range(len(list)-1,0,-1):
					p = list[i]
					if not p.is_masked():
						dep_pkgs.append(create_dep_pkgs_data(dep, p))
						done = True
						break
				if not done:
					dep_pkgs.append(create_dep_pkgs_data(dep, list[-1]))
			else:
				dep_pkgs.append(create_dep_pkgs_data(dep, pkg))

		return dep_pkgs

	def get_global_settings(self, key):
		self._settingslock.acquire()
		self._settings.settings.setcpv(self._cpv)
		v = self._settings.settings[key]
		self._settingslock.release()
		return v

	def get_ebuild_path(self):
		return self._settings.porttree.dbapi.findname(self._cpv)

	def get_package_settings(self, var, tree = None):
		if not tree:
			mytree = self._settings.vartree
			if not self.is_installed():
				mytree = self._settings.porttree
		else:
			mytree = tree
		r = mytree.dbapi.aux_get(self._cpv,[var])
		
		return r[0]

	def get_use_flags(self):
		if self.is_installed():
			return self.get_package_settings("USE", tree = self._settings.vartree)
		else: return ""

	def compare_version(self,other):
		v1 = self._scpv
		v2 = portage.catpkgsplit(other.get_cpv())
		# if category is different
		if v1[0] != v2[0]:
			return cmp(v1[0],v2[0])
		# if name is different
		elif v1[1] != v2[1]:
			return cmp(v1[1],v2[1])
		# Compare versions
		else:
			return portage.pkgcmp(v1[1:],v2[1:])

	def matches (self, criterion):
		return system.cpv_matches(self.get_cpv(), criterion)
