"""Download and merge m3u8 video streams."""

import subprocess
from pathlib import Path

# Try to get ffmpeg from imageio-ffmpeg as fallback
_ffmpeg_path = None
try:
    import imageio_ffmpeg
    _ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass


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
    if not check_ffmpeg():
        raise RuntimeError(
            "ffmpeg is not installed. Please install it first.\n"
            "  - Windows: winget install ffmpeg\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Linux: apt install ffmpeg"
        )

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
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to download video after {retries} attempts: {e.stderr.decode()}")
            continue
