#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2019       Paul Culley <paulr2787_at_gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
""" Themes
This module implements the Preferences Themes load patches.
"""
import os
import types
import glob
from gi.repository import Gtk, Gio, GLib, Pango
from gi.repository.GObject import BindingFlags
#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.config import config
from gramps.gui.configure import (GrampsPreferences, ConfigureDialog,
                                  WIKI_HELP_PAGE, WIKI_HELP_SEC)
from gramps.gui.display import display_help
from gramps.gen.utils.alive import update_constants
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext


#-------------------------------------------------------------------------
#
# GrampsPreferences
#
#-------------------------------------------------------------------------
class MyPrefs(GrampsPreferences):
    ''' Adds a new line of controls to the 'Colors' preferences panel.
    Theme, dark-theme and Font choices are added. '''

    def __init__(self, uistate, dbstate):
        ''' this replaces the GrampsPreferences __init__
        It includes the patching fixes and calls my version of the Theme panel
        '''
        # Patching in the methods
        self.add_themes_panel = types.MethodType(
            MyPrefs.add_themes_panel, self)
        self.gtk_css = types.MethodType(
            MyPrefs.gtk_css, self)
        self.theme_changed = types.MethodType(
            MyPrefs.theme_changed, self)
        self.dark_variant_changed = types.MethodType(
            MyPrefs.dark_variant_changed, self)
        self.t_text_changed = types.MethodType(
            MyPrefs.t_text_changed, self)
        self.font_changed = types.MethodType(
            MyPrefs.font_changed, self)
        self.font_filter = types.MethodType(
            MyPrefs.font_filter, self)
        self.default_clicked = types.MethodType(
            MyPrefs.default_clicked, self)
        # Copy of original __init__
        page_funcs = (
            self.add_behavior_panel,
            self.add_famtree_panel,
            self.add_formats_panel,
            self.add_text_panel,
            self.add_prefix_panel,
            self.add_date_panel,
            self.add_researcher_panel,
            self.add_advanced_panel,
            self.add_themes_panel)

        ConfigureDialog.__init__(self, uistate, dbstate, page_funcs,
                                 GrampsPreferences, config,
                                 on_close=update_constants)
        help_btn = self.window.add_button(_('_Help'), Gtk.ResponseType.HELP)
        help_btn.connect(
            'clicked', lambda x: display_help(WIKI_HELP_PAGE, WIKI_HELP_SEC))
        self.setup_configs('interface.grampspreferences', 700, 450)

    def add_themes_panel(self, configdialog):
        ''' This adds a line to the top of the original 'Color' panel '''
        text, grid = self.add_color_panel(configdialog)

        grid.insert_row(0)
        th_grid = Gtk.Grid()
        th_grid.set_border_width(12)
        th_grid.set_column_spacing(6)
        # Theme combo
        self.theme = Gtk.ComboBoxText()
        self.t_names = set()
        # scan for standard Gtk themes
        themes = Gio.resources_enumerate_children("/org/gtk/libgtk/theme", 0)
        for theme in themes:
            if theme.endswith('/'):  # the modern way of finding
                self.t_names.add(theme[:-1])
            elif (theme.startswith('HighContrast') or
                  theme.startswith('Raleigh') or
                  theme.startswith('gtk-win32')):  # older method of hard coded
                self.t_names.add(theme.replace('.css', ''))
        # scan for user themes
        self.gtk_css(os.path.join(GLib.get_home_dir(), '.themes'))
        self.gtk_css(os.path.join(GLib.get_user_data_dir(), 'themes'))
        # scan for system themes
        dirs = GLib.get_system_data_dirs()
        for directory in dirs:
            self.gtk_css(os.path.join(directory, 'themes'))

        self.gtksettings = Gtk.Settings.get_default()
        # get current theme
        c_theme = self.gtksettings.get_property('gtk-theme-name')
        # fill combo with names and select active if current matches
        for indx, theme in enumerate(self.t_names):
            self.theme.append_text(theme)
            if theme == c_theme:
                self.theme.set_active(indx)

        if os.environ.get("GTK_THEME"):
            # theme is hardcoded, nothing we can do
            self.theme.set_sensitive(False)
            self.theme.set_tooltip_text(_("Theme is hardcoded by GTK_THEME"))
        else:
            self.theme.connect('changed', self.theme_changed)
        lwidget = Gtk.Label(label=(_("%s: ") % _('Theme')))
        th_grid.attach(lwidget, 0, 0, 1, 1)
        th_grid.attach(self.theme, 1, 0, 1, 1)

        # Dark theme
        self.dark = Gtk.CheckButton(label=_("Dark Variant"))
        value = self.gtksettings.get_property(
            'gtk-application-prefer-dark-theme')
        self.dark.set_active(value)
        self.dark.connect('toggled', self.dark_variant_changed)
        th_grid.attach(self.dark, 2, 0, 1, 1)
        self.dark_variant_changed(self.dark)
        if os.environ.get("GTK_THEME"):
            # theme is hardcoded, nothing we can do
            self.dark.set_sensitive(False)
            self.dark.set_tooltip_text(_("Theme is hardcoded by GTK_THEME"))

        # Toolbar Text
        t_text = Gtk.CheckButton.new_with_mnemonic(
            _("_Toolbar") + ' ' + _('Text'))
        value = config.get('interface.toolbar-text')
        t_text.set_active(value)
        t_text.connect('toggled', self.t_text_changed)
        th_grid.attach(t_text, 3, 0, 1, 1)

        # Default
        button = Gtk.Button(label=_('Default'))
        button.connect('clicked', self.default_clicked)
        th_grid.attach(button, 4, 0, 1, 1)

        # Font
        font_button = Gtk.FontButton(show_style=False)
        font_button.set_filter_func(self.font_filter, None)
        self.gtksettings.bind_property(
            'gtk-font-name', font_button, "font-name",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE)
        lwidget = Gtk.Label(label=_("%s: ") % _('Font'))
        th_grid.attach(lwidget, 5, 0, 1, 1)
        th_grid.attach(font_button, 6, 0, 1, 1)
        font_button.connect('font-set', self.font_changed)
        grid.attach(th_grid, 0, 0, 7, 1)

        return _('Colors'), grid

    def theme_changed(self, obj):
        ''' deal with combo changed '''
        value = obj.get_active_text()
        if value:
            config.set('preferences.theme', value)
            self.gtksettings.set_property('gtk-theme-name', value)

    def dark_variant_changed(self, obj):
        """
        Update dark_variant widget.
        """
        value = obj.get_active()
        config.set('preferences.theme-dark-variant', str(value))
        self.gtksettings.set_property('gtk-application-prefer-dark-theme',
                                      value)

    def t_text_changed(self, obj):
        ''' Toolbar text changed '''
        value = obj.get_active()
        config.set('interface.toolbar-text', value)
        self.uistate.viewmanager.toolbar.set_style(
            Gtk.ToolbarStyle.BOTH if value else Gtk.ToolbarStyle.ICONS)

    def font_changed(self, obj):
        ''' deal with font changed '''
        font = obj.get_font()
        config.set('preferences.font', font)

    def font_filter(self, family, face, *obj):
        desc = face.describe()
        if (desc.get_style() == Pango.Style.NORMAL and
            desc.get_weight() == Pango.Weight.NORMAL):
            return True
        return False

    def default_clicked(self, obj):
        self.gtksettings.set_property('gtk-font-name', self.def_font)
        self.gtksettings.set_property('gtk-theme-name', self.def_theme)
        self.gtksettings.set_property('gtk-application-prefer-dark-theme',
                                      self.def_dark)
        config.set('preferences.font', '')
        config.set('preferences.theme', '')
        config.set('preferences.theme-dark-variant', '')
        # fill combo with names and select active if current matches
        self.theme.remove_all()
        for indx, theme in enumerate(self.t_names):
            self.theme.append_text(theme)
            if theme == self.def_theme:
                self.theme.set_active(indx)
        self.dark.set_active(self.def_dark)

    def gtk_css(self, directory):
        if not os.path.isdir(directory):
            return
        for dir_entry in glob.glob(
            os.path.join(directory, '*', 'gtk-3.*', 'gtk.css')):
            self.t_names.add(dir_entry.replace('\\', '/').split('/')[-3])