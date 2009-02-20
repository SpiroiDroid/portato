# -*- coding: utf-8 -*-
#
# File: portato/db/database.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

from __future__ import absolute_import, with_statement

from threading import RLock
from functools import wraps

class PkgData (object):
    __slots__ = ("cat", "pkg", "inst", "disabled")

    def __init__ (self, cat, pkg, inst = False, disabled = False):
        self.cat = cat
        self.pkg = pkg
        self.inst = inst
        self.disabled = disabled

    def __iter__ (self):
        return iter((self.cat, self.pkg, self.inst, self.disabled))

    def __cmp__ (self, other):
        return cmp(self.pkg.lower(), other.pkg.lower())

    def __repr__ (self):
        return "<Package (%(cat)s, %(pkg)s, %(inst)s)>" % {"cat" : self.cat, "pkg" : self.pkg, "inst" : self.inst}

class Database (object):

    ALL = _("ALL")

    def __init__ (self):
        self._lock = RLock()

    @staticmethod
    def lock (f):
        @wraps(f)
        def wrapper (self, *args, **kwargs):
            with self._lock:
                r = f(self, *args, **kwargs)
                
            return r
        
        return wrapper

    def populate (self, category = None):
        """Populates the database.
        
        @param category: An optional category - so only packages of this category are inserted.
        @type category: string
        """
        raise NotImplentedError

    def get_cat (self, cat = None, byName = True, showDisabled = False):
        """Returns the packages in the category.
        
        @param cat: category to return the packages from; if None it defaults to C{ALL}
        @type cat: string
        @param byName: selects whether to return the list sorted by name or by installation
        @type byName: boolean
        @param showDisabled: should disabled packages be returned
        @type showDisabled: boolean
        @return: an iterator over the packages
        @rtype: L{PkgData}<iterator>
        """
        raise NotImplentedError

    def get_categories (self, installed = False):
        """Returns all categories.
        
        @param installed: Only return these with at least one installed package.
        @type installed: boolean
        @returns: the list of categories
        @rtype: string<iterator>
        """
        raise NotImplentedError

    def disable (self, cpv):
        """Marks the CPV as disabled.

        @param cpv: the cpv to mark
        """
        raise NotImplentedError

    def reload (self, cat = None):
        """Reloads the given category.
        
        @param cat: category
        @type cat: string
        """
        raise NotImplentedError