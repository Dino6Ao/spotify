Python script for Spotify playlist sorting which was created with the help of AI.

First, specify your own credentials and the playlist you want to sort at the top of the script (commented section) and then run it.

## How it works:  
This will shuffle your existing playlist and creates a new one with the maximum artist separation so the songs from the same artist will be played as far apart from each other as possible. Example:

Playlist contains 1 000 songs,  
Artist A has 50 songs in it  
Artist B has 40 songs in it  
Artist C has 5 songs in it  
etc.  

Total number of all songs gets divided by number of songs from one artist and those are then placed roughly equaly between each other, so song from artist A will be in the playlist every ~20th position (1 000 / 50 = 20), song from Artist C will be there every ~200th position (1 000 / 5 = 200) etc. This way, the artist separation in the playlist is maximized.

Songs from one artist are sorted by release date (from oldest to newest).
