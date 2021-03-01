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

from gi.repository import GObject, GLib, Gio, TotemPlParser

from gettext import gettext as _
import itertools
import sqlite3
from datetime import datetime
from threading import Lock
import json

from lollypop.database import Database
from lollypop.define import App, Type
from lollypop.objects import Track
from lollypop.logger import Logger
from lollypop.sqlcursor import SqlCursor
from lollypop.localized import LocalizedCollation
from lollypop.shown import ShownPlaylists
from lollypop.database_upgrade import DatabasePlaylistsUpgrade


class Playlists(GObject.GObject):
    """
        Playlists manager
    """
    __LOCAL_PATH = GLib.get_user_data_dir() + "/lollypop"
    _DB_PATH = "%s/playlists.db" % __LOCAL_PATH
    __gsignals__ = {
        # Add or remove a playlist
        "playlists-changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        # Objects added/removed to/from playlist
        "playlist-track-added": (
            GObject.SignalFlags.RUN_FIRST, None, (int, str, int)),
        "playlist-track-removed": (
            GObject.SignalFlags.RUN_FIRST, None, (int, str, int))
    }
    __create_playlists = """CREATE TABLE playlists (
                            id INTEGER PRIMARY KEY,
                            name TEXT NOT NULL,
                            synced INT NOT NULL DEFAULT 0,
                            smart_enabled INT NOT NULL DEFAULT 0,
                            smart_sql TEXT,
                            mtime BIGINT NOT NULL)"""

    __create_tracks = """CREATE TABLE tracks (
                        playlist_id INT NOT NULL,
                        uri TEXT NOT NULL)"""

    def __init__(self):
        """
            Init playlists manager
        """
        self.thread_lock = Lock()
        GObject.GObject.__init__(self)
        upgrade = DatabasePlaylistsUpgrade()
        # Create db schema
        f = Gio.File.new_for_path(self._DB_PATH)
        if not f.query_exists():
            try:
                with SqlCursor(self, True) as sql:
                    sql.execute(self.__create_playlists)
                    sql.execute(self.__create_tracks)
                    sql.execute("PRAGMA user_version=%s" % upgrade.version)
            except:
                pass
        else:
            upgrade.upgrade(self)

    def add(self, name):
        """
            Add a playlist
            @param name as str
            @return playlist_id as int
            @thread safe
        """
        if name == _("Loved tracks"):
            return Type.LOVED
        with SqlCursor(self, True) as sql:
            result = sql.execute("INSERT INTO playlists (name, mtime)"
                                 " VALUES (?, ?)",
                                 (name, datetime.now().strftime("%s")))
            GLib.idle_add(self.emit, "playlists-changed", result.lastrowid)
            return result.lastrowid

    def exists(self, playlist_id):
        """
            Return True if playlist exists
            @param playlist_id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM playlists\
                                  WHERE rowid=?",
                                 (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return True
            else:
                return False

    def rename(self, playlist_id, name):
        """
            Rename playlist
            @param playlist_id as int
            @param name as str
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE playlists\
                        SET name=?\
                        WHERE rowid=?",
                        (name, playlist_id))
            GLib.idle_add(self.emit, "playlists-changed", playlist_id)

    def remove(self, playlist_id):
        """
            Remove playlist
            @param playlist_id as int
        """
        with SqlCursor(self, True) as sql:
            sql.execute("DELETE FROM playlists\
                        WHERE rowid=?",
                        (playlist_id,))
            sql.execute("DELETE FROM tracks\
                        WHERE playlist_id=?",
                        (playlist_id,))
            GLib.idle_add(self.emit, "playlists-changed", playlist_id)

    def clear(self, playlist_id):
        """
            Clear playlsit
            @param playlist_id as int
        """
        with SqlCursor(self, True) as sql:
            sql.execute("DELETE FROM tracks\
                         WHERE playlist_id=?", (playlist_id,))

    def add_uri(self, playlist_id, uri, signal=False):
        """
            Add uri to playlist
            @param playlist_id as int
            @param uri as str
            @param signal as bool
        """
        if self.exists_track(playlist_id, uri):
            return
        if signal:
            position = len(self.get_track_uris(playlist_id))
            self.emit("playlist-track-added", playlist_id, uri, position)
        with SqlCursor(self, True) as sql:
            sql.execute("INSERT INTO tracks VALUES (?, ?)", (playlist_id, uri))
            sql.execute("UPDATE playlists SET mtime=?\
                         WHERE rowid=?", (datetime.now().strftime("%s"),
                                          playlist_id))

    def add_uris(self, playlist_id, uris, signal=False):
        """
            Add uris to playlists (even if exists)
            @param playlist_id as int
            @param uris as [str]
            @param signal as bool
        """
        for uri in uris:
            self.add_uri(playlist_id, uri, signal)

    def add_tracks(self, playlist_id, tracks, signal=False):
        """
            Add tracks to playlist
            @param playlist_id as int
            @param tracks as [Track]
            @param signal as bool
        """
        for track in tracks:
            self.add_uri(playlist_id, track.uri, signal)

    def insert_track(self, playlist_id, track, position):
        """
            Insert track at position, will remove track first if exists
            @param playlist_id as int
            @param track as Track
            @param position as int
        """
        SqlCursor.add(self)
        track_ids = self.get_track_ids(playlist_id)
        if track.id in track_ids:
            index = track_ids.index(track.id)
            track_ids.remove(track.id)
            if index < position:
                position -= 1
        track_ids.insert(position, track.id)
        self.clear(playlist_id)
        tracks = [Track(track_id) for track_id in track_ids]
        self.add_tracks(playlist_id, tracks)
        SqlCursor.remove(self)

    def remove_uri(self, playlist_id, uri, signal=False):
        """
            Remove uri from playlist
            @param playlist_id as int
            @param uri a str
            @param signal as bool
        """
        if not self.exists_track(playlist_id, uri):
            return
        if signal:
            uris = self.get_track_uris(playlist_id)
            position = uris.index(uri)
            self.emit("playlist-track-removed", playlist_id, uri, position)
        with SqlCursor(self, True) as sql:
            sql.execute("DELETE FROM tracks WHERE uri=? AND playlist_id=?",
                        (uri, playlist_id))
            sql.execute("UPDATE playlists SET mtime=?\
                         WHERE rowid=?", (datetime.now().strftime("%s"),
                                          playlist_id))

    def remove_uris(self, playlist_id, uris, signal=False):
        """
            Remove uris from playlist
            @param playlist_id as int
            @param uris as [str]
            @param signal as bool
        """
        for uri in uris:
            self.remove_uri(playlist_id, uri, signal)

    def remove_tracks(self, playlist_id, tracks, signal=False):
        """
            Remove tracks from playlist
            @param playlist_id as int
            @param tracks as [Track]
            @param signal as bool
        """
        for track in tracks:
            self.remove_uri(playlist_id, track.uri, signal)

    def remove_uri_from_all(self, uri):
        """
            Remove track from all playlists
            @param uri as str
        """
        with SqlCursor(self, True) as sql:
            sql.execute("DELETE FROM tracks\
                        WHERE uri=?",
                        (uri,))

    def get(self):
        """
            Return availables playlists
            @return [int, str, str]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid, name, name\
                                  FROM playlists\
                                  ORDER BY name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(result)

    def get_ids(self):
        """
            Return availables playlists
            @return [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM playlists\
                                  ORDER BY name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(itertools.chain(*result))

    def get_last(self):
        """
            Return 6 last modified playlist
            @return [string]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid, name\
                                  FROM playlists\
                                  WHERE smart_enabled=0\
                                  ORDER BY mtime DESC\
                                  LIMIT 4")
            return list(result)

    def get_track_uris(self, playlist_id):
        """
            Return availables track uris for playlist
            @param playlist_id as int
            @return [str]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT uri\
                                  FROM tracks\
                                  WHERE playlist_id=?", (playlist_id,))
            return list(itertools.chain(*result))

    def get_track_ids(self, playlist_id):
        """
            Return availables track ids for playlist
            @param playlist_id as int
            @return [int]
        """
        track_ids = []
        if playlist_id == Type.POPULARS:
            track_ids = App().tracks.get_rated()
            for track in App().tracks.get_populars():
                track_ids.append(track)
        elif playlist_id == Type.RECENTS:
            track_ids = App().tracks.get_recently_listened_to()
        elif playlist_id == Type.NEVER:
            track_ids = App().tracks.get_never_listened_to()
        elif playlist_id == Type.RANDOMS:
            track_ids = App().tracks.get_randoms()
        elif playlist_id == Type.LOVED:
            track_ids = App().playlists.get_track_ids_sorted(playlist_id)
        else:
            with SqlCursor(self) as sql:
                result = sql.execute("SELECT music.tracks.rowid\
                                      FROM tracks, music.tracks\
                                      WHERE tracks.playlist_id=?\
                                      AND music.tracks.uri=\
                                      main.tracks.uri",
                                     (playlist_id,))
                track_ids = list(itertools.chain(*result))
        return track_ids

    def get_tracks(self, playlist_id):
        """
            Return availables tracks for playlist
            @param playlist_id as int
            @return [Track]
        """
        return [Track(track_id)
                for track_id in self.get_track_ids(playlist_id)]

    def get_duration(self, playlist_id):
        """
            Return playlist duration
            @param playlist_id as int
            @return duration as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT SUM(music.tracks.duration)\
                                  FROM tracks, music.tracks\
                                  WHERE tracks.playlist_id=?\
                                  AND music.tracks.uri=\
                                  main.tracks.uri",
                                 (playlist_id,))
            v = result.fetchone()
            if v is not None and v[0] is not None:
                return v[0]
            return 0

    def get_track_ids_sorted(self, playlist_id):
        """
            Return availables track ids for playlist sorted by artist/album
            @param playlist_id as int
            @return array of track id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT music.tracks.rowid\
                                  FROM tracks, music.tracks,\
                                  music.track_artists, music.artists\
                                  WHERE tracks.playlist_id=?\
                                  AND music.track_artists.track_id=\
                                  music.tracks.rowid\
                                  AND music.artists.id=\
                                  music.track_artists.artist_id\
                                  AND music.tracks.uri=\
                                  main.tracks.uri\
                                  ORDER BY\
                                  music.artists.sortname, album_id",
                                 (playlist_id,))
            return list(itertools.chain(*result))

    def get_id(self, playlist_name):
        """
            Get playlist id
            @param playlist_name as str
            @return playlst id as int
        """
        if playlist_name == _("Loved tracks"):
            return Type.LOVED

        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                 FROM playlists\
                                 WHERE name=?", (playlist_name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return Type.NONE

    def get_name(self, playlist_id):
        """
            Get playlist name
            @param playlist_id as int
            @return playlist name as str
        """
        if playlist_id < 0:
            for (id, name, sortname) in ShownPlaylists.get(True):
                if id == playlist_id:
                    return name

        with SqlCursor(self) as sql:
            result = sql.execute("SELECT name\
                                 FROM playlists\
                                 WHERE rowid=?", (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_names(self, playlist_ids):
        """
            Return playlist names
            @param playlist_ids as [int]
            @return names as [str]
        """
        names = []
        for playlist_id in playlist_ids:
            if playlist_id == Type.POPULARS:
                names.append(_("Popular tracks"))
            elif playlist_id == Type.RECENTS:
                names.append(_("Recently played"))
            elif playlist_id == Type.NEVER:
                names.append(_("Never played"))
            elif playlist_id == Type.RANDOMS:
                names.append(_("Random tracks"))
            elif playlist_id == Type.SEARCH:
                names.append(_("Search"))
            else:
                names.append(self.get_name(playlist_id))
        return names

    def get_synced(self, playlist_id, index):
        """
            True if playlist synced
            @param playlist_id as int
            @param index as int
            @return bool
        """
        if playlist_id < 0:
            internal_ids = App().settings.get_value(
                    "sync-internal-ids").get_string()
            try:
                data = json.loads(internal_ids)
            except:
                data = {}
            synced_ids = []
            for synced_id in data.keys():
                if data[synced_id] & (1 << index):
                    synced_ids.append(int(synced_id))
            return playlist_id in synced_ids
        else:
            with SqlCursor(self) as sql:
                result = sql.execute("SELECT synced\
                                     FROM playlists\
                                     WHERE rowid=?", (playlist_id,))
                v = result.fetchone()
                if v is not None:
                    return v[0] & (1 << index)
                return False

    def get_synced_ids(self, index):
        """
            Return availables synced playlists
            @return [int]
        """
        with SqlCursor(self) as sql:
            internal_ids = App().settings.get_value(
                    "sync-internal-ids").get_string()
            try:
                data = json.loads(internal_ids)
            except:
                data = {}
            synced_ids = []
            for playlist_id in data.keys():
                if data[playlist_id] & (1 << index):
                    synced_ids.append(int(playlist_id))
            result = sql.execute("SELECT rowid\
                                  FROM playlists\
                                  WHERE synced & (1 << ?)\
                                  ORDER BY name\
                                  COLLATE NOCASE COLLATE LOCALIZED",
                                 (index,))
            return list(itertools.chain(*result)) + synced_ids

    def get_smart(self, playlist_id):
        """
            True if playlist is smart
            @param playlist_id as int
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT smart_enabled\
                                 FROM playlists\
                                 WHERE rowid=?", (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return False

    def get_smart_sql(self, playlist_id):
        """
            Get SQL smart request
            @param playlist_id as int
            @return str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT smart_sql\
                                 FROM playlists\
                                 WHERE rowid=?", (playlist_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def set_synced(self, playlist_id, synced):
        """
            Mark playlist as synced
            @param playlist_id as int
            @param synced as bool
        """
        if playlist_id < 0:
            internal_ids = App().settings.get_value(
                "sync-internal-ids").get_string()
            try:
                data = json.loads(internal_ids)
            except:
                data = {}
            data[str(playlist_id)] = synced
            internal_ids = json.dumps(data)
            App().settings.set_value("sync-internal-ids",
                                     GLib.Variant("s", internal_ids))
        else:
            with SqlCursor(self, True) as sql:
                sql.execute("UPDATE playlists\
                            SET synced=?\
                            WHERE rowid=?",
                            (synced, playlist_id))

    def set_smart(self, playlist_id, smart):
        """
            Mark playlist as smart
            @param playlist_id as int
            @param smart as bool
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE playlists\
                        SET smart_enabled=?\
                        WHERE rowid=?",
                        (smart, playlist_id))

    def set_smart_sql(self, playlist_id, request):
        """
            Set playlist SQL smart request
            @param playlist_id as int
            @param request as str
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE playlists\
                        SET smart_sql=?\
                        WHERE rowid=?",
                        (request, playlist_id))

    def import_uri(self, playlist_id, uri, start=None, down=True):
        """
            Import uri in playlist
            @param playlist_id as int
            @param uri as str
            @param start track id as int
            @param down as bool
        """
        try:
            uri = uri.strip("\n\r")
            f = Gio.File.new_for_uri(uri)
            if f.query_exists():
                if f.query_file_type(Gio.FileQueryInfoFlags.NONE,
                                     None) == Gio.FileType.DIRECTORY:
                    walk_uris = [uri]
                    track_ids = []
                    while walk_uris:
                        uri = walk_uris.pop(0)
                        try:
                            d = Gio.File.new_for_uri(uri)
                            infos = d.enumerate_children(
                                "standard::name,standard::type",
                                Gio.FileQueryInfoFlags.NONE,
                                None)
                        except Exception as e:
                            Logger.info("Playlists::import_uri(): %s" % e)
                            continue
                        for info in infos:
                            f = infos.get_child(info)
                            if info.get_file_type() == Gio.FileType.DIRECTORY:
                                walk_uris.append(f.get_uri())
                            else:
                                track_id = App().tracks.get_id_by_uri(
                                    f.get_uri())
                                if track_id is not None:
                                    track_ids.append(track_id)
                else:
                    track_id = App().tracks.get_id_by_uri(uri)
                    track_ids = [track_id]
                tracks = []
                if start is None:
                    for track_id in track_ids:
                        tracks.append(Track(track_id))
                    self.add_tracks(playlist_id, tracks)
                else:
                    # Insert at wanted position
                    playlist_track_ids = self.get_track_ids(playlist_id)
                    start_idx = playlist_track_ids.index(start)
                    if down:
                        start_idx += 1
                    for track_id in track_ids:
                        playlist_track_ids.insert(start_idx, track_id)
                        GLib.idle_add(self.emit, "playlist-add",
                                      playlist_id, track_id, start_idx)
                        start_idx += 1
                    self.clear(playlist_id)
                    tracks = []
                    for track_id in playlist_track_ids:
                        tracks.append(Track(track_id))
                    self.add_tracks(playlist_id, tracks)
        except:
            pass

    def get_position(self, playlist_id, track_id):
        """
            Get track position in playlist
            @param playlist_id as int
            @param track_id as int
            @return position as int
        """
        i = 0
        for tid in self.get_track_ids(playlist_id):
            if track_id == tid:
                break
            i += 1
        return i

    def exists_track(self, playlist_id, uri):
        """
            Check if track id exist in playlist
            @param playlist_id as int
            @param uri as str
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT uri\
                                  FROM tracks\
                                  WHERE playlist_id=?\
                                  AND uri=?",
                                 (playlist_id, uri))
            v = result.fetchone()
            if v is not None:
                return True
            return False

    def exists_album(self, playlist_id, album):
        """
            Return True if object_id is already present in playlist
            @param playlist_id as int
            @param album as Album/Disc
            @return bool
        """
        # We do not use Album object for performance reasons
        playlist_uris = self.get_track_uris(playlist_id)
        track_uris = album.track_uris
        return len(set(playlist_uris) & set(track_uris)) == len(track_uris)

    def remove_device(self, index):
        """
            Remove device from DB
            @param index as int => device index
        """
        with SqlCursor(self, True) as sql:
            sql.execute("UPDATE playlists SET synced = synced & ~(1<<?)",
                        (index,))

    def import_tracks(self, f):
        """
            Import file as playlist
            @param f as Gio.File
        """
        basename = ".".join(f.get_basename().split(".")[:-1])
        parser = TotemPlParser.Parser.new()
        playlist_id = self.get_id(basename)
        if playlist_id in [Type.NONE, Type.LOVED]:
            playlist_id = self.add(basename)
            uris = self.get_tracks(playlist_id)
            if not uris:
                parser.connect("entry-parsed", self.__on_entry_parsed,
                               playlist_id, uris)
                parser.parse_async(f.get_uri(), True,
                                   None, self.__on_parse_finished,
                                   playlist_id, uris)

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            sql = sqlite3.connect(self._DB_PATH, 600.0)
            sql.execute('ATTACH DATABASE "%s" AS music' % Database.DB_PATH)
            sql.create_collation("LOCALIZED", LocalizedCollation())
            return sql
        except:
            exit(-1)

#######################
# PRIVATE             #
#######################
    def __on_parse_finished(self, parser, result, playlist_id, uris):
        """
            Add tracks to playlists
            @param parser as TotemPlParser.Parser
            @param result as Gio.AsyncResult
            @param playlist_id as int
            @param uris as [str]
        """
        self.add_uris(playlist_id, uris)

    def __on_entry_parsed(self, parser, uri, metadata, playlist_id, uris):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param track uri as str
            @param metadata as GLib.HastTable
            @param playlist_id as int
            @param uris as [str]
        """
        uris.append(uri)
