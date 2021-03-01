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

from lollypop.view import View
from lollypop.define import App
from lollypop.widgets_equalizer import EqualizerWidget


class EqualizerView(View):
    """
        Show equalizer widget
    """

    def __init__(self):
        """
            Init view
        """
        View.__init__(self)
        widget = EqualizerWidget()
        widget.show()
        self.add(widget)

##############
# PROTECTED  #
##############
    def _on_map(self, widget):
        """
            Show buttons
        """
        App().window.emit("show-can-go-back", True)
        App().window.emit("can-go-back-changed", True)

    def _on_unmap(self, widget):
        """
            Destroy self
            @param widget as Gtk.Widget
        """
        self.destroy_later()

############
# PRIVATE  #
############
