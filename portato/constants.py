# -*- coding: utf-8 -*-
#
# File: portato/constants.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
Constants used through out the program. Mainly different pathes.
These should be set during the installation.

@var APP: the application name
@type APP: string
@var VERSION: the current version
@type VERSION: string
@var HOME: shortcut to $HOME
@type HOME: string

@var CONFIG_DIR: The configuration directory.
@type CONFIG_DIR: string
@var CONFIG_LOCATION: L{CONFIG_DIR} plus name of the config file.
@type CONFIG_LOCATION: string

@var ROOT_DIR: Overall root -- normally just '/'.
@type ROOT_DIR: string
@var DATA_DIR: Directory which contains all shared files.
@type DATA_DIR: string

@var ICON_DIR: directory containing the icons
@type ICON_DIR: string
@var APP_ICON: the path of the application icon
@type APP_ICON: string

@var LOCALE_DIR: the path to the directory where the locale files (*.mo) are stored.
@type LOCALE_DIR: string
@var PLUGIN_DIR: Directory containing the plugin xmls.
@type PLUGIN_DIR: string
@var SETTINGS_DIR: Directory containing the user specific settings.
@type SETTINGS_DIR: string
@var TEMPLATE_DIR: Directory containing the UI template files.
@type TEMPLATE_DIR: string

@var REPOURI: the URI of the git repository -- only used in live versions
@type REPOURI: string
@var REVISION: the revision of the live version
@type REVISION: string
"""
import os
from os.path import join as pjoin

# ktsuss does not reset this correctly
if os.getuid() == 0:
    os.environ["HOME"] = "/root"

ROOT_DIR = ""
DATA_DIR = "./"

# icons
ICON_DIR = pjoin(ROOT_DIR, DATA_DIR, "icons/")
APP_ICON = pjoin(ICON_DIR, "portato-icon.png")

# general
APP = "portato"
VERSION = "9999"
HOME = os.environ["HOME"]

# config
CONFIG_DIR = pjoin(ROOT_DIR, "etc/")
CONFIG_LOCATION = pjoin(CONFIG_DIR, "portato.cfg")
SESSION_DIR = pjoin(os.environ["HOME"], ".portato")

# misc dirs
LOCALE_DIR = "i18n/"
PLUGIN_DIR = pjoin(ROOT_DIR, DATA_DIR, "plugins/")
SETTINGS_DIR = pjoin(HOME, "."+APP)
TEMPLATE_DIR = "portato/gui/templates/"

# live versions only
REPOURI = "git://github.com/Necoro/portato.git::master"
REVISION = ""
