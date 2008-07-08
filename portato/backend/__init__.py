# -*- coding: utf-8 -*-
#
# File: portato/backend/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import

from ..helper import debug
from .system_interface import SystemInterface
from .exceptions import BlockedException, PackageNotFoundException, DependencyCalcError, InvalidSystemError

SYSTEM = "portage" # the name of the current system
_sys = None # the SystemInterface-instance

class _Package (object):
	"""Wrapping class from which L{portato.backend.Package} inherits. This is used by the flags module to check
	whether an object is a package. It cannot use the normal Package class as this results in cyclic dependencies."""

	def __init__ (self):
		raise TypeError, "Calling __init__ on portato.backend._Package objects is not allowed."

class SystemWrapper (SystemInterface):
	"""This is a wrapper to the different system interfaces, allowing the direct import via C{from portato.backend import system}.
	With this wrapper a change of the system is propagated to all imports."""
	
	def __getattribute__ (self, name):
		"""Just pass all attribute accesses directly to _sys."""
		return getattr(_sys, name)

def set_system (new_sys):
	"""Sets the current system to a new one.

	@param new_sys: the name of the system to take
	@type new_sys: string"""

	global SYSTEM
	if new_sys != SYSTEM:
		SYSTEM = new_sys
		load_system()

def load_system ():
	"""Loads the current chosen system.

	@raises InvalidSystemError: if an inappropriate system is set"""
	
	global _sys

	if SYSTEM == "portage":
		debug("Setting Portage System")
		from .portage import PortageSystem
		_sys = PortageSystem ()
	elif SYSTEM == "catapult":
		debug("Setting Catapult System")
		from .catapult import CatapultSystem
		_sys = CatapultSystem()
	else:
		raise InvalidSystemError, SYSTEM

system = SystemWrapper()

def is_package(what):
	return isinstance(what, _Package)

load_system()
