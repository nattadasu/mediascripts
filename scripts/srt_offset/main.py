import argparse
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SubtitleLine:
    index: int
    start: int  # Start time in milliseconds
    end: int    # End time in milliseconds
    text: List[str]

    def to_srt_format(self) -> str:
        """Converts the SubtitleLine to SRT format string."""
        start_time = self.ms_to_timestamp(self.start)
        end_time = self.ms_to_timestamp(self.end)
        return f"{self.index}\n{start_time} --> {end_time}\n" + "\n".join(self.text) + "\n"

    @staticmethod
    def ms_to_timestamp(ms: int) -> str:
        """Converts milliseconds to SRT timestamp format."""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


class SRTOffsetAdjuster:
    def __init__(self, offset: int):
        self.offset = offset
        self.subtitles: List[SubtitleLine] = []

    def load_srt(self, filepath: str):
        """Reads the SRT file and parses it into SubtitleLine objects."""
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()

        blocks = content.strip().split('\n\n')
        for block in blocks:
            lines = block.splitlines()
            if len(lines) < 3:
                continue  # Skip invalid blocks

            index = int(lines[0])
            start, end = self.parse_timestamp(lines[1])
            text = lines[2:]

            # Adjust time with offset and only add if start is non-negative
            adjusted_start = start + self.offset
            adjusted_end = end + self.offset

            if adjusted_start >= 0:
                self.subtitles.append(SubtitleLine(index, adjusted_start, adjusted_end, text))

    @staticmethod
    def parse_timestamp(timestamp_line: str) -> (int, int):
        """Parses SRT timestamp format to milliseconds for start and end times."""
        match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})', timestamp_line)
        if not match:
            raise ValueError("Invalid timestamp format")

        start_time = (
            int(match.group(1)) * 3600000 +
            int(match.group(2)) * 60000 +
            int(match.group(3)) * 1000 +
            int(match.group(4))
        )
        end_time = (
            int(match.group(5)) * 3600000 +
            int(match.group(6)) * 60000 +
            int(match.group(7)) * 1000 +
            int(match.group(8))
        )
        return start_time, end_time

    def save_srt(self, filepath: str):
        """Writes the adjusted subtitles to a new SRT file, re-indexing them."""
        with open(filepath, 'w', encoding='utf-8') as file:
            for new_index, subtitle in enumerate(self.subtitles, start=1):
                subtitle.index = new_index  # Update index for each subtitle
                file.write(subtitle.to_srt_format() + "\n")


def main():
    parser = argparse.ArgumentParser(description="Adjust SRT subtitle timing by a specified offset.")
    parser.add_argument("input_file", type=str, help="Path to the input SRT file.")
    parser.add_argument("output_file", type=str, help="Path to save the output SRT file.")
    parser.add_argument("offset", type=int, help="Offset in milliseconds (positive or negative).")
    args = parser.parse_args()

    adjuster = SRTOffsetAdjuster(args.offset)
    adjuster.load_srt(args.input_file)
    adjuster.save_srt(args.output_file)
    print(f"Subtitle offset adjustment complete. Saved to {args.output_file}.")


if __name__ == "__main__":
    main()
