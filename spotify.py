


import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import pyperclip

SPOTIFY_CLIENT_ID = "bdb2e21d2b384b31bea7e4c622140d81"
SPOTIFY_CLIENT_SECRET = "9fca954348d84b658aeb2987a068ef69"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID,
                                                           client_secret=SPOTIFY_CLIENT_SECRET))

def get_song_names(spotify_urls):
    song_names = []
    
    for index, url in enumerate(spotify_urls):
        match = re.search(r"track/([a-zA-Z0-9]+)", url)
        if not match:
            song_names.append(f"Invalid URL: {url}")
            continue
        
        track_id = match.group(1)
        
        try:
            track = sp.track(track_id)
            song_names.append(f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}")
        except Exception as e:
            song_names.append(f"Error fetching {url}: {e}")
        
    
    return song_names

def get_links_from_clipboard():
    text = pyperclip.paste() 
    urls = text.strip().split("\n")
    return [url.strip() for url in urls if "spotify.com/track/" in url]

# **Run the script**
spotify_urls = get_links_from_clipboard()

if not spotify_urls:
    print("No valid Spotify track URLs found in clipboard.")
else:
    print(f"Found {len(spotify_urls)} Spotify links! Fetching song names...\n")
    songs = get_song_names(spotify_urls)
    for song in songs:
        print(song)
