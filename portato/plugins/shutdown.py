# -*- coding: utf-8 -*-
#
# File: portato/plugins/shutdown.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

import os

def shutdown (*args, **kwargs):
	"""Shutdown the computer. May not work if not root."""
	os.system("shutdown -h now")