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

import itertools

from lollypop.sqlcursor import SqlCursor
from lollypop.define import App, Type, OrderBy
from lollypop.utils import get_network_available


class GenresDatabase:
    """
        Genres database helper
    """

    def __init__(self):
        """
            Init genres database object
        """
        pass

    def add(self, name):
        """
            Add a new genre to database
            @param name as string
            @return inserted rowid as int
            @warning: commit needed
        """
        with SqlCursor(App().db, True) as sql:
            result = sql.execute("INSERT INTO genres (name) VALUES (?)",
                                 (name,))
            return result.lastrowid

    def get_id(self, name):
        """
            Get genre id for name
            @param name as string
            @return genre id as int
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT rowid FROM genres\
                                  WHERE name=?", (name,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_name(self, genre_id):
        """
            Get genre name for genre id
            @param genre_id as int
            @return str
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT name FROM genres\
                                  WHERE rowid=?", (genre_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_album_ids(self, genre_id, ignore=False):
        """
            Get all availables albums for genres
            @param genre_id as int
            @param ignore as bool
            @return [int]
        """
        orderby = App().settings.get_enum("orderby")
        if OrderBy.ARTIST:
            order = " ORDER BY artists.sortname\
                     COLLATE NOCASE COLLATE LOCALIZED,\
                     albums.timestamp,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.NAME:
            order = " ORDER BY albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        elif orderby == OrderBy.YEAR:
            order = " ORDER BY albums.timestamp DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        else:
            order = " ORDER BY albums.popularity DESC,\
                     albums.name\
                     COLLATE NOCASE COLLATE LOCALIZED"
        with SqlCursor(App().db) as sql:
            filters = (genre_id, )
            request = "SELECT albums.rowid\
                       FROM albums, album_genres\
                       WHERE album_genres.genre_id=?\
                       AND album_genres.album_id=albums.rowid"
            if not get_network_available():
                request += " AND albums.synced!=%s" % Type.NONE
            if ignore:
                request += " AND albums.loved != -1"
            request += order
            result = sql.execute(request, filters)
            return list(itertools.chain(*result))

    def get(self):
        """
            Get all availables genres
            @return [(id as int, name as string)]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT DISTINCT\
                                  genres.rowid, genres.name,genres.name\
                                  FROM genres\
                                  WHERE genres.rowid IN (\
                                    SELECT album_genres.genre_id\
                                    FROM album_genres, albums\
                                    WHERE album_genres.album_id=albums.rowid\
                                    AND albums.mtime!=0)\
                                  ORDER BY genres.name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(result)

    def get_ids(self):
        """
            Get all availables genres ids
            @return [id as int]
        """
        with SqlCursor(App().db) as sql:
            result = sql.execute("SELECT DISTINCT genres.rowid\
                                  FROM genres\
                                  WHERE genres.rowid IN (\
                                    SELECT album_genres.genre_id\
                                    FROM album_genres, albums\
                                    WHERE album_genres.album_id=albums.rowid\
                                    AND albums.mtime!=0)\
                                  ORDER BY genres.name\
                                  COLLATE NOCASE COLLATE LOCALIZED")
            return list(itertools.chain(*result))

    def clean(self):
        """
            Clean genres
        """
        with SqlCursor(App().db, True) as sql:
            sql.execute("DELETE FROM genres WHERE genres.rowid NOT IN (\
                            SELECT album_genres.genre_id FROM album_genres)")
            sql.execute("DELETE FROM genres WHERE genres.rowid NOT IN (\
                            SELECT track_genres.genre_id FROM track_genres)")
