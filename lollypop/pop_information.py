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

from lollypop.define import App
from lollypop.view_information import InformationView
from lollypop.widgets_utils import Popover


class InformationPopover(Popover):
    """
        Popover with artist information
    """

    def __init__(self, minimal=False):
        """
            Init artist infos
            @param minimal as bool
        """
        Popover.__init__(self)
        self.__minimal = minimal
        self.__view = InformationView(minimal)
        self.__view.show()
        self.connect("map", self.__on_map)
        self.add(self.__view)

    def populate(self, artist_id=None):
        """
            Show information for artists
            @param artist_id as int
        """
        self.__view.populate(artist_id)

#######################
# PROTECTED           #
#######################

#######################
# PRIVATE             #
#######################
    def __on_map(self, widget):
        """
            Connect signal and resize
            @param widget as Gtk.Widget
        """
        size = App().window.get_size()
        if self.__minimal:
            self.set_size_request(min(size[0] * 0.6, 500),
                                  min(size[1] * 0.5, 600))
        else:
            self.set_size_request(min(size[0] * 0.6, 1000),
                                  min(size[1] * 0.7, 800))
