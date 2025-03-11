import os
import re
import subprocess
import sys
from math import ceil
from platform import system
from urllib.parse import quote

SYSTEM_OS = system()

# Replace if necessary
match SYSTEM_OS:
    case "Linux":
        MAGICK_PATH = (
            subprocess.run(["which", "magick"], capture_output=True)
            .stdout.decode("utf-8")
            .strip()
        )
    case "Darwin":
        MAGICK_PATH = (
            subprocess.run(["which", "magick"], capture_output=True)
            .stdout.decode("utf-8")
            .strip()
        )
    case "Windows":
        try:
            MAGICK_PATH = (
                subprocess.run(["where", "magick"], capture_output=True)
                .stdout.decode("utf-8")
                .strip()
            )
            if not MAGICK_PATH:
                raise FileNotFoundError
            print(MAGICK_PATH)
        except Exception:
            MAGICK_PATH = os.path.join(
                os.getenv("ProgramFiles"), "ImageMagick-7.1.1-Q16-HDRI", "magick.exe"
            )
            print(MAGICK_PATH)
    case _:
        print("Unsupported OS")
        sys.exit(1)

if not os.path.exists(MAGICK_PATH):
    print("Path: ImageMagick not found")
    sys.exit(1)

MAGISK_VERSION: tuple[int, int, int, int] = (0, 0, 0, 0)


def get_magisk_version() -> tuple[int, int, int, int]:
    """Get Magisk version"""
    global MAGISK_VERSION
    try:
        raw = (
            subprocess.run([MAGICK_PATH, "--version"], capture_output=True)
            .stdout.decode("utf-8")
            .strip()
        )
        version = re.search(r"ImageMagick (\d+)\.(\d+)\.(\d+)-(\d+)", raw)
        if version is None:
            raise FileNotFoundError
        MAGISK_VERSION = tuple(map(int, version.groups()))
        print(f"ImageMagick version: {MAGISK_VERSION}")
    except FileNotFoundError:
        print(f'Can\'t parse ImageMagick version:"""\n{raw}\n"""')
        sys.exit(1)
    return MAGISK_VERSION


commands = [MAGICK_PATH, "convert"]

# if it's above 7.1.1.20, use magick instead of convert
if get_magisk_version() >= (7, 1, 1, 20):
    commands = [MAGICK_PATH]


def convert_jpg_to_png(path: str) -> str:
    """Converts a jpg image to png"""
    new_path = (
        path.replace(".jpg", ".png")
        if path.endswith(".jpg")
        else path.replace(".jpeg", ".png")
    )
    command_list = commands + [path, new_path]
    subprocess.run(command_list)
    return new_path


def convert_png_to_ico(
    path: str,
    gravity: str = "center",
    resize: int = 256,
    background: str = "transparent",
) -> str:
    """Converts a png image to an ico"""
    new_path = path.replace(".png", ".ico")
    command_list = commands + [
        path,
        "-gravity",
        gravity,
        "-resize",
        f"{resize}x{resize}",
        "-background",
        background,
        "-extent",
        f"{resize}x{resize}",
        new_path,
    ]
    subprocess.run(command_list)
    return new_path


def convert_ico_to_icns(path: str) -> str:
    """Converts an ico image to an icns for macOS"""
    new_path = path.replace(".ico", ".icns")
    command_list = commands + [path, new_path]
    subprocess.run(command_list)
    return new_path


def delete_png(path: str, png_generated: str | bool = False) -> None:
    """Deletes a png image"""
    os.remove(path) if png_generated else None


def dump_desktop_ini(*path: str) -> None:
    """Dumps a desktop.ini file"""
    with open(os.path.join(*path, "desktop.ini"), "w") as desktop_ini:
        # check if folder icon is poster.ico, else use folder.ico
        folder_icon = (
            "poster.ico"
            if os.path.exists(os.path.join(*path, "poster.ico"))
            else "folder.ico"
        )
        desktop_ini.write(f"""[ViewState]
Mode=
Vid=
FolderType=Pictures
[.ShellClassInfo]
IconResource={folder_icon},0
""")


def find_jpg_or_png(*path: str) -> str | None:
    """Finds a jpg or png image of poster or folder"""
    lookup = ("poster", "folder")
    for file in os.listdir(os.path.join(*path)):
        if file.startswith(lookup) and (
            file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png")
        ):
            return os.path.join(*path, file)


