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

from gi.repository import Gio, GLib, Gtk, Gst

from lollypop.define import App, ScanType, Type


class ApplicationActions:
    """
        Application actions
    """

    def __init__(self):
        """
            Init actions
        """
        self.__user_scan = False
        settings_action = Gio.SimpleAction.new("settings",
                                               GLib.VariantType("i"))
        settings_action.connect("activate", self.__on_settings_activate)
        App().add_action(settings_action)

        update_action = Gio.SimpleAction.new("update_db", None)
        update_action.connect("activate", self.__on_update_db_activate)
        App().add_action(update_action)

        fullscreen_action = Gio.SimpleAction.new("fullscreen", None)
        App().player.connect("current-changed",
                             self.__on_current_changed,
                             fullscreen_action)
        fullscreen_action.set_enabled(False)
        fullscreen_action.connect("activate", self.__on_fullscreen_activate)
        App().add_action(fullscreen_action)

        equalizer_action = Gio.SimpleAction.new("equalizer", None)
        equalizer_action.connect("activate", self.__on_equalizer_activate)
        App().set_accels_for_action("app.equalizer", ["<Shift><Alt>e"])
        App().add_action(equalizer_action)

        show_sidebar = App().settings.get_value("show-sidebar")
        sidebar_action = Gio.SimpleAction.new_stateful(
            "sidebar",
            None,
            GLib.Variant.new_boolean(show_sidebar))
        sidebar_action.connect("change-state", self.__on_sidebar_change_state)
        App().add_action(sidebar_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.__on_about_activate)
        App().add_action(about_action)

        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self.__on_shortcuts_activate)
        App().add_action(shortcuts_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda x, y: App().quit(True))
        App().add_action(quit_action)

        seek_action = Gio.SimpleAction.new("seek",
                                           GLib.VariantType.new("i"))
        seek_action.connect("activate", self.__on_seek_action)
        App().add_action(seek_action)
        player_action = Gio.SimpleAction.new("shortcut",
                                             GLib.VariantType.new("s"))
        player_action.connect("activate", self.__on_player_action)
        App().add_action(player_action)

        search_action = Gio.SimpleAction.new("search",
                                             GLib.VariantType.new("s"))
        App().add_action(search_action)
        App().set_accels_for_action("app.search('')", ["<Control>f"])

        App().scanner.connect("scan-finished", self.__on_scan_finished)
        self.__setup_global_shortcuts()
        self.enable_special_shortcuts(True)

    def enable_special_shortcuts(self, enable):
        """
            Enable special shortcuts
            @param enable as bool
        """
        if enable:
            if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
                App().set_accels_for_action("app.seek(10)", ["Left"])
                App().set_accels_for_action("app.seek(-10)", ["Right"])
            else:
                App().set_accels_for_action("app.seek(10)", ["Right"])
                App().set_accels_for_action("app.seek(-10)", ["Left"])
            App().set_accels_for_action("app.shortcut::play_pause",
                                        ["c", "space"])
            App().set_accels_for_action("app.shortcut::play", ["x"])
            App().set_accels_for_action("app.shortcut::stop", ["v"])
            App().set_accels_for_action("app.shortcut::next", ["n"])
            App().set_accels_for_action("app.shortcut::prev", ["p"])
        else:
            App().set_accels_for_action("app.seek(10)", [])
            App().set_accels_for_action("app.seek(-10)", [])
            App().set_accels_for_action("app.shortcut::play_pause", [])
            App().set_accels_for_action("app.shortcut::play", [])
            App().set_accels_for_action("app.shortcut::stop", [])
            App().set_accels_for_action("app.shortcut::next", [])
            App().set_accels_for_action("app.shortcut::prev", [])

