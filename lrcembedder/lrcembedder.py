import os
import sys
import re
import io
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from mutagen.mp4 import MP4
from mutagen.id3 import ID3, USLT, SYLT
from mutagen.flac import FLAC


# set log file path on current working directory
now = datetime.now()
log_path = os.path.join(os.getcwd(), f'lrcembedder_{now.strftime("%Y%m%d_%H%M%S")}.log')
mp4_exts = ('.m4a', '.m4b', '.m4p', '.m4r', '.mp4', '.aac', '.alac')
timestamp_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]')


def colorize(text: str, color: str = 'white', bg: str = 'black', bold: bool = False) -> str:
    """
    Colorize text

    :param text: text to colorize
    :type text: str
    :param color: text color, defaults to 'white'
    :type color: str, optional
    :param bg: background color, defaults to 'black'
    :type bg: str, optional
    :param bold: whether to bold the text, defaults to False
    :type bold: bool, optional
    :return: colorized text
    :rtype: str
    """
    colors = {
        'black': 30,
        'red': 31,
        'green': 32,
        'yellow': 33,
        'blue': 34,
        'purple': 35,
        'cyan': 36,
        'white': 37
    }
    bgs = {
        'black': 40,
        'red': 41,
        'green': 42,
        'yellow': 43,
        'blue': 44,
        'purple': 45,
        'cyan': 46,
        'white': 47
    }
    color_code = colors.get(color, 37)
    bg_code = bgs.get(bg, 40)
    bold_code = 1 if bold else 0
    return f'\033[{bold_code};{color_code};{bg_code}m{text}\033[0m'

def uncolorize(text: str) -> str:
    """
    Remove color from text

    :param text: text to remove color
    :type text: str
    :return: uncolorized text
    :rtype: str
    """
    return re.sub(r'\033\[\d+(?:;\d+)*m', '', text)

def reprint(text: str = "", end: str = "\n"):
    """
    Print text to stdout and log file

    :param text: text to print
    :type text: str
    :param end: end of line
    :type end: str
    """
    if len(text) > 0:
        now = datetime.now()
        date = colorize(now.strftime("%Y-%m-%d"), color='blue')
        time = colorize(now.strftime("%H:%M:%S"), color='green')
        text = f'[{date} {time}] {text}' if end == "\n" else text
    sys.stdout.write(text + end)
    if len(text) == 0:
        return
    with open(log_path, 'a') as file:
        file.write(uncolorize(text) + end)

print = reprint

class SyncStatus(Enum):
    UNSYNCED = 0
    SYNCED = 1
    BOTH = 2


@dataclass
class Timestamp:
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    milliseconds: int = 0

    def __str__(self):
        if self.hours > 0:
            return f'[{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}.{self.milliseconds:03d}]'
        return f'[{self.minutes:02d}:{self.seconds:02d}.{self.milliseconds:03d}]'

    def to_milliseconds(self):
        return self.hours * 3600000 + self.minutes * 60000 + self.seconds * 1000 + self.milliseconds

    @staticmethod
    def from_timestamp(timestamp: str) -> 'Timestamp':
        """
        Convert timestamp string to Timestamp object

        :param timestamp: timestamp string
        :type timestamp: str
        :return: Timestamp object
        :rtype: Timestamp
        """
        match = re.match(timestamp_pattern, timestamp)
        if match:
            minutes, seconds, milliseconds = match.groups()
            h = int(minutes) // 60
            m = int(minutes) % 60
            s = int(seconds)
            ms = int(milliseconds)
            return Timestamp(h, m, s, ms)
        return Timestamp()

    @staticmethod
    def from_milliseconds(milliseconds: int) -> 'Timestamp':
        """
        Convert milliseconds to Timestamp object

        :param milliseconds: milliseconds
        :type milliseconds: int
        :return: Timestamp object
        :rtype: Timestamp
        """
        h = milliseconds // 3600000
        m = (milliseconds % 3600000) // 60000
        s = (milliseconds % 60000) // 1000
        ms = milliseconds % 1000
        return Timestamp(h, m, s, ms)


