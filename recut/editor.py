"""Video editing: cut, concatenate, and transcode."""

import subprocess
import tempfile
from pathlib import Path

from recut.analyzer import Scene
from recut.config import PlatformConfig
from recut.downloader import get_ffmpeg_path


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run FFmpeg command, raising on error."""
    subprocess.run(cmd, capture_output=True, check=True)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def cut_fragment(video_path: Path, fragment: Scene, output_path: Path) -> Path:
    """Cut a single fragment from video."""
    _run_ffmpeg([
        get_ffmpeg_path(), "-i", str(video_path),
        "-ss", format_timestamp(fragment.start),
        "-to", format_timestamp(fragment.end),
        "-c", "copy", "-y", str(output_path)
    ])
    return output_path


def concatenate_fragments(fragment_paths: list[Path], output_path: Path) -> Path:
    """Concatenate video fragments."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for path in fragment_paths:
            f.write(f"file '{path}'\n")
        list_file = f.name

    try:
        _run_ffmpeg([
            get_ffmpeg_path(), "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy", "-y", str(output_path)
        ])
    finally:
        Path(list_file).unlink()

    return output_path


def transcode_for_platform(video_path: Path, output_path: Path, config: PlatformConfig) -> Path:
    """Transcode video for social media platform."""
    scale_filter = f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease"
    pad_filter = f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2"

    _run_ffmpeg([
        get_ffmpeg_path(), "-i", str(video_path),
        "-vf", f"{scale_filter},{pad_filter}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", "-y", str(output_path)
    ])
    return output_path


def create_short(video_path: Path, fragments: list[Scene], output_path: Path, config: PlatformConfig) -> Path:
    """Create short video from selected fragments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Cut and concatenate fragments
        fragment_paths = []
        for i, frag in enumerate(fragments):
            frag_path = tmpdir / f"fragment_{i}.mp4"
            cut_fragment(video_path, frag, frag_path)
            fragment_paths.append(frag_path)

        concat_path = tmpdir / "concatenated.mp4"
        concatenate_fragments(fragment_paths, concat_path)

        # Transcode for platform
        transcode_for_platform(concat_path, output_path, config)

    return output_path


def extract_audio_for_mixing(video_path: Path, audio_path: Path) -> Path:
    """Extract audio from video for mixing (WAV format)."""
    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    _run_ffmpeg([
        get_ffmpeg_path(), "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        "-y", str(audio_path)
    ])
    return audio_path


def merge_video_audio_subtitle(
    video_path: Path,
    original_audio_path: Path,
    dubbing_audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    dubbing_volume: float = 1.0,
    original_volume: float = 0.3
) -> Path:
    """Merge video with audio tracks and subtitle.

    Uses -shortest to ensure output duration matches video length,
    trimming any excess audio if dubbing is longer than video.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare subtitle path for FFmpeg (handle Windows paths)
    subtitle_path_str = str(subtitle_path).replace("\\", "/")
    if len(subtitle_path_str) > 1 and subtitle_path_str[1] == ":":
        subtitle_path_str = subtitle_path_str[0] + "\\:" + subtitle_path_str[2:]

    subtitle_filter = f"subtitles='{subtitle_path_str}':force_style='Alignment=2,MarginV=60'"
    audio_filter = f"[1:a]volume={dubbing_volume}[voice];[2:a]volume={original_volume}[bg];[voice][bg]amix=inputs=2[aout]"

    _run_ffmpeg([
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-i", str(dubbing_audio_path),
        "-i", str(original_audio_path),
        "-filter_complex", audio_filter,
        "-vf", subtitle_filter,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",  # Output duration matches shortest input (video)
        "-y", str(output_path)
    ])

    return output_path
