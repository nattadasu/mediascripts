import subprocess
import sys
import os

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


def convert_png_to_ico(path: str, gravity: str = "center", transparent: str = "white",
                       resize: int = 256, background: str = "transparent") -> str:
    """Converts a png image to an ico"""
    new_path = path.replace(".png", ".ico")
    subprocess.run([magick_path, "convert", path, "-gravity", gravity, "-resize",
                    f"{resize}x{resize}", "-background", background, "-extent", f"{resize}x{resize}",
                    "-transparent", transparent, new_path])
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
        # uncomment if you want to get asked everytime
        # do_it = input(f"Convert {path} to ICO? (y/n): ")
        # if do_it.lower() != "y":
        #     # delete png if generated
        #     delete_png(path, png_generated)
        #     continue
        convert_png_to_ico(path)
        delete_png(path, png_generated)
        dump_desktop_ini(*paths)
        print(f"Converted {path} to ICO")
        return
    else:
        print("No images found")
    
if __name__ == "__main__":
    load_path = input("Enter path to folder containing poster and folder images: ")
    # recursively fetch directories in load_path
    for root, dirs, files in os.walk(load_path):
        for dir in dirs:
            do_stuff(root, dir)
