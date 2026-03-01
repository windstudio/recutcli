"""Video editing: cut, concatenate, and transcode."""

import subprocess
import tempfile
from pathlib import Path

from recut.analyzer import Scene
from recut.config import PlatformConfig
from recut.downloader import get_ffmpeg_path


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def cut_fragment(video_path: Path, fragment: Scene, output_path: Path) -> Path:
    """Cut a single fragment from video.

    Args:
        video_path: Source video path
        fragment: Scene to extract
        output_path: Output file path

    Returns:
        Path to the extracted fragment
    """
    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-ss", format_timestamp(fragment.start),
        "-to", format_timestamp(fragment.end),
        "-c", "copy",
        "-y",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def concatenate_fragments(fragment_paths: list[Path], output_path: Path) -> Path:
    """Concatenate video fragments.

    Args:
        fragment_paths: List of fragment file paths
        output_path: Output file path

    Returns:
        Path to the concatenated video
    """
    # Create file list for ffmpeg
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for path in fragment_paths:
            f.write(f"file '{path}'\n")
        list_file = f.name

    try:
        cmd = [
            get_ffmpeg_path(),
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "-y",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    finally:
        Path(list_file).unlink()

    return output_path


def transcode_for_platform(video_path: Path, output_path: Path, config: PlatformConfig) -> Path:
    """Transcode video for social media platform.

    Args:
        video_path: Source video path
        output_path: Output file path
        config: Platform configuration

    Returns:
        Path to the transcoded video
    """
    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-vf", f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease,pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def create_short(
    video_path: Path,
    fragments: list[Scene],
    output_path: Path,
    config: PlatformConfig
) -> Path:
    """Create short video from selected fragments.

    Args:
        video_path: Source video path
        fragments: Selected fragments to include
        output_path: Final output path
        config: Platform configuration

    Returns:
        Path to the final video
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Cut each fragment
        fragment_paths = []
        for i, frag in enumerate(fragments):
            frag_path = tmpdir / f"fragment_{i}.mp4"
            cut_fragment(video_path, frag, frag_path)
            fragment_paths.append(frag_path)

        # Concatenate fragments
        concat_path = tmpdir / "concatenated.mp4"
        concatenate_fragments(fragment_paths, concat_path)

        # Transcode for platform
        transcode_for_platform(concat_path, output_path, config)

    return output_path
