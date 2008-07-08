# -*- coding: utf-8 -*-
#
# File: portato/plugin.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2008 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

"""
A module managing the plugins for Portato.
"""

from __future__ import absolute_import
__docformat__ = "restructuredtext"

import os
import os.path as osp
import traceback
from collections import defaultdict
from functools import wraps

from .helper import debug, warning, info, error
from .constants import PLUGIN_DIR
from .backend import system
from . import plugins as plugin_module

class PluginLoadException (Exception):
	"""
	Exception signaling a failed plugin loading.
	"""
	pass

class Menu (object):
	"""
	One single menu entry.

	:IVariables:

		label : string
			The label of the entry. Can have underscores to define the shortcut.

		call
			The function to call, if the entry is clicked.
	"""
	__slots__ = ("label", "call")

	def __init__ (self, label, call):
		self.label = label
		self.call = call

class Call (object):
	"""
	This class represents an object, which is attached to a specified hook.

	:IVariables:

		plugin : `Plugin`
			The plugin where this call belongs to.

		hook : string
			The name of the corresponding hook.

		call
			The function to call.

		type : string
			This is either ``before``, ``after`` or ``override`` and defines the type of the call:

				before
					access before the original function
				override
					access *instead of* the original function. **USE THIS ONLY IF YOU KNOW WHAT YOU ARE DOING**
				after
					access after the original function has been called

			Default: ``before``

		dep : string
			This defines a plugin which should be executed after/before this one.
			``"*"`` means all and ``"-*"`` means none.
	"""
	__slots__ = ("plugin", "hook", "call", "type", "dep")

	def __init__ (self, plugin, hook, call, type = "before", dep = None):
		self.plugin = plugin
		self.hook = hook
		self.call = call
		self.type = type
		self.dep = dep

class Hook (object):
	"""
	Representing a hook with all the `Call` s for the different types.
	"""
			
	__slots__ = ("before", "override", "after")

	def __init__ (self):
		self.before = []
		self.override = None
		self.after = []

class Plugin (object):
	"""
	This is the main plugin object. It is used where ever a plugin is wanted, and it is the one, which needs to be subclassed by plugin authors.

	:CVariables:

		STAT_DISABLED : status
			Status: Disabled.

		STAT_TEMP_ENABLED : status
			Status: Enabled for this session only.

		STAT_ENABLED : status
			Status: Enabled.

		STAT_TEMP_DISABLED : status
			Status: Disabled for this session only.

		STAT_HARD_DISABLED : status
			Status: Forced disabled by program (i.e. because of errors in the plugin).
	"""

	(STAT_DISABLED, STAT_TEMP_ENABLED, STAT_ENABLED, STAT_TEMP_DISABLED) = range(4)
	STAT_HARD_DISABLED = -1

	def __init__ (self, disable = False):
		"""
		:param disable: Forcefully disable the plugin
		:type disable: bool
		"""
		self.__menus = [] #: List of `Menu`
		self.__calls = [] #: List of `Call`
		self._unresolved_deps = False #: Does this plugin has unresolved dependencies?

		self.status = self.STAT_ENABLED #: The status of this plugin
		
		if disable:
			self.status = self.STAT_HARD_DISABLED

	def _init (self):
		"""
		Method called from outside to init the extension parts of this plugin.
		If the current status is `STAT_HARD_DISABLED` or there are unresolved dependencies, the init process is not started.
		"""

		for d in self.deps:
			if not system.find_packages(d, pkgSet="installed", with_version = False):
				self._unresolved_deps = True
				break
		
		if self.status != self.STAT_HARD_DISABLED and not self._unresolved_deps:
			self.init()
	
	def init (self):
		"""
		This method is called by `_init` and should be overriden by the plugin author.

		:precond: No unresolved deps and the status is not `STAT_HARD_DISABLED`.
		"""
		pass

	@property
	def author (self):
		"""
		Returns the plugin's author.
		The author is given by the ``__author__`` variable.

		:rtype: string
		"""
		return getattr(self, "__author__", "")

	@property
	def description (self):
		"""
		Returns the description of this plugin.
		It is given by either a ``__description__`` variable or by the normal class docstring.

		:rtype: string
		"""
		if hasattr(self, "__description__"):
			return self.__description__
		else:
			return getattr(self, "__doc__", "")

	@property
	def name (self):
		"""
		The name of the plugin. If no ``__name__`` variable is given, the class name is taken.

		:rtype: string
		"""
		return getattr(self, "__name__", self.__class__.__name__)

	@property
	def menus (self):
		"""
		Returns an iterator over the menus for this plugin.

		:rtype: iter<`Menu`>
		"""
		return iter(self.__menus)

	@property
	def calls (self):
		"""
		Returns an iterator over the registered calls for this plugin.

		:rtype: iter<`Call`>
		"""
		return iter(self.__calls)

	@property
	def deps (self):
		"""
		Returns an iterator of the dependencies or ``None`` if there are none.
		The dependencies are given in the ``__dependency__`` variable.

		:rtype: None or iter<string>
		"""
		if hasattr(self, "__dependency__"):
			return iter(self.__dependency__)
		else:
			return None

	@property
	def enabled (self):
		"""
		Returns ``True`` if the plugin is enabled.

		:rtype: boolean
		:see: `status`
		"""
		return (self.status in (self.STAT_ENABLED, self.STAT_TEMP_ENABLED))
	
	def add_menu (self, label, callable):
		"""
		Adds a new menu item for this plugin.

		:see: `Menu`
		"""
		self.__menus.append(Menu(label, callable))

	def add_call (self, hook, callable, type = "before", dep = None):
		"""
		Adds a new call for this plugin.

		:see: `Call`
		"""
		self.__calls.append(Call(self, hook, callable, type, dep))


