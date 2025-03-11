from os import walk
from sys import platform
from pathlib import Path
from random import choice
from subprocess import run as sub_run
from re import match

from alive_progress import alive_bar
from typer import Argument, run
from typing_extensions import Annotated

if platform == "win32":
    from os import startfile

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".ts", ".flv")


def check_dir(path: Path) -> bool:
    """
    Check if directory contains video files, only in the top level.

    :param path: Path to directory
    :type path: Path
    :return: True if directory contains video files
    :rtype: bool
    """
    # check if directory contains video files
    for item in path.iterdir():
        if item.suffix.lower() in VIDEO_EXTENSIONS:
            return True
    return False


def get_random_dir(path: Path) -> Path | None:
    """
    Get a random directory from the given path.

    :param path: Path to directory
    :type path: Path
    :return: Random directory
    :rtype: Path
    """
    final: list[Path] = []
    # count total directories, recursively
    count = sum(len(dirs) for _, dirs, _ in walk(path))
    # recursively search for directories with video files
    with alive_bar(count, title="Searching for video files") as bar:
        for root, dirs, _ in walk(path):
            for d in dirs:
                d = Path(root) / d
                bar()
                if check_dir(d):
                    final.append(d)
    # filter out directories named as metadata, trickplay
    final = [d for d in final if not any(part in d.parts for part in ["metadata", "trickplay"])]
    # remove specials directory if "Season *" exists
    return choice(final) if final else None


def pick_earliest_season(path: Path) -> Path | None:
    """
    Pick the earliest season from the given path.

    :param path: Path to directory
    :type path: Path
    :return: Earliest season directory
    :rtype: Path
    """
    if not path:
        return None
    if ["Season", "Specials"] in path.parts:
        path_ = path.parent
        # find the earliest season directory
        for item in path_.iterdir():
            if "Season" in item.name:
                return item
    return path


def pick_first_video(path: Path | None) -> Path | None:
    """
    Pick the first episode from the given path.

    :param path: Path to directory
    :type path: Path
    :return: First video file path
    :rtype: Path
    """
    if not path:
        return None
    # assuming the format  is S**E01 for shows and either first video in movies
    for item in path.iterdir():
        if match(r"S\d{2}E01", item.stem):
            return item
        if item.suffix.lower() in VIDEO_EXTENSIONS:
            return item
    return None


def main(path: Annotated[Path, Argument(help="Path to directory")]):
    """
    Get a random directory from the given path.

    :param path: Path to directory
    :type path: Path
    """
    path = Path(path)
    if path.is_dir():
        random_dir = get_random_dir(path)
        while random_dir:
            season = pick_earliest_season(random_dir)
            video = pick_first_video(season)
            if video:
                break
            random_dir = get_random_dir(path)
        if video:
            print(f"\n\n{video}")
            ask = input("Open the video? [Y/n/r] (Default: Y): ")
            if ask.lower() == "n":
                exit(0)
            elif ask.lower() == "r":
                main(path)
            else:
                if platform == "linux":
                    sub_run(["xdg-open", str(video)])
                elif platform == "win32":
                    startfile(str(video))
                elif platform == "darwin":
                    sub_run(["open", str(video)])
        else:
            print("No video files found")
            exit(1)
    else:
        print("Invalid path")
        exit(1)
    exit(0)


if __name__ == "__main__":
    run(main)
