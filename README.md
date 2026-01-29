Python script for Spotify playlist sorting which was created with the help of AI.

First, specify your own credentials and the playlist you want to sort at the top of the script (commented section) and then run it.

## How it works:  
This will shuffle your existing playlist and creates a new one with the maximum artist separation so the songs from the same artist will be played as far apart from each other as possible. Example:

Playlist contains 1 000 songs,  
Artist A has 50 songs in it  
Artist B has 40 songs in it  
Artist C has 20 songs in it  
Artist D has 5 songs in it  
etc.  

Total number of all songs gets divided by number of songs from one artist and placed roughly equaly between each other, so song from artist A will be in the playlist every ~20th position (1 000 / 50 = 20), song from Artist D will be there every ~200th position (1 000 / 5 = 200) etc. This way, the artist separation in the playlist is maximized.

Songs from one artist are sorted by popularity first (from least to most) by default, but you can also sort them by release date (from oldest to newest), just uncomment the desired line in the script

*#sorted_by_date = sort_by_release_date(tracks)                # uncomment if you want sorting by release date first  
sorted_by_date = sort_by_popularity(tracks)                   # uncomment if you want sorting by popularity first*
