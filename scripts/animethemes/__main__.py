import argparse as ap
import subprocess as sp
from dataclasses import dataclass as dcl
from os import path as op
from os import remove, walk
from pathlib import Path
from time import sleep
from typing import Annotated, Any, List, Literal, TypedDict, Union

import requests as req
from defusedxml import ElementTree as ET
from pydantic import BaseModel, Field, HttpUrl
from tqdm import tqdm


@dcl
class BytesSize:
    gibi: float  # GiB
    mebi: float  # MiB
    kibi: float  # KiB
    byte: int

    @classmethod
    def from_bytes(cls, size: int) -> "BytesSize":
        return cls(
            gibi=size / 2**30,
            mebi=size / 2**20,
            kibi=size / 2**10,
            byte=size,
        )

    def __str__(self) -> str:
        if self.gibi > 1:
            return f"{self.gibi:.2f} GiB"
        elif self.mebi > 1:
            return f"{self.mebi:.2f} MiB"
        elif self.kibi > 1:
            return f"{self.kibi:.2f} KiB"
        return f"{self.byte} bytes"

    def __repr__(self) -> str:
        str_ = ", ".join([f"{k}={v}" for k, v in self.__dict__.items()])
        return f"BytesSize({str_})"


class Audio(BaseModel):
    id: int
    basename: str
    filename: str
    path: str
    size: int
    link: HttpUrl


class Video(BaseModel):
    id: int
    basename: str
    filename: str
    lyrics: bool
    nc: bool
    overlap: Any
    path: str
    resolution: int
    size: int
    source: str
    subbed: bool
    uncen: bool
    tags: Any
    link: HttpUrl
    audio: Union[Audio, None]


class AnimeThemeEntry(BaseModel):
    id: int
    episodes: Union[str, None]
    notes: Union[str, None]
    nsfw: Union[bool, None]
    spoiler: Union[bool, None]
    version: Union[str, int, None]
    videos: List[Video]


class ArtistSong(BaseModel):
    alias: Union[str, None]
    as_: Annotated[Union[str, None], Field(alias="as")]


class Artist(BaseModel):
    id: int
    name: str
    slug: str
    artistsong: Union[ArtistSong, None]


class Song(BaseModel):
    id: int
    title: str
    artists: List[Artist]


class AnimeTheme(BaseModel):
    id: int
    sequence: Union[int, None]
    slug: str
    type: str
    song: Song
    animethemeentries: Union[List[AnimeThemeEntry], None]


class Anime(BaseModel):
    id: int
    name: str
    media_format: Union[str, None]
    season: Union[str, None]
    slug: str
    synopsis: Union[str, None]
    year: Union[int, None]
    animethemes: Union[List[AnimeTheme], None]


class Links(BaseModel):
    first: Union[HttpUrl, None]
    last: Union[HttpUrl, None]
    prev: Union[HttpUrl, None]
    next: Union[HttpUrl, None]


class Meta(BaseModel):
    current_page: Union[int, None]
    from_: Annotated[Union[int, None], Field(alias="from")]
    per_page: int
    to: Union[int, None]


class AnimeQueryResult(BaseModel):
    anime: list[Anime]
    links: Links
    meta: Meta


class SongMetadata(BaseModel):
    title: str
    artist: str
    album: str


def conv_ogg_to_mp3(
    ogg_path: Union[str, Path], mp3_path: Union[str, Path], metadata: SongMetadata
) -> None:
    # allow overwrite without prompt
    ogg_path = Path(ogg_path)
    if not ogg_path.exists():
        raise FileNotFoundError(f"File {ogg_path} does not exist.")
    # check if folder.jpg/jpeg/png exists, use it as album art
    album_art = None
    for ext in ["jpg", "jpeg", "png"]:
        spotter = ogg_path.with_name(f"folder.{ext}")
        if spotter.exists():
            album_art = spotter
            break
    # fmt: off
    params = [
        "ffmpeg", "-hide_banner", "-y", "-loglevel", "error",
        "-i", str(ogg_path.absolute()),
    ]
    if album_art:
        params.extend(["-i", str(album_art.absolute())])
    params.extend([
        "-metadata", f"title={metadata.title}",
        "-metadata", f"artist={metadata.artist}",
        "-metadata", f"album={metadata.album}",
        "-codec:a", "libmp3lame",
    ])
    if album_art:
        params.extend([
            "-map", "0:0", "-map", "1:0",
            "-disposition:0", "attached_pic",
        ])
    params.append(str(mp3_path))
    sp.run(params, check=True)
    # fmt: on


