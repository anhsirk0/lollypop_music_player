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

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstAudio", "1.0")
gi.require_version("GstPbutils", "1.0")
gi.require_version("TotemPlParser", "1.0")
from gi.repository import Gtk, Gio, GLib, Gdk, Gst
Gst.init(None)

from threading import current_thread
from pickle import dump
from signal import signal, SIGINT, SIGTERM


try:
    from lollypop.lastfm import LastFM
except Exception as e:
    print(e)
    print("$ sudo pip3 install pylast")
    LastFM = None

from lollypop.utils import set_proxy_from_gnome
from lollypop.application_actions import ApplicationActions
from lollypop.utils import is_audio, is_pls
from lollypop.define import Type, LOLLYPOP_DATA_PATH, ScanType
from lollypop.window import Window
from lollypop.database import Database
from lollypop.player import Player
from lollypop.inhibitor import Inhibitor
from lollypop.art import Art
from lollypop.logger import Logger
from lollypop.helper_spotify import SpotifyHelper
from lollypop.sqlcursor import SqlCursor
from lollypop.settings import Settings
from lollypop.database_albums import AlbumsDatabase
from lollypop.database_artists import ArtistsDatabase
from lollypop.database_genres import GenresDatabase
from lollypop.database_tracks import TracksDatabase
from lollypop.notification import NotificationManager
from lollypop.playlists import Playlists
from lollypop.objects import Album, Track
from lollypop.helper_task import TaskHelper
from lollypop.helper_art import ArtHelper
from lollypop.collectionscanner import CollectionScanner