@dataclass
class Lyric:
    timestamp: Timestamp
    text: str

    def __str__(self):
        return f'{self.timestamp}{self.text}'


def check_sync_or_unsync(path_or_content: str, is_content: bool = False) -> SyncStatus | None:
    """
    Check if lyrics is synced or unsynced

    :param path_or_content: file path or lyrics content
    :type path_or_content: str
    :param is_content: whether path_or_content is lyrics content
    :type is_content: bool, defaults to False
    :return: SyncStatus
    :rtype: SyncStatus | None
    """

    if not os.path.exists(path_or_content) and not is_content:
        print(f'File {path_or_content} does not exist')
        return None

    # if path is a binary file, return None
    if not is_content:
        with open(path_or_content, 'r') as file:
            if not file.readable():
                return None
            content = file.read()
    else:
        content = path_or_content

    if re.search(timestamp_pattern, content):
        return SyncStatus.SYNCED
    return SyncStatus.UNSYNCED


class LyricComparisonResult(Enum):
    ERROR = -1
    EQUAL = 0
    FILE_IS_SYNC = 1
    EMBEDDED_IS_SYNC = 2

def compare_lrc_to_embedded_lrc(lrc_path: str, embedded_lrc: str) -> LyricComparisonResult:
    """
    Compare .lrc file to embedded lyrics

    :param lrc_path: .lrc file path
    :type lrc_path: str
    :param embedded_lrc: embedded lyrics
    :type embedded_lrc: str
    :return: comparison result
    :rtype: LyricComparisonResult
    """
    file_sync_status = check_sync_or_unsync(lrc_path)
    embedded_sync_status = check_sync_or_unsync(embedded_lrc, is_content=True)

    if file_sync_status is None or embedded_sync_status is None:
        return LyricComparisonResult.ERROR

    if file_sync_status == embedded_sync_status:
        return LyricComparisonResult.EQUAL
    elif file_sync_status == SyncStatus.SYNCED:
        return LyricComparisonResult.FILE_IS_SYNC
    elif embedded_sync_status == SyncStatus.SYNCED:
        return LyricComparisonResult.EMBEDDED_IS_SYNC
    else:
        return LyricComparisonResult.EQUAL


def destruct_lyrics(content: str) -> list[Lyric]:
    """
    Destruct lyrics to list of Lyric objects

    :param content: lyrics text
    :type content: str
    :return: list of Lyric objects
    :rtype: list[Lyric]
    """

    lyrics = []
    for line in content.splitlines(True):
        match = re.match(timestamp_pattern, line)
        if match:
            timestamp = Timestamp.from_timestamp(match.group(0))
            text = line[match.end():]
            text = text.strip()
            lyrics.append(Lyric(timestamp, text))
    return lyrics


def construct_lyrics(lyrics: list[Lyric]) -> str:
    """
    Construct lyrics from list of Lyric objects

    :param lyrics: list of Lyric objects
    :type lyrics: list[Lyric]
    :return: lyrics text
    :rtype: str
    """

    content = ''
    for lyric in lyrics:
        content += str(lyric) + '\r\n'
    return content


def construct_sylt(lyrics: list[Lyric]) -> SYLT:
    """
    Construct SYLT lyrics from list of Lyric objects

    :param lyrics: list of Lyric objects
    :type lyrics: list[Lyric]
    :return: SYLT object
    :rtype: SYLT
    """

    tuples: list[tuple[str, int]] = []

    for lyric in lyrics:
        tuples.append((lyric.text, lyric.timestamp.to_milliseconds()))

    return SYLT(encoding=3, lang='eng', desc='', text=tuples)


def remove_timestamp_for_itunes(lyrics: str) -> str:
    """
    Remove timestamp from lyrics for iTunes

    :param lyrics: lyrics text
    :type lyrics: str
    :return: lyrics text without timestamp
    :rtype: str
    """
    return re.sub(timestamp_pattern, '', lyrics)

