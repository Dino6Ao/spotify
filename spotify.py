import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import defaultdict
import requests

# ==========================
# SPOTIFY APP CREDENTIALS
# ==========================
CLIENT_ID = "xxxxx"                                     # rewrite to your own Client ID
CLIENT_SECRET = "xxxxx"                                 # rewrite to your own Client Secret
REDIRECT_URI = "http://127.0.0.1:8000/callback"         # rewrite to your own Redirect URI

# ==========================
# PLAYLIST SETTINGS
# ==========================
SOURCE_PLAYLIST_ID = "abcde"                          # rewrite with the playlist ID you want to sort
NEW_PLAYLIST_NAME = "abcde_NEW"                       # rewrite to how the new playlist should be named

SCOPES = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-private "
    "playlist-modify-public"
)

# ==========================
# AUTH
# ==========================

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        open_browser=True,
        cache_path=".spotify_cache"
    )
)

user_id = sp.current_user()["id"]

# ==========================
# LOAD PLAYLIST TRACKS
# ==========================

def load_all_tracks(playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id, limit=50)
    tracks.extend(results["items"])

    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])

    clean = []
    for item in tracks:
        t = item.get("item")
        if t and t.get("id"):
            clean.append(t)
    return clean

# ==========================
# SORT BY RELEASE DATE OR POPULARITY
# ==========================

def sort_by_release_date(tracks):
    def get_date(t):
        return t.get("album", {}).get("release_date", "0000")
    return sorted(tracks, key=lambda t: get_date(t))
    
def sort_by_popularity(tracks):
    return sorted(tracks, key=lambda t: t.get("popularity", 0))


# ==========================
# PROPORTIONAL ARTIST SEPARATION
# ==========================

def artist_separation_final(tracks):
    from collections import defaultdict

    # 1. Group by artist (tracks already sorted)
    groups = defaultdict(list)
    for t in tracks:
        artist = t["artists"][0]["name"]
        groups[artist].append(t)

    total = len(tracks)

    # 2. Sort artists by track count (descending)
    artists = sorted(groups.keys(), key=lambda a: len(groups[a]), reverse=True)

    # 3. Prepare empty playlist
    result = [None] * total

    # 4. Place artists one-by-one
    for artist in artists:
        artist_tracks = groups[artist]
        c = len(artist_tracks)

        # 4a. Get remaining empty positions
        empty_positions = [i for i, v in enumerate(result) if v is None]
        m = len(empty_positions)

        # 4b. Compute spacing across remaining empty slots
        step = m / c

        # 4c. Ideal positions inside empty_positions
        ideal_positions = [int(round(i * step)) for i in range(c)]

        # 4d. Place each track at nearest empty slot to ideal position
        for i, track in enumerate(artist_tracks):
            ideal_index = ideal_positions[i]

            # Clamp
            if ideal_index < 0:
                ideal_index = 0
            if ideal_index >= m:
                ideal_index = m - 1

            # Find nearest free empty slot
            offset = 0
            while True:
                for candidate in (ideal_index - offset, ideal_index + offset):
                    if 0 <= candidate < m:
                        real_pos = empty_positions[candidate]
                        if result[real_pos] is None:
                            result[real_pos] = track
                            break
                else:
                    offset += 1
                    continue
                break

    return result


def randomize_tracks(tracks, seed=None, max_attempts=50):
    def get_date(t):
        return t.get("album", {}).get("release_date", "0000")

    if seed is not None:
        random.seed(seed)

    # 1) Global shuffle
    shuffled = tracks[:] 
    random.shuffle(shuffled)

    # 2) Map artist -> positions in shuffled list
    artist_positions = defaultdict(list)
    for idx, t in enumerate(shuffled):
        artist = t["artists"][0]["name"]
        artist_positions[artist].append(idx)

    # 3) Helper to check the order
    def is_monotonic(dates):
        if len(dates) < 3:
            return True
    
        # Check monotonic ascending
        ascending = all(dates[i] <= dates[i+1] for i in range(len(dates)-1))
    
        # Check monotonic descending
        descending = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
    
        # Check triple repetition
        for i in range(len(dates) - 2):
            if dates[i] == dates[i+1] == dates[i+2]:
                return True  # reject this sequence
    
        # Return True if monotonic OR triple repetition
        return ascending or descending

    # 4) For each artist with multiple tracks, ensure their tracks are not in ascending order
    for artist, positions in artist_positions.items():
        if len(positions) < 3:
            continue

        current_tracks = [shuffled[i] for i in positions]
        dates = [get_date(t) for t in current_tracks]
            
        if not is_monotonic(dates):
            continue

        # Try random permutations of the artist's tracks among the same positions
        attempts = 0
        success = False
        while attempts < max_attempts and not success:
            attempts += 1
            perm = current_tracks[:]
            random.shuffle(perm)
            perm_dates = [get_date(t) for t in perm]
            if not is_monotonic(perm_dates):
                for pos, new_track in zip(positions, perm):
                    shuffled[pos] = new_track
                success = True

        # Fallback: perform random swaps between these positions and other random positions
        if not success:
            other_indices = [i for i in range(len(shuffled)) if i not in positions]
            if other_indices:
                for pos in positions:
                    swap_with = random.choice(other_indices)
                    shuffled[pos], shuffled[swap_with] = shuffled[swap_with], shuffled[pos]
                    other_indices.remove(swap_with)
                    if other_indices == []:
                        break

    return shuffled


# ==========================
# MAIN LOGIC
# ==========================

print("Loading playlist...")
tracks = load_all_tracks(SOURCE_PLAYLIST_ID)

print(f"Loaded {len(tracks)} tracks. Sorting...")
#sorted_by_date = sort_by_release_date(tracks)             # uncomment
#sorted_by_date = sort_by_popularity(tracks)               # uncomment
sorted_by_date = randomize_tracks(tracks)                  # uncomment


print("Applying proportional artist separation...")
final_sorted = artist_separation_final(sorted_by_date)

track_ids = [t["id"] for t in final_sorted]

#####
token = sp.auth_manager.get_access_token(as_dict=False)

url = "https://api.spotify.com/v1/me/playlists"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

data = {
    "name": NEW_PLAYLIST_NAME,
    "description": "artist separation",
    "public": False
}
print("Creating new playlist...")

response = requests.post(url, headers=headers, json=data)
response.raise_for_status()

new_playlist = response.json()
print(new_playlist["id"])
#####

new_id = new_playlist["id"]

print("Adding tracks...")
for i in range(0, len(track_ids), 100):
    sp.playlist_add_items(new_id, track_ids[i:i+100])

print("Done!")
print("New playlist ID:", new_id)