class AnimeThemes:
    def __init__(
        self,
        downloads: List[Literal["audio", "video"]] = ["audio", "video"],
        ow: bool = False,
        no_conv: bool = False,
    ) -> None:
        self.base_api = "https://api.animethemes.moe"
        self.g_param = {
            "include": "animethemes.animethemeentries.videos.audio,animethemes.song.artists"
        }
        self.downloads = downloads
        self.overwrite = ow
        self.no_convert = no_conv

    def search_by_platform(self, platform: str, media_id: str) -> AnimeQueryResult:
        url = f"{self.base_api}/anime"
        filters = {
            "filter[has]": "resources",
            "filter[site]": platform,
            "filter[external_id]": media_id,
        }
        return AnimeQueryResult(
            **req.get(url, params={**filters, **self.g_param}).json()
        )

    def get_anime(self, slug: str) -> Anime:
        url = f"{self.base_api}/anime/{slug}"
        return Anime(**req.get(url, params=self.g_param).json())

    def _download_files(self, url: str, path: Union[str, Path]) -> None:
        """Download files from the given URL and utilize tqdm for progress bar."""
        with req.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            with (
                open(path, "wb") as f,
                tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc="      ",
                ) as bar,
            ):
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))

    def download_video(self, video: Video, base_path: Union[str, Path]) -> None:
        url = video.link
        filename = f"backdrops/{video.basename}"
        # if backdrops directory does not exist, create it
        if not op.exists(op.join(base_path, "backdrops")):
            Path(op.join(base_path, "backdrops")).mkdir()
        path = Path(op.join(base_path, filename))
        with open(op.join(base_path, "backdrops/.nomedia"), "w") as nmd:
            nmd.write("")
        if not self.overwrite and path.exists():
            print(f"      {video.basename} already exists, skipping...")
            return
        self._download_files(str(url), path)

    def download_audio(
        self, audio: Audio, base_path: Union[str, Path]
    ) -> tuple[Path, bool]:
        url = audio.link
        cont = audio.basename.split(".")[-1]
        filename = f"theme.{cont}"
        path = Path(op.join(base_path, filename))
        mp3 = Path(op.join(base_path, "theme.mp3"))
        if not self.overwrite and (mp3.exists() or path.exists()):
            print(f"      {audio.basename} already exists, skipping...")
            return path, True
        self._download_files(str(url), path)
        return path, False

    def _audio_loop(
        self, audio: Audio, base_path: Union[str, Path], metadata: SongMetadata
    ) -> None:
        bytes_size = BytesSize.from_bytes(audio.size)
        print(f"      Downloading {audio.basename} ({bytes_size})...")
        path, is_exists = self.download_audio(audio, base_path)
        # make use of is_exists to skip conversion
        if not self.no_convert and not is_exists:
            print(f"      Converting {audio.basename} to MP3...")
            conv_ogg_to_mp3(path, Path(op.join(base_path, "theme.mp3")), metadata)
            # remove the original audio file
            remove(path)
        print(f"      Downloaded {audio.basename}")

        return

    def _video_loop(self, video: Video, base_path: Union[str, Path]) -> None:
        bytes_size = BytesSize.from_bytes(video.size)
        print(f"      Downloading {video.basename} ({bytes_size})...")
        self.download_video(video, base_path)
        print(f"      Downloaded {video.basename}")
        return

    def __download(
        self,
        anime: Anime,
        video: Video,
        base_path: Union[str, Path],
        metadata: SongMetadata,
    ) -> None:
        if "audio" in self.downloads and video.audio:
            try:
                self._audio_loop(video.audio, base_path, metadata)
            except Exception as err:
                print(f"        Error downloading audio for {anime.name}: {err}")
        if "video" in self.downloads:
            try:
                self._video_loop(video, base_path)
            except Exception as err:
                print(f"        Error downloading video for {anime.name}: {err}")

    def smart_download(self, anime: Anime, base_path: Union[str, Path]) -> None:
        """Smart-ly download theme songs and videos.

        1. Download 1st OP theme song and video, if any.
        2. Download 1st ED theme song and video, if 1st OP is not available.
        """
        if not anime.animethemes:
            raise ValueError("No themes available for this anime.")
        for theme in anime.animethemes:
            if not theme or not theme.animethemeentries:
                continue
            for entry in theme.animethemeentries:
                if not entry:
                    continue
                for video in entry.videos:
                    if not video:
                        continue
                    meta = SongMetadata(
                        title=theme.song.title,
                        artist="; ".join(
                            [artist.name for artist in theme.song.artists]
                        ),
                        album=f"{anime.name} — {theme.slug}",
                    )
                    self.__download(anime, video, base_path, meta)
                    break
                break
            break


