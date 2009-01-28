# -*- coding: utf-8 -*-
#
# File: portato/db/database.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

class PkgData (object):
    __slots__ = ("cat", "pkg", "inst")

    def __init__ (self, cat, pkg, inst):
        self.cat = cat
        self.pkg = pkg
        self.inst = inst

    def __iter__ (self):
        return iter((self.cat, self.pkg, self.inst))

    def __cmp__ (self, other):
        return cmp(self.pkg.lower(), other.pkg.lower())

    def __repr__ (self):
        return "<Package (%(cat)s, %(pkg)s, %(inst)s)>" % {"cat" : self.cat, "pkg" : self.pkg, "inst" : self.inst}

class Database (object):

    ALL = _("ALL")

    def populate (self, category = None):
        """Populates the database.
        
        @param category: An optional category - so only packages of this category are inserted.
        @type category: string
        """
        raise NotImplentedError

    def get_cat (self, cat = None, byName = True):
        """Returns the packages in the category.
        
        @param cat: category to return the packages from; if None it defaults to C{ALL}
        @type cat: string
        @param byName: selects whether to return the list sorted by name or by installation
        @type byName: boolean
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

    def reload (self, cat = None):
        """Reloads the given category.
        
        @param cat: category
        @type cat: string
        """
        raise NotImplentedError
