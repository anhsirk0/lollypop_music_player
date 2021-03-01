# Copyright (c) 2014-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GLib, Gtk

from gettext import gettext as _

from lollypop.widgets_rating import RatingWidget
from lollypop.widgets_loved import LovedWidget
from lollypop.define import App
from lollypop.widgets_utils import Popover


class RemoveMenuPopover(Gtk.PopoverMenu):
    """
        Contextual menu for removing Rows
    """

    def __init__(self, rows):
        """
            Init menu
            @param rows as [Row]
        """
        Gtk.PopoverMenu.__init__(self)
        self.__rows = rows
        button = Gtk.ModelButton.new()
        if len(rows) == 1:
            button.set_label(_("Remove track"))
        else:
            button.set_label(_("Remove tracks"))
        button.show()
        button.connect("clicked", self.__on_button_clicked)
        self.add(button)

#######################
# PRIVATE             #
#######################
    def __on_button_clicked(self, button):
        """
            Remove rows
            @param button as Gtk.ModelButton
        """
        from lollypop.widgets_row_dnd import DNDRow
        for r in self.__rows:
            DNDRow.destroy_track_row(r)


class TrackMenuPopover(Popover):
    """
        Contextual menu widget for a track
    """

    def __init__(self, track, menu):
        """
            Init widget
            @param track as Track
            @param menu as Gio.Menu
        """
        Popover.__init__(self)
        if menu is not None:
            self.bind_model(menu, None)

        if track.mtime == 0:
            return

        if track.year is not None:
            year_label = Gtk.Label.new()
            year_label.set_text(str(track.year))
            dt = GLib.DateTime.new_from_unix_local(track.timestamp)
            year_label.set_tooltip_text(dt.format(_("%Y-%m-%d")))
            year_label.set_margin_end(5)
            year_label.get_style_context().add_class("dim-label")
            year_label.set_property("halign", Gtk.Align.END)
            year_label.set_property("hexpand", True)
            year_label.show()

        # Hack to add two widgets in popover
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)

        stack = Gtk.Stack()
        stack.add_named(grid, "main")
        stack.show_all()

        menu_widget = self.get_child()
        if menu_widget is not None:
            self.remove(menu_widget)
            grid.add(menu_widget)

        hgrid = Gtk.Grid()
        hgrid.get_style_context().add_class("popover-rating-loved-grid")
        rating = RatingWidget(track)
        rating.set_property("halign", Gtk.Align.START)
        rating.set_margin_end(10)
        rating.show()

        loved = LovedWidget(track)
        loved.set_property("halign", Gtk.Align.START)
        loved.set_property("hexpand", True)
        loved.show()

        hgrid.add(rating)
        hgrid.add(loved)

        if track.year is not None:
            hgrid.add(year_label)
        hgrid.show()

        if track.mtime in [-1, 0]:
            edit = Gtk.Entry()
            edit.set_margin_top(5)
            edit.set_margin_start(5)
            edit.set_margin_end(5)
            edit.set_margin_bottom(5)
            edit.set_property("hexpand", True)
            edit.set_text(track.uri)
            edit.connect("changed", self.__on_edit_changed, track)
            edit.show()
            grid.add(edit)

        grid.add(hgrid)
        self.add(stack)

#######################
# PRIVATE             #
#######################
    def __on_edit_changed(self, edit, track):
        """
            Update track uri
            @param edit as Gtk.Edit
            @param track as Track
        """
        from urllib.parse import urlparse
        text = edit.get_text()
        parsed = urlparse(text)
        if parsed.scheme not in ["http", "https", "web"]:
            text = "web://null"
        App().tracks.set_uri(track.id, text)
        track.reset("uri")