class AnimeIds(TypedDict):
    AniDB: Union[str, None]
    AniList: Union[str, None]
    Kitsu: Union[str, None]


def read_anime_ids(nfo_path: str) -> AnimeIds:
    ids: AnimeIds = {
        "AniDB": None,
        "AniList": None,
        "Kitsu": None,
    }
    # load xml
    with open(nfo_path, "r", encoding="utf-8") as f:
        xml = f.read()
    root = ET.fromstring(xml)
    # parse xml, example:
    # <tvshow>...<anilistid>1</anilistid><anidbid>1</anidbid><kitsu>1</kitsu>...</tvshow>

    for child in root:
        if child.tag == "anilistid":
            ids["AniList"] = child.text
        elif child.tag == "anidbid":
            ids["AniDB"] = child.text
        elif child.tag == "kitsuid":
            ids["Kitsu"] = child.text

    return ids


def loop_over_anime_ids(nfo_path: str, anitheme_instance: AnimeThemes) -> None:
    ids: AnimeIds = read_anime_ids(nfo_path)
    path = Path(nfo_path)
    path = path.parent
    for platform, media_id in ids.items():
        if media_id:
            print(f"  Searching for {platform} ID {media_id}...")
            res = anitheme_instance.search_by_platform(platform, media_id)
            for anime in res.anime:
                sleep(0.3)
                print(f"    Downloading themes for {anime.name}...")
                try:
                    anitheme_instance.smart_download(anime, path)
                except Exception as err:
                    print(f"    Error downloading themes for {anime.name}: {err}")
                return


def args_parser() -> ap.Namespace:
    parser = ap.ArgumentParser(
        description="Download anime theme songs and videos, optimized for Jellyfin."
    )
    parser.add_argument("path", type=str, help="Path to the nfo file.")
    # -a or --audio
    parser.add_argument(
        "-a",
        "--audio",
        action="store_true",
        help="Download audio files.",
    )
    # -v or --video
    parser.add_argument(
        "-v",
        "--video",
        action="store_true",
        help="Download video files.",
    )
    parser.add_argument(
        "--is-directory",
        action="store_true",
        help="Process all nfo files in the directory.",
    )
    # overwrite media
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing media files.",
    )
    # dont convert media
    parser.add_argument(
        "--no-convert",
        action="store_true",
        default=False,
        help="Do not convert audio files from OGG to MP3 with ffmpeg.",
    )
    return parser.parse_args()


def main() -> None:
    args = args_parser()
    # show help if no arguments are provided
    if not args.audio and not args.video:
        print(
            "Please provide at least one of the following arguments: --audio, --video"
        )
        return
    downloads = []
    if args.audio:
        downloads.append("audio")
    if args.video:
        downloads.append("video")
    at = AnimeThemes(downloads, ow=args.overwrite, no_conv=args.no_convert)
    if args.is_directory:
        for root, _, files in walk(args.path):
            for file in files:
                if file.endswith("tvshow.nfo") or file.endswith("movie.nfo"):
                    print(f"Searching in {root}...")
                    print(f"  Processing {file}...")
                    loop_over_anime_ids(op.join(root, file), at)
                    print()
                    sleep(1)
    else:
        loop_over_anime_ids(args.path, at)


if __name__ == "__main__":
    main()
