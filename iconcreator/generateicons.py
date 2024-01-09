import subprocess
import sys
from platform import system
import os
from math import ceil

# Replace if necessary
magick_path: str = os.path.join("C:\\", "Program Files", "ImageMagick-7.1.1-Q16-HDRI", "magick.exe")
if not os.path.exists(magick_path):
    print("ImageMagick not found")
    sys.exit(1)


def convert_jpg_to_png(path: str) -> str:
    """Converts a jpg image to png"""
    new_path = path.replace(".jpg", ".png") if path.endswith(".jpg") else path.replace(".jpeg", ".png")
    subprocess.run([magick_path, "convert", path, new_path])
    return new_path


def convert_png_to_ico(path: str, gravity: str = "center", resize: int = 256,
                       background: str = "transparent") -> str:
    """Converts a png image to an ico"""
    new_path = path.replace(".png", ".ico")
    subprocess.run([magick_path, "convert", path, "-gravity", gravity, "-resize",
                    f"{resize}x{resize}", "-background", background, "-extent", f"{resize}x{resize}",
                    new_path])
    return new_path
    return new_path

def delete_png(path: str, png_generated: str | bool = False) -> None:
    """Deletes a png image"""
    os.remove(path) if png_generated else None

def dump_desktop_ini(*path: str) -> None:
    """Dumps a desktop.ini file"""
    with open(os.path.join(*path, "desktop.ini"), "w") as desktop_ini:
        # check if folder icon is poster.ico, else use folder.ico
        folder_icon = "poster.ico" if os.path.exists(os.path.join(*path, "poster.ico")) else "folder.ico"
        desktop_ini.write(f"""[ViewState]
Mode=
Vid=
FolderType=Pictures
[.ShellClassInfo]
IconResource={folder_icon},0
""")


def set_windows_folder_icon(*path: str) -> None:
    """Sets a folder icon for Windows"""
    folder_icon = "poster.ico" if os.path.exists(os.path.join(*path, "poster.ico")) else "folder.ico"
    subprocess.run(["attrib", "+r", os.path.join(*path)])
    subprocess.run(["attrib", "+h", os.path.join(*path, "desktop.ini")])
    subprocess.run(["attrib", "+r", os.path.join(*path, folder_icon)])


def refresh_folder(*path: str) -> None:
    """Refreshes a folder"""
    from win32com.shell import shellcon, shell # type: ignore
    shell.SHChangeNotify(shellcon.SHCNE_ASSOCCHANGED, shellcon.SHCNF_IDLIST, None, None)

def configure_folder_icon(*path: str) -> None:
    """Configures folder icon for all platforms"""
    match system():
        case "Windows":
            set_windows_folder_icon(*path)
        case _:
            print("Unsupported OS")
            sys.exit(1)

def do_stuff(*paths: str) -> None:
    """Converts folder containing jpg images to ico"""
    print("Converting poster on " + '\\'.join(paths))
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

if __name__ == "__main__":
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
                print("-" * ceil((os.get_terminal_size().columns)/2))
        print("Retrying...")
        yeet(load_path)
