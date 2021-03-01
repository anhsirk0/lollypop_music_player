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

from gi.repository import Gio, Gtk

from gettext import gettext as _

from lollypop.define import App
from lollypop.logger import Logger
from lollypop.menu_sync import SyncPlaylistsMenu


class PlaylistMenu(Gio.Menu):
    """
        A playlist menu
    """

    def __init__(self, playlist_id):
        """
            Init variable
            @param playlist_id as int
        """
        Gio.Menu.__init__(self)
        self.__playlist_id = playlist_id
        save_action = Gio.SimpleAction(name="save_pl_action")
        App().add_action(save_action)
        save_action.connect("activate", self.__on_save_action_activate)
        self.append(_("Save playlist"), "app.save_pl_action")
        smart_action = Gio.SimpleAction(name="smart_action")
        App().add_action(smart_action)
        smart_action.connect("activate", self.__on_smart_action_activate)
        self.append(_("Manage smart playlist"), "app.smart_action")
        if not App().window.is_adaptive:
            split_action = Gio.SimpleAction.new_stateful(
                "split_action",
                None,
                App().settings.get_value("split-view"))
            split_action.connect("change-state",
                                 self.__on_split_action_change_state)
            App().add_action(split_action)
            self.append(_("Split view"), "app.split_action")
        remove_action = Gio.SimpleAction(name="remove_pl_action")
        App().add_action(remove_action)
        remove_action.connect("activate", self.__on_remove_action_activate)
        self.append(_("Remove playlist"), "app.remove_pl_action")
        self.append_section(_("Synchronization"),
                            SyncPlaylistsMenu(playlist_id))

#######################
# PRIVATE             #
#######################
    def __on_smart_action_activate(self, action, variant):
        """
            Show smart playlist editor
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().window.container.show_smart_playlist_editor(self.__playlist_id)

    def __on_remove_action_activate(self, action, variant):
        """
            Remove playlist
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        def remove_playlist():
            App().playlists.remove(self.__playlist_id)
        from lollypop.app_notification import AppNotification
        notification = AppNotification(_("Remove this playlist?"),
                                       [_("Confirm")],
                                       [remove_playlist])
        notification.show()
        App().window.container.add_overlay(notification)
        notification.set_reveal_child(True)

    def __on_save_action_activate(self, action, variant):
        """
            Save playlist to file
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        filechooser = Gtk.FileChooserNative.new(_("Save playlist"),
                                                App().window,
                                                Gtk.FileChooserAction.SAVE,
                                                _("Save"),
                                                _("Cancel"))
        filter = Gtk.FileFilter.new()
        filter.set_name("audio/x-mpegurl")
        filter.add_mime_type("audio/x-mpegurl")
        filechooser.add_filter(filter)
        filechooser.set_do_overwrite_confirmation(True)
        name = App().playlists.get_name(self.__playlist_id)
        filechooser.set_current_name("%s.m3u" % name)
        filechooser.connect("response", self.__on_save_response)
        filechooser.run()

    def __on_save_response(self, dialog, response_id):
        """
            Save playlist
            @param dialog as Gtk.NativeDialog
            @param response_id as int
        """
        try:
            if response_id == Gtk.ResponseType.ACCEPT:
                uris = App().playlists.get_track_uris(self.__playlist_id)
                stream = dialog.get_file().replace(
                    None,
                    False,
                    Gio.FileCreateFlags.REPLACE_DESTINATION,
                    None)
                stream.write("#EXTM3U\n".encode("utf-8"))
                for uri in uris:
                    string = "%s\n" % uri
                    stream.write(string.encode("utf-8"))
                stream.close()
        except Exception as e:
            Logger.error("PlaylistMenu::__on_save_response(): %s", e)

    def __on_split_action_change_state(self, action, value):
        """
            Activate party mode
            @param action as Gio.SimpleAction
            @param value as bool
        """
        App().settings.set_value("split-view", value)
        action.set_state(value)
