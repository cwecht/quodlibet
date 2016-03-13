# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango

from quodlibet import config
from quodlibet import util
from quodlibet import browsers
from quodlibet import app

from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.x import ScrolledWindow, Action
from quodlibet.qltk import Icons
from quodlibet.qltk.window import Window, PersistentWindowMixin
from quodlibet.util.library import background_filter


class FilterMenu(object):
    _MENU = """
        <ui>
        <menubar name='Menu'>
        <menu action='Filters'>
          <menuitem action='FilterGenre' always-show-image='true'/>
          <menuitem action='FilterArtist' always-show-image='true'/>
          <menuitem action='FilterAlbum' always-show-image='true'/>
          <separator/>
          <menuitem action='RandomGenre' always-show-image='true'/>
          <menuitem action='RandomArtist' always-show-image='true'/>
          <menuitem action='RandomAlbum' always-show-image='true'/>
          <separator/>
          <menuitem action='All' always-show-image='true'/>
          <menuitem action='PlayedRecently' always-show-image='true'/>
          <menuitem action='AddedRecently' always-show-image='true'/>
          <menuitem action='TopRated' always-show-image='true'/>
        </menu>
        </menubar>
        </ui>"""

    def __init__(self, library, player, ui=None):
        self._browser = None
        self._library = library
        self._player = player

        ag = Gtk.ActionGroup.new('QuodLibetFilterActions')
        for name, icon_name, label, cb in [
                ('Filters', "", _("_Filters"), None),
                ("PlayedRecently", Icons.EDIT_FIND, _("Recently _Played"),
                 self.__filter_menu_actions),
                ("AddedRecently", Icons.EDIT_FIND, _("Recently _Added"),
                 self.__filter_menu_actions),
                ("TopRated", Icons.EDIT_FIND, _("_Top 40"),
                 self.__filter_menu_actions),
                ("All", Icons.EDIT_FIND, _("All _Songs"),
                 self.__filter_menu_actions)]:
            action = Action(name=name, icon_name=icon_name, label=label)
            if cb:
                action.connect('activate', cb)
            ag.add_action(action)

        for tag_, lab in [
            ("genre", _("Filter on _Genre")),
            ("artist", _("Filter on _Artist")),
            ("album", _("Filter on Al_bum"))]:
            act = Action(
                name="Filter%s" % util.capitalize(tag_), label=lab,
                icon_name=Icons.EDIT_SELECT_ALL)
            act.connect('activate', self.__filter_on, tag_, None, player)
            ag.add_action(act)

        for (tag_, accel, label) in [
            ("genre", "G", _("Random _Genre")),
            ("artist", "T", _("Random _Artist")),
            ("album", "M", _("Random Al_bum"))]:
            act = Action(name="Random%s" % util.capitalize(tag_),
                         label=label, icon_name=Icons.DIALOG_QUESTION)
            act.connect('activate', self.__random, tag_)
            ag.add_action_with_accel(act, "<Primary>" + accel)

        ui = ui or Gtk.UIManager()
        ui.insert_action_group(ag, -1)
        ui.add_ui_from_string(self._MENU)
        self._ui = ui

        ui.get_widget("/Menu/Filters/TopRated").set_tooltip_text(
                _("The 40 songs you've played most (more than 40 may "
                  "be chosen if there are ties)"))

        # https://git.gnome.org/browse/gtk+/commit/?id=b44df22895c79
        menu_item = ui.get_widget("/Menu/Filters")
        if isinstance(menu_item, Gtk.ImageMenuItem):
            menu_item.set_image(None)

        self._player_id = player.connect("song-started", self._on_song_started)
        self.set_song(player.song)

        self._hide_menus()

    def destroy(self):
        if self._player:
            self._player.disconnect(self._player_id)
        self._player = None
        self._browser = None
        self._library = None

    def _on_song_started(self, player, song):
        self.set_song(song)

    def __random(self, item, key):
        self._browser.filter_random(key)

    def __filter_on(self, action, header, songs, player):
        # Fall back to the playing song
        if songs is None:
            if player.song:
                songs = [player.song]
            else:
                return

        self._browser.filter_on(songs, header)

    def __filter_menu_actions(self, menuitem):
        name = menuitem.get_name()

        if name == "PlayedRecently":
            self._make_query("#(lastplayed < 7 days ago)")
        elif name == "AddedRecently":
            self._make_query("#(added < 7 days ago)")
        elif name == "TopRated":
            bg = background_filter()
            songs = (bg and filter(bg, self._library)) or self._library
            songs = [song.get("~#playcount", 0) for song in songs]
            if len(songs) == 0:
                return
            songs.sort()
            if len(songs) < 40:
                self._make_query("#(playcount > %d)" % (songs[0] - 1))
            else:
                self._make_query("#(playcount > %d)" % (songs[-40] - 1))
        elif name == "All":
            self._browser.unfilter()

    def _make_query(self, query):
        if self._browser.can_filter_text():
            self._browser.filter_text(query.encode('utf-8'))
            self._browser.activate()

    def _hide_menus(self):
        menus = {
            'genre': [
                "/Menu/Filters/FilterGenre",
                "/Menu/Filters/RandomGenre",
            ],
            'artist': [
                "/Menu/Filters/FilterArtist",
                "/Menu/Filters/RandomArtist",
            ],
            'album': [
                "/Menu/Filters/FilterAlbum",
                "/Menu/Filters/RandomAlbum",
            ],
            None: [
                "/Menu/Filters/PlayedRecently",
                "/Menu/Filters/AddedRecently",
                "/Menu/Filters/TopRated",
                "/Menu/Filters/All",
            ],
        }

        for key, widgets in menus.items():
            if self._browser:
                can_filter = self._browser.can_filter(key)
            else:
                can_filter = False
            for widget in widgets:
                self._ui.get_widget(widget).set_property('visible', can_filter)

    def set_browser(self, browser):
        self._browser = browser
        self._hide_menus()

    def set_song(self, song):
        for wid in ["FilterAlbum", "FilterArtist", "FilterGenre"]:
            self._ui.get_widget(
                '/Menu/Filters/' + wid).set_sensitive(bool(song))

        if song:
            for h in ['genre', 'artist', 'album']:
                self._ui.get_widget(
                    "/Menu/Filters/Filter%s" % h.capitalize()).set_sensitive(
                    h in song)

    def get_widget(self):
        return self._ui.get_widget("/Menu")

    def get_accel_group(self):
        return self._ui.get_accel_group()


