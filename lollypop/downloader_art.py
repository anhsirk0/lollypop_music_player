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

from gi.repository import GLib, Soup

import json
from base64 import b64encode

from lollypop.define import App, GOOGLE_API_ID, Type, AUDIODB_CLIENT_ID
from lollypop.define import SPOTIFY_CLIENT_ID, SPOTIFY_SECRET
from lollypop.utils import get_network_available, noaccents
from lollypop.logger import Logger
from lollypop.objects import Album
from lollypop.downloader import Downloader
from lollypop.helper_task import TaskHelper


class ArtDownloader(Downloader):
    """
        Download art from the web
    """

    def __init__(self):
        """
            Init art downloader
        """
        Downloader.__init__(self)
        self.__albums_queue = []
        self.__albums_history = []
        self.__in_albums_download = False
        self.__cache_artists_running = False

    def search_album_artworks(self, artist, album, cancellable):
        """
            Search album artworks
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @thread safe
        """
        results = []
        for (api, a_helper, helper, b_helper) in self._WEBSERVICES:
            if helper is None:
                continue
            method = getattr(self, helper)
            uri = method(artist, album, cancellable)
            if uri is not None:
                results.append((uri, api))
        GLib.idle_add(self.emit, "uri-artwork-found", results)

    def search_artist_artwork(self, artist, cancellable):
        """
            Search artist artwork
            @param album as str
            @param cancellable as Gio.Cancellable
            @thread safe
        """
        results = []
        for (api, helper, a_helper, b_helper) in self._WEBSERVICES:
            if helper is None:
                continue
            method = getattr(self, helper)
            uri = method(artist, cancellable)
            if uri is not None:
                results.append((uri, api))
        GLib.idle_add(self.emit, "uri-artwork-found", results)

    def cache_album_artwork(self, album_id):
        """
            Download album artwork
            @param album_id as int
        """
        if album_id in self.__albums_history or\
                not get_network_available("DATA"):
            return
        self.__albums_queue.append(album_id)
        if not self.__in_albums_download:
            App().task_helper.run(self.__cache_albums_art)

    def cache_artists_artwork(self):
        """
            Cache info for all artists
        """
        if self.__cache_artists_running or not get_network_available("DATA"):
            return
        self.__cache_artists_running = True
        App().task_helper.run(self.__cache_artists_artwork)

    def search_artwork_from_google(self, search, cancellable):
        """
            Get google uri for search
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        if not get_network_available("GOOGLE"):
            GLib.idle_add(self.emit, "uri-artwork-found", None)
            return
        key = App().settings.get_value("cs-api-key").get_string() or\
            App().settings.get_default_value("cs-api-key").get_string()
        uri = "https://www.googleapis.com/" +\
              "customsearch/v1?key=%s&cx=%s" % (key, GOOGLE_API_ID) +\
              "&q=%s&searchType=image" % GLib.uri_escape_string(search,
                                                                "",
                                                                False)
        App().task_helper.load_uri_content(uri,
                                           cancellable,
                                           self.__on_load_google_content)

    def search_artwork_from_startpage(self, search, cancellable):
        """
            Get google uri for search
            @param search as str
            @param cancellable as Gio.Cancellable
        """
        if not get_network_available("STARTPAGE"):
            GLib.idle_add(self.emit, "uri-artwork-found", None)
            return
        uri = "https://www.startpage.com/do/search?flimgsize=isz%3Al"
        uri += "&image-size-select=&flimgexwidth=&flimgexheight=&abp=-1"
        uri += "&cat=pics&query=%s" % GLib.uri_escape_string(search, "", False)
        App().task_helper.load_uri_content(uri,
                                           cancellable,
                                           self.__on_load_startpage_content)

    def reset_history(self):
        """
            Reset download history
        """
        self.__albums_history = []

#######################
# PROTECTED           #
#######################
    def _get_deezer_artist_artwork_uri(self, artist, cancellable=None):
        """
            Return deezer artist information
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("DEEZER"):
            return None
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.deezer.com/search/artist/?" +\
                  "q=%s&output=json&index=0&limit=1&" % artist_formated
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                uri = None
                decode = json.loads(data.decode("utf-8"))
                uri = decode["data"][0]["picture_xl"]
                return uri
        except Exception as e:
            Logger.debug("ArtDownloader::_get_deezer_artist_artwork_uri(): %s"
                         % e)
        return None

    def _get_spotify_artist_artwork_uri(self, artist, cancellable=None):
        """
            Return spotify artist information
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("SPOTIFY"):
            return None
        try:
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.spotify.com/v1/search?q=%s" % artist_formated +\
                  "&type=artist"
            token = "Bearer %s" % self.__get_spotify_token(cancellable)
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                uri = None
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    if noaccents(item["name"].lower()) ==\
                            noaccents(artist.lower()):
                        uri = item["images"][0]["url"]
                        return uri
        except Exception as e:
            Logger.debug("ArtDownloader::_get_spotify_artist_artwork_uri(): %s"
                         % e)
        return None

    def _get_deezer_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork uri from deezer
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("DEEZER"):
            return None
        try:
            album_formated = GLib.uri_escape_string(album, None, True)
            uri = "https://api.deezer.com/search/album/?" +\
                  "q=%s&output=json" % album_formated
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                uri = None
                for item in decode["data"]:
                    if noaccents(item["artist"]["name"].lower()) ==\
                            noaccents(artist.lower()):
                        uri = item["cover_xl"]
                        return uri
        except Exception as e:
            Logger.error("ArtDownloader::__get_deezer_album_artwork_uri: %s"
                         % e)
        return None

    def _get_spotify_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork uri from spotify
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("SPOTIFY"):
            return None
        artists_spotify_ids = []
        try:
            token = self.__get_spotify_token(cancellable)
            artist_formated = GLib.uri_escape_string(
                artist, None, True).replace(" ", "+")
            uri = "https://api.spotify.com/v1/search?q=%s" % artist_formated +\
                  "&type=artist"
            token = "Bearer %s" % token
            helper = TaskHelper()
            helper.add_header("Authorization", token)
            (status, data) = helper.load_uri_content_sync(uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["artists"]["items"]:
                    artists_spotify_ids.append(item["id"])

            for artist_spotify_id in artists_spotify_ids:
                uri = "https://api.spotify.com/v1/artists/" +\
                      "%s/albums" % artist_spotify_id
                (status, data) = helper.load_uri_content_sync(uri, cancellable)
                if status:
                    decode = json.loads(data.decode("utf-8"))
                    uri = None
                    for item in decode["items"]:
                        if noaccents(item["name"].lower()) ==\
                                noaccents(album.lower()):
                            return item["images"][0]["url"]
        except Exception as e:
            Logger.error("ArtDownloader::_get_album_art_spotify_uri: %s" % e)
        return None

    def _get_itunes_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork uri from itunes
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("ITUNES"):
            return None
        try:
            album_formated = GLib.uri_escape_string(
                album, None, True).replace(" ", "+")
            uri = "https://itunes.apple.com/search" +\
                  "?entity=album&term=%s" % album_formated
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                for item in decode["results"]:
                    if noaccents(item["artistName"].lower()) ==\
                            noaccents(artist.lower()):
                        uri = item["artworkUrl60"].replace("60x60",
                                                           "1024x1024")
                        return uri
        except Exception as e:
            Logger.error("ArtDownloader::_get_album_art_itunes_uri: %s"
                         % e)
        return None

    def _get_audiodb_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork from audiodb
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @thread safe
        """
        if not get_network_available("AUDIODB"):
            return None
        try:
            album = GLib.uri_escape_string(album, None, True)
            artist = GLib.uri_escape_string(artist, None, True)
            uri = "https://theaudiodb.com/api/v1/json/"
            uri += "%s/searchalbum.php?s=%s&a=%s" % (AUDIODB_CLIENT_ID,
                                                     artist,
                                                     album)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                if decode["album"]:
                    for item in decode["album"]:
                        uri = item["strAlbumThumb"]
                        return uri
        except Exception as e:
            Logger.error("ArtDownloader::_get_audiodb_album_artwork_uri: %s"
                         % e)
        return None

    def _get_audiodb_artist_artwork_uri(self, artist, cancellable=None):
        """
            Get artist artwork uri from audiodb
            @param artist as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @thread safe
        """
        if not get_network_available("AUDIODB"):
            return None
        try:
            artist = GLib.uri_escape_string(artist, None, True)
            uri = "https://theaudiodb.com/api/v1/json/"
            uri += "%s/search.php?s=%s" % (AUDIODB_CLIENT_ID, artist)
            (status, data) = App().task_helper.load_uri_content_sync(
                uri, cancellable)
            if status:
                decode = json.loads(data.decode("utf-8"))
                uri = None
                for item in decode["artists"]:
                    for key in ["strArtistFanart", "strArtistThumb"]:
                        uri = item[key]
                        if uri is not None:
                            return uri
        except Exception as e:
            Logger.error("ArtDownloader::_get_audiodb_artist_artwork_uri: %s"
                         % e)
        return None

    def _get_lastfm_album_artwork_uri(self, artist, album, cancellable=None):
        """
            Get album artwork uri from lastfm
            @param artist as str
            @param album as str
            @param cancellable as Gio.Cancellable
            @return uri as str
            @tread safe
        """
        if not get_network_available("LASTFM"):
            return None
        if App().lastfm is not None:
            try:
                last_album = App().lastfm.get_album(artist, album)
                uri = last_album.get_cover_image(4)
                return uri
            except Exception as e:
                Logger.error("ArtDownloader::_get_album_art_lastfm_uri: %s"
                             % e)
        return None

