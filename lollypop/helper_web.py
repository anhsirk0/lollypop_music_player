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

from lollypop.helper_web_youtube import YouTubeHelper
from lollypop.define import App


class WebHelper:
    """
        Web helper
    """

    def __init__(self):
        """
            Init helper
        """
        self.__helpers = [YouTubeHelper()]

    def set_uri(self, track, cancellable):
        """
            Set uri for track
            @param track as Track
            @param cancellable as Gio.Cancellable
        """
        if track.is_http:
            return
        for helper in self.__helpers:
            uri = helper.get_uri(track, cancellable)
            if uri:
                App().tracks.set_uri(track.id, uri)
                track.set_uri(uri)
                return

    def get_track_content(self, track):
        """
            Get content uri
            @param track as Track
            @return content uri as str
        """
        for helper in self.__helpers:
            uri = helper.get_uri_content(track)
            if uri:
                return uri
        return ""
