# -*- coding: utf-8 -*-
#
# File: portato/gui/gtk/windows.py
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2007 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

# gtk stuff
import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
import gobject

# our backend stuff
from portato.helper import *
from portato.constants import CONFIG_LOCATION, VERSION, DATA_DIR
from portato.backend import flags, system
from portato.backend.exceptions import *

# plugins
from portato import plugin

# more GUI stuff
from portato.gui.gui_helper import Database, Config, EmergeQueue
from dialogs import *
from wrapper import GtkTree, GtkConsole
from usetips import UseTips

# other
import types

GLADE_FILE = DATA_DIR+"portato.glade"

class Window:
	def __init__ (self):
		self.tree = gtk.glade.XML(GLADE_FILE, root = self.__class__.__name__)
		self.tree.signal_autoconnect(self)
		self.window = self.tree.get_widget(self.__class__.__name__)

	@staticmethod
	def watch_cursor (func):
		"""This is a decorator for functions being so time consuming, that it is appropriate to show the watch-cursor.
		@attention: this function relies on the gtk.Window-Object being stored as self.window"""
		def wrapper (self, *args, **kwargs):
			ret = None
			def cb_idle():
				try:
					ret = func(self, *args, **kwargs)
				finally:
					self.window.window.set_cursor(None)
				return False
			
			watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
			self.window.window.set_cursor(watch)
			gobject.idle_add(cb_idle)
			return ret
		return wrapper

	def create_popup (self, name):
		popupTree = gtk.glade.XML(GLADE_FILE, root = name)
		popupTree.signal_autoconnect(self)
		return popupTree.get_widget(name)

