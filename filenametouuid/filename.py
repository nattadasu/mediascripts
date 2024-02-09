import os
import shutil
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import uuid
import re

def get_year_from_date(date: str | None) -> str:
    if date is None or date == '':
        return '0000'
    # return as YYYY no matter what
    return re.search(r'\d{4}', date).group()

def process_music_files(root_dir: str) -> None:
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for filename in files:
            file_path = os.path.join(root, filename)

            # Get file extension
            ext = filename.split('.')[-1].lower()
            daykeyname = 'date'

            # Get metadata based on file extension
            if ext == 'mp3':
                audio = EasyID3(file_path)
                # get musicbrainz track id keyname
                mbid = audio.get('musicbrainz_trackid', [None])[0]
            elif ext == 'flac':
                audio = FLAC(file_path)
                mbid = audio.get('musicbrainz_trackid', [None])[0]
            elif ext == 'm4a':
                audio = MP4(file_path)
                mbid = audio.get('----:com.apple.iTunes:MusicBrainz Track Id', [None])[0]
                # clear binary string artifacts
                if mbid:
                    mbid = mbid.decode('utf-8')
                daykeyname = '\xa9day'
            else:
                # Skip files with unsupported extensions
                continue

            # Generate new filename
            year = get_year_from_date(audio.get(daykeyname, [''])[0])
            # random 4 unique string
            randstr = uuid.uuid4().hex[:4]
            new_filename = f"mbid_{mbid}_{year}!{randstr}.{ext}" if mbid else f"genc_{uuid.uuid4()}_{year}!{randstr}.{ext}"

            # Move renamed file to root of working directory
            new_path = os.path.join(root_dir, new_filename)
            shutil.move(file_path, new_path)
            print(f"Renamed file: {file_path} -> {new_path}")

        # Remove empty folders
        for folder in dirs:
            folder_path = os.path.join(root, folder)
            if not os.listdir(folder_path):
                os.rmdir(folder_path)
                print(f"Removed empty folder: {folder_path}")

if __name__ == "__main__":
    working_directory = input("Specify path (. for current directory): ")
    if working_directory == '.':
        working_directory = os.getcwd()

    process_music_files(working_directory)
    print("Processing completed.")
