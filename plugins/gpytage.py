# -*- coding: utf-8 -*-
#
# File: plugins/gpytage.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from subprocess import Popen

class GPytage (Plugin):
	__author__ = "René 'Necoro' Neumann"
	__description__ = "Adds a menu entry to directly start <b>gpytage</b>, a config editor."
	__dependency__ = ["app-portage/gpytage"]

	def init (self):
		self.add_menu("Config _Editor", self.menu)

	def menu (self, *args):
		Popen(["/usr/bin/gpytage"])

register(GPytage)
