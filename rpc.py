from pypresence import Presence
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from cryptography.fernet import Fernet
import json
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TRCK

credentials_json_path = 'credentials.json'
encrypted_json_path = 'encrypted_credentials.json'
key_path = 'encryption.key'
songs_folder = 'songs'

if not os.path.exists(key_path):
    key = Fernet.generate_key()
    with open(key_path, 'wb') as key_file:
        key_file.write(key)
else:
    with open(key_path, 'rb') as key_file:
        key = key_file.read()

cipher_suite = Fernet(key)

def encrypt_credentials(json_path):
    with open(json_path, 'r') as file:
        credentials = json.load(file)

    encrypted_credentials = {
        'DISCORD_CLIENT_ID': cipher_suite.encrypt(credentials['DISCORD_CLIENT_ID'].encode()).decode(),
        'SPOTIFY_CLIENT_ID': cipher_suite.encrypt(credentials['SPOTIFY_CLIENT_ID'].encode()).decode(),
        'SPOTIFY_CLIENT_SECRET': cipher_suite.encrypt(credentials['SPOTIFY_CLIENT_SECRET'].encode()).decode(),
        'SPOTIFY_REDIRECT_URI': credentials['SPOTIFY_REDIRECT_URI']
    }

    with open(encrypted_json_path, 'w') as file:
        json.dump(encrypted_credentials, file)

if not os.path.exists(encrypted_json_path):
    encrypt_credentials(credentials_json_path)

with open(encrypted_json_path, 'r') as file:
    encrypted_credentials = json.load(file)

credentials = {
    'DISCORD_CLIENT_ID': cipher_suite.decrypt(encrypted_credentials['DISCORD_CLIENT_ID'].encode()).decode(),
    'SPOTIFY_CLIENT_ID': cipher_suite.decrypt(encrypted_credentials['SPOTIFY_CLIENT_ID'].encode()).decode(),
    'SPOTIFY_CLIENT_SECRET': cipher_suite.decrypt(encrypted_credentials['SPOTIFY_CLIENT_SECRET'].encode()).decode(),
    'SPOTIFY_REDIRECT_URI': encrypted_credentials['SPOTIFY_REDIRECT_URI']
}

RPC = Presence(credentials['DISCORD_CLIENT_ID'])
RPC.connect()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=credentials['SPOTIFY_CLIENT_ID'],
    client_secret=credentials['SPOTIFY_CLIENT_SECRET'],
    redirect_uri=credentials['SPOTIFY_REDIRECT_URI'],
    scope="user-read-playback-state"
))

def get_current_spotify_song(spotify_client):
    current_playback = spotify_client.current_playback()
    if current_playback and current_playback['is_playing']:
        track = current_playback['item']
        song_name = track['name']
        artist_name = track['artists'][0]['name']
        album_name = track['album']['name']
        progress_ms = current_playback['progress_ms']
        duration_ms = track['duration_ms']

        end_timestamp = int(time.time()) + (duration_ms - progress_ms) // 1000

        return {
            'song_name': song_name,
            'artist_name': artist_name,
            'album_name': album_name,
            'end_timestamp': end_timestamp
        }
    return None

def get_local_track_number(song_name):
    for file in os.listdir(songs_folder):
        if song_name.lower() in file.lower() and file.lower().endswith('.mp3'):
            try:
                audio = MP3(os.path.join(songs_folder, file), ID3=ID3)
                if 'TRCK' in audio:
                    track_data = audio['TRCK']
                    track_number = int(track_data.text[0].split('/')[0])
                    return track_number
            except Exception as e:
                print(f"Error reading metadata from {file}: {e}")
    return None

while True:
    song_details = get_current_spotify_song(sp)
    if song_details:
        track_number = get_local_track_number(song_details['song_name'])
        if track_number is not None:
            try:
                RPC.update(
                    state=f"by {song_details['artist_name']}",
                    details=song_details['song_name'],
                    large_image=str(track_number), 
                    small_image='spotify',
                    large_text=song_details['album_name'],
                    end=song_details['end_timestamp']
                )
            except Exception as e:
                print(f"Failed to update Discord presence: {e}")
        else:
            RPC.clear()
    else:
        RPC.clear()

    time.sleep(15)