class Application(Gtk.Application, ApplicationActions):
    """
        Lollypop application:
            - Handle appmenu
            - Handle command line
            - Create main window
    """

    def __init__(self, version):
        """
            Create application
            @param version as str
        """
        Gtk.Application.__init__(
            self,
            application_id="org.gnome.Lollypop",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.__version = version
        self.set_property("register-session", True)
        signal(SIGINT, lambda a, b: self.quit())
        signal(SIGTERM, lambda a, b: self.quit())
        # Set main thread name
        # We force it to current python 3.6 name, to be sure in case of
        # change in python
        current_thread().setName("MainThread")
        set_proxy_from_gnome()
        GLib.setenv("PULSE_PROP_media.role", "music", True)
        GLib.setenv("PULSE_PROP_application.icon_name",
                    "org.gnome.Lollypop", True)
        # Fix proxy for python
        proxy = GLib.environ_getenv(GLib.get_environ(), "all_proxy")
        if proxy is not None and proxy.startswith("socks://"):
            proxy = proxy.replace("socks://", "socks4://")
            from os import environ
            environ["all_proxy"] = proxy
            environ["ALL_PROXY"] = proxy
        # Ideally, we will be able to delete this once Flatpak has a solution
        # for SSL certificate management inside of applications.
        if GLib.file_test("/app", GLib.FileTest.EXISTS):
            paths = ["/etc/ssl/certs/ca-certificates.crt",
                     "/etc/pki/tls/cert.pem",
                     "/etc/ssl/cert.pem"]
            for path in paths:
                if GLib.file_test(path, GLib.FileTest.EXISTS):
                    GLib.setenv("SSL_CERT_FILE", path, True)
                    break
        self.cursors = {}
        self.notify = None
        self.scrobblers = []
        self.debug = False
        self.shown_sidebar_tooltip = False
        self.__window = None
        self.__fs_window = None
        self.__scanner_timeout_id = None
        self.__scanner_uris = []
        GLib.set_application_name("Lollypop")
        GLib.set_prgname("lollypop")
        self.add_main_option("play-ids", b"a", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Play ids", None)
        self.add_main_option("debug", b"d", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Debug Lollypop", None)
        self.add_main_option("set-rating", b"r", GLib.OptionFlags.NONE,
                             GLib.OptionArg.STRING, "Rate the current track",
                             None)
        self.add_main_option("play-pause", b"t", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Toggle playback",
                             None)
        self.add_main_option("stop", b"s", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Stop playback",
                             None)
        self.add_main_option("next", b"n", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Go to next track",
                             None)
        self.add_main_option("prev", b"p", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Go to prev track",
                             None)
        ## my edits 
        self.add_main_option("set-next", b"m", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Set next track by track id",
                             None)
        ## my edits ends
        
        self.add_main_option("emulate-phone", b"e", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE,
                             "Emulate a Librem phone",
                             None)
        self.add_main_option("version", b"v", GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE,
                             "Lollypop version",
                             None)
        self.connect("command-line", self.__on_command_line)
        self.connect("handle-local-options", self.__on_handle_local_options)
        self.connect("activate", self.__on_activate)
        self.connect("shutdown", lambda a: self.__save_state())
        self.register(None)
        if self.get_is_remote():
            Gdk.notify_startup_complete()

    def init(self):
        """
            Init main application
        """
        self.settings = Settings.new()
        # Mount enclosing volume as soon as possible
        uris = self.settings.get_music_uris()
        try:
            for uri in uris:
                if uri.startswith("file:/"):
                    continue
                f = Gio.File.new_for_uri(uri)
                f.mount_enclosing_volume(Gio.MountMountFlags.NONE,
                                         None,
                                         None,
                                         None)
        except Exception as e:
            Logger.error("Application::init(): %s" % e)

        cssProviderFile = Gio.File.new_for_uri(
            "resource:///org/gnome/Lollypop/application.css")
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.db = Database()
        self.playlists = Playlists()
        self.albums = AlbumsDatabase()
        self.artists = ArtistsDatabase()
        self.genres = GenresDatabase()
        self.tracks = TracksDatabase()
        self.player = Player()
        self.inhibitor = Inhibitor()
        self.scanner = CollectionScanner()
        self.art = Art()
        self.notify = NotificationManager()
        self.art.update_art_size()
        self.task_helper = TaskHelper()
        self.art_helper = ArtHelper()
        self.spotify = SpotifyHelper()
        if not self.settings.get_value("disable-mpris"):
            from lollypop.mpris import MPRIS
            MPRIS(self)

        settings = Gtk.Settings.get_default()
        self.__gtk_dark = settings.get_property(
            "gtk-application-prefer-dark-theme")
        if not self.__gtk_dark:
            dark = self.settings.get_value("dark-ui")
            settings.set_property("gtk-application-prefer-dark-theme", dark)
        ApplicationActions.__init__(self)
        startup_one_ids = self.settings.get_value("startup-one-ids")
        startup_two_ids = self.settings.get_value("startup-two-ids")
        if startup_one_ids:
            self.settings.set_value("state-one-ids", startup_one_ids)
            self.settings.set_value("state-three-ids", GLib.Variant("ai", []))
        if startup_two_ids:
            self.settings.set_value("state-two-ids", startup_two_ids)

    def do_startup(self):
        """
            Init application
        """
        Gtk.Application.do_startup(self)

        if self.__window is None:
            self.init()
            self.__window = Window()
            self.__window.connect("delete-event", self.__hide_on_delete)
            self.__window.show()
            self.player.restore_state()

    def quit(self, vacuum=False):
        """
            Quit Lollypop
            @param vacuum as bool
        """
        if self.settings.get_value("save-state"):
            # Special case, we can't handle this earlier
            if self.window.is_adaptive:
                visible = self.window.container.stack.get_visible_child()
                if visible == self.window.container.list_one:
                    self.settings.set_value("state-one-ids",
                                            GLib.Variant("ai", []))
                    self.settings.set_value("state-two-ids",
                                            GLib.Variant("ai", []))
                elif visible == self.window.container.list_two:
                    selected_ids = self.window.container.list_one.selected_ids
                    self.settings.set_value("state-one-ids",
                                            GLib.Variant("ai", selected_ids))
                    self.settings.set_value("state-two-ids",
                                            GLib.Variant("ai", []))
        else:
            self.settings.set_value("state-one-ids", GLib.Variant("ai", []))
            self.settings.set_value("state-two-ids", GLib.Variant("ai", []))
        # Then vacuum db
        if vacuum:
            self.__vacuum()
            self.art.clean_web()
        self.__window.hide()
        for scrobbler in self.scrobblers:
            scrobbler.save()
        Gio.Application.quit(self)

    def set_mini(self):
        """
            Set mini player on/off
        """
        if self.__window is not None:
            self.__window.set_mini()

    def load_listenbrainz(self):
        """
            Load listenbrainz support if needed
        """
        if self.settings.get_value("listenbrainz-user-token").get_string():
            from lollypop.listenbrainz import ListenBrainz
            for scrobbler in self.scrobblers:
                if isinstance(scrobbler, ListenBrainz):
                    return
            listenbrainz = ListenBrainz()
            self.scrobblers.append(listenbrainz)
            self.settings.bind("listenbrainz-user-token", listenbrainz,
                               "user_token", 0)

    def fullscreen(self):
        """
            Go fullscreen
        """
        def on_destroy(window):
            self.__fs_window = None
            self.__window.show()

        if self.__fs_window is None:
            self.__window.hide()
            from lollypop.fullscreen import FullScreen
            self.__fs_window = FullScreen(self)
            self.__fs_window.show()
            self.__fs_window.connect("destroy", on_destroy)

    @property
    def devices(self):
        """
            Get available devices
            Merge connected and known
            @return [str]
        """
        devices = self.__window.toolbar.end.devices_popover.devices
        devices += list(self.settings.get_value("devices"))
        result = []
        # Do not use set() + filter() because we want to keep order
        for device in devices:
            if device not in result and device != "":
                result.append(device)
        return result

    @property
    def is_fullscreen(self):
        """
            Return True if application is fullscreen
        """
        return self.__fs_window is not None

    @property
    def lastfm(self):
        """
            Get lastfm provider from scrobbler
            @return LastFM/None
        """
        if LastFM is None:
            return None
        from pylast import LastFMNetwork
        for scrobbler in self.scrobblers:
            if isinstance(scrobbler, LastFMNetwork):
                return scrobbler
        return None

    @property
    def main_window(self):
        """
            Get main window
        """
        return self.__window

    @property
    def window(self):
        """
            Get current application window
            @return Gtk.Window
        """
        if self.__fs_window is not None:
            return self.__fs_window
        else:
            return self.__window

    @property
    def gtk_application_prefer_dark_theme(self):
        """
            Return default gtk value
            @return bool
        """
        return self.__gtk_dark

#######################
# PRIVATE             #
#######################
    def __save_state(self):
        """
            Save window position and view
        """
        if not self.settings.get_value("save-state"):
            return

        if self.player.current_track.id is None or\
                self.player.current_track.mtime == 0:
            track_id = None
        elif self.player.current_track.id == Type.RADIOS:
            from lollypop.radios import Radios
            radios = Radios()
            track_id = radios.get_id(
                self.player.current_track.radio_name)
        else:
            track_id = self.player.current_track.id
            # Save albums context
            try:
                with open(LOLLYPOP_DATA_PATH + "/Albums.bin", "wb") as f:
                    dump(list(self.player.albums), f)
            except Exception as e:
                Logger.error("Application::__save_state(): %s" % e)
        dump(track_id, open(LOLLYPOP_DATA_PATH + "/track_id.bin", "wb"))
        dump([self.player.is_playing, self.player.is_party],
             open(LOLLYPOP_DATA_PATH + "/player.bin", "wb"))
        dump(self.player.queue,
             open(LOLLYPOP_DATA_PATH + "/queue.bin", "wb"))
        # Save current playlist
        if self.player.current_track.id == Type.RADIOS:
            playlist_ids = [Type.RADIOS]
        elif not self.player.playlist_ids:
            playlist_ids = []
        else:
            playlist_ids = self.player.playlist_ids
        dump(playlist_ids,
             open(LOLLYPOP_DATA_PATH + "/playlist_ids.bin", "wb"))
        if self.player.current_track.id is not None:
            position = self.player.position
        else:
            position = 0
        dump(position, open(LOLLYPOP_DATA_PATH + "/position.bin", "wb"))
        self.player.stop_all()
        self.__window.container.stop_all()

    def __vacuum(self):
        """
            VACUUM DB
        """
        try:
            if self.scanner.is_locked():
                self.scanner.stop()
                GLib.idle_add(self.__vacuum)
                return
            self.tracks.del_non_persistent()
            self.tracks.clean()
            self.albums.clean()
            self.artists.clean()
            self.genres.clean()

            from lollypop.radios import Radios
            with SqlCursor(self.db) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
            with SqlCursor(self.playlists) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
            with SqlCursor(Radios()) as sql:
                sql.isolation_level = None
                sql.execute("VACUUM")
                sql.isolation_level = ""
        except Exception as e:
            Logger.error("Application::__vacuum(): %s" % e)

    def __on_handle_local_options(self, app, options):
        """
            Handle local options
            @param app as Gio.Application
            @param options as GLib.VariantDict
        """
        if options.contains("version"):
            print("Lollypop %s" % self.__version)
            exit(0)
        return -1

    def __on_command_line(self, app, app_cmd_line):
        """
            Handle command line
            @param app as Gio.Application
            @param options as Gio.ApplicationCommandLine
        """
        try:
            args = app_cmd_line.get_arguments()
            options = app_cmd_line.get_options_dict()
            if options.contains("debug"):
                self.debug = True
            # We are forced to enable scrobblers here if we want full debug
            if not self.scrobblers:
                if LastFM is not None:
                    self.scrobblers = [LastFM("lastfm"),
                                       LastFM("librefm")]
                self.load_listenbrainz()
            if options.contains("set-rating"):
                value = options.lookup_value("set-rating").get_string()
                try:
                    value = min(max(0, int(value)), 5)
                    if self.player.current_track.id is not None:
                        self.player.current_track.set_rate(value)
                except Exception as e:
                    Logger.error("Application::__on_command_line(): %s", e)
                    pass
            elif options.contains("play-pause"):
                self.player.play_pause()
            elif options.contains("stop"):
                self.player.stop()
            ## my edits
            elif options.contains("set-next"):
                try:
                    track_id = int(args[1])
                    try:
                        self.player.append_to_queue(track_id, notify=True)
                    except:
                        pass
                except:
                    pass
                    
            ## my edits ends
            
            elif options.contains("play-ids"):
                try:
                    value = options.lookup_value("play-ids").get_string()
                    ids = value.split(";")
                    tracks = []
                    for id in ids:
                        if id[0:2] == "a:":
                            album = Album(int(id[2:]))
                            tracks += album.tracks
                        else:
                            tracks.append(Track(int(id[2:])))
                    self.player.load(tracks[0])
                    self.player.populate_playlist_by_tracks(tracks,
                                                            [Type.SEARCH])
                except Exception as e:
                    Logger.error("Application::__on_command_line(): %s", e)
                    pass
            elif options.contains("next"):
                self.player.next()
            elif options.contains("prev"):
                self.player.prev()
            elif options.contains("emulate-phone"):
                self.__window.toolbar.end.devices_popover.add_fake_phone()
            elif len(args) > 1:
                uris = []
                pls = []
                for uri in args[1:]:
                    try:
                        uri = GLib.filename_to_uri(uri)
                    except:
                        pass
                    f = Gio.File.new_for_uri(uri)
                    if not f.query_exists():
                        uri = GLib.filename_to_uri(
                            "%s/%s" % (GLib.get_current_dir(), uri))
                        f = Gio.File.new_for_uri(uri)
                    if is_audio(f):
                        uris.append(uri)
                    elif is_pls(f):
                        pls.append(uri)
                    else:
                        info = f.query_info(Gio.FILE_ATTRIBUTE_STANDARD_TYPE,
                                            Gio.FileQueryInfoFlags.NONE,
                                            None)
                        if info.get_file_type() == Gio.FileType.DIRECTORY:
                            uris.append(uri)
                if pls:
                    from gi.repository import TotemPlParser
                    parser = TotemPlParser.Parser.new()
                    parser.connect("entry-parsed",
                                   self.__on_entry_parsed, uris)
                    parser.parse_async(uri, True, None,
                                       self.__on_parse_finished, uris)
                else:
                    self.__on_parse_finished(None, None, uris)
            elif self.__window is not None:
                if not self.__window.is_visible():
                    self.__window.present()
                    self.player.emit("status-changed")
                    self.player.emit("current-changed")
            Gdk.notify_startup_complete()
        except Exception as e:
            Logger.error("Application::__on_command_line(): %s", e)
        return 0

    def __on_parse_finished(self, parser, result, uris):
        """
            Play stream
            @param parser as TotemPlParser.Parser
            @param result as Gio.AsyncResult
            @param uris as [str]
        """
        def scanner_update():
            self.__scanner_timeout_id = None
            self.player.play_uris(self.__scanner_uris)
            self.scanner.update(ScanType.EPHEMERAL, self.__scanner_uris)
            self.__scanner_uris = []

        if self.__scanner_timeout_id is not None:
            GLib.source_remove(self.__scanner_timeout_id)
        self.__scanner_uris += uris
        self.__scanner_timeout_id = GLib.timeout_add(500,
                                                     scanner_update)

    def __on_entry_parsed(self, parser, uri, metadata, uris):
        """
            Add playlist entry to external files
            @param parser as TotemPlParser.Parser
            @param uri as str
            @param metadata as GLib.HastTable
            @param uris as str
        """
        uris.append(uri)

    def __hide_on_delete(self, widget, event):
        """
            Hide window
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        # Quit if background mode is on but player is off
        if not self.settings.get_value("background-mode") or\
                not self.player.is_playing:
            GLib.idle_add(self.quit, True)
        return widget.hide_on_delete()

    def __on_activate(self, application):
        """
            Call default handler
            @param application as Gio.Application
        """
        self.__window.present()
