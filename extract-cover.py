import os
import io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TRCK
from PIL import Image

songs_dir = os.path.join(os.getcwd(), 'songs')
cover_art_dir = os.path.join(os.getcwd(), 'cover_art')

if not os.path.exists(cover_art_dir):
    os.makedirs(cover_art_dir)

def extract_and_resize_cover_art(audio_path, cover_art_dir, track_number):
    file_name, file_extension = os.path.splitext(os.path.basename(audio_path))
    try:
        if file_extension.lower() == '.mp3':
            audio = MP3(audio_path, ID3=ID3)
            audio['TRCK'] = TRCK(encoding=3, text=str(track_number))
            audio.save()

            if 'APIC:' in audio.tags:
                artwork = audio.tags['APIC:'].data
                with io.BytesIO(artwork) as art_stream:
                    image = Image.open(art_stream)

                    if image.size < (512, 512):
                        image = image.resize((512, 512), Image.LANCZOS)
                    elif image.size > (800, 800):
                        image = image.resize((800, 800), Image.LANCZOS)

                    cover_art_path = os.path.join(cover_art_dir, f"{track_number}.png")
                    image.save(cover_art_path, format='PNG')

    except Exception as e:
        print(f"An error occurred while processing the audio file '{audio_path}': {e}")

track_number = 1
for file in sorted(os.listdir(songs_dir)):
    if file.lower().endswith('.mp3'):
        extract_and_resize_cover_art(os.path.join(songs_dir, file), cover_art_dir, track_number)
        track_number += 1

print(f"Cover art extraction and resizing complete. Check the '{cover_art_dir}' directory.")