class AbstractDialog (Window):
	"""A class all our dialogs get derived from. It sets useful default vars and automatically handles the ESC-Button."""

	def __init__ (self, parent):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		Window.__init__(self)

		# set parent
		self.window.set_transient_for(parent)
		
		# catch the ESC-key
		self.window.connect("key-press-event", self.cb_key_pressed)

	def cb_key_pressed (self, widget, event):
		"""Closes the window if ESC is pressed."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Escape":
			self.close()
			return True
		else:
			return False

	def close (self, *args):
		self.window.destroy()

class AboutWindow (AbstractDialog):
	"""A window showing the "about"-informations."""

	def __init__ (self, parent, plugins):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window"""
		
		AbstractDialog.__init__(self, parent)

		label = self.tree.get_widget("aboutLabel")
		label.set_markup("""
<big><b>Portato v.%s</b></big>
A Portage-GUI
		
This software is licensed under the terms of the GPLv2.
Copyright (C) 2006-2007 René 'Necoro' Neumann &lt;necoro@necoro.net&gt;

<small>Thanks to Fred for support and ideas :P</small>
""" % VERSION)

		view = self.tree.get_widget("pluginList")
		store = gtk.ListStore(str,str)
		
		view.set_model(store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Plugin", cell, markup = 0)
		view.append_column(col)
		
		col = gtk.TreeViewColumn("Authors", cell, text = 1)
		view.append_column(col)

		for p in [("<b>"+n+"</b>",a) for n,a in plugins]:
			store.append(p)

		self.window.show_all()

class SearchWindow (AbstractDialog):
	"""A window showing the results of a search process."""
	
	def __init__ (self, parent, list, jump_to):
		"""Constructor.

		@param parent: parent-window
		@type parent: gtk.Window
		@param list: list of results to show
		@type list: string[]
		@param jump_to: function to call if "OK"-Button is hit
		@type jump_to: function(string)"""
		
		AbstractDialog.__init__(self, parent)
		
		self.list = list # list to show
		self.jump_to = jump_to # function to call for jumping
		
		# combo box
		self.combo = gtk.combo_box_new_text()
		for x in list:
			self.combo.append_text(x)
		self.combo.set_active(0) # first item
		self.combo.connect("key-press-event", self.cb_key_pressed_combo)
		
		self.window.add(self.combo)

		# finished --> show
		self.window.show_all()

	def cb_key_pressed_combo (self, widget, event):
		"""Emulates a ok-button-click."""
		keyname = gtk.gdk.keyval_name(event.keyval)
		if keyname == "Return": # take it as an "OK" if Enter is pressed
			self.window.destroy()
			self.jump_to(self.list[self.combo.get_active()])
			return True
		else:
			return False

class PreferenceWindow (AbstractDialog):
	"""Window displaying some preferences."""
	
	# all checkboxes in the window
	# widget name -> option name
	checkboxes = {
			"debugCheck"			: "debug_opt",
			"deepCheck"				: "deep_opt",
			"newUseCheck"			: "newuse_opt",
			"maskPerVersionCheck"	: "maskPerVersion_opt",
			"usePerVersionCheck"	: "usePerVersion_opt",
			"useTipsCheck"			: ("useTips_opt", "gtk_sec"),
			"testPerVersionCheck"	: "testingPerVersion_opt"
			}
	
	# all edits in the window
	# widget name -> option name
	edits = {
			"maskFileEdit"		: "maskFile_opt",
			"testFileEdit"		: "testingFile_opt",
			"useFileEdit"		: "useFile_opt",
			"syncCommandEdit"	: "syncCmd_opt"
			}

	# mapping from the radio buttons to the system name
	# widget name -> option
	system_radios = {
			"portageRadio" : "portage",
			"pkgCoreRadio" : "pkgcore",
			"paludisRadio" : "paludis"
			}

	# mapping from the system name to the radio button
	# option -> widget name
	systems = {}
	systems.update(zip(system_radios.values(), system_radios.keys()))

	def __init__ (self, parent, cfg):
		"""Constructor.

		@param parent: parent window
		@type parent: gtk.Window
		@param cfg: configuration object
		@type cfg: gui_helper.Config"""
		
		AbstractDialog.__init__(self, parent)

		# our config
		self.cfg = cfg
		
		# set the bg-color of the hint
		hintEB = self.tree.get_widget("hintEB")
		hintEB.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#f3f785"))

		# the checkboxes
		for box in self.checkboxes:
			val = self.checkboxes[box]
			if type(val) == types.TupleType:
				self.tree.get_widget(box).\
						set_active(self.cfg.get_boolean(val[0], section = self.cfg.const[val[1]]))
			else:
				self.tree.get_widget(box).\
						set_active(self.cfg.get_boolean(val))

		# the edits
		for edit in self.edits:
			self.tree.get_widget(edit).\
					set_text(self.cfg.get(self.edits[edit]))

		# the system radios
		self.tree.get_widget(self.systems[self.cfg.get("system_opt").lower()]).set_active(True)

		self.window.show_all()

	def _save(self):
		"""Sets all options in the Config-instance."""
		
		for box in self.checkboxes:
			val = self.checkboxes[box]
			if type(val) == types.TupleType:
				self.cfg.set_boolean(val[0], self.tree.get_widget(box).get_active(), section = self.cfg.const[val[1]])
			else:
				self.cfg.set_boolean(val, self.tree.get_widget(box).get_active())

		for edit in self.edits:
			self.cfg.set(self.edits[edit],self.tree.get_widget(edit).get_text())

		for radio in self.system_radios:
			if self.tree.get_widget(radio).get_active():
				self.cfg.set("system_opt", self.system_radios[radio])
					
	def cb_ok_clicked(self, button):
		"""Saves, writes to config-file and closes the window."""
		self._save()
		try:
			self.cfg.write()
		except IOError, e:
			io_ex_dialog(e)

		self.window.destroy()

	def cb_cancel_clicked (self, button):
		"""Just closes - w/o saving."""
		self.window.destroy()

class EbuildWindow (AbstractDialog):
	"""The window showing the ebuild."""

	def __init__ (self, parent, package):
		"""Constructor.

		@param parent: the parent window
		@type parent: gtk.Window
		@param package: the actual package
		@type package: backend.Package"""

		AbstractDialog.__init__(self,parent)
		
		# we want it to get minimized
		self.window.set_transient_for(None)

		self.window.set_title(package.get_cpv())
		
		# set geometry (same as MainWindow)
		mHeight = 800
		if gtk.gdk.screen_height() <= 800: mHeight = 600
		self.window.set_geometry_hints (self.window, min_width = 800, min_height = mHeight, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())

		self.package = package

		self._build_view()
		self._show()

	def _build_view(self):
		"""Creates the buffer and the view."""
		self.buf = gtk.TextBuffer()
		self.view = gtk.TextView(self.buf)

	def _show (self):
		"""Fill the buffer with content and shows the window."""
		self.view.set_editable(False)
		self.view.set_cursor_visible(False)
		
		try: # read ebuild
			f = open(self.package.get_ebuild_path(), "r")
			lines = f.readlines()
			f.close()
		except IOError,e:
			io_ex_dialog(e)
			return

		self.buf.set_text("".join(lines))

		self.tree.get_widget("ebuildScroll").add(self.view)
		self.window.show_all()

class PackageTable:
	"""A window with data about a specfic package."""

	def __init__ (self, main):
		"""Build up window contents.
		
		@param main: the main window
		@type main: MainWindow"""

		self.main = main
		self.tree = main.tree
		self.window = main.window
		self.tree.signal_autoconnect(self)
		
		# the table
		self.table = self.tree.get_widget("PackageTable")
		
		# the combo vb
		self.comboVB = self.tree.get_widget("comboVB")

		# chechboxes
		self.installedCheck = self.tree.get_widget("installedCheck")
		self.maskedCheck = self.tree.get_widget("maskedCheck")
		self.testingCheck = self.tree.get_widget("testingCheck")

		# labels
		self.descLabel = self.tree.get_widget("descLabel")
		self.notInSysLabel = self.tree.get_widget("notInSysLabel")
		self.missingLabel = self.tree.get_widget("missingLabel")
		
		# buttons
		self.emergeBtn = self.tree.get_widget("pkgEmergeBtn")
		self.unmergeBtn = self.tree.get_widget("pkgUnmergeBtn")
		self.cancelBtn = self.tree.get_widget("pkgCancelBtn")
		self.ebuildBtn = self.tree.get_widget("pkgEbuildBtn")
		
		# useList
		self.useListScroll = self.tree.get_widget("useListScroll")
		self.useList = None

	def update (self, cp, queue = None, version = None, doEmerge = True, instantChange = False):
		"""Updates the table to show the contents for the package.
		
		@param cp: the selected package
		@type cp: string (cp)
		@param queue: emerge-queue (if None the emerge-buttons are disabled)
		@type queue: EmergeQueue
		@param version: if not None, specifies the version to select
		@type version: string
		@param doEmerge: if False, the emerge buttons are disabled
		@type doEmerge: False
		@param instantChange: if True the changed keywords are updated instantly
		@type instantChange: boolean"""
		
		self.cp = cp # category/package
		self.version = version # version - if not None this is used
		self.queue = queue
		self.doEmerge = doEmerge
		self.instantChange = instantChange

		# packages and installed packages
		self.packages = system.sort_package_list(system.find_packages(cp, masked = True))
		self.instPackages = system.sort_package_list(system.find_installed_packages(cp, masked = True))

		# version-combo-box
		self.vCombo = self.build_vers_combo()
		if not self.doEmerge: self.vCombo.set_sensitive(False)
		children = self.comboVB.get_children()
		if children:
			for c in children: 
				self.comboVB.remove(c)
		self.comboVB.pack_start(self.vCombo)

		# the label (must be here, because it depends on the combo box)
		desc = self.actual_package().get_package_settings("DESCRIPTION").replace("&","&amp;")
		if not desc: 
			desc = "<no description>"
			use_markup = False
		else:
			desc = "<b>"+desc+"</b>"
			use_markup = True
		desc = "<i><u>"+self.actual_package().get_cp()+"</u></i>\n\n"+desc
		self.descLabel.set_use_markup(use_markup)
		self.descLabel.set_label(desc)
		
		if not self.queue or not self.doEmerge: 
			self.emergeBtn.set_sensitive(False)
			self.unmergeBtn.set_sensitive(False)
		
		# current status
		self.cb_combo_changed(self.vCombo)
		self.table.show_all()

	def hide (self):
		self.table.hide_all()

	def fill_use_list(self, store):
		"""Fills a given ListStore with the use-flag data.
		
		@param store: the store to fill
		@type store: gtk.ListStore"""

		pkg = self.actual_package()
		pkg_flags = pkg.get_all_use_flags()
		pkg_flags.sort()
	
		actual_exp = None
		actual_exp_it = None

		for use in pkg_flags:
			exp = pkg.use_expanded(use, suggest = actual_exp)
			if exp is not None:
				if exp != actual_exp:
					actual_exp_it = store.append(None, [None, exp, "<i>This is an expanded use flag and cannot be selected</i>"])
					actual_exp = exp
			else:
				actual_exp_it = None
				actual_exp = None

			store.append(actual_exp_it, [pkg.is_use_flag_enabled(use), use, system.get_use_desc(use, self.cp)])
		
		return store

	def build_use_list (self):
		"""Builds the useList."""
		store = gtk.TreeStore(bool, str, str)
		self.fill_use_list(store)

		# build view
		view = gtk.TreeView(store)
		cell = gtk.CellRendererText()
		tCell = gtk.CellRendererToggle()
		tCell.set_property("activatable", True)
		tCell.connect("toggled", self.cb_use_flag_toggled, store)
		view.append_column(gtk.TreeViewColumn("Enabled", tCell, active = 0))
		view.append_column(gtk.TreeViewColumn("Flags", cell, text = 1))
		view.append_column(gtk.TreeViewColumn("Description", cell, markup = 2))

		view.set_search_column(1)
		view.set_enable_tree_lines(True)

		if store.iter_n_children(None) == 0: # if there are no nodes in the list ...
			view.set_child_visible(False) # ... do not show the list
		else:
			view.set_child_visible(True)
		return view

	def build_vers_combo (self):
		"""Creates the combo box with the different versions."""
		combo = gtk.combo_box_new_text()

		# append versions
		for s in [x.get_version() for x in self.packages]:
			combo.append_text(s)
		
		# activate the first one
		try:
			best_version = ""
			if self.version:
				best_version = self.version
			else:
				best_version = system.find_best_match(self.packages[0].get_cp(), (self.instPackages != [])).get_version()
			for i in range(len(self.packages)):
				if self.packages[i].get_version() == best_version:
					combo.set_active(i)
					break
		except AttributeError: # no package found
#			debug('catched AttributeError => no "best package" found. Selected first one.')
			combo.set_active(0)

		combo.connect("changed", self.cb_combo_changed)
		
		return combo

	def actual_package (self):
		"""Returns the actual selected package.
		
		@returns: the actual selected package
		@rtype: backend.Package"""
		
		return self.packages[self.vCombo.get_active()]

	def _update_keywords (self, emerge, update = False):
		if emerge:
			try:
				try:
					self.queue.append(self.actual_package().get_cpv(), unmerge = False, update = update)
				except PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
						self.queue.append(self.actual_package().get_cpv(), unmerge = False, unmask = True, update = update)
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
		else:
			try:
				self.queue.append(self.actual_package().get_cpv(), unmerge = True)
			except PackageNotFoundException, e:
				debug("Package could not be found",e[0], error = 1)
				#masked_dialog(e[0])

	def cb_combo_changed (self, combo):
		"""Callback for the changed ComboBox.
		It then rebuilds the useList and the checkboxes."""
		
		# remove old useList
		w = self.useListScroll.get_child()
		if w:
			self.useListScroll.remove(w)
		
		# build new
		self.useList = self.build_use_list()
		self.useListScroll.add(self.useList)
		pkg = self.actual_package()
		
		#
		# rebuild the buttons and checkboxes in all the different manners which are possible
		#
		if (not pkg.is_in_system()) or pkg.is_missing_keyword():
			if not pkg.is_in_system():
				self.missingLabel.hide()
				self.notInSysLabel.show()
			else: # missing keyword
				self.missingLabel.show()
				self.notInSysLabel.hide()
			
			self.installedCheck.hide()
			self.maskedCheck.hide()
			self.testingCheck.hide()
			self.emergeBtn.set_sensitive(False)
		else: # normal package
			self.missingLabel.hide()
			self.notInSysLabel.hide()
			self.installedCheck.show()
			self.maskedCheck.show()
			self.testingCheck.show()
			if self.doEmerge:
				self.emergeBtn.set_sensitive(True)
			self.installedCheck.set_active(pkg.is_installed())
			
			if pkg.is_masked(use_changed = False) and not pkg.is_masked(use_changed = True):
				self.maskedCheck.set_label("<i>(Masked)</i>")
				self.maskedCheck.get_child().set_use_markup(True)
			else:
				self.maskedCheck.set_label("Masked")
			
			if pkg.is_locally_masked():
				self.maskedCheck.set_label("<b>Masked</b>")
				self.maskedCheck.get_child().set_use_markup(True)
				self.maskedCheck.set_active(True)
			else:
				self.maskedCheck.set_active(pkg.is_masked(use_changed = False))
			
			if pkg.is_testing(use_keywords = False) and not pkg.is_testing(use_keywords = True):
				self.testingCheck.set_label("<i>(Testing)</i>")
				self.testingCheck.get_child().set_use_markup(True)
			else:
				self.testingCheck.set_label("Testing")
			
			self.testingCheck.set_active(pkg.is_testing(use_keywords = False))

		if self.doEmerge:
			# set emerge-button-label
			if not self.actual_package().is_installed():
				self.emergeBtn.set_label("E_merge")
				self.unmergeBtn.set_sensitive(False)
			else:
				self.emergeBtn.set_label("Re_merge")
				self.unmergeBtn.set_sensitive(True)
		
		self.table.show_all()

		return True

	def cb_button_pressed (self, b, event):
		"""Callback for pressed checkboxes. Just quits the event-loop - no redrawing."""
		if not isinstance(b, gtk.CellRendererToggle):
			b.emit_stop_by_name("button-press-event")
		return True

	def cb_package_revert_clicked (self, button):
		"""Callback for pressed revert-button."""
		self.actual_package().remove_new_use_flags()
		self.actual_package().remove_new_masked()
		self.actual_package().remove_new_testing()
		self.cb_combo_changed(self.vCombo)
		if self.instantChange:
			self._update_keywords(True, update = True)
		return True

	def cb_package_emerge_clicked (self, button):
		"""Callback for pressed emerge-button. Adds the package to the EmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			self._update_keywords(True)
			self.main.notebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_package_unmerge_clicked (self, button):
		"""Callback for pressed unmerge-button clicked. Adds the package to the UnmergeQueue."""
		if not am_i_root():
			not_root_dialog()
		else:
			self._update_keywords(False)
			self.main.notebook.set_current_page(self.main.QUEUE_PAGE)
		return True

	def cb_package_ebuild_clicked(self, button):
		hook = plugin.hook("open_ebuild", self.actual_package(), self.window)
		hook(EbuildWindow)(self.window, self.actual_package())
		return True

	def cb_testing_toggled (self, button):
		"""Callback for toggled testing-checkbox."""
		status = button.get_active()

		if self.actual_package().is_testing(use_keywords = False) == status:
			return False

		if not self.actual_package().is_testing(use_keywords = True):
			self.actual_package().set_testing(False)
			button.set_label("Testing")
			button.set_active(True)
		else:
			self.actual_package().set_testing(True)
			if self.actual_package().is_testing(use_keywords=False):
				button.set_label("<i>(Testing)</i>")
				button.get_child().set_use_markup(True)
				button.set_active(True)

		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_masked_toggled (self, button):
		"""Callback for toggled masking-checkbox."""
		status = button.get_active()
		pkg = self.actual_package()

		if pkg.is_masked(use_changed = False) == status and not pkg.is_locally_masked():
			return False

		if pkg.is_locally_masked() and status:
			return False
	
		if not pkg.is_masked(use_changed = True):
			pkg.set_masked(True)
			if pkg.is_locally_masked():
				button.set_label("<b>Masked</b>")
				button.get_child().set_use_markup(True)
			else:
				button.set_label("Masked")

			button.set_active(True)
		else:
			locally = pkg.is_locally_masked()
			pkg.set_masked(False)
			if pkg.is_masked(use_changed=False) and not locally:
				button.set_label("<i>(Masked)</i>")
				button.get_child().set_use_markup(True)
				button.set_active(True)
			else:
				button.set_label("Masked")
		
		if self.instantChange:
			self._update_keywords(True, update = True)
		
		return True

	def cb_use_flag_toggled (self, cell, path, store):
		"""Callback for a toggled use-flag button."""
		flag = store[path][1]
		pkg = self.actual_package()
		
		if flag in pkg.get_global_settings("USE_EXPAND").split(" "): # ignore expanded flags
			return False

		store[path][0] = not store[path][0]
		prefix = ""
		if not store[path][0]:
			prefix = "-"
		
		pkg.set_use_flag(prefix+flag)	
		if self.instantChange:
			self._update_keywords(True, update = True)
	
		return True

class MainWindow (Window):
	"""Application main window."""

	# NOTEBOOK PAGE CONSTANTS
	PKG_PAGE = 0
	QUEUE_PAGE = 1
	CONSOLE_PAGE = 2

	def __init__ (self):	
		"""Build up window"""

		# main window stuff
		Window.__init__(self)
		self.window.set_title(("Portato (%s)" % VERSION))
		mHeight = 800
		if gtk.gdk.screen_height() <= 800: mHeight = 600
		self.window.set_geometry_hints (self.window, min_width = 600, min_height = mHeight, max_height = gtk.gdk.screen_height(), max_width = gtk.gdk.screen_width())

		# booleans
		self.doUpdate = False

		# installed pixbuf
		self.instPixbuf = self.window.render_icon(gtk.STOCK_YES, gtk.ICON_SIZE_MENU)
		
		# package db
		self.db = Database()
		self.db.populate()

		# config
		try:
			self.cfg = Config(CONFIG_LOCATION)
		except IOError, e:
			io_ex_dialog(e)
			raise

		self.cfg.modify_external_configs()

		# set plugins and plugin-menu
		plugin.load_plugins()
		menus = plugin.get_plugins().get_plugin_menus()
		if menus:
			self.tree.get_widget("pluginMenuItem").set_no_show_all(False)
			pluginMenu = self.tree.get_widget("pluginMenu")

			for m in menus:
				item = gtk.MenuItem(m.label)
				item.connect("activate", m.call)
				pluginMenu.append(item)

		# set vpaned position
		vpaned = self.tree.get_widget("vpaned")
		vpaned.set_position(mHeight/2)

		# cat and pkg list
		self.catList = self.tree.get_widget("catList")
		self.pkgList = self.tree.get_widget("pkgList")
		self.build_cat_list()
		self.build_pkg_list()

		# queue list
		self.useTips = UseTips(0, self.cfg)
		self.queueList = self.tree.get_widget("queueList")
		self.build_queue_list()

		# the terminal
		self.console = GtkConsole()
		self.termHB = self.tree.get_widget("termHB")
		self.build_terminal()
		
		# notebook
		self.notebook = self.tree.get_widget("notebook")
		self.window.show_all()
		
		# table
		self.packageTable = PackageTable(self)
		self.packageTable.hide()

		# popups
		self.queuePopup = self.create_popup("queuePopup")
		self.consolePopup = self.create_popup("consolePopup")

		# set emerge queue
		self.queueTree = GtkTree(self.queueList.get_model())
		self.queue = EmergeQueue(console = self.console, tree = self.queueTree, db = self.db, title_update = self.title_update)

	def show_package (self, *args, **kwargs):
		self.packageTable.update(*args, **kwargs)
		self.notebook.set_current_page(self.PKG_PAGE)

	def build_terminal (self):
		"""Builds the terminal."""
		
		self.console.set_scrollback_lines(1024)
		self.console.set_scroll_on_output(True)
		self.console.set_font_from_string("Monospace 11")
		self.console.connect("button-press-event", self.cb_right_click)
		termScroll = gtk.VScrollbar(self.console.get_adjustment())
		self.termHB.pack_start(self.console, True, True)
		self.termHB.pack_start(termScroll, False)

	def build_queue_list (self):
		"""Builds the queue list."""

		store = gtk.TreeStore(str,str)
		
		self.queueList.set_model(store)
		
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Queue", cell, text = 0)
		self.queueList.append_column(col)
		
		col = gtk.TreeViewColumn("Options", cell, markup = 1)
		self.queueList.append_column(col)

		self.useTips.add_view(self.queueList)

	def build_cat_list (self):
		"""Builds the category list."""
		
		store = gtk.ListStore(str)

		# build categories
		for p in system.list_categories():
			store.append([p])
		# sort them alphabetically
		store.set_sort_column_id(0, gtk.SORT_ASCENDING)

		self.catList.set_model(store)
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn("Categories", cell, text = 0)
		self.catList.append_column(col)

	def build_pkg_list (self, name = None):
		"""Builds the package list.
		
		@param name: name of the selected catetegory
		@type name: string"""
		
		store = gtk.ListStore(str, gtk.gdk.Pixbuf)
		self.fill_pkg_store(store,name)
		
		# build view
		self.pkgList.set_model(store)
		
		col = gtk.TreeViewColumn("Packages")

		# adding the pixbuf
		cell = gtk.CellRendererPixbuf()
		col.pack_start(cell, False)
		col.add_attribute(cell, "pixbuf", 1)
		
		# adding the package name
		cell = gtk.CellRendererText()
		col.pack_start(cell, True)
		col.add_attribute(cell, "text", 0)
		
		self.pkgList.append_column(col)

	def fill_pkg_store (self, store, name = None):
		"""Fills a given ListStore with the packages in a category.
		
		@param store: the store to fill
		@type store: gtk.ListStore
		@param name: the name of the category
		@type name: string
		@returns: the filled store
		@rtype: gtk.ListStore"""

		if name:
			for pkg, is_inst in self.db.get_cat(name):
				if is_inst:
					icon = self.instPixbuf
				else:
					icon = None
				store.append([pkg, icon])
		return store

	def jump_to (self, cp):
		"""Is called when we want to jump to a specific package."""
		self.show_package(cp, self.queue)

	def title_update (self, title):
		
		if title == None: title = "Console"
		else: title = ("Console (%s)" % title)

		gobject.idle_add(self.notebook.set_tab_label_text, self.termHB, title)

	def cb_cat_list_selection (self, view):
		"""Callback for a category-list selection. Updates the package list with the packages in the category."""
		# get the selected category
		sel = view.get_selection()
		store, it = sel.get_selected()
		if it:
			self.selCatName = store.get_value(it, 0)
			self.pkgList.get_model().clear()
			self.fill_pkg_store(self.pkgList.get_model(), self.selCatName)
		return True

	def cb_pkg_list_selection (self, view):
		"""Callback for a package-list selection. Updates the package info."""
		sel = view.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 0)
			self.show_package(self.selCatName+"/"+package, self.queue)
		return True

	def cb_row_activated (self, view, path, *args):
		"""Callback for an activated row in the emergeQueue. Opens a package window."""
		store = self.queueTree
		if len(path) > 1:
			iterator = store.get_original().get_iter(path)
			if store.is_in_emerge(iterator):
				package = store.get_value(iterator, 0)
				cat, name, vers, rev = system.split_cpv(package)
				if rev != "r0": vers = vers+"-"+rev
				self.show_package(cat+"/"+name, queue = self.queue, version = vers, instantChange = True, doEmerge = False)
		return True

	def cb_emerge_clicked (self, action):
		"""Do emerge."""
		
		self.notebook.set_current_page(self.CONSOLE_PAGE)
		
		if len(flags.newUseFlags) > 0:
			changed_flags_dialog("use flags")
			flags.write_use_flags()
		
		if len(flags.new_masked)>0 or len(flags.new_unmasked)>0 or len(flags.newTesting)>0:
			debug("new masked:",flags.new_masked)
			debug("new unmasked:", flags.new_unmasked)
			debug("new testing:", flags.newTesting)
			changed_flags_dialog("masking keywords")
			flags.write_masked()
			flags.write_testing()
			system.reload_settings()
		
		if not self.doUpdate:
			self.queue.emerge(force=True)
		else:
			self.queue.update_world(force=True, newuse = self.cfg.get_boolean("newuse_opt"), deep = self.cfg.get_boolean("deep_opt"))
			self.doUpdate = False
		
	def cb_unmerge_clicked (self, button):
		"""Do unmerge."""

		self.notebook.set_current_page(self.CONSOLE_PAGE)
		self.queue.unmerge(force=True)
		return True

	@Window.watch_cursor
	def cb_update_clicked (self, action):
		if not am_i_root():
			not_root_dialog()
		
		else:
			updating = system.update_world(newuse = self.cfg.get_boolean("newuse_opt"), deep = self.cfg.get_boolean("deep_opt"))

			debug("updating list:", [(x.get_cpv(), y.get_cpv()) for x,y in updating],"--> length:",len(updating))
			try:
				try:
					for pkg, old_pkg in updating:
						self.queue.append(pkg.get_cpv(), unmask = False)
				except PackageNotFoundException, e:
					if unmask_dialog(e[0]) == gtk.RESPONSE_YES:
						for pkg, old_pkg in updating:
							self.queue.append(pkg.get_cpv(), unmask = True)
			
			except BlockedException, e:
				blocked_dialog(e[0], e[1])
				self.queue.remove_children(self.queue.emergeIt)
			if len(updating): self.doUpdate = True
		return True

	def cb_remove_clicked (self, button):
		"""Removes a selected item in the (un)emerge-queue if possible."""
		selected = self.queueList.get_selection()

		if selected:
			model, iter = selected.get_selected()
			
			if iter == None: return False

			if not model.iter_parent(iter): # top-level
				if model.iter_n_children(iter) > 0: # and has children which can be removed :)
					if remove_queue_dialog() == gtk.RESPONSE_YES :
						self.queue.remove_children(iter)
						self.doUpdate = False
			
			elif model.iter_parent(model.iter_parent(iter)): # this is in the 3rd level => dependency
				remove_deps_dialog()
			else:
				self.queue.remove_with_children(iter)
				self.doUpdate = False
		
		return True

	def cb_sync_clicked (self, action):
		if not am_i_root():
			not_root_dialog()
		else:
			self.notebook.set_current_page(self.CONSOLE_PAGE)
			cmd = self.cfg.get("syncCmd_opt")

			if cmd != "emerge --sync":
				cmd = cmd.split()
				self.queue.sync(cmd)
			else:
				self.queue.sync()

	def cb_save_flags_clicked (self, action):
		if not am_i_root():
			not_root_dialog()
		else:
			flags.write_use_flags()
			flags.write_testing()
			flags.write_masked()
	
	@Window.watch_cursor
	def cb_reload_clicked (self, action):
		"""Reloads the portage settings and the database."""
		system.reload_settings()
		del self.db
		self.db = Database()
		self.db.populate()

	@Window.watch_cursor
	def cb_search_clicked (self, entry):
		"""Do a search."""
		if entry.get_text() != "":
			packages = system.find_all_packages(entry.get_text(), withVersion = False)

			if packages == []:
				nothing_found_dialog()
			else:
				if len(packages) == 1:
					self.jump_to(packages[0])
				else:
					SearchWindow(self.window, packages, self.jump_to)

	def cb_preferences_clicked (self, button):
		PreferenceWindow(self.window, self.cfg)
		return True

	def cb_about_clicked (self, button):
		queue = plugin.get_plugins()
		if queue is None:
			queue = []
		else:
			queue = queue.get_plugin_data()
		AboutWindow(self.window, queue)
		return True

	def cb_right_click (self, object, event):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			
			if object == self.queueList:
				pthinfo = object.get_path_at_pos(x, y)
				if pthinfo is not None:
					path, col, cellx, celly = pthinfo
					it = self.queueTree.get_original().get_iter(path)
					if self.queueTree.is_in_emerge(it) and self.queueTree.iter_has_parent(it):
						object.grab_focus()
						object.set_cursor(path, col, 0)
						self.queuePopup.popup(None, None, None, event.button, time)
					return True
			elif object == self.console:
				self.consolePopup.popup(None, None, None, event.button, time)
			else:
				return False
		else:
			return False

	def cb_oneshot_clicked (self, action):
		sel = self.queueList.get_selection()
		store, it = sel.get_selected()
		if it:
			package = store.get_value(it, 0)
			if not self.cfg.get_local(package, "oneshot_opt"):
				set = True
			else:
				set = False
			
			self.cfg.set_local(package, "oneshot_opt", set)
			self.queue.append(package, update = True, oneshot = set, forceUpdate = True)

	def cb_kill_clicked (self, action):
		self.queue.kill_emerge()

	def cb_copy_clicked (self, action):
		self.console.copy_clipboard()

	def cb_destroy (self, widget):
		"""Calls main_quit()."""
		gtk.main_quit()
	
	def main (self):
		"""Main."""
		gobject.threads_init() 
		# now subthreads can run normally, but are not allowed to touch the GUI. If threads should change sth there - use gobject.idle_add().
		# for more informations on threading and gtk: http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq20.006.htp
		gtk.main()
