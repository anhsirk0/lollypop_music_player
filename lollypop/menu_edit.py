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

from gi.repository import Gio, GLib

from gettext import gettext as _

from lollypop.define import App
from lollypop.objects import Track, Album
from lollypop.logger import Logger


class EditMenu(Gio.Menu):
    """
        Edition menu for album
    """

    def __init__(self, object):
        """
            Init edit menu
            @param object as Album/Track
        """
        Gio.Menu.__init__(self)
        # Ignore genre_ids/artist_ids
        if isinstance(object, Album):
            self.__object = Album(object.id)
        else:
            self.__object = Track(object.id)
        if isinstance(self.__object, Album):
            self.__set_save_action()
        if self.__object.is_in_user_collection and App().art.tag_editor:
            self.__set_edit_action()

#######################
# PRIVATE             #
#######################
    def __set_save_action(self):
        """
            Set save action
        """
        if self.__object.mtime == 0:
            save_action = Gio.SimpleAction(name="save_album_action")
            App().add_action(save_action)
            save_action.connect("activate",
                                self.__on_save_action_activate,
                                True)
            self.append(_("Save in collection"), "app.save_album_action")
        elif self.__object.mtime == -1:
            save_action = Gio.SimpleAction(name="remove_album_action")
            App().add_action(save_action)
            save_action.connect("activate",
                                self.__on_save_action_activate,
                                False)
            self.append(_("Remove from collection"), "app.remove_album_action")

    def __set_edit_action(self):
        """
            Set edit action
        """
        edit_tag_action = Gio.SimpleAction(name="edit_tag_action")
        App().add_action(edit_tag_action)
        edit_tag_action.connect("activate", self.__on_edit_tag_action_activate)
        self.append(_("Modify information"), "app.edit_tag_action")

    def __on_save_action_activate(self, action, variant, save):
        """
            Save album to collection
            @param Gio.SimpleAction
            @param GLib.Variant
            @param save as bool
        """
        self.__object.save(save)
        App().tracks.del_non_persistent()
        App().tracks.clean()
        App().albums.clean()
        App().artists.clean()
        App().genres.clean()

    def __on_edit_tag_action_activate(self, action, variant):
        """
            Run tag editor
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        try:
            path = GLib.filename_from_uri(self.__object.uri)[0]
            if GLib.find_program_in_path("flatpak-spawn") is not None:
                argv = ["flatpak-spawn", "--host", App().art.tag_editor, path]
            else:
                argv = [App().art.tag_editor, path]
            (pid, stdin, stdout, stderr) = GLib.spawn_async(
                argv, flags=GLib.SpawnFlags.SEARCH_PATH |
                GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
                standard_input=False,
                standard_output=False,
                standard_error=False
            )
        except Exception as e:
            Logger.error("MenuPopover::__on_edit_tag_action_activate(): %s"
                         % e)
