import argparse
import random
import subprocess
from pathlib import Path


def get_video_duration(video_path):
    """Get the duration of the video in seconds."""
    # fmt: off
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # fmt: on
    return float(result.stdout)


def generate_screenshots(video_path, output_folder, num_screenshots=10):
    """Generate screenshots at random durations from the video."""
    duration = get_video_duration(video_path)
    video_name = video_path.stem

    # Create the output directory
    output_dir = Path(output_folder) / video_name
    output_dir.mkdir(parents=True, exist_ok=True)

    for _ in range(num_screenshots):
        random_time = random.uniform(0, duration)
        rand_str = str(random_time).replace(".", "_")
        screenshot_path = output_dir / f"{rand_str}.jpg"
        # run verbosely, force overwrite
        # fmt: off
        subprocess.run(
            [
                "ffmpeg",
                "-ss", str(random_time),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                "-y", "-loglevel", "error",
                str(screenshot_path),
            ],
        )
        # fmt: on

def process_videos_in_folder(folder_path, output_folder):
    """Recursively process videos in the folder and generate screenshots."""
    video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".ts", ".flv")
    folder_path = Path(folder_path)

    for video_path in folder_path.rglob("*"):
        if video_path.suffix.lower() in video_extensions:
            print(f"Processing {video_path}")
            generate_screenshots(video_path, output_folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate screenshots from videos.")
    parser.add_argument("input_folder", type=str, help="Folder to search for videos")
    # Optional argument to specify the output folder
    parser.add_argument(
        "--output_folder", type=str, help="Folder to save the screenshots"
    )
    args = parser.parse_args()

    process_videos_in_folder(
        args.input_folder, args.output_folder or Path(args.input_folder) / "metadata"
    )