def fix_lyrics(text: str, use_cr: bool = True, itunes: bool = False) -> str:
    """
    Fix lyrics text to be properly formatted

    :param text: lyrics text
    :type text: str
    :param use_cr: whether to use CRLF instead of LF
    :type use_cr: bool, defaults to True
    :param itunes: remove timestamp for iTunes
    :type itunes: bool, defaults to False
    :return: fixed lyrics text
    :rtype: str
    """
    # if its BOM, remove it
    if text.startswith('\ufeff'):
        text = text[1:]
    if '\r' not in text and use_cr:
        # Replace LF with CRLF
        text = text.replace('\n', '\r\n')
    elif '\r' in text and not use_cr:
        # Replace CRLF with LF
        text = text.replace('\r\n', '\n')

    # format lrcs
    is_sync = check_sync_or_unsync(text, is_content=True)
    if is_sync == SyncStatus.SYNCED:
        print("    Lyrics is synced")
        lyrics = destruct_lyrics(text)
        print(f"    Found {len(lyrics)} lines of lyrics, showing first 3 lines:")
        # print first 3 lyrics
        for lyric in lyrics[:3]:
            print(f"      {lyric}")
        print('      ...') if len(lyrics) > 3 else None
        # if the first timestamp is not 0, add a timestamp at the beginning
        print(f"    First timestamp: {lyrics[0].timestamp}")
        milli = lyrics[0].timestamp.to_milliseconds()
        print(f"    First timestamp in milliseconds: {milli}")
        if milli > 0:
            lyrics.insert(0, Lyric(Timestamp(), ''))
            print("    Added a timestamp at the beginning, new first 3 lines:")
            for lyric in lyrics[:3]:
                print(f"      {lyric}")
            print('      ...') if len(lyrics) > 3 else None
        text = construct_lyrics(lyrics)
    # clear empty lines
    if '\r\n' in text:
        text = re.sub(r'((?:\r\n)+\r\n)', r'\r\n', text)
    else:
        text = re.sub(r'((?:\n)+\n)', r'\n', text)

    if itunes:
        text = remove_timestamp_for_itunes(text)

    return text


