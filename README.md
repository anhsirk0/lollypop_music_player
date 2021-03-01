# Lollypop music player (my edit)

Official app: https://gitlab.gnome.org/World/lollypop

Lollypop is a new GNOME music playing application.

## my changes
Added an option to add song to queue from commandline through the song id
I needed this option for a rofi script i wrote to manage song on the go

P.S. this is based on an older version of Lollypop (I like two column view & its not available in newer versions)
### to get songs id 
```bash
$ echo "select id, name from tracks;" | sqlite3 ~/.local/share/lollypop/lollypop.db
```

### to add a song to queue
```bash
$ lollypop -m 411
```
or 

```bash
$ lollypop --set-next 411
```

song with id '411' will be added to queue

*the rofi script also include*
![rofi.png](https://github.com/anhsirk0/lollypop_music_player/blob/master/rofi/rofi.png)

## Depends on

- `gtk3 >= 3.20`
- `gobject-introspection`
- `appstream-glib`
- `gir1.2-gstreamer-1.0 (Debian)`
- `python3`
- `meson >= 0.40`
- `ninja`
- `totem-plparser`
- `python-cairo`
- `python-gobject`
- `python-sqlite`
- `python-pylast >= 1.0`

## Building from Git

```bash
$ git clone https://anhsirk0/lollypop_music_player
$ cd lollypop*
$ meson builddir --prefix=/usr
# sudo ninja -C builddir install
```