class PluginQueue (object):
	"""
	Class managing and loading the plugins.
	
	:IVariables:

		plugins : `Plugin` []
			The list of managed plugins.

		hooks : string -> `Hook`
			For each hook name map to a `Hook` object holding the corresponding `Call` objects.
	"""

	def __init__ (self):
		"""
		Constructor.
		"""

		self.plugins = []
		self.hooks = defaultdict(Hook)

	def get_plugins (self, list_disabled = True):
		"""
		Returns the plugins.

		:param list_disabled: Also list disabled plugins.
		:type list_disabled: boolean

		:rtype: iter<`Plugin`>
		"""
		return (x for x in self.plugins if (x.enabled or list_disabled))

	def load (self):
		"""
		Load the plugins.
		
		This method scans the `portato.constants.PLUGIN_DIR` for python modules and tries to load them. If the modules are real plugins,
		they have called `register` and thus the plugins are added.
		"""

		# look them up
		plugins = []
		for f in os.listdir(PLUGIN_DIR):
			path = osp.join(PLUGIN_DIR, f)
			if osp.isdir(path):
				if osp.isfile(osp.join(path, "__init__.py")):
					plugins.append(f)
				else:
					debug("'%s' is not a plugin: __init__.py missing", path)
			else:
				if f.endswith(".py"):
					plugins.append(f[:-3])
				elif f.endswith(".pyc") or f.endswith(".pyo"):
					pass # ignore .pyc and .pyo
				else:
					debug("'%s' is not a plugin: not a .py file", path)

		# some magic ...
		plugin_module.__path__.insert(0, PLUGIN_DIR.rstrip("/")) # make the plugins loadable as "portato.plugins.name"
		# add Plugin and register to the builtins, so the plugins always have the correct version :)
		plugin_module.__builtins__["Plugin"] = Plugin
		plugin_module.__builtins__["register"] = register

		for p in plugins: # import them
			try:
				exec "from portato.plugins import %s" % p in {}
			except PluginLoadException, e:
				error(_("Loading plugin '%(plugin)s' failed: %(error)s"), {"plugin" : p, "error" : e.message})
			except:
				tb = traceback.format_exc()
				error(_("Loading plugin '%(plugin)s' failed: %(error)s"), {"plugin" : p, "error" : tb})

		self._organize()

	def add (self, plugin, disable = False):
		"""
		Adds a plugin to the internal list.

		:Parameters:

			plugin : `Plugin`
				``Plugin`` subclass or instance to add. If a class is passed, it is instantiated.

			disable : boolean
				Disable the plugin.

		:raise PluginLoadException: passed plugin is not of class `Plugin`
		"""

		if callable(plugin) and Plugin in plugin.__bases__:
			p = plugin(disable = disable) # need an instance and not the class
		elif isinstance(plugin, Plugin):
			p = plugin
			if disable:
				p.status = p.STAT_HARD_DISABLED
		else:
			raise PluginLoadException, "Is neither a subclass nor an instance of Plugin."

		p._init()

		self.plugins.append(p)
		
		if p.status == p.STAT_HARD_DISABLED:
			msg = _("Plugin is disabled!")
		elif p._unresolved_deps:
			msg = _("Plugin has unresolved dependencies - disabled!")
		else:
			msg = ""
		
		info("%s %s", _("Plugin '%s' loaded.") % p.name, msg)

	def hook (self, hook, *hargs, **hkwargs):
		"""
		The decorator to use in the program.
		All parameters except ``hook`` are passed to plugins.

		:param hook: the name of the hook
		:type hook: string
		"""

		def hook_decorator (func):
			"""
			The real decorator.
			"""
			h = self.hooks[hook]

			active = Hook()

			# remove disabled
			for type in ("before", "after"):
				calls = getattr(h, type)
				aCalls = getattr(active, type)
				for call in calls:
					if call.plugin.enabled:
						aCalls.append(call)

			if h.override and h.override.plugin.enabled:
				active.override = h.override

			@wraps(func)
			def wrapper (*args, **kwargs):
				ret = None

				# before
				for call in active.before:
					debug("Accessing hook '%(hook)s' of plugin '%(plugin)s' (before).", {"hook" : hook, "plugin": call.plugin.name})
					call.call(*hargs, **hkwargs)
				
				if active.override: # override
					info(_("Overriding hook '%(hook)s' with plugin '%(plugin)s'."), {"hook": hook, "plugin": active.override.plugin.name})
					ret = active.override.call(*hargs, **hkwargs)
				else: # normal
					ret = func(*args, **kwargs)

				# after
				for call in active.after:
					debug("Accessing hook '%(hook)s' of plugin '%(plugin)s' (after).", {"hook": hook, "plugin": call.plugin.name})
					call.call(*hargs, **hkwargs)

				return ret

			return wrapper

		return hook_decorator

	def _organize (self):
		"""
		Organizes the lists of `Call` in a way, that all dependencies are fullfilled.
		"""
		unresolved_before = defaultdict(list)
		unresolved_after = defaultdict(list)
		star_before = defaultdict(Hook) # should be _before_ all other
		star_after = defaultdict(Hook) # should be _after_ all other

		for plugin in self.plugins: # plugins
			for call in plugin.calls: # hooks in plugin
				if call.type == "before":
					if call.dep is None: # no dependency -> straight add
						self.hooks[call.hook].before.append(call)
					elif call.dep == "*":
						self.hooks[call.hook].before.insert(0, call)
					elif call.dep == "-*":
						star_before[call.hook].append(call)
					else:
						named = [x.plugin.name for x in self.hooks[call.hook].before]
						if call.dep in named:
							self.hooks[call.hook].before.insert(named.index(call.dep), call)
						else:
							unresolved_before[call.hook].append(call)

				elif call.type == "after":
					if call.dep is None: # no dependency -> straight add
						self.hooks[call.hook].after.append(call)
					elif call.dep == "*":
						star_after[call.hook].append(call)
					elif call.dep == "-*":
						self.hooks[call.hook].after.insert(0, call)
					else:
						named = [x.plugin.name for x in self.hooks[call.hook].after]
						if call.dep in named:
							self.hooks[call.hook].after.insert(named.index(call.dep)+1, call)
						else:
							unresolved_after[call.hook].append(call)
				
				# type = "override"
				elif call.type == "override":
					if self.hooks[call.hook].override:
						warning(_("For hook '%(hook)s' an override is already defined by plugin '%(plugin)s'!"), {"hook": call.hook, "plugin": self.hooks[call.hook].override.plugin.name})
						warning(_("It is now replaced by the one from plugin '%s'!"), call.plugin.name)
					
					self.hooks[call.hook].override = call
					continue
		
		self._resolve_unresolved(unresolved_before, unresolved_after)

		for hook, calls in star_before.iteritems():
			self.hooks[hook].before.extend(calls) # append the list

		for hook, calls in star_after.iteritems():
			self.hooks[hook].after.extend(calls) # append the list


	def _resolve_unresolved (self, before, after):
		def resolve(hook, list, type, add):
			if not list: 
				return
			
			callList = getattr(self.hooks[hook], type)
			named = [x.plugin.name for x in callList]

			while list and named:
				newNamed = [] # use newNamed, so in each iteration only the plugins inserted last are searched
				for call in list[:]:
					if call.dep in named:
						callList.insert(named.index(call.dep)+add, call)
						list.remove(call)
						newNamed.append(call.plugin.name)

				named = newNamed

			for l in list:
				warning(_("Command for hook '%(hook)s' in plugin '%(plugin)s' could not be added due to missing dependant: '%(dep)s'!"), {"hook": hook, "plugin": l.plugin.name, "dep": l.dep})

		for hook in before:
			resolve(hook, before[hook], "before", 0)
		
		for hook in after:
			resolve(hook, after[hook], "after", 1)


__plugins = None

def load_plugins():
	"""
	Loads the plugins.
	"""
	
	global __plugins
	if __plugins is None:
		__plugins = PluginQueue()
		__plugins.load()
	

def get_plugin_queue():
	"""
	Returns the actual `PluginQueue`. If it is ``None``, they are not being loaded yet.

	:rtype: `PluginQueue` or ``None``"""
	return __plugins

def hook(hook, *args, **kwargs):
	"""
	Shortcut to `PluginQueue.hook`. If no `PluginQueue` is loaded, this does nothing.
	"""
	if __plugins is None:
		def pseudo_decorator(f):
			return f
		return pseudo_decorator
	else:
		return __plugins.hook(hook, *args, **kwargs)

def register (plugin, disable = False):
	"""
	Registers a plugin.

	:see: `PluginQueue.add`
	"""
	if __plugins is not None:
		__plugins.add(plugin, disable)
