# Icon Creator

*Automatically create and set folder icons from media poster!*

> [!NOTE]
>
> This script may require using Jellyfin or tinyMediaManager to automatically
> download images for your media.

## Requirements

* Python 3.10+
* [Jellyfin](https://jellyfin.org/) or [tinyMediaManager](https://www.tinymediamanager.org/)
  * Image assets for your media (e.g. posters, backgrounds, etc.) have to be
    downloaded and stored in the same directory as your media.
    * On Jellyfin, make sure to enable the option to download images in the
      server settings.
  * The script will automatically use/pick `folder.jpg` or `poster.jpg` as the
    icon for your media.
* [ImageMagick](https://imagemagick.org/index.php)

## Usage

0. Install the requirements listed above.
1. Download the script and place it somewhere on your system. `~/Downloads` is
   an okay place.
   * Open following link and save the page as `generateicons.py`:
     https://raw.githubusercontent.com/nattadasu/mediascripts/main/iconcreator/generateicons.py
2. Check ImageMagick PATH by running `magick -version` in your terminal. If it
   doesn't work, you may need to add it to your PATH.
   * On Windows, check if `ImageMagick-*` folder exists in `C:\Program Files`.
   * If exist, modify path on the script to point to the `magick.exe` file on
     line 13
   * For example, if the path is `C:\Program Files\ImageMagick-7.1.0-Q16-HDRI`,
     then the path to `magick.exe` is:

     ```py
     magick_path: str = os.path.join("C:", "Program Files", "ImageMagick-7.1.0-Q16-HDRI", "magick.exe")
     ```

3. Open terminal/command prompt and run the script with the path to your media
   folder as the argument.
   * For example, if your script is located in `~/Downloads/generateicons.py`,
     then you would run:

     ```sh
     python ~/Downloads/generateicons.py
     ```

     or in Windows:

     ```bat
     python C:\Users\Username\Downloads\generateicons.py
     ```

4. The script will ask you the path to your media folder. Enter the path and
   press enter.
   * On Windows, you may find the path is "invalid" and exits the script. You
     can fix this by either replacing all `\` with `\\`, or replacing `\` with
     `/`
5. Wait for the script to finish. It will automatically create and set icons for
   your media folders.
6. Enjoy!

## Known Issues

* Due to limitations on Windows, folders with the poster image as the icon will
  set to read-only. In order to fix this, you have to manually remove the
  read-only attribute on the folder via properties. Note that this will also
  "reset" the icon to the default folder icon.
* The script is completely untested on *nix (GNOME or GTK-based DE, KDE, LXDE,
  LXQT) and especially on macOS. If you encounter any issues, please open an
  issue on GitHub.

## Disclaimer

THIS SCRIPT MAY POTENTIALLY MODIFY OR DELETE YOUR FILES AND CHANGES YOUR MEDIA
FOLDER ATTRIBUTES. USE AT YOUR OWN RISK. NO WARRANTY AND SUPPORT WILL BE
PROVIDED FOR THIS SCRIPT REGARDLESS OF THE SITUATION.