def export_lyrics_to_file(path: str, fmt: str = "lrc",
                          force_overwrite: bool = False, compat: bool = True) -> bool:
    """
    Export lyrics to file

    :param path: audio file path
    :type path: str
    :param fmt: lyrics format
    :type fmt: str, defaults to "lrc"
    :param force_overwrite: force overwrite existing file
    :type force_overwrite: bool, defaults to False
    :return: True if success
    """
    if not os.path.exists(path):
        print(f'  Export: File {path} does not exist')
        return False

    audio = None
    synced_lyrics = None
    unsynced_lyrics = None
    if path.endswith('.mp3'):
        audio = ID3(path)
        unsynced_lyrics = audio.getall('USLT')
        if unsynced_lyrics and len(unsynced_lyrics) > 1:
            print(f'  Export: Multiple USLT tags found in {path}, only the first one will be used')
        synced_lyrics = audio.getall('SYLT')
        if synced_lyrics and len(synced_lyrics) > 1:
            print(f'  Export: Multiple SYLT tags found in {path}, only the first one will be used')
        # Use first item in list
        if unsynced_lyrics:
            unsynced_lyrics = unsynced_lyrics[0].text
        try:
            if synced_lyrics:
                synced_lyrics = synced_lyrics[0].text
                lyrics = [Lyric(Timestamp.from_milliseconds(line[1]), line[0]) for line in synced_lyrics]
                synced_lyrics = construct_lyrics(lyrics)
            else:
                synced_lyrics = unsynced_lyrics[0].text
        except Exception as e:
            print(f'  Export: Failed to read synced lyrics from {path}: {e}')
            print("    Reusing unsynced lyrics")
            synced_lyrics = unsynced_lyrics
    elif path.endswith(mp4_exts):
        audio = MP4(path)
        unsynced_lyrics = audio.get('\xa9lyr', None)
        synced_lyrics = unsynced_lyrics
    elif path.endswith('.flac'):
        audio = FLAC(path)
        unsynced_lyrics = audio.get('LYRICS', None)
        synced_lyrics = unsynced_lyrics
    else:
        print(f'  Export: Unsupported file format: {path}')
        return False

    if not unsynced_lyrics and not synced_lyrics:
        print(f'  Export: No lyrics found in {path}')
        if type(audio) is ID3 and (len(audio.getall('USLT')) > 0 or len(audio.getall('SYLT')) > 0):
            print("    There's possibly a SYLT/USLT tag in the file, but it seems the logic to read lyric skipped it accidentally")
            print("    Please report this issue to the developer")
        return False

    target_path = path.rsplit('.', 1)[0] + f'.{fmt}'
    if os.path.exists(target_path) and not force_overwrite:
        print(f'  Export: File {target_path} already exists')
        return False

    with open(target_path, 'w') as file:
        check_sync = check_sync_or_unsync(target_path, synced_lyrics or unsynced_lyrics)
        if synced_lyrics:
            lyrics = synced_lyrics[0] if type(synced_lyrics) is list else synced_lyrics
            fixed_lyrics = fix_lyrics(lyrics, use_cr=compat)
            match check_sync:
                case LyricComparisonResult.FILE_IS_SYNC:
                    print("  Export: .lrc is synced compared to embedded lyrics, skip to avoid data loss (even on force overwrite)")
                    return False
                case _:
                    file.write(fixed_lyrics)
        else:
            lyrics = unsynced_lyrics[0]
            fixed_lyrics = fix_lyrics(lyrics, use_cr=compat)
            file.write(fixed_lyrics)

    return True

def import_lyrics_from_file(path: str, compat: bool = True,
                            itunes: bool = False) -> bool:
    """
    Import lyrics from file

    :param path: audio file path
    :type path: str
    :param compat: use CRLF EOL for Windows apps
    :type compat: bool
    :param itunes: remove timestamp for iTunes
    :type itunes: bool
    :return: True if success
    """

    if not os.path.exists(path):
        print(f'  Import: File {path} does not exist')
        return False

    audio = None
    if path.endswith('.mp3'):
        audio = ID3(path)
    elif path.endswith(mp4_exts):
        audio = MP4(path)
    elif path.endswith('.flac'):
        audio = FLAC(path)
    else:
        print(f'  Import: Unsupported file format: {path}')
        return False

    # find .lrc/.txt file
    lrc_path = path.rsplit('.', 1)[0] + '.lrc'
    txt_path = path.rsplit('.', 1)[0] + '.txt'
    if os.path.exists(lrc_path):
        source = lrc_path
    elif os.path.exists(txt_path):
        source = txt_path
    else:
        print(f'  Import: No lyrics file found for {path}')
        return False

    # check if lyrics is synced or unsynced
    status = check_sync_or_unsync(source)
    if status is None:
        return False

    # read lyrics from file
    with open(source, 'r', encoding='utf-8') as file:
        lyrics = file.read()

    # fix lyrics
    lyrics = fix_lyrics(lyrics, use_cr=compat, itunes=itunes)

    # write lyrics to audio file
    if type(audio) is ID3:
        # delete existing USLT and SYLT tags
        try:
            audio.delall('USLT')
        except KeyError:
            pass
        try:
            audio.delall('SYLT')
        except KeyError:
            pass
        audio['USLT'] = USLT(encoding=3, lang='eng', desc='', text=lyrics)
        audio['SYLT'] = construct_sylt(destruct_lyrics(lyrics))
    elif type(audio) is MP4:
        audio['\xa9lyr'] = lyrics
    elif type(audio) is FLAC:
        audio['LYRICS'] = lyrics
    else:
        print(f'  Import: Unsupported file format: {path}')
        return False

    audio.save()
    return True