def set_linux_icon(*path: str) -> None:
    # Although by default some DE/FM supports JPEG/PNG, we decided to rather use
    # .ico for compatibility and speed
    folder_icon = find_jpg_or_png(*path)
    if folder_icon:
        paths = os.path.join(*path)
        as_uri = "file://" + quote(folder_icon)
        linux_commands = {
            "GNOME": [
                "gio",
                "set",
                #"-t",
                #"string",
                "-d",
                paths,
                "metadata::custom-icon",
               # as_uri,
            ],
            "KDE": ["kioclient5", "setIcon", paths, folder_icon],
            "LXDE": ["pcmanfm", "-w", paths, folder_icon],
            "LXQt": ["pcmanfm-qt", "-w", paths, folder_icon],
            "XFCE": [
                "xfconf-query",
                "-c",
                "xfce4-desktop",
                "-p",
                "/desktop-icons/file-icons",
                "-s",
                f"{{'{os.path.join(*path)}': '{folder_icon}'}}",
            ],
        }
        for de, command in linux_commands.items():
            if os.path.exists(f"/usr/bin/{command[0].lower()}"):
                subprocess.run(command)
                print(f"{de} detected, setting folder icon")
        else:
            print("Unsupported DE")
        return
    else:
        print("No images found")
    return


def set_macos_folder_icon(*path: str) -> None:
    """Sets a folder icon for macOS"""
    folder_icon = (
        "poster.ico"
        if os.path.exists(os.path.join(*path, "poster.ico"))
        else "folder.ico"
    )
    folder_icon = convert_ico_to_icns(os.path.join(*path, folder_icon))
    subprocess.run(["SetFile", "-a", "C", os.path.join(*path)])
    subprocess.run(["SetFile", "-a", "V", os.path.join(*path, folder_icon)])


def set_windows_folder_icon(*path: str) -> None:
    """Sets a folder icon for Windows"""
    folder_icon = (
        "poster.ico"
        if os.path.exists(os.path.join(*path, "poster.ico"))
        else "folder.ico"
    )
    subprocess.run(["attrib", "+r", os.path.join(*path)])
    subprocess.run(["attrib", "+h", os.path.join(*path, "desktop.ini")])
    subprocess.run(["attrib", "+r", os.path.join(*path, folder_icon)])


def refresh_folder(*path: str) -> None:
    """Refreshes a folder"""
    from win32com.shell import shell, shellcon  # type: ignore

    shell.SHChangeNotify(shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None)


def configure_folder_icon(*path: str) -> None:
    """Configures folder icon for all platforms"""
    match system():
        case "Linux":
            set_linux_icon(*path)
        case "Darwin":
            set_macos_folder_icon(*path)
        case "Windows":
            set_windows_folder_icon(*path)
        case _:
            print("Unsupported OS")
            sys.exit(1)


def do_stuff(*paths: str) -> None:
    """Converts folder containing jpg images to ico"""
    print("Converting poster on " + os.path.join(*paths))
    # check if PNG is not exist but JP(E)G is
    image_paths: list[tuple[str, bool]] = []
    for path in os.listdir(os.path.join(*paths)):
        sanity = path.startswith("poster") or path.startswith("folder")
        if (path.endswith(".png")) and sanity:
            image_paths.append((os.path.join(*paths, path), False))
        elif (path.endswith(".jpg") or path.endswith(".jpeg")) and sanity:
            image_paths.append((convert_jpg_to_png(os.path.join(*paths, path)), True))

    # convert PNG to ICO
    for path, png_generated in image_paths:
        convert_png_to_ico(path)
        delete_png(path, png_generated)
        dump_desktop_ini(*paths)
        configure_folder_icon(*paths)
        print(f"Converted {path} to ICO")
        return
    else:
        print("No images found")


def yeet(path: str) -> None:
    """Run the process"""
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            do_stuff(root, dir)
            print("=" * os.get_terminal_size().columns)
    if system() == "Windows":
        print("Refreshing folder")
        refresh_folder(path)
    print("Done!")


def remove_file_attribs(root_: str, dir_: str, target: str | None = None) -> None:
    """Removes file attributes"""
    path = os.path.join(root_, dir_, target) if target else os.path.join(root_, dir_)
    if target:
        subprocess.run(["attrib", "-r", "-s", "-h", path])
    else:
        subprocess.run(["attrib", "-r", "-s", "-h", path, "/d", "/s"])


def main() -> None:
    load_path = input("Enter path to folder containing poster and folder images: ")
    try:
        yeet(load_path)
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)
    except PermissionError:
        print("=" * os.get_terminal_size().columns)
        print("Permission denied, clearing attributes if necessary")
        for root, dirs, files in os.walk(load_path):
            for dir in dirs:
                curr = os.path.join(root, dir)
                print(f"Clearing attributes on {curr}")
                remove_file_attribs(root, dir)
                if os.path.exists(os.path.join(root, dir, "desktop.ini")):
                    remove_file_attribs(root, dir, "desktop.ini")
                if os.path.exists(os.path.join(root, dir, "poster.ico")):
                    remove_file_attribs(root, dir, "poster.ico")
                if os.path.exists(os.path.join(root, dir, "folder.ico")):
                    remove_file_attribs(root, dir, "folder.ico")
                print("-" * ceil((os.get_terminal_size().columns) / 2))
        print("Retrying...")
        yeet(load_path)


if __name__ == "__main__":
    main()
