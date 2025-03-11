"""
Generate a list of tracks in an album to be distributed to AB and similar trackers
"""

import os
import re
from typing import TypedDict, Union

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


class Metadata(TypedDict):
    title: str
    titlesort: str
    artist: str
    duration: int


def get_metadata(file_path: str) -> Union[Metadata, None]:
    if file_path.endswith(".mp3"):
        audio = MP3(file_path, ID3=EasyID3)
        title_key = "title"
        artist_key = "artist"
    elif file_path.endswith(".flac"):
        audio = FLAC(file_path)
        title_key = "title"
        artist_key = "artist"
    elif file_path.endswith(".m4a"):
        audio = MP4(file_path)
        title_key = "\xa9nam"  # '\xa9nam' is the atom for title in M4A files
        artist_key = "\xa9ART"  # '\xa9ART' is the atom for artist in M4A files
    else:
        return None
    if audio is None:
        return None
    data: Metadata = {
        "title": audio.get(title_key, [""])[0],  # type: ignore
        "titlesort": audio.get("titlesort", [""])[0] if "titlesort" in audio else None,  # type: ignore
        "artist": audio.get(artist_key, [""])[0],  # type: ignore
        "duration": int(audio.info.length),
    }
    return data


def print_metadata(index: Union[str, int], metadata: Metadata) -> None:
    title = metadata["titlesort"] if metadata["titlesort"] else metadata["title"]
    minutes = metadata["duration"] // 60
    seconds = metadata["duration"] % 60
    # add leading zero to index if needed
    index = re.sub(r"^0+", "", str(index))
    index = str(index).zfill(2)
    print(f"{index}. {title} ({minutes}:{seconds}) ", end="")
    print(f"[{metadata['title']}] " if metadata["titlesort"] else "", end="")
    print(f"(by {metadata['artist']})")


def main():
    folder_path = input("Enter the folder path: ")

    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print("Invalid folder path. Exiting.")
        return

    files = [
        f
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]

    for index, file_name in enumerate(files, start=1):
        file_path = os.path.join(folder_path, file_name)
        metadata = get_metadata(file_path)

        if metadata:
            print_metadata(index, metadata)
        else:
            print(f"Skipping {file_name} - Unsupported format")


if __name__ == "__main__":
    main()