def main(user_input: str | None = None, overwrite: bool | None = None,
         loop: int = 0, windows_compat: bool | None = None,
         itunes_compat: bool | None = None) -> dict[str, int]:
    if loop == 0:
        user_input = user_input or input('Enter folder path: ')
        if not os.path.exists(user_input):
            print(f'Folder {user_input} does not exist')
            return
        overwrite = overwrite or input('Overwrite existing lyrics file? (y/N): ')
        if overwrite is True or (type(overwrite) is str and overwrite.lower() == 'y'):
            overwrite = True
        else:
            overwrite = False
        windows_compat = input('Use Windows CLRF instead of *nix LF? Note for Musicbee user, CRLF will show as 2 separate lines (y/N): ')
        if windows_compat is True or (type(windows_compat) is str and windows_compat.lower() == 'y'):
            windows_compat = True
        else:
            windows_compat = False
        itunes_compat = input('Remove timestamp on embedded lyrics, if you manage your music library with iTunes? (y/N): ')
        if itunes_compat is True or (type(itunes_compat) is str and itunes_compat.lower() == 'y'):
            itunes_compat = True
        else:
            itunes_compat = False
    else:
        buff = io.StringIO()
        sys.stdout = buff

    expected, total = 0, 0
    fmt: dict[str, int] = {}

    for root, dirs, files in os.walk(user_input):
        for file in files:
            expected += 1
            fmt[file.rsplit('.', 1)[1]] = fmt.get(file.rsplit('.', 1)[1], 0) + 1
            if file.endswith(mp4_exts) or file.endswith('.mp3') or file.endswith('.flac'):
                try:
                    path = os.path.join(root, file)
                    print(f'Processing {path}...')
                    exp_status = export_lyrics_to_file(path, force_overwrite=overwrite, compat=windows_compat)
                    print("  Exported lyrics to file") if exp_status else print("  Skipped exporting lyrics")
                    imp_status = import_lyrics_from_file(path, compat=windows_compat)
                    print("  Imported lyrics from file") if imp_status else print("  Import failed")
                    if exp_status or imp_status:
                        total += 1
                except Exception as e:
                    print(f'  Failed to process {file}: {e}')
                    sys.exit(1)
                print()
            elif file.endswith('.lrc') or file.endswith('.txt'):
                try:
                    path = os.path.join(root, file)
                    print(f"Processing {path}...")
                    with open(path, 'r') as f:
                        content = f.read()
                    print('  Trying to fix the lyric file')
                    fixed = fix_lyrics(content, use_cr=windows_compat)
                    print("  Function run successfully")
                    with open(path, 'w') as f:
                        f.write(fixed)
                    print('  Fixed successfully')
                    total += 1
                except Exception as e:
                    print(f'  Failed to fix {file}: {e}')
                    sys.exit(1)
                print()
            else:
                print(f'Skipped {path} (not supported file format)')
                print()

    if loop == 1:
        print()
        return fmt

    print("Do final check... This might take a while")
    fmt = main(user_input=user_input, overwrite=overwrite, loop=1,
               windows_compat=windows_compat, itunes_compat=itunes_compat)
    sys.stdout = sys.__stdout__
    print("Final formatting done\n")

    print('File format distribution:')
    formatable_exts = mp4_exts + ('.mp3', '.flac', '.lrc', '.txt')
    # count files that are not formatable
    not_formatable = 0
    for key, value in fmt.items():
        print(f'  {key}: {value}', end='')
        if f".{key}" not in formatable_exts:
            print(' (not formatable)', end='')
            not_formatable += value
        print()
    print()
    print(f'Fixed {total} files out of {expected} files, {not_formatable} files are not formatable, {expected - total - not_formatable} files are skipped')
    print(f"See log file at {log_path}")
    sys.exit(0)


if __name__ == '__main__':
    main()
