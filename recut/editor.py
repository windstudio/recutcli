"""Video editing: cut, concatenate, and transcode."""

import tempfile
from pathlib import Path

from recut.analyzer import Scene
from recut.config import PlatformConfig, get_thumbnail_config
from recut.downloader import get_ffmpeg_path, run_ffmpeg


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run FFmpeg command, raising on error."""
    run_ffmpeg(cmd)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def cut_fragment(video_path: Path, fragment: Scene, output_path: Path) -> Path:
    """Cut a single fragment from video with proper re-encoding.

    Re-encoding ensures accurate cuts at non-keyframe positions.
    """
    _run_ffmpeg([
        get_ffmpeg_path(),
        "-ss", format_timestamp(fragment.start),  # Input seeking (faster)
        "-i", str(video_path),
        "-t", format_timestamp(fragment.end - fragment.start),  # Duration instead of -to
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-r", "30",  # Force consistent 30fps
        "-y", str(output_path)
    ])
    return output_path


def concatenate_fragments(fragment_paths: list[Path], output_path: Path) -> Path:
    """Concatenate video fragments with consistent encoding.

    Re-encoding ensures all fragments have matching parameters.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for path in fragment_paths:
            f.write(f"file '{path}'\n")
        list_file = f.name

    try:
        _run_ffmpeg([
            get_ffmpeg_path(), "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-r", "30",  # Consistent 30fps
            "-y", str(output_path)
        ])
    finally:
        Path(list_file).unlink()

    return output_path


def create_short(video_path: Path, fragments: list[Scene], output_path: Path, config: PlatformConfig) -> Path:
    """Create short video from selected fragments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Cut fragments (now with re-encoding)
        fragment_paths = []
        for i, frag in enumerate(fragments):
            frag_path = tmpdir / f"fragment_{i}.mp4"
            cut_fragment(video_path, frag, frag_path)
            fragment_paths.append(frag_path)

        concat_path = tmpdir / "concatenated.mp4"
        concatenate_fragments(fragment_paths, concat_path)

        # Only resize/pad for platform, no re-encoding needed for quality
        scale_filter = f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease"
        pad_filter = f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2"

        _run_ffmpeg([
            get_ffmpeg_path(), "-i", str(concat_path),
            "-vf", f"{scale_filter},{pad_filter}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "copy",  # Audio already encoded
            "-movflags", "+faststart", "-y", str(output_path)
        ])

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


def _merge_with_audio(
    video_path: Path,
    dubbing_audio_path: Path,
    original_audio_path: Path,
    subtitle_filter: str,
    output_path: Path,
    dubbing_volume: float,
    original_volume: float,
    logo_path: Path | None
) -> None:
    """Merge video with mixed audio and subtitle filter, optional logo overlay.

    Shared by the thumbnail/no-thumbnail merge paths; differs only in the
    base video input.
    """
    audio_filter = f"[1:a]volume={dubbing_volume}[voice];[2:a]volume={original_volume}[bg];[voice][bg]amix=inputs=2:duration=first[aout]"

    if logo_path:
        # Overlay logo on video (input 0: video, input 3: logo), then apply subtitles
        # Apply 70% opacity to logo
        video_filter = f"[3:v]format=rgba,colorchannelmixer=aa=0.7[logo];[0:v][logo]overlay=40:40[vl];[vl]{subtitle_filter}[vout]"
        _run_ffmpeg([
            get_ffmpeg_path(),
            "-i", str(video_path),
            "-i", str(dubbing_audio_path),
            "-i", str(original_audio_path),
            "-i", str(logo_path),
            "-filter_complex", f"{audio_filter};{video_filter}",
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",  # Trim video to match audio duration
            "-y", str(output_path)
        ])
    else:
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
            "-shortest",  # Trim video to match audio duration
            "-y", str(output_path)
        ])


def _build_subtitle_filter(subtitle_path_str: str, subtitle_font_size: int) -> str:
    """Build the subtitles filter string with forced style."""
    return f"subtitles='{subtitle_path_str}':force_style='Alignment=2,MarginV=60,FontSize={subtitle_font_size}'"


def merge_video_audio_subtitle(
    video_path: Path,
    original_audio_path: Path,
    dubbing_audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    dubbing_volume: float = 1.0,
    original_volume: float = 0.2,
    thumbnail_path: Path | None = None,
    logo_path: Path | None = None
) -> Path:
    """Merge video with audio tracks, subtitle, and optional thumbnail/logo overlay.

    Args:
        video_path: Path to the base video
        original_audio_path: Path to original audio extracted from video
        dubbing_audio_path: Path to dubbing audio
        subtitle_path: Path to SRT subtitle file
        output_path: Path for output video
        dubbing_volume: Volume for dubbing audio (default 1.0)
        original_volume: Volume for original background audio (default 0.2)
        thumbnail_path: Optional path to thumbnail image to prepend as first frame (0.5s)
        logo_path: Optional path to logo image to overlay throughout video

    Returns:
        Path to the output video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get subtitle font size from config
    subtitle_font_size = get_thumbnail_config().font_size_subtitle

    # Prepare subtitle path for FFmpeg (handle Windows paths)
    subtitle_path_str = str(subtitle_path).replace("\\", "/")
    if len(subtitle_path_str) > 1 and subtitle_path_str[1] == ":":
        subtitle_path_str = subtitle_path_str[0] + "\\:" + subtitle_path_str[2:]

    # Check if logo exists
    has_logo = logo_path and Path(logo_path).exists()
    has_thumbnail = thumbnail_path and Path(thumbnail_path).exists()

    thumbnail_duration = 0.5  # Fixed 0.5 seconds

    if has_thumbnail:
        # Use temporary directory for thumbnail processing
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            _process_with_thumbnail(
                video_path, thumbnail_path, tmpdir, thumbnail_duration,
                dubbing_audio_path, original_audio_path, subtitle_path_str,
                output_path, dubbing_volume, original_volume, has_logo, logo_path
            )
    else:
        # No thumbnail, process directly
        subtitle_filter = _build_subtitle_filter(subtitle_path_str, subtitle_font_size)
        _merge_with_audio(
            video_path, dubbing_audio_path, original_audio_path,
            subtitle_filter, output_path, dubbing_volume, original_volume,
            logo_path if has_logo else None
        )

    return output_path