#######################
# PRIVATE             #
#######################
    def __setup_global_shortcuts(self):
        """
            Setup global shortcuts
        """
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            App().set_accels_for_action("app.shortcut::go_back",
                                        ["<Alt>Right", "Back"])
        else:
            App().set_accels_for_action("app.shortcut::go_back",
                                        ["<Alt>Left", "Back"])
        App().set_accels_for_action("app.shortcut::filter", ["<Control>i"])
        App().set_accels_for_action("app.shortcut::volume",
                                    ["<Shift><Alt>v"])
        App().set_accels_for_action("app.shortcut::lyrics",
                                    ["<Shift><Alt>l"])
        App().set_accels_for_action("app.shortcut::next_album", ["<Control>n"])
        App().set_accels_for_action("app.shortcut::current_artist",
                                    ["<Control><Alt>a"])
        App().set_accels_for_action("app.shortcut::show_sidebar", ["F9"])
        App().set_accels_for_action("app.update_db", ["<Control>u"])
        App().set_accels_for_action("app.settings(-14)", ["<Control>comma"])
        App().set_accels_for_action("app.fullscreen", ["F11", "F7"])
        App().set_accels_for_action("app.mini", ["<Control>m"])
        App().set_accels_for_action("app.about", ["F3"])
        App().set_accels_for_action("app.shortcuts", ["F2"])
        App().set_accels_for_action("app.help", ["F1"])
        App().set_accels_for_action("app.quit", ["<Control>q"])
        App().set_accels_for_action("app.shortcut::loved", ["<Alt>l"])
        App().set_accels_for_action("app.shortcut::reload", ["<Control>r"])
        App().set_accels_for_action("app.shortcut::volume_up",
                                    ["<Shift><Alt>Up"])
        App().set_accels_for_action("app.shortcut::volume_down",
                                    ["<Shift><Alt>Down"])
        App().set_accels_for_action("app.shortcut::list_one_type_ahead",
                                    ["<Control>o"])
        App().set_accels_for_action("app.shortcut::list_two_type_ahead",
                                    ["<Control>t"])

    def __on_update_db_activate(self, action=None, param=None):
        """
            Search for new music
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if App().window:
            self.__user_scan = True
            App().scanner.update(ScanType.FULL)

    def __on_scan_finished(self, scanner, modifications):
        """
            Run artwork update if needed
            @param scanner as CollectionScanner
            @param modifications as bool
        """
        if self.__user_scan:
            if App().settings.get_value("artist-artwork"):
                App().art.cache_artists_artwork()
        self.__user_scan = False

    def __on_about_activate_response(self, dialog, response_id):
        """
            Destroy about dialog when closed
            @param dialog as Gtk.Dialog
            @param response id as int
        """
        dialog.destroy()

    def __on_sidebar_change_state(self, action, value):
        """
            Show/hide sidebar
            @param action as Gio.SimpleAction
            @param value as bool
        """
        action.set_state(value)
        App().settings.set_value("show-sidebar",
                                 GLib.Variant("b", value))
        App().window.container.show_sidebar(value)

    def __on_fullscreen_activate(self, action, param):
        """
            Show a fullscreen window with cover and artist information
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        App().fullscreen()

    def __on_equalizer_activate(self, action, param):
        """
            Show equalizer view
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        App().window.container.show_view([Type.EQUALIZER])

    def __on_settings_activate(self, action, param):
        """
            Show settings dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        if App().window.is_adaptive:
            App().window.container.show_view([Type.SETTINGS])
        else:
            from lollypop.dialog_settings import SettingsDialog
            dialog = SettingsDialog(param.get_int32())
            dialog.show()

    def __on_about_activate(self, action, param):
        """
            Setup about dialog
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/AboutDialog.ui")
        about = builder.get_object("about_dialog")
        about.set_transient_for(App().window)
        about.connect("response", self.__on_about_activate_response)
        about.show()

    def __on_shortcuts_activate(self, action, param):
        """
            Show shorctus
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/Shortcuts.ui")
        builder.get_object("shortcuts").set_transient_for(App().window)
        builder.get_object("shortcuts").show()

    def __on_current_changed(self, player, action):
        """
            Activate action if wanted
            @param player as Player
            @param action as Gio.SimpleAction
        """
        action.set_enabled(not App().player.current_track.id is None)

    def __on_seek_action(self, action, param):
        """
            Seek in stream
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        seconds = param.get_int32()
        position = App().player.position
        seek = position / Gst.SECOND + seconds
        if seek < 0:
            seek = 0
        if seek > App().player.current_track.duration:
            seek = App().player.current_track.duration - 2
        App().player.seek(seek)

    def __on_player_action(self, action, param):
        """
            Change player state
            @param action as Gio.SimpleAction
            @param param as GLib.Variant
        """
        string = param.get_string()
        if string == "play_pause":
            App().player.play_pause()
        elif string == "play":
            App().player.play()
        elif string == "stop":
            App().player.stop()
        elif string == "next":
            App().player.next()
        elif string == "next_album":
            App().player.skip_album()
        elif string == "prev":
            App().player.prev()
        elif string == "go_back":
            App().window.go_back()
        elif string == "lyrics":
            App().window.container.show_lyrics()
        elif string == "reload":
            App().window.container.reload_view()
        elif string == "volume_up":
            App().player.set_volume(App().player.volume + 0.1)
        elif string == "volume_down":
            App().player.set_volume(App().player.volume - 0.1)
        elif string == "list_one_type_ahead":
            if App().window.container.list_one.is_visible():
                App().window.container.list_one.type_ahead_popover.popup()
        elif string == "list_two_type_ahead":
            if App().window.container.list_two.is_visible():
                App().window.container.list_two.type_ahead_popover.popup()
        elif string == "show_sidebar":
            value = App().settings.get_value("show-sidebar")
            App().settings.set_value("show-sidebar",
                                     GLib.Variant("b", not value))
            App().main_window.container.show_sidebar(not value)
        elif string == "filter":
            if App().main_window.container.view is not None:
                App().main_window.container.view.enable_filter()
        elif string == "volume":
            App().window.container.show_view([Type.EQUALIZER])
        elif string == "current_artist":
            if App().player.current_track.id is not None and\
                    App().player.current_track.id > 0:
                artist_ids = App().player.current_track.album.artist_ids
                App().window.container.show_artist_view(artist_ids)
        elif string == "loved":
            track = App().player.current_track
            if track.id is not None and track.id >= 0:
                if track.loved < 1:
                    loved = track.loved + 1
                else:
                    loved = Type.NONE
                track.set_loved(loved)
                if App().notify is not None:
                    if track.loved == 1:
                        heart = "❤"
                    elif track.loved == -1:
                        heart = "⏭"
                    else:
                        heart = "♡"
                    App().notify.send("%s - %s: %s" %
                                      (", ".join(track.artists),
                                       track.name,
                                       heart))
