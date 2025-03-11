import io
import logging
import os
import re
import sys
from dataclasses import dataclass as dcls
from dataclasses import field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import typer as cli
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.id3._frames import SYLT, USLT
from mutagen.mp4 import MP4

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)
# show warning and above

MP4_EXTS = (".mp4", ".m4a", ".m4b", ".m4p", ".m4r", ".aac", ".alac")
FLAC_EXTS = (".flac",)
MP3_EXTS = (".mp3",)

SUPPORTED_EXTS = MP4_EXTS + FLAC_EXTS + MP3_EXTS

lrctimestamp_ptrn = re.compile(r"\[((?:\d{1,2}):)?(\d{2}):(\d{2})\.(\d{2,3})\]")
"""Lyric timestamp pattern: [hh:mm:ss.ms] or [mm:ss.ms]"""


@dcls
class LyricTiming:
    milliseconds: int = 0
    seconds: int = 0
    minutes: int = 0
    hours: int = 0

    def __str__(self):
        final = f"{self.minutes:02}:{self.seconds:02}.{self.milliseconds:03}]"
        if self.hours:
            return f"[{self.hours:02}:{final}"
        return f"[{final}"

    @property
    def to_miliseconds(self):
        return (
            self.hours * 3600000
            + self.minutes * 60000
            + self.seconds * 1000
            + self.milliseconds
        )

    @property
    def as_word_timestamp(self):
        string = str(self).replace("[", "<").replace("]", ">")
        return f"{string}"

    @classmethod
    def from_str(cls, time: str):
        match = lrctimestamp_ptrn.match(time)
        if not match:
            raise ValueError(f"Invalid time format: {time}")
        groups = match.groups()
        # reverse the groups
        milliseconds, seconds, minutes, hours = groups[::-1]
        return cls(
            hours=int(hours) if hours else 0,
            minutes=int(minutes),
            seconds=int(seconds),
            milliseconds=int(milliseconds),
        )

    @classmethod
    def from_milliseconds(cls, milliseconds: int):
        hours, milliseconds = divmod(milliseconds, 3600000)
        minutes, milliseconds = divmod(milliseconds, 60000)
        seconds, milliseconds = divmod(milliseconds, 1000)
        log.debug(
            f"Converted {milliseconds} to {hours}:{minutes}:{seconds}.{milliseconds}"
        )
        return cls(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
        )

@dcls
class LyricLine:
    timestamp: LyricTiming
    text: str

    def __str__(self):
        return f"{self.timestamp}{self.text}"


class SyncStatus(Enum):
    UNSYNCED = 0
    SYNCED = 1
    BOTH = 2
    SYNC_WITH_METADATA = 3
    INSTRUMENTAL = 4