#######################
# PRIVATE             #
#######################
    def __get_spotify_token(self, cancellable):
        """
            Get a new auth token
            @param cancellable as Gio.Cancellable
            @return str
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
                return decode["access_token"]
        except:
            return ""

    def __cache_artists_artwork(self):
        """
            Cache artwork for all artists
        """
        # Then cache for lastfm/spotify/deezer/...
        for (artist_id, artist, sort) in App().artists.get([]):
            if App().art.artist_artwork_exists(artist)[0]:
                continue
            for (api, helper, a_helper, b_helper) in self._WEBSERVICES:
                if helper is None:
                    continue
                try:
                    method = getattr(self, helper)
                    uri = method(artist)
                    if uri is not None:
                        (status,
                         data) = App().task_helper.load_uri_content_sync(uri,
                                                                         None)
                        if status:
                            App().art.add_artist_artwork(artist, data)
                            break
                except Exception as e:
                    Logger.error(
                        "ArtDownloader::__cache_artists_artwork(): %s" % e)
                    App().art.add_artist_artwork(artist, None)
        self.__cache_artists_running = False

    def __cache_albums_art(self):
        """
            Cache albums artwork (from queue)
            @thread safe
        """
        self.__in_albums_download = True
        try:
            while self.__albums_queue:
                album_id = self.__albums_queue.pop()
                album = App().albums.get_name(album_id)
                artist_ids = App().albums.get_artist_ids(album_id)
                is_compilation = artist_ids and\
                    artist_ids[0] == Type.COMPILATIONS
                if is_compilation:
                    artist = ""
                else:
                    artist = ", ".join(App().albums.get_artists(album_id))
                for (api, a_helper, helper, b_helper) in self._WEBSERVICES:
                    if helper is None:
                        continue
                    method = getattr(self, helper)
                    uri = method(artist, album)
                    if uri is not None:
                        (status,
                         data) = App().task_helper.load_uri_content_sync(uri,
                                                                         None)
                        if status:
                            self.__albums_history.append(album_id)
                            App().art.save_album_artwork(data, Album(album_id))
                            break
        except Exception as e:
            Logger.error("ArtDownloader::__cache_albums_art: %s" % e)
        self.__albums_history.append(album_id)
        self.__in_albums_download = False

    def __on_load_google_content(self, uri, loaded, content):
        """
            Extract uris from content
            @param uri as str
            @param loaded as bool
            @param content as bytes
        """
        try:
            if not loaded:
                self.emit("uri-artwork-found", [])
                return
            decode = json.loads(content.decode("utf-8"))
            results = []
            for item in decode["items"]:
                if item["link"] is not None:
                    results.append((item["link"], "Google"))
            self.emit("uri-artwork-found", results)
        except Exception as e:
            self.emit("uri-artwork-found", [])
            Logger.error("ArtDownloader::__on_load_google_content(): %s: %s"
                         % (e, content))

    def __on_load_startpage_content(self, uri, loaded, content):
        """
            Extract uris from content
            @param uri as str
            @param loaded as bool
            @param content as bytes
        """
        try:
            if not loaded:
                self.emit("uri-artwork-found", [])
                return
            found_uris = []
            import re
            data = content.decode("utf-8")
            res = re.findall(r'.*oiu=([^&]*).*', data)
            for data in res:
                uri = GLib.uri_unescape_string(data, "")
                if uri in found_uris or uri is None:
                    continue
                found_uris.append(uri)
            results = [(uri, "Startpage") for uri in found_uris]
            self.emit("uri-artwork-found", results)
        except Exception as e:
            self.emit("uri-artwork-found", [])
            Logger.error("ArtDownloader::__on_load_startpage_content(): %s"
                         % e)
