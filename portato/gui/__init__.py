# -*- coding: utf-8 -*-
#
# File: portato/gui/__init__.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2010 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>



from ..helper import error
from .exception_handling import register_ex_handler
from .exceptions import PreReqError
from .dialogs import prereq_error_dialog

def run ():
    from .windows.splash import SplashScreen
    s = SplashScreen(_("Loading Backend"))

    register_ex_handler()
    s.show()
    
    from .windows.main import MainWindow
    try:
        m = MainWindow(s)
        s.destroy()
        del s
        
        m.main()
    except PreReqError as e:
        error("Prerequisite not matched. Aborting.")
        prereq_error_dialog(e)
        s.destroy()
