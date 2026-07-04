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

    # 1. Group by artist
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

        # 4a. Remaining empty positions
        empty_positions = [i for i, v in enumerate(result) if v is None]
        m = len(empty_positions)

        # 4b. Fractional spacing targets
        # (i + 0.5) ensures centered spacing
        targets = [(i + 0.5) * m / c for i in range(c)]

        # 4c. Map each target to nearest unused empty slot index
        used = set()
        ideal_positions = []
        for t in targets:
            # find nearest free index in empty_positions
            best = min(
                (i for i in range(m) if i not in used),
                key=lambda x: abs(x - t)
            )
            used.add(best)
            ideal_positions.append(best)

        # 4d. Place tracks
        for pos, track in zip(ideal_positions, artist_tracks):
            real_pos = empty_positions[pos]
            result[real_pos] = track

    return result


def randomize_tracks(tracks, seed=None, max_attempts=50):
    from collections import defaultdict
    import random

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

    # --- BAD SEQUENCE CHECKERS ---

    # A) ascending/descending chronological order
    def is_monotonic_order(dates):
        if len(dates) < 3:
            return False
        ascending = all(dates[i] <= dates[i+1] for i in range(len(dates)-1))
        descending = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
        return ascending or descending

    # B) repetition checker (double, triple, quadruple, quintuple)
    def is_bad_repetition(dates, repetition_limit):
        if len(dates) < repetition_limit:
            return False
        for i in range(len(dates) - repetition_limit + 1):
            if all(dates[i] == dates[i + j] for j in range(repetition_limit)):
                return True
        return False

    # 4) Process each artist
    for artist, positions in artist_positions.items():
        if len(positions) < 3:
            continue

        current_tracks = [shuffled[i] for i in positions]
        dates = [get_date(t) for t in current_tracks]

        # repetition limits to try in phases
        repetition_limits = [2, 3, 4, 5]

        # check if ANY bad pattern exists
        bad_pattern_exists = (
            is_monotonic_order(dates) or
            any(is_bad_repetition(dates, r) for r in repetition_limits)
        )

        if not bad_pattern_exists:
            continue

        # fallback permutation if all attempts fail
        final_perm = current_tracks[:]
        success = False

        # --- PHASES ---
        # 1) avoid double repetition
        # 2) avoid triple repetition
        # 3) avoid quadruple repetition
        # 4) avoid quintuple repetition
        # also avoid monotonic ascending/descending in ALL phases
        for limit in repetition_limits:
            attempts = 0
            while attempts < max_attempts and not success:
                attempts += 1

                perm = current_tracks[:]
                random.shuffle(perm)
                perm_dates = [get_date(t) for t in perm]

                # must avoid BOTH monotonic order AND repetition
                if (
                    not is_monotonic_order(perm_dates) and
                    not is_bad_repetition(perm_dates, limit)
                ):
                    # success → apply permutation
                    for pos, new_track in zip(positions, perm):
                        shuffled[pos] = new_track
                    final_perm = perm
                    success = True
                    break

            if success:
                break

        # --- FALLBACK ---
        # If all max_attempts fail → keep final_perm
        if not success:
            for pos, new_track in zip(positions, final_perm):
                shuffled[pos] = new_track

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