def _process_with_thumbnail(
    video_path: Path,
    thumbnail_path: Path,
    tmpdir: Path,
    thumbnail_duration: float,
    dubbing_audio_path: Path,
    original_audio_path: Path,
    subtitle_path_str: str,
    output_path: Path,
    dubbing_volume: float,
    original_volume: float,
    has_logo: bool,
    logo_path: Path | None
) -> Path:
    """Process video with thumbnail prepended."""
    # Get subtitle font size from config
    subtitle_font_size = get_thumbnail_config().font_size_subtitle

    # Prepend thumbnail as first frame (0.5s)
    thumbnail_video = tmpdir / "thumbnail_video.mp4"
    _run_ffmpeg([
        get_ffmpeg_path(),
        "-loop", "1",
        "-i", str(thumbnail_path),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(thumbnail_duration),
        "-r", "30",  # Match video frame rate
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-y", str(thumbnail_video)
    ])

    # Concatenate thumbnail with main video
    concat_video = tmpdir / "concat_video.mp4"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(f"file '{thumbnail_video.resolve()}'\n")
        f.write(f"file '{video_path.resolve()}'\n")
        list_file = f.name

    try:
        _run_ffmpeg([
            get_ffmpeg_path(), "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-r", "30",  # Maintain consistent frame rate
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-y", str(concat_video)
        ])
    finally:
        Path(list_file).unlink()

    # Apply subtitles (timestamps already include offset if thumbnail was generated)
    subtitle_filter = _build_subtitle_filter(subtitle_path_str, subtitle_font_size)

    _merge_with_audio(
        concat_video, dubbing_audio_path, original_audio_path,
        subtitle_filter, output_path, dubbing_volume, original_volume,
        logo_path if has_logo else None
    )

    return output_path


def append_outro(video_path: Path, outro_path: Path, output_path: Path) -> Path:
    """Append outro video to main video using FFmpeg concat.

    The outro video keeps its original audio. No additional filters applied.

    Args:
        video_path: Path to the main video (with dubbing, subtitles, logo)
        outro_path: Path to the outro video
        output_path: Path for output video

    Returns:
        Path to the output video

    Raises:
        RuntimeError: If FFmpeg fails
    """
    output_path = Path(output_path)
    video_path = Path(video_path)
    outro_path = Path(outro_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use FFmpeg with two inputs and concat filter
    # Setsar is needed to normalize SAR (Sample Aspect Ratio) between videos
    _run_ffmpeg([
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-i", str(outro_path),
        "-filter_complex",
        "[0:v]format=yuv420p,setsar=1[v0];[1:v]format=yuv420p,setsar=1[v1];[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[outv][outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-y", str(output_path)
    ])

    return output_path
