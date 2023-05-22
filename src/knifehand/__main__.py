"""Command-line interface."""
import os
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import click
import numpy as np
from click import Path
from moviepy.editor import ImageSequenceClip  # type: ignore
from moviepy.editor import VideoFileClip
from moviepy.editor import concatenate_videoclips
from numpy.typing import NDArray


def detect_cut_signature(
    frame: NDArray[np.uint32], required_pixels: int = 10, color_tolerance: int = 30
) -> bool:
    """Detects if the frame contains the cut signature.

    The cut signature is detected if the top-left corner has three color blocks
    in the order cyan, magenta, and yellow. The signature boundary is a 20x20
    pixel area, and there's an optional tolerance value to allow for tuning.

    Args:
        frame (NDArray[np.uint32]):
            The frame as a 3D numpy array (height, width, channels).
        required_pixels (int):
            How many pixels of each color to look for (default is 10).
        color_tolerance (int):
            The tolerance for color differences (default is 30).

    Returns:
        found_signature (bool):
            True if the frame contains a cut signature, False otherwise.
    """
    # Define the RGB values for cyan, magenta, and yellow
    cyan = np.array([0, 255, 255])
    magenta = np.array([255, 0, 255])
    yellow = np.array([255, 255, 0])

    # Get the top-left 20x20 pixels area
    region = frame[:20, :20, :]

    # Check if there are enough pixels matching each color within the given tolerance
    cyan_pixels = np.sum(np.all(np.abs(region - cyan) <= color_tolerance, axis=-1))
    magenta_pixels = np.sum(
        np.all(np.abs(region - magenta) <= color_tolerance, axis=-1)
    )
    yellow_pixels = np.sum(np.all(np.abs(region - yellow) <= color_tolerance, axis=-1))

    # If there are enough pixels for each color, consider it a cut.
    # NOTE: Wrapped in a ternary because np.bool upsets typeguard.
    found_signature: bool = (
        True
        if (
            cyan_pixels >= required_pixels
            and magenta_pixels >= required_pixels
            and yellow_pixels >= required_pixels
        )
        else False
    )

    return found_signature


def filter_cut(
    video: VideoFileClip, frame_filter: Callable[[NDArray[np.uint32]], bool]
) -> Tuple[VideoFileClip, List[Tuple[int, int, int]]]:  # pragma: no cover
    """Removes sections of a video indicated by `frame_filter`.

    Args:
        video (VideoFileClip):
            The video clip to process.
        frame_filter ( Callable[[numpy.ndarray], bool]):
            A function, returing a boolean if the frame should be cut from
            `video`. It should take the frame as a 3D numpy array.

    Returns:
        video (VideoFileClip):
            The processed video clip with any frames matching `frame_filter`
            removed from the clip.
        cuts (list[tuple[int, int, int]]):
            A list of cuts made to the video, used for reporting, specifically
            the start, end and length of each cut.
    """
    fps = video.fps
    cuts = []
    frames = []
    cut_frames = []
    cut_start = None

    # TODO: Split this out to make it testable, right now it's too ambagious.

    # Iterate over frames
    for i, frame in enumerate(video.iter_frames()):
        # Check for cut
        if frame_filter(frame):
            cut_frames.append(i)
            # Check if start of cut
            if cut_start is None:
                cut_start = i
        else:
            # If we were in a cut, this is the end
            if cut_start is not None:
                cuts.append((cut_start, i - 1, len(cut_frames)))
                cut_start = None
                cut_frames = []
            frames.append(frame)

    # Handle case where video ends with a cut
    if cut_start is not None:
        cuts.append((cut_start, i, len(cut_frames)))

    # Create new video without the cuts
    new_video = ImageSequenceClip(frames, fps=fps)

    return new_video, cuts


def load_video(video_path: str) -> Union[VideoFileClip, None]:  # pragma: no cover
    """Function to load a video using MoviePy.

    Args:
        video_path (str):
            Path to the video file.

    Returns:
        video (VideoFileClip):
            The video file as a VideoFileClip object.
    """
    try:
        video = VideoFileClip(video_path)
        return video
    except Exception as e:
        print(f"Error loading video: {e}")
        return None


@click.group()
def main() -> None:  # pragma: no cover
    """Knifehand - Slightly more precise than Axehand."""


@main.command()
@click.argument("video_path", type=Path(exists=True))
@click.option(
    "--output_dir",
    type=Path(exists=True, file_okay=False),
    default=".",
    help="Directory to output the processed video and cut info file.",
)
@click.option(
    "--intro_path",
    default=None,
    type=Path(exists=True),
    help="Path to the intro video file.",
)
@click.option(
    "--outro_path",
    default=None,
    type=Path(exists=True),
    help="Path to the outro video file.",
)
def process_video(
    video_path: str,
    output_dir: str,
    intro_path: Optional[str] = None,
    outro_path: Optional[str] = None,
) -> None:  # pragma: no cover
    """Cuts any flagged sections from a video, and optionally bookends it.

    Loads a video, cuts out anything that matches that signature, optionally
    appends intro and outro, and writes it to an output file.

    Output format is optimised for Youtube.
    """
    # Set up paths
    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    video_output_path = os.path.join(output_dir, f"edited_{base_filename}.mp4")
    cuts_output_path = os.path.join(output_dir, f"edited_{base_filename}.txt")

    # Load the main video
    main_video = load_video(video_path)

    # Cut out anything that matches detect_cut_signature
    main_video, cuts = filter_cut(main_video, detect_cut_signature)
    report = []
    with open(cuts_output_path, "w") as file:
        for start, end, length in cuts:
            start_time = start / main_video.fps
            end_time = end / main_video.fps
            report_line = f"{start_time:.2f} - {end_time:.2f} - Cut, {length} frames.\n"
            report.append(report_line)
            file.write(report_line)

    # List to hold all clips
    clips = []

    # Load and append intro if provided
    if intro_path is not None:
        intro = load_video(intro_path)
        clips.append(intro)

    # Append main video
    clips.append(main_video)

    # Load and append outro if provided
    if outro_path is not None:
        outro = load_video(outro_path)
        clips.append(outro)

    # Concatenate all clips
    final_clip = concatenate_videoclips(clips)

    # Write the final video to the output path
    final_clip.write_videofile(video_output_path, codec="libx264", audio_codec="aac")

    # Dump the report to console
    click.echo("\nSTATS FOR NERDS:")
    click.echo("".join(report))


if __name__ == "__main__":
    main(prog_name="knifehand")  # pragma: no cover
