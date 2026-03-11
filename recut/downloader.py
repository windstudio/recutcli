"""Download and merge m3u8 video streams."""

import subprocess
import urllib.request
from pathlib import Path

# Try to get ffmpeg from imageio-ffmpeg as fallback
_ffmpeg_path = None
try:
    import imageio_ffmpeg
    _ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass

# Shared ffmpeg installation message
FFMPEG_INSTALL_MSG = """ffmpeg is not installed. Please install it first.
  - Windows: winget install ffmpeg
  - macOS: brew install ffmpeg
  - Linux: apt install ffmpeg"""


def get_ffmpeg_path() -> str:
    """Get ffmpeg executable path, using imageio-ffmpeg as fallback."""
    global _ffmpeg_path
    if _ffmpeg_path:
        return _ffmpeg_path
    return "ffmpeg"


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        subprocess.run(
            [get_ffmpeg_path(), "-version"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def download_and_merge_m3u8(m3u8_url: str, output_path: Path, retries: int = 3) -> Path:
    """Download m3u8 stream and merge into a single video file.

    Args:
        m3u8_url: URL of the m3u8 playlist
        output_path: Path to save the merged video
        retries: Number of retry attempts on failure

    Returns:
        Path to the downloaded video file
    """
    output_path = Path(output_path)
    ffmpeg = get_ffmpeg_path()

    for attempt in range(retries):
        try:
            cmd = [
                ffmpeg,
                "-i", m3u8_url,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                "-y",  # Overwrite output
                str(output_path)
            ]
            # Show FFmpeg output so user can see download progress
            subprocess.run(cmd, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to download video after {retries} attempts")
            continue


def download_video(url: str, output_path: Path, retries: int = 3) -> Path:
    """Download video from URL directly.

    Args:
        url: URL of the video file (mp4, avi, etc.)
        output_path: Path to save the video
        retries: Number of retry attempts on failure

    Returns:
        Path to the downloaded video file

    Raises:
        RuntimeError: If download fails after all retries
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                output_path.write_bytes(response.read())
            return output_path
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to download video after {retries} attempts: {e}")
            continue

    return output_path
