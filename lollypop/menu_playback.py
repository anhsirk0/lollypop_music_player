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

from gi.repository import Gio

from gettext import gettext as _

from lollypop.define import App
from lollypop.objects import Track


class PlaybackMenu(Gio.Menu):
    """
        Contextual menu for queue
    """

    def __init__(self, track):
        """
            Init playlists menu
            @param track as Track
        """
        Gio.Menu.__init__(self)
        self.__track = track
        self.__set_playback_actions()
        self.__set_queue_actions()
        self.__set_stop_after_action()

#######################
# PRIVATE             #
#######################
    def __is_in_current_playlist(self):
        """
            Check if track in Player current playlist
            @return bool
        """
        if App().player.albums:
            for album in App().player.albums:
                if self.__track.album.id == album.id:
                    if self.__track.id in album.track_ids:
                        return True
        elif App().player.playlist_ids:
            if self.__track.id in App().player.playlist_track_ids:
                return True
        return False

    def __set_playback_actions(self):
        """
            Set playback actions
        """
        if not self.__is_in_current_playlist():
            append_playback_action = Gio.SimpleAction(
                name="append_playback_action")
            App().add_action(append_playback_action)
            append_playback_action.connect("activate",
                                           self.__append_to_playback)
            self.append(_("Add to playback"), "app.append_playback_action")
        else:
            del_playback_action = Gio.SimpleAction(name="del_playback_action")
            App().add_action(del_playback_action)
            del_playback_action.connect("activate",
                                        self.__remove_from_playback)
            self.append(_("Remove from playback"), "app.del_playback_action")

    def __set_queue_actions(self):
        """
            Set queue actions
        """
        if self.__track.id not in App().player.queue:
            append_queue_action = Gio.SimpleAction(name="append_queue_action")
            App().add_action(append_queue_action)
            append_queue_action.connect("activate",
                                        self.__append_to_queue)
            self.append(_("Add to queue"), "app.append_queue_action")
        else:
            del_queue_action = Gio.SimpleAction(name="del_queue_action")
            App().add_action(del_queue_action)
            del_queue_action.connect("activate",
                                     self.__remove_from_queue)
            self.append(_("Remove from queue"), "app.del_queue_action")

    def __set_stop_after_action(self):
        """
            Add an action to stop playback after track
        """
        if self.__is_in_current_playlist() and \
                isinstance(self.__track, Track):
            stop_after_action = Gio.SimpleAction(name="stop_after_action")
            App().add_action(stop_after_action)
            if self.__track.id == App().player.stop_after_track_id:
                stop_after_action.connect("activate", self.__stop_after, None)
                self.append(_("Do not stop after"),
                            "app.stop_after_action")
            else:
                stop_after_action.connect("activate", self.__stop_after,
                                          self.__track.id)
                self.append(_("Stop after"), "app.stop_after_action")

    def __stop_after(self, action, variant, track_id):
        """
            Tell player to stop after track
            @param Gio.SimpleAction
            @param GLib.Variant
            @param track_id as int/None
        """
        App().player.stop_after(track_id)
        if track_id == App().player.current_track.id:
            App().player.set_next()

    def __append_to_playback(self, action, variant):
        """
            Append track to playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        albums = App().player.albums
        # If album last in list, merge
        if albums and albums[-1].id == self.__track.album.id:
            albums[-1].insert_track(self.__track)
            App().player.set_next()
        # Add album with only one track
        else:
            # We do not want to share same album with multiple user add
            # If needed, previous merge will do the job
            album = self.__track.album.clone(True)
            album.set_tracks([self.__track])
            if App().player.is_playing:
                App().player.add_album(album)
            else:
                App().player.play_album(album)

    def __remove_from_playback(self, action, variant):
        """
            Delete track id from playback
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        for album in App().player.albums:
            if album.id == self.__track.album.id:
                if self.__track.id in album.track_ids:
                    index = album.track_ids.index(self.__track.id)
                    track = album.tracks[index]
                    album.remove_track(track)
                    break
        App().player.set_next()
        App().player.set_prev()

    def __append_to_queue(self, action, variant):
        """
            Append track to queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.append_to_queue(self.__track.id, False)
        App().player.emit("queue-changed")

    def __remove_from_queue(self, action, variant):
        """
            Delete track id from queue
            @param Gio.SimpleAction
            @param GLib.Variant
        """
        App().player.remove_from_queue(self.__track.id, False)
        App().player.emit("queue-changed")
