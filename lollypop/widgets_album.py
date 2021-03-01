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

from gi.repository import Gtk, Gdk

from lollypop.define import App, ViewType
from lollypop.widgets_utils import Popover


class AlbumWidget:
    """
        Album widget
    """

    def __init__(self, album, genre_ids, artist_ids):
        """
            Init Album widget
            @param album as Album
            @param genre_ids as [int]
            @param artist_ids as [int]
        """
        self._artwork = None
        self._album = album
        self._genre_ids = genre_ids
        self._artist_ids = artist_ids
        self.__filtered = False
        self.connect("destroy", self.__on_destroy)
        self._scan_signal = App().scanner.connect("album-updated",
                                                  self._on_album_updated)

    def set_selection(self):
        """
            Mark widget as selected if currently playing
        """
        if self._artwork is None:
            return
        selected = self._album.id == App().player.current_track.album.id
        if selected:
            self._artwork.set_state_flags(Gtk.StateFlags.SELECTED, True)
        else:
            self._artwork.set_state_flags(Gtk.StateFlags.NORMAL, True)

    def set_filtered(self, b):
        """
            Set widget filtered
            @param b as bool
            @return bool (should be shown)
        """
        self.__filtered = b
        return not b

    @property
    def album(self):
        """
            @return Album
        """
        return self._album

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__filtered

    @property
    def filter(self):
        """
            @return str
        """
        return " ".join([self._album.name] + self._album.artists)

#######################
# PROTECTED           #
#######################
    def _on_album_updated(self, scanner, album_id, destroy):
        pass

    def _on_button_release(self, eventbox, event):
        """
            Handle album mouse click
            @param eventbox as Gtk.EventBox
            @param event as Gdk.EventButton
        """
        if event.button != 1:
            from lollypop.menu_objects import AlbumMenu
            popover = Popover.new_from_model(self._artwork,
                                             AlbumMenu(
                                                self._album,
                                                ViewType.ALBUM))
            popover.set_position(Gtk.PositionType.BOTTOM)
            rect = Gdk.Rectangle()
            rect.x = event.x
            rect.y = event.y
            rect.width = rect.height = 1
            popover.set_pointing_to(rect)
            popover.popup()

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self._scan_signal is not None:
            App().scanner.disconnect(self._scan_signal)
