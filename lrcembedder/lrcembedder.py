import os
import sys
import re
import io
from enum import Enum
from dataclasses import dataclass

from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.flac import FLAC


mp4_exts = ('.m4a', '.m4b', '.m4p', '.m4r', '.mp4', '.aac', '.alac')
timestamp_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]')


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


def fix_lyrics(text: str) -> str:
    """
    Fix lyrics text to be properly formatted

    :param text: lyrics text
    :type text: str
    :return: fixed lyrics text
    :rtype: str
    """
    # if its BOM, remove it
    if text.startswith('\ufeff'):
        text = text[1:]
    if '\r' not in text:
        # Replace LF with CRLF
        text = text.replace('\n', '\r\n')

    # format lrcs
    is_sync = check_sync_or_unsync(text, is_content=True)
    if is_sync == SyncStatus.SYNCED:
        print("    Lyrics is synced")
        lyrics = destruct_lyrics(text)
        print(f"    Found {len(lyrics)} lines of lyrics, showing first 3 lines:")
        # print first 3 lyrics
        for lyric in lyrics[:3]:
            print(f"      {lyric}")
        # if the first timestamp is not 0, add a timestamp at the beginning
        print(f"    First timestamp: {lyrics[0].timestamp}")
        milli = lyrics[0].timestamp.to_milliseconds()
        print(f"    First timestamp in milliseconds: {milli}")
        if milli > 0:
            lyrics.insert(0, Lyric(Timestamp(), ''))
            print("    Added a timestamp at the beginning, new first 3 lines:")
            for lyric in lyrics[:3]:
                print(f"      {lyric}")
        text = construct_lyrics(lyrics)
    # clear empty lines
    text = re.sub(r'((?:\r\n)+\r\n)', r'\r\n', text)

    return text


def export_lyrics_to_file(path: str, fmt: str = "lrc", force_overwrite: bool = False) -> bool:
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
        audio = MP3(path)
        # find first dict with key that stsarts with 'USLT::'
        for key in audio.keys():
            if key.startswith('USLT::'):
                unsynced_lyrics = audio[key].text
                synced_lyrics = unsynced_lyrics
                break
        lyrics = []
        for key in audio.keys():
            if key.startswith('SYLT::'):
                synced_lyrics = audio[key].text
                # construct tuple of (text, timestamp) to list of Lyric objects
                lyrics = [Lyric(Timestamp.from_milliseconds(line[1]), line[0]) for line in synced_lyrics]
                synced_lyrics = construct_lyrics(lyrics)
                break
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
        if type(audio) is MP3:
            print("    There's possibly a SYLT/USLT tag in the file, but it seems the logic to read lyric skipped it accidentally")
            print("    Please report this issue to the developer")
        return False

    target_path = path.rsplit('.', 1)[0] + f'.{fmt}'
    if os.path.exists(target_path) and not force_overwrite:
        print(f'  Export: File {target_path} already exists')
        return False

    with open(target_path, 'w') as file:
        if synced_lyrics:
            lyrics = synced_lyrics[0] if type(synced_lyrics) is list else synced_lyrics
            fixed_lyrics = fix_lyrics(lyrics)
            file.write(fixed_lyrics)
        else:
            lyrics = unsynced_lyrics[0]
            fixed_lyrics = fix_lyrics(lyrics)
            file.write(fixed_lyrics)

    return True


def import_lyrics_from_file(path: str) -> bool:
    """
    Import lyrics from file

    :param path: audio file path
    :type path: str
    :return: True if success
    """

    if not os.path.exists(path):
        print(f'  Import: File {path} does not exist')
        return False

    audio = None
    if path.endswith('.mp3'):
        audio = MP3(path)
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
    lyrics = fix_lyrics(lyrics)

    # write lyrics to audio file
    if type(audio) is MP3:
        # with open(f"{path}.mutagen.pydump", "w") as f:
        #     print(f"    Dumping audio file to {path}.mutagen.pydump...")
        #     f.write(repr(audio))
        if status == SyncStatus.SYNCED:
            # find first dict with key that stsarts with 'USLT::'
            destruct = destruct_lyrics(lyrics)
            # convert to list of tuple (text, timestamp)
            text_timestamp = [(lyric.text, lyric.timestamp.to_milliseconds()) for lyric in destruct]
            for key in audio.keys():
                if key.startswith('SYLT::'):
                    audio[key].text = text_timestamp
                    break
        for key in audio.keys():
            if key.startswith('USLT::'):
                audio[key].text = lyrics
                break
    elif type(audio) is MP4:
        audio['\xa9lyr'] = lyrics
    elif type(audio) is FLAC:
        audio['LYRICS'] = lyrics
    else:
        print(f'  Import: Unsupported file format: {path}')
        return False

    audio.save()
    return True


def main(user_input: str | None = None, overwrite: bool | None = None, loop: int = 0) -> dict[str, int]:
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
                    exp_status = export_lyrics_to_file(path, force_overwrite=overwrite)
                    print("  Exported lyrics to file") if exp_status else print("  Skipped exporting lyrics")
                    imp_status = import_lyrics_from_file(path)
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
                    fixed = fix_lyrics(content)
                    print("  Function run successfully")
                    with open(path, 'w') as f:
                        f.write(fixed)
                    print('  Fixed successfully')
                    total += 1
                except Exception as e:
                    print(f'  Failed to fix {file}: {e}')
                    sys.exit(1)
                print()

    if loop == 1:
        return fmt

    print("Do final check... This might take a while")
    fmt = main(user_input=user_input, overwrite=overwrite, loop=1)
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
    print(f'\nFixed {total} files out of {expected} files, {not_formatable} files are not formatable, {expected - total - not_formatable} files are skipped')
    sys.exit(0)


if __name__ == '__main__':
    main()
