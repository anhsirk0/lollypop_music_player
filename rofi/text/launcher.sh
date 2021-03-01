#!/bin/bash

## lollypop database
db=~/.local/share/lollypop/lollypop.db

dir="$HOME/.config/rofi/lollypop/text"
## get all songs id and name by popularity
# sql_query="select id, name from tracks order by popularity desc;"
## for artists
sql_query="select tracks.id, tracks.name, artists.name from tracks 
    join track_artists on track_artists.track_id = tracks.id 
    join artists on track_artists.artist_id = artists.id
    order by popularity desc ;"
echo $sql_query | sqlite3 $db > $dir/all_songs.txt

# remove some unwanted stuff from track names
sed -i 's/(.*)|/|/g' $dir/all_songs.txt
sed -i 's/Ft.*|/|/g' $dir/all_songs.txt
sed -i 's/(.*)//g' $dir/all_songs.txt

# for tracks names only
# awk -F "|" '{print $2}' all_songs.txt > track_names.txt

awk -F "|" '!seen[$1]++ {print $1,"|", $2," - " ,$3}' \
                $dir/all_songs.txt > $dir/all_tracks.txt
# for track and artists names
# awk -F "|" '!seen[$1]++ {print $2,"  _ " ,$3}' $dir/all_songs.txt > $dir/track_names_and_artists.txt
awk -F "|" '{print $2}' $dir/all_tracks.txt > $dir/track_names_and_artists.txt

theme="style_7"

tracks="$dir/track_names_and_artists.txt"
all_tracks="$dir/all_tracks.txt"

total_songs=$(wc -l $all_tracks | cut -d " " -f1)

# add next option
sed -i '1 s/^/ Play next\n/' $tracks

chosen=$(cat $tracks | rofi -p "  Add song to Queue ($total_songs songs)" -dmenu -i -theme $dir/$theme)

if [[ -z "$chosen" ]] ; then
    exit
else
    if [[ "$chosen" == " Play next" ]] ; then
        notify-send "Next" && lollypop -n
    else
        notify-send "Added : $chosen"
        id=$(grep "$chosen" $all_tracks | awk -F "|" 'NR==1 {print $1}')
        [[ -z "$id" ]] && exit || lollypop -m $id
    fi
fi
