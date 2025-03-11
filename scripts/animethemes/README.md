# `animethemes`

Download anime themes from animethemes.moe for Jellyfin theme song feature.

## Initial Requirements

1. `.NFO` files for each anime in your library.
2. `Jellyfin` server with theme song feature enabled.
3. `ffmpeg` installed and added to system path.
4. `Python 3.6` or higher, and installed required packages by running `pip install -r requirements.txt`.

## Lookup Requirements

Make sure that your anime library have enabled one or more of the following agents:

1. `AniDB`
2. `AniList`
3. `Kitsu`

## Usage

* `-a`, `--audio`: Download audio files.
* `-v`, `--video`: Download OP/ED videos, app will only download one video per anime.
* `--is-directory`: Process all nfo files recursively in the current working directory.
* `--overwrite`: Overwrite existing files.
* `--no-convert`: Do not convert downloaded music files from `.ogg` to `.mp3`.

Command line examples:

```bash
$> python animethemes -a -v "path/to/anime.nfo"
$> python animethemes -a -v --is-directory "path/to/anime/directory"
```
