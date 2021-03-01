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

from gi.repository import Gtk, Gdk, GLib

from gettext import gettext as _

from lollypop.logger import Logger
from lollypop.widgets_utils import Popover
from lollypop.controller_information import InformationController
from lollypop.define import App, Type, ArtBehaviour


class ToolbarInfo(Gtk.Bin, InformationController):
    """
        Informations toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        InformationController.__init__(self, True,
                                       ArtBehaviour.CROP_SQUARE |
                                       ArtBehaviour.CACHE)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/ToolbarInfo.ui")
        builder.connect_signals(self)
        self.__timeout_id = None
        self.__width = 0

        self._infobox = builder.get_object("info")
        self.add(self._infobox)

        self._spinner = builder.get_object("spinner")

        self.__labels = builder.get_object("nowplaying_labels")
        self.__labels.connect("query-tooltip", self.__on_query_tooltip)
        self.__labels.set_property("has-tooltip", True)

        self._title_label = builder.get_object("title")
        self._artist_label = builder.get_object("artist")
        self._artwork = builder.get_object("artwork")
        self._artwork.set_property("has-tooltip", True)

        self.connect("realize", self.__on_realize)
        App().art.connect("album-artwork-changed", self.__update_cover)
        App().art.connect("radio-artwork-changed", self.__update_logo)
        self.connect("button-press-event", self.__on_button_press_event)
        self.connect("button-release-event", self.__on_button_release_event)
        self.__gesture = Gtk.GestureLongPress.new(self)
        self.__gesture.connect("pressed", self.__on_gesture_pressed)
        # We want to get release event after gesture
        self.__gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.__gesture.set_button(0)

    def do_get_preferred_width(self):
        """
            We force preferred width
            @return (int, int)
        """
        return (self.__width, self.__width)

    def get_preferred_height(self):
        """
            Return preferred height
            @return (int, int)
        """
        return self.__labels.get_preferred_height()

    def set_width(self, width):
        """
            Set widget width
            @param width as int
        """
        self.__width = width
        self.set_property("width-request", width)

    def set_mini(self, mini):
        """
            Show/hide
            @param mini as bool
        """
        if mini:
            self.hide()
        else:
            self.show()

    def on_current_changed(self, player):
        """
            Update widgets
            player as Player
        """
        if self.get_realized():
            InformationController.on_current_changed(self,
                                                     self.__art_size,
                                                     None)

    @property
    def art_size(self):
        """
            Get art size
            return int
        """
        return self.__art_size

#######################
# PROTECTED           #
#######################
    def _on_eventbox_realize(self, eventbox):
        """
            Show hand cursor over
        """
        try:
            eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        except:
            Logger.warning(_("You are using a broken cursor theme!"))

    def _on_artwork(self, surface):
        """
            Set artwork
            @param surface as str
        """
        if surface is None:
            if App().player.current_track.id == Type.RADIOS:
                icon_name = "audio-input-microphone-symbolic"
            else:
                icon_name = "folder-music-symbolic"
            self._artwork.set_from_icon_name(icon_name,
                                             Gtk.IconSize.BUTTON)
            self._artwork.set_size_request(self.__art_size, self.__art_size)
        else:
            InformationController._on_artwork(self, surface)
            self._artwork.set_size_request(-1, -1)

#######################
# PRIVATE             #
#######################
    def __update_cover(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album_id as int
        """
        if App().player.current_track.album.id == album_id:
            self._previous_artwork_id = None
            self.update_artwork(self.__art_size, self.__art_size)

    def __update_logo(self, art, name):
        """
            Update logo for name
            @param art as Art
            @param name as str
        """
        if App().player.current_track.album_artist == name:
            pixbuf = App().art.get_radio_artwork(
                name, self.__art_size, self.__art_size)
            self._artwork.set_from_surface(pixbuf)

    def __popup_menu(self):
        """
            Show contextual menu
        """
        if App().window.is_adaptive or not self._artwork.get_visible():
            return
        from lollypop.menu_toolbar import ToolbarMenu
        menu = ToolbarMenu(App().player.current_track)
        if App().player.current_track.id >= 0:
            from lollypop.pop_menu import TrackMenuPopover
            popover = TrackMenuPopover(App().player.current_track, menu)
            popover.set_relative_to(self._infobox)
        elif App().player.current_track.id == Type.RADIOS:
            popover = Popover.new_from_model(self._infobox, menu)
        popover.popup()

    def __on_button_press_event(self, widget, event):
        """
            Handle right click
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if event.button == 3:
            self.__popup_menu()
            return True

    def __on_button_release_event(self, widget, event):
        """
            Handle buttons
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if App().window.is_adaptive or not self._artwork.get_visible():
            return
        if App().player.current_track.id == Type.RADIOS:
            from lollypop.pop_tunein import TuneinPopover
            popover = TuneinPopover()
            popover.populate()
        elif App().player.current_track.id is not None:
            from lollypop.pop_information import InformationPopover
            popover = InformationPopover()
            popover.populate()
        popover.set_relative_to(self._infobox)
        popover.popup()
        return True

    def __on_gesture_pressed(self, gesture, x, y):
        """
            Show current track menu
            @param gesture as Gtk.GestureLongPress
            @param x as int
            @param y as int
        """
        self.__popup_menu()

    def __on_realize(self, toolbar):
        """
            Calculate art size
            @param toolbar as ToolbarInfos
        """
        self.__art_size = self.get_allocated_height()
        if App().player.current_track.id is not None:
            self.on_current_changed(App().player)

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = GLib.markup_escape_text(self._artist_label.get_text())
            title = GLib.markup_escape_text(self._title_label.get_text())
            tooltip.set_markup("<b>%s</b> - %s" % (artist, title))
        else:
            return False
        return True