class LibraryBrowser(Window, util.InstanceTracker, PersistentWindowMixin):

    @classmethod
    def open(cls, Kind, library, player):
        """Creates and shows a new browser instance"""

        browser = cls(Kind, library, player)
        browser.show()
        return browser

    @classmethod
    def save(cls):
        """See which browser windows are open and save their names
        so we can restore them on start.
        """

        names = []
        for browser in cls.instances():
            names.append(browser.name)
        config.set("memory", "open_browsers", "\n".join(names))

    @classmethod
    def restore(cls, library, player):
        """restore saved browser windows"""

        value = config.get("memory", "open_browsers", "")
        for name in value.split():
            kind = browsers.get(name)
            browser = cls(kind, library, player)
            browser.show_maybe()

    def __init__(self, Kind, library, player):
        super(LibraryBrowser, self).__init__(dialog=False)
        self._register_instance()
        self.name = Kind.__name__

        self.set_default_size(600, 400)
        self.enable_window_tracking("browser_" + self.name)
        self.set_title(Kind.name + " - Quod Libet")
        self.add(Gtk.VBox())

        view = SongList(library, update=True)
        view.info.connect("changed", self.__set_time)
        self.songlist = view

        sw = ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.browser = browser = Kind(library)
        if browser.can_reorder:
            view.enable_drop()
        elif browser.dropped:
            view.enable_drop(False)
        if browser.accelerators:
            self.add_accel_group(browser.accelerators)

        self.__container = browser.pack(sw)
        self.get_child().pack_start(self.__container, True, True, 0)

        main = self.get_child()
        bottom = Gtk.HBox()
        main.pack_end(bottom, False, True, 0)

        self._filter_menu = filter_menu = FilterMenu(library, player)
        filter_menu.set_browser(self.browser)
        self.add_accel_group(filter_menu.get_accel_group())
        bottom.pack_start(filter_menu.get_widget(), False, True, 0)
        filter_menu.get_widget().show()

        self.__statusbar = Gtk.Label()
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_padding(6, 3)
        self.__statusbar.set_ellipsize(Pango.EllipsizeMode.START)
        bottom.pack_end(self.__statusbar, True, True, 0)
        self.__statusbar.show()
        bottom.show()

        browser.connect('songs-selected', self.__browser_cb)
        browser.finalize(False)
        view.connect('popup-menu', self.__menu, library)
        view.connect('drag-data-received', self.__drag_data_recv)
        view.connect('row-activated', self.__enqueue, player)

        if browser.headers is not None:
            view.connect('columns-changed', self.__cols_changed, browser)
            self.__cols_changed(view, browser)
        sw.show_all()
        for c in self.get_child().get_children():
            c.show()
        self.get_child().show()

        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *args):
        self._filter_menu.destroy()

    def __browser_cb(self, browser, songs, sorted):
        if browser.background:
            bg = background_filter()
            if bg:
                songs = filter(bg, songs)
        self.songlist.set_songs(songs, sorted)

    def __enqueue(self, view, path, column, player):
        app.window.playlist.enqueue([view.get_model()[path][0]])
        if player.song is None:
            player.next()

    def __drag_data_recv(self, view, *args):
        if self.browser.can_reorder:
            songs = view.get_songs()
            self.browser.reordered(songs)
        view.clear_sort()

    def __cols_changed(self, view, browser):
        for header in view.get_columns():
            tag = header.header_name
            for t in util.tagsplit(tag):
                if t in browser.headers:
                    header.set_visible(True)
                    break
            else:
                header.set_visible(False)

    def __menu(self, view, library):
        path, col = view.get_cursor()
        header = col.header_name
        menu = view.Menu(header, self.browser, library)
        if menu is not None:
            view.popup_menu(menu, 0, Gtk.get_current_event_time())
        return True

    def __set_time(self, info, songs):
        i = len(songs)
        length = sum(song.get("~#length", 0) for song in songs)
        t = self.browser.status_text(count=i,
                                     time=util.format_time_long(length))
        self.__statusbar.set_text(t)
