# Copyright (c) 2014-2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, Soup, GObject

import json
from base64 import b64encode
from time import time, sleep

from lollypop.logger import Logger
from lollypop.objects import Album, Track
from lollypop.helper_task import TaskHelper
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET, App


class SpotifyHelper(GObject.Object):
    """
        Helper for Spotify
    """
    __CHARTS = "https://spotifycharts.com/regional/%s/weekly/latest/download"
    __gsignals__ = {
        "new-album": (GObject.SignalFlags.RUN_FIRST, None,
                      (GObject.TYPE_PYOBJECT, str)),
        "new-artist": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        "search-finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        """
            Init object
        """
        GObject.Object.__init__(self)
        self.__token_expires = 0
        self.__token = None
        self.__loading_token = False

    def get_token(self):
        """
            Get a new auth token
        """
        try:
            token_uri = "https://accounts.spotify.com/api/token"
            credentials = "%s:%s" % (SPOTIFY_CLIENT_ID, SPOTIFY_SECRET)
            encoded = b64encode(credentials.encode("utf-8"))
            credentials = encoded.decode("utf-8")
            session = Soup.Session.new()
            data = {"grant_type": "client_credentials"}
            msg = Soup.form_request_new_from_hash("POST", token_uri, data)
            msg.request_headers.append("Authorization",
                                       "Basic %s" % credentials)
            status = session.send_message(msg)
            if status == 200:
                body = msg.get_property("response-body")
                data = body.flatten().get_data()
                decode = json.loads(data.decode("utf-8"))
                self.__token_expires = int(time()) + int(decode["expires_in"])
                self.__token = decode["access_token"]
        except Exception as e:
            Logger.error("SpotifyHelper::get_token(): %s", e)

    def wait_for_token(self):
        """
            True if should wait for token
            @return bool
        """
        def on_token(token):
            self.__loading_token = False
        # Remove 60 seconds to be sure
        wait = int(time()) + 60 > self.__token_expires or\
            self.__token is None
        if wait and not self.__loading_token:
            self.__loading_token = True
            App().task_helper.run(self.get_token, callback=(on_token,))
        return wait

    def get_artist_id(self, artist_name, callback):
        """
            Get artist id
            @param artist_name as str
            @param callback as function
        """
        if self.wait_for_token():
            GLib.timeout_add(
                500, self.get_artist_id, artist_name, callback)
            return
        try:
            def on_content(uri, status, data):
                found = False
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    for item in decode["artists"]["items"]:
                        found = True
                        artist_id = item["uri"].split(":")[-1]
                        callback(artist_id)
                        return
                if not found:
                    callback(None)
            artist_name = GLib.uri_escape_string(
                artist_name, None, True).replace(" ", "+")
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?q=%s&type=artist" %\
                artist_name
            helper.load_uri_content(uri, None, on_content)
        except Exception as e:
            Logger.error("SpotifyHelper::get_artist_id(): %s", e)
            callback(None)

    def get_similar_artists(self, artist_id, cancellable):
        """
           Get similar artists
           @param artist_id as int
           @param cancellable as Gio.Cancellable
           @return artists as [str]
        """
        artists = []
        try:
            while self.wait_for_token():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/related-artists" %\
                artist_id
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]:
                    artists.append(item["name"])
        except Exception as e:
            Logger.error("SpotifyHelper::get_similar_artists(): %s", e)
        return artists

    def search_similar_artists(self, spotify_id, cancellable):
        """
            Search similar artists
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
        """
        try:
            while self.wait_for_token():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            found = False
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/artists/%s/related-artists" % \
                  spotify_id
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]:
                    if cancellable.is_cancelled():
                        raise Exception("cancelled")
                    found = True
                    artist_name = item["name"]
                    cover_uri = item["images"][1]["url"]
                    GLib.idle_add(self.emit, "new-artist",
                                  artist_name, cover_uri)
        except Exception as e:
            Logger.error("SpotifyHelper::search_similar_artists(): %s", e)
        if not found:
            GLib.idle_add(self.emit, "new-artist", None, None)

    def search(self, search, cancellable):
        """
            Get albums related to search
            We need a thread because we are going to populate DB
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        try:
            while self.wait_for_token():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = "https://api.spotify.com/v1/search?"
            uri += "q=%s&type=album,track" % search
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                album_ids = []
                self.__create_albums_from_album_payload(
                                                 decode["albums"]["items"],
                                                 album_ids,
                                                 cancellable)
                self.__create_albums_from_tracks_payload(
                                                 decode["tracks"]["items"],
                                                 album_ids,
                                                 cancellable)
        except Exception as e:
            Logger.warning("SpotifyHelper::search(): %s", e)
            # Do not emit search-finished on cancel
            if str(e) == "cancelled":
                return
        GLib.idle_add(self.emit, "search-finished")

    def charts(self, cancellable, language="global"):
        """
            Get albums related to search
            We need a thread because we are going to populate DB
            @param cancellable as Gio.Cancellable
            @param language as str
        """
        from csv import reader
        try:
            while self.wait_for_token():
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                sleep(1)
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            uri = self.__CHARTS % language
            spotify_ids = []
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = data.decode("utf-8")
                for line in decode.split("\n"):
                    try:
                        for row in reader([line]):
                            if not row:
                                continue
                            url = row[4]
                            if url == "URL":
                                continue
                            spotify_id = url.split("/")[-1]
                            if spotify_id:
                                spotify_ids.append(spotify_id)
                    except Exception as e:
                        Logger.warning("SpotifyHelper::charts(): %s", e)
            album_ids = []
            for spotify_id in spotify_ids:
                if cancellable.is_cancelled():
                    raise Exception("cancelled")
                payload = self.__get_track_payload(helper,
                                                   spotify_id,
                                                   cancellable)
                self.__create_albums_from_tracks_payload(
                                                 [payload],
                                                 album_ids,
                                                 cancellable)
        except Exception as e:
            Logger.warning("SpotifyHelper::charts(): %s", e)
            # Do not emit search-finished on cancel
            if str(e) == "cancelled":
                return
        GLib.idle_add(self.emit, "search-finished")

#######################
# PRIVATE             #
#######################
    def __get_track_payload(self, helper, spotify_id, cancellable):
        """
            Get track payload
            @param helper as TaskHelper
            @param spotify_id as str
            @param cancellable as Gio.Cancellable
            @return {}
        """
        try:
            uri = "https://api.spotify.com/v1/tracks/%s" % spotify_id
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            Logger.error("SpotifyHelper::__get_track_payload(): %s", e)
        return None

    def __create_album(self, album_id, cover_uri, cancellable):
        """
            Create album and download cover
            @param cancellable as Gio.Cancellable
        """
        if not cancellable.is_cancelled():
            GLib.idle_add(self.emit, "new-album", Album(album_id), cover_uri)

    def __create_albums_from_tracks_payload(self, payload, album_ids,
                                            cancellable):
        """
            Get albums from a track payload
            @param payload as {}
            @param album_ids as [int]
            @param cancellable as Gio.Cancellable
        """
        new_album_ids = {}
        # Populate tracks
        for item in payload:
            if cancellable.is_cancelled():
                raise Exception("cancelled")
            track_id = App().db.exists_in_db(item["album"]["name"],
                                             [artist["name"]
                                             for artist in item["artists"]],
                                             item["name"])
            if track_id is not None:
                track = Track(track_id)
                if track.album.id not in album_ids:
                    if track.is_web:
                        self.__create_album(track.album.id, None, cancellable)
                    album_ids.append(track.album.id)
                continue
            (album_id,
             track_id,
             cover_uri) = self.__save_track(item)
            if album_id not in new_album_ids.keys():
                new_album_ids[album_id] = cover_uri
        for album_id in new_album_ids.keys():
            if album_id not in album_ids:
                album_ids.append(album_id)
                self.__create_album(album_id,
                                    new_album_ids[album_id],
                                    cancellable)

    def __create_albums_from_album_payload(self, payload, album_ids,
                                           cancellable):
        """
            Get albums from an album payload
            @param payload as {}
            @param album_ids as [int]
            @param cancellable as Gio.Cancellable
        """
        # Populate tracks
        for album_item in payload:
            if cancellable.is_cancelled():
                return
            album_id = App().db.exists_in_db(
                                     album_item["name"],
                                     [artist["name"]
                                      for artist in album_item["artists"]],
                                     None)
            if album_id is not None:
                if album_id not in album_ids:
                    album = Album(album_id)
                    if album.tracks:
                        track = album.tracks[0]
                        if track.is_web:
                            self.__create_album(album_id, None, cancellable)
                    album_ids.append(album_id)
                continue
            uri = "https://api.spotify.com/v1/albums/%s" % album_item["id"]
            token = "Bearer %s" % self.__token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                track_payload = decode["tracks"]["items"]
                for item in track_payload:
                    item["album"] = album_item
                self.__create_albums_from_tracks_payload(track_payload,
                                                         album_ids,
                                                         cancellable)

    def __save_track(self, payload):
        """
            Save track to DB as non persistent
            @param payload as {}
            @return track_id
        """
        title = payload["name"]
        _artists = []
        for artist in payload["artists"]:
            _artists.append(artist["name"])
        _album_artists = []
        for artist in payload["album"]["artists"]:
            _album_artists.append(artist["name"])
        # Translate to tag value
        artists = ";".join(_artists)
        album_artists = ";".join(_album_artists)
        album_name = payload["album"]["name"]
        discnumber = int(payload["disc_number"])
        discname = None
        tracknumber = int(payload["track_number"])
        try:
            release_date = "%sT00:00:00" % payload["album"]["release_date"]
            dt = GLib.DateTime.new_from_iso8601(release_date,
                                                GLib.TimeZone.new_local())
            timestamp = dt.to_unix()
            year = dt.get_year()
        except Exception as e:
            Logger.warning("SpotifyHelper::__save_track(): %s", e)
            timestamp = None
            year = None
        duration = payload["duration_ms"] // 1000
        cover_uri = payload["album"]["images"][1]["url"]
        uri = "web://%s" % payload["id"]
        (track_id, album_id) = App().scanner.save_track(
                   None, artists, "", "", album_artists, "", "",
                   album_name, None, uri, 0, 0,
                   0, 0, 0, title, duration, tracknumber,
                   discnumber, discname, year, timestamp, 0,
                   0, 0, 0, 0, "", 0)
        return (album_id, track_id, cover_uri)
