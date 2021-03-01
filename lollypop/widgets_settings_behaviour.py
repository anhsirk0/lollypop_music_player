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

from gi.repository import Gtk, GLib

from gettext import gettext as _

from lollypop.define import App, NetworkAccessACL


class BehaviourSettingsWidget(Gtk.Bin):
    """
        Widget allowing user to set behaviour options
    """

    def __init__(self):
        """
            Init widget
        """
        Gtk.Bin.__init__(self)
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Lollypop/SettingsBehaviour.ui")

        switch_scan = builder.get_object("switch_scan")
        switch_scan.set_state(App().settings.get_value("auto-update"))

        switch_background = builder.get_object("switch_background")
        switch_background.set_state(
            App().settings.get_value("background-mode"))

        switch_state = builder.get_object("switch_state")
        switch_state.set_state(App().settings.get_value("save-state"))

        switch_import = builder.get_object("switch_import")
        switch_import.set_state(App().settings.get_value("import-playlists"))

        switch_network_access = builder.get_object("switch_network_access")
        network_access = App().settings.get_value("network-access")
        switch_network_access.set_state(network_access)

        switch_transitions = builder.get_object("switch_transitions")
        smooth_transitions = App().settings.get_value("smooth-transitions")
        switch_transitions.set_state(smooth_transitions)
        builder.get_object("transitions_button").set_sensitive(
            smooth_transitions)

        switch_mix_party = builder.get_object("switch_mix_party")
        switch_mix_party.set_state(App().settings.get_value("party-mix"))

        switch_artwork_tags = builder.get_object("switch_artwork_tags")

        # Check for kid3-cli
        self.__check_for_kid3(switch_artwork_tags)

        self.__popover_transitions = builder.get_object("popover-transitions")
        self.__scale_transition_duration = builder.get_object(
            "scale_transition_duration")
        self.__scale_transition_duration.set_range(1, 20)
        self.__scale_transition_duration.set_value(
            App().settings.get_value("transition-duration").get_int32())

        self.__popover_network = builder.get_object("popover-network")
        switch_network_access = builder.get_object("switch_network_access")
        network_access = App().settings.get_value("network-access")
        switch_network_access.set_state(network_access)
        builder.get_object("network_button").set_sensitive(
            network_access)

        acl = App().settings.get_value("network-access-acl").get_int32()
        for key in NetworkAccessACL.keys():
            if acl & NetworkAccessACL[key]:
                builder.get_object(key).set_state(True)

        self.add(builder.get_object("widget"))
        builder.connect_signals(self)

#######################
# PROTECTED           #
#######################
    def _on_enable_network_access_state_set(self, widget, state):
        """
            Save network access state
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("network-access",
                                 GLib.Variant("b", state))

    def _on_enable_switch_state_set(self, widget, state):
        """
            Save network acl state
            @param widget as Gtk.Switch
            @param state as bool
        """
        key = widget.get_name()
        acl = App().settings.get_value("network-access-acl").get_int32()
        if state:
            acl |= NetworkAccessACL[key]
        else:
            acl &= ~NetworkAccessACL[key]
        acl = App().settings.set_value("network-access-acl",
                                       GLib.Variant("i", acl))
        App().art.reset_history()
        App().art.cache_artists_artwork()

    def _on_switch_scan_state_set(self, widget, state):
        """
            Update scan setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("auto-update",
                                 GLib.Variant("b", state))

    def _on_switch_background_state_set(self, widget, state):
        """
            Update background mode setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("background-mode",
                                 GLib.Variant("b", state))

    def _on_switch_state_state_set(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-state",
                                 GLib.Variant("b", state))

    def _on_switch_import_state_set(self, widget, state):
        """
            Update save state setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("import-playlists",
                                 GLib.Variant("b", state))

    def _on_transitions_button_clicked(self, widget):
        """
            Show popover
            @param widget as Gtk.Button
        """
        self.__popover_transitions.popup()
        # https://gitlab.gnome.org/GNOME/pango/issues/309
        self.__scale_transition_duration.set_draw_value(True)

    def _on_network_button_clicked(self, widget):
        """
            Show popover
            @param widget as Gtk.Button
        """
        self.__popover_network.popup()

    def _on_switch_transitions_state_set(self, widget, state):
        """
            Update smooth transitions setting
            @param widget as Gtk.Button
            @param state as bool
        """
        widget.set_sensitive(state)
        App().settings.set_value("smooth-transitions",
                                 GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_switch_mix_party_state_set(self, widget, state):
        """
            Update party mix setting
            @param widget as Gtk.Range
        """
        App().settings.set_value("party-mix", GLib.Variant("b", state))
        App().player.update_crossfading()

    def _on_scale_transition_duration_value_changed(self, widget):
        """
            Update mix duration setting
            @param widget as Gtk.Range
        """
        value = widget.get_value()
        App().settings.set_value("transition-duration",
                                 GLib.Variant("i", value))

    def _on_switch_artwork_tags_state_set(self, widget, state):
        """
            Update artwork in tags setting
            @param widget as Gtk.Switch
            @param state as bool
        """
        App().settings.set_value("save-to-tags", GLib.Variant("b", state))

#######################
# PRIVATE             #
#######################
    def __check_for_kid3(self, switch):
        """
            Update grid/switch based on result
            @param switch as Gtk.Switch
        """
        if not App().art.kid3_available:
            box = switch.get_parent()
            switch.destroy()
            label = Gtk.Label.new(_("You need to install kid3-cli"))
            label.get_style_context().add_class("dim-label")
            label.set_property("halign", Gtk.Align.END)
            label.show()
            box.pack_end(label, False, False, 0)
        else:
            switch.set_state(App().settings.get_value("save-to-tags"))