class ForegroundAnsiCode(Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37


class BackgroundAnsiCode(Enum):
    BLACK = 40
    RED = 41
    GREEN = 42
    YELLOW = 43
    BLUE = 44
    MAGENTA = 45
    CYAN = 46
    WHITE = 47


class LyricComparison(Enum):
    ERROR = -1
    """Comparison failed"""
    EQUAL = 0
    """Both lyric files in sidecar and embedded are equal"""
    FILE_IS_SYNC = 1
    """Sidecar lyric file is synced"""
    EMBEDDED_IS_SYNC = 2
    """Lyric embedded in the file is synced or has better quality"""
    MUSIC_IS_INSTRUMENTAL = 3
    """Lyric is instrumental, marked by "[au: instrumental]" metadata"""


def colorize(
    text,
    color: ForegroundAnsiCode | str = ForegroundAnsiCode.WHITE,
    bg: BackgroundAnsiCode | str = BackgroundAnsiCode.BLACK,
    bold: bool = False,
):
    """
    Colorize the given text with the given color and background color.

    :param text: Text to colorize
    :type text: str
    :param color: Foreground color
    :type color: ForegroundAnsiCode
    :param bg: Background color
    :type bg: BackgroundAnsiCode
    :param bold: Bold text
    :type bold: bool
    :return: Colorized text
    :rtype: str
    """

    try:
        if isinstance(color, str):
            color = ForegroundAnsiCode[color.upper()]
        if isinstance(bg, str):
            bg = BackgroundAnsiCode[bg.upper()]
    except KeyError as err:
        raise ValueError(f"Invalid color input: {err}")
    return f"\033[{color.value};{bg.value};{'1' if bold else '0'}m{text}\033[0m"

NETEASE_CREDITS = ["乐队", "作曲", "作詞", "作词", "出品", "制作人", "工程师", "录音师", "录音棚", "指挥", "母带", "混音", "編曲", "编曲"]

NETEASE_CREDITS_PTRN = re.compile(r"(?:\[(?:\d+:)?\d+:\d+\.\d+\] ?)?(" + "|".join(NETEASE_CREDITS) + r") ?(:|：) ?([^\n]+)")

def is_lyric_sync(content: str) -> SyncStatus:
    """
    Check if the given content is a synced lyric file.

    :param content: File content
    :type content: str
    :return: Sync status
    :rtype: SyncStatus
    """
    if re.search(lrctimestamp_ptrn, content):
        metadata = re.findall(r"\[(\w{2,3}):([^\]]+)\]", content)
        if ("au", "instrumental") in metadata:
            log.debug("Lyric is instrumental")
            return SyncStatus.INSTRUMENTAL
        if metadata:
            log.debug(f"Lyric is synced with standard metadata: {metadata}")
            return SyncStatus.SYNC_WITH_METADATA
        if re.search(NETEASE_CREDITS_PTRN, content):
            log.debug("Lyric is synced with metadata from Netease")
            return SyncStatus.SYNC_WITH_METADATA
        log.debug("Lyric file is synced")
        return SyncStatus.SYNCED
    log.debug("Lyric file is not synced")
    return SyncStatus.UNSYNCED


def check_sync_or_unsync(
    path_or_content: Path | str, is_content: bool = False
) -> tuple[SyncStatus | None, str | None]:
    """
    Check if the given path or content is a synced lyric file.
    Wrote for backward compatibility.

    :param path_or_content: Path to file or content
    :type path_or_content: Path | str
    :param is_content: If the given path_or_content is a content
    :type is_content: bool
    :return: Sync status
    :rtype: SyncStatus
    """
    if is_content and not isinstance(path_or_content, Path):
        return (is_lyric_sync(path_or_content), path_or_content)
    try:
        with open(path_or_content, "r") as file:
            data = file.read()
            return (is_lyric_sync(data), data)
    except FileNotFoundError:
        log.error(f"File not found: {path_or_content}")
        return (None, None)


def compare_lrc_and_embedded(lrc_path: str, embedded_lyric: str) -> LyricComparison:
    """
    Compare the given lyric file and embedded lyric.

    :param lrc_path: Path to lyric file
    :type lrc_path: str
    :param embedded_lyric: Embedded lyric
    :type embedded_lyric: str
    :return: Comparison result
    :rtype: LyricComparison
    """
    lrc_status, lrc_content = check_sync_or_unsync(lrc_path)
    embed_status, embed_content = check_sync_or_unsync(embedded_lyric, is_content=True)

    # check if the lyric in either lrc or embed has [au:instrumental]
    if lrc_status == SyncStatus.INSTRUMENTAL or embed_status == SyncStatus.INSTRUMENTAL:
        return LyricComparison.MUSIC_IS_INSTRUMENTAL

    if lrc_status == SyncStatus.SYNCED and embed_status == SyncStatus.SYNCED:
        if lrc_content == embed_content:
            return LyricComparison.EQUAL
        return LyricComparison.EMBEDDED_IS_SYNC
    elif lrc_status == SyncStatus.SYNCED:
        return LyricComparison.FILE_IS_SYNC
    elif embed_status == SyncStatus.SYNCED:
        return LyricComparison.EMBEDDED_IS_SYNC
    elif lrc_status == embed_status:
        return LyricComparison.EQUAL
    return LyricComparison.ERROR

def deconstruct_lyric(content: str) -> list[LyricLine]:
    """
    Deconstruct the given lyric content to a list of LyricLine objects.

    :param content: Lyric content
    :type content: str
    :return: List of LyricLine objects
    :rtype: list[LyricLine]
    """
    lines = content.splitlines()
    lyric_lines = []
    for line in lines:
        if not line:
            continue
        matching = lrctimestamp_ptrn.match(line)
        if matching:
            timestamp = LyricTiming.from_str(matching.group(0))
            text = line[matching.end() :]
            lyric_lines.append(LyricLine(timestamp=timestamp, text=text))
    return lyric_lines

def construct_lyric(lyric_lines: list[LyricLine]) -> str:
    """
    Construct a lyric content from the given list of LyricLine objects.

    :param lyric_lines: List of LyricLine objects
    :type lyric_lines: list[LyricLine]
    :return: Lyric content
    :rtype: str
    """
    return "\n".join(map(str, lyric_lines))

def convert_to_sylt(lyric_lines: list[LyricLine]) -> SYLT:
    """
    Convert the given list of LyricLine objects to a SYLT object.

    :param lyric_lines: List of LyricLine objects
    :type lyric_lines: list[LyricLine]
    :return: SYLT object
    :rtype: SYLT
    """
    sylt = SYLT(encoding=3, lang="eng", format=1)
    tuples : list[tuple[str, int]] = []
    for line in lyric_lines:
        tuples.append((line.text, line.timestamp.to_miliseconds))
    sylt.text = tuples
    return sylt

def convert_to_uslt(lyric_lines: list[LyricLine]) -> USLT:
    """
    Convert the given list of LyricLine objects to a USLT object.

    :param lyric_lines: List of LyricLine objects
    :type lyric_lines: list[LyricLine]
    :return: USLT object
    :rtype: USLT
    """
    uslt = USLT(encoding=3, lang="eng", desc="Lyrics")
    uslt.text = construct_lyric(lyric_lines)
    return uslt

def remove_timestamps(lyrics: str) -> str:
    """
    Remove timestamps from the given lyric content.

    :param lyrics: Lyric content
    :type lyrics: str
    :return: Lyric content without timestamps
    :rtype: str
    """
    return re.sub(lrctimestamp_ptrn, "", lyrics)

def fix_lyric(lyrics: str, remove_timestamp: bool = False) -> str:
    """
    Fix the given lyric content by removing timestamps and extra spaces.

    :param lyrics: Lyric content
    :type lyrics: str
    :param remove_timestamp: Remove timestamps
    :type remove_timestamp: bool
    :return: Fixed lyric content
    :rtype: str
    """
    # remove MP3Tag artifact
    log.debug("Removing MP3Tag artifact, if any")
    lyrics = re.sub(r"^(?:\w+)?\|\|", "", lyrics)
    is_sync = is_lyric_sync(lyrics)
    if is_sync == SyncStatus.SYNC_WITH_METADATA:
        log.debug("Lyric contains some metadata")
        log.debug("Removing metadata")
        lyrics = re.sub(r"\[(\w{2,3}):([^\]]+)\]", "", lyrics)
        # remove netease credits
        log.debug("Removing Netease credits")
        lyrics = re.sub(NETEASE_CREDITS_PTRN, "", lyrics)
        # remove empty lines
        log.debug("Removing empty lines")
        lyrics = re.sub(r"\n{2,}", "\n", lyrics)
        is_sync = is_lyric_sync(lyrics)
    if is_sync == SyncStatus.SYNCED:
        log.debug("Lyric is synced, fixing")
        deconst = deconstruct_lyric(lyrics)
        log.debug(f"Found {len(deconst)} lines, showing first 3")
        # add dummy line if less than 3 lines
        if len(deconst) < 3:
            deconst.extend([LyricLine(LyricTiming(), "") for _ in range(3 - len(deconst))])
        for line in deconst[:3]:
            log.debug(f"{line.timestamp} {line.text}")
        log.debug("First timestamp: %s", deconst[0].timestamp)
        milli = deconst[0].timestamp.to_miliseconds
        log.debug("First timestamp inf ms: %s", milli)
        if milli > 0:
            log.debug("First line is not at 0, adding dummy line")
            deconst.insert(0, LyricLine(LyricTiming(), ""))
        log.debug("Reconstructing lyric")
        lyrics = construct_lyric(deconst)
    if remove_timestamp and is_sync in [SyncStatus.SYNCED, SyncStatus.SYNC_WITH_METADATA]:
        lyrics = remove_timestamps(lyrics)
    log.debug("Removing extra spaces")
    strip = "\n".join(map(str.strip, lyrics.splitlines()))

    return strip

def dissect_mp3(path: Path) -> tuple[ID3, Any, Any]:
    """
    Dissect the given MP3 file.

    :param path: Path to the MP3 file
    :type path: Path
    :return: ID3 object, tags, and lyrics
    :rtype: tuple[ID3, Any, Any]
    """
    id3 = ID3(path)
    unsync_l = id3.getall('USLT')
    if unsync_l and len(unsync_l) > 1:
        log.warning("Multiple USLT frames found, using the first one")
    unsync = unsync_l[0] if unsync_l else None
    unsynt = unsync.text if unsync else ""
    sync_l = id3.getall('SYLT')
    if sync_l and len(sync_l) > 1:
        log.warning("Multiple SYLT frames found, using the first one")
    sync = sync_l[0] if sync_l else None
    try:
        if sync:
            synct = sync.text
            lyrics = [LyricLine(LyricTiming.from_milliseconds(li[1]), li[0]) for li in synct]
            const = construct_lyric(lyrics)
        else:
            const = unsynt
    except (ValueError, TypeError) as err:
        log.error(f"Error constructing lyric: {err}")
        log.warning("Using unsynced lyric")
        const = unsynt
    return (id3, unsynt, const)

def dissect_mp4(path: Path) -> tuple[MP4, Any, Any]:
    """
    Dissect the given MP4 file.

    :param path: Path to the MP4 file
    :type path: Path
    :return: MP4 object, tags, and lyrics
    :rtype: tuple[MP4, Any, Any]
    """
    mp4 = MP4(path)
    unsync = mp4.get("\xa9lyr")
    return (mp4, unsync, unsync)

def dissect_flac(path: Path) -> tuple[FLAC, Any, Any]:
    """
    Dissect the given FLAC file.

    :param path: Path to the FLAC file
    :type path: Path
    :return: FLAC object, tags, and lyrics
    :rtype: tuple[FLAC, Any, Any]
    """
    flac = FLAC(path)
    unsync = flac.get("LYRICS")
    return (flac, unsync, unsync)


def export_lyrics(path: Path, overwrite: bool = False) -> bool:
    """
    Export lyrics from the given file.

    :param path: Path to the music file
    :type path: Path
    :param overwrite: Overwrite existing lyrics
    :type overwrite: bool
    :return: Export status
    :rtype: bool
    """

    if not path.exists():
        log.error(f"File not found: {path}")
        return False

    if path.suffix not in SUPPORTED_EXTS:
        log.error(f"Unsupported file format: {path.suffix}")
        return False

    if path.suffix in MP4_EXTS:
        audio, unsync, sync = dissect_mp4(path)
    elif path.suffix in FLAC_EXTS:
        audio, unsync, sync = dissect_flac(path)
    else:
        audio, unsync, sync = dissect_mp3(path)

    if not sync and not unsync:
        log.error("No lyrics found")
        if isinstance(audio, ID3) and (len(audio.getall("USLT")) or len(audio.getall("SYLT")) > 0):
            log.warning("There's possibly a SYLT/USLT tag in the file, but the logic accidentally skipped it")
        return False

    # find sidecar lyric file, either txt or lrc
    lrc_sidecar = path.with_suffix(".lrc")
    txt_sidecar = path.with_suffix(".txt")
    if lrc_sidecar.exists():
        sidecar = lrc_sidecar
    elif txt_sidecar.exists():
        sidecar = txt_sidecar
    else:
        sidecar = None

    if sidecar and not overwrite:
        log.error(f"Lyric sidecar file already exists: {sidecar}")
        return False

    sync_stats = is_lyric_sync(sync) if sync else None
    if sync_stats == SyncStatus.SYNCED:
        with open(lrc_sidecar, "w") as file:
            file.write(sync)
        log.info(f"Lyric sidecar file saved: {lrc_sidecar}")
