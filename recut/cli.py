# recut/cli.py
"""Command-line interface for recut."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from urllib.parse import urlparse, unquote
import re

from recut import __version__
from recut.analyzer import detect_scenes, select_top_fragments, Scene, get_video_duration, save_scenes_to_json, load_scenes_from_json
from recut.config import get_platform_config, PLATFORMS, load_dotenv_config, get_api_config, get_tts_config, get_thumbnail_config
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, download_video, FFMPEG_INSTALL_MSG
from recut.editor import create_short, extract_audio_for_mixing, merge_video_audio_subtitle
from recut.scraper import fetch_kickstarter_page, extract_m3u8_url
from recut.transcriber import extract_audio, transcribe_audio, save_transcript
from recut.translator import translate_and_generate_metadata, save_chinese_script, parse_chinese_script
from recut.tts import generate_audio, get_audio_duration
from recut.subtitle import generate_srt, align_subtitle
from recut.thumbnail import generate_thumbnail
from recut.checkpoint import (
    get_checkpoint_dir,
    get_name_from_path,
    check_progress,
    save_metadata,
    load_metadata,
    create_metadata,
)


def _extract_filename_from_url(url: str) -> str:
    """Extract a valid filename from URL path's last segment.

    Example:
        https://example.com/projects/user/my-project-name?ref=xxx
        -> my-project-name
    """
    parsed = urlparse(url)
    # Get path and remove trailing slash
    path = unquote(parsed.path).rstrip('/')
    # Get last segment
    last_segment = path.split('/')[-1] if path else 'output'
    # Sanitize: keep only alphanumeric, hyphen, underscore
    filename = re.sub(r'[^\w\-]', '-', last_segment)
    return filename or 'output'


def _exit_on_error(message: str, error: Exception | None = None) -> None:
    """Print error message and exit."""
    detail = f": {error}" if error else ""
    click.echo(f"Error {message}{detail}", err=True)
    raise SystemExit(1)


@click.command()
@click.argument("url", required=False)
@click.option("-o", "--output", default=None, help="Output video file path (default: auto-generated from URL)")
@click.option("--platform", type=click.Choice(list(PLATFORMS.keys())), default="tiktok", help="Target platform")
@click.option("--scene-threshold", type=float, default=0.3, help="Scene change detection threshold")
@click.option("--video-url", help="Direct video URL (mp4, avi, m3u8, etc.)")
@click.option("--tts-engine", type=click.Choice(["edge", "coqui", "minimax"]), default=None, help="TTS engine")
@click.option("--duration", type=int, default=None, help="Video duration in seconds (default: 30)")
@click.option("--title", help="English title from video page (optional)")
@click.option("--chs-title", help="Chinese title (skip LLM title generation)")
@click.option("--image", type=str, help="主素材图路径或URL（用于封面图生成）")
@click.option("--pause-on-chs-script", is_flag=True, help="Pause after generating Chinese script for user review")
@click.option("--resume", default=None, help="Resume from checkpoint (directory or .md file path)")
@click.version_option(version=__version__)
def main(
    url: str | None,
    output: str | None,
    platform: str,
    scene_threshold: float,
    video_url: str | None,
    tts_engine: str | None,
    duration: int | None,
    title: str | None,
    chs_title: str | None,
    image: str | None,
    pause_on_chs_script: bool,
    resume: str | None,
):
    """Download video from URL and create a short social media video with Chinese dubbing.

    With --pause-on-chs-script: Pause after generating Chinese script for user review.
    With --resume: Continue from a paused checkpoint.
    """
    load_dotenv_config()

    # Handle resume mode
    if resume:
        return handle_resume(resume, tts_engine=tts_engine)

    # URL is required for non-resume mode
    if not url:
        _exit_on_error("URL is required when not using --resume")

    # Convert literal \n to actual newlines in chs_title
    if chs_title:
        chs_title = chs_title.replace('\\n', '\n')

    api_config = get_api_config()
    if not api_config.llm_api_key:
        _exit_on_error("LLM_API_KEY not set. Please set it in .env file.")

    if not check_ffmpeg():
        _exit_on_error(FFMPEG_INSTALL_MSG)

    config = get_platform_config(platform, duration=duration)
    tts_config = get_tts_config()

    # Generate default output path from URL if not specified
    if not output:
        filename = _extract_filename_from_url(url)
        output = f"{filename}.mp4"

    # Prepend 'output' base directory
    output_path = Path("output") / output

    # Setup output structure
    output_parent = output_path.parent
    output_stem = output_path.stem
    checkpoint_dir = get_checkpoint_dir(output_path)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Save initial metadata
    metadata = create_metadata(
        source_url=url,
        platform=platform,
        scene_threshold=scene_threshold,
        duration=config.max_duration,
        title=title,
        chs_title=chs_title,
        image=image,
        tts_engine=tts_engine,
    )
    metadata_path = checkpoint_dir / f"{output_stem}_metadata.json"
    save_metadata(metadata, metadata_path)

    # Get video URL
    if not video_url:
        click.echo(f"Fetching Kickstarter page: {url}")
        try:
            html = fetch_kickstarter_page(url)
        except Exception as e:
            _exit_on_error("fetching page", e)

        click.echo("Extracting video URL...")
        video_url = extract_m3u8_url(html)
        if not video_url:
            _exit_on_error("Could not find video URL in page")

    # Phase 1: Download video
    raw_video_path = checkpoint_dir / f"{output_stem}_raw.mp4"
    if raw_video_path.exists():
        click.echo(f"Skipping download: {raw_video_path} already exists")
    else:
        click.echo("Downloading video...")
        try:
            parsed_url = urlparse(video_url)
            if parsed_url.path.endswith(".m3u8"):
                download_and_merge_m3u8(video_url, raw_video_path)
            else:
                download_video(video_url, raw_video_path)
        except Exception as e:
            _exit_on_error("downloading video", e)

    # Phase 2: Analyze scenes
    scenes_path = checkpoint_dir / f"{output_stem}_scenes.json"
    if scenes_path.exists():
        click.echo(f"Loading scenes from: {scenes_path}")
        fragments = load_scenes_from_json(scenes_path)
    else:
        click.echo("Analyzing scenes...")
        fragments = detect_scenes(raw_video_path, threshold=scene_threshold)
        if not fragments:
            click.echo("Warning: No scenes detected. Using fixed intervals.")
            video_duration = get_video_duration(raw_video_path)
            fragments = [
                Scene(start=i * 5.0, end=min((i + 1) * 5.0, video_duration))
                for i in range(int(video_duration / 5.0))
            ]
        save_scenes_to_json(fragments, scenes_path)
    click.echo(f"Found {len(fragments)} scenes.")

    # Phase 3: Transcribe
    script_path = checkpoint_dir / f"{output_stem}_script.md"
    if script_path.exists():
        click.echo(f"Loading transcript from: {script_path}")
        transcript = script_path.read_text(encoding="utf-8")
    else:
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            audio_path = tmpdir / "audio.wav"
            click.echo("Extracting audio...")
            try:
                extract_audio(raw_video_path, audio_path)
            except Exception as e:
                _exit_on_error("extracting audio", e)

            click.echo("Transcribing with Whisper...")
            try:
                transcript = transcribe_audio(audio_path)
            except Exception as e:
                _exit_on_error("transcribing audio", e)

        click.echo(f"Saving transcript to: {script_path}")
        try:
            save_transcript(transcript, script_path)
        except Exception as e:
            _exit_on_error("saving transcript", e)

    # Phase 4: Translate and generate Chinese script
    chs_script_path = output_parent / f"{output_stem}.md"
    if chs_script_path.exists():
        click.echo(f"Loading Chinese script from: {chs_script_path}")
        metadata_from_script = parse_chinese_script(chs_script_path)
        chinese_script = metadata_from_script["transcript"]
        # Use loaded metadata
        final_title = metadata_from_script.get("title", "")
        final_tags = metadata_from_script.get("tags", [])
    else:
        click.echo("Generating Chinese script with metadata...")
        try:
            metadata_result = translate_and_generate_metadata(
                transcript,
                api_key=api_config.llm_api_key,
                base_url=api_config.llm_api_url,
                model=api_config.llm_model,
                duration=config.max_duration,
                english_title=title,
                chs_title=chs_title,
                tts_engine=tts_engine
            )
        except Exception as e:
            _exit_on_error("generating metadata", e)

        chinese_script = metadata_result["transcript"]
        final_title = metadata_result["title"]
        final_tags = metadata_result["tags"]

        click.echo(f"Saving Chinese script to: {chs_script_path}")
        try:
            save_chinese_script(chs_script_path, metadata_result, source_url=url)
        except Exception as e:
            _exit_on_error("saving Chinese script", e)

    # Check for pause mode
    if pause_on_chs_script:
        click.echo(f"\n{'='*50}")
        click.echo(f"Chinese script saved to: {chs_script_path}")
        click.echo("Please review and edit the script if needed.")
        click.echo(f"To continue, run: recut --resume {chs_script_path}")
        click.echo(f"{'='*50}\n")
        return

    # Continue with remaining phases
    _run_remaining_phases(
        checkpoint_dir=checkpoint_dir,
        output_stem=output_stem,
        output_path=output_path,
        raw_video_path=raw_video_path,
        fragments=fragments,
        chinese_script=chinese_script,
        config=config,
        platform=platform,
        tts_engine=tts_engine,
        tts_config=tts_config,
        title=final_title,
        image=image,
        api_config=api_config,
    )


def handle_resume(resume_path: str, tts_engine: str | None = None) -> None:
    """Handle resume from checkpoint.

    Args:
        resume_path: Path to checkpoint directory or .md file
        tts_engine: Optional TTS engine override
    """
    path = Path(resume_path)

    # Determine checkpoint directory and name
    if path.is_file() and path.suffix == ".md":
        chs_script_path = path
        name = path.stem
        checkpoint_dir = path.parent / name
    else:
        checkpoint_dir = path
        name = get_name_from_path(path)
        chs_script_path = checkpoint_dir.parent / f"{name}.md"

    if not checkpoint_dir.exists():
        _exit_on_error(f"Checkpoint directory not found: {checkpoint_dir}")

    if not chs_script_path.exists():
        _exit_on_error(f"Chinese script not found: {chs_script_path}")

    # Load metadata
    metadata_path = checkpoint_dir / f"{name}_metadata.json"
    if not metadata_path.exists():
        _exit_on_error(f"Metadata not found: {metadata_path}")

    metadata = load_metadata(metadata_path)

    # Check progress
    progress = check_progress(checkpoint_dir, name)
    click.echo(f"Checkpoint progress: {progress}")

    # Load required files
    raw_video_path = checkpoint_dir / f"{name}_raw.mp4"
    if not raw_video_path.exists():
        _exit_on_error(f"Raw video not found: {raw_video_path}")

    scenes_path = checkpoint_dir / f"{name}_scenes.json"
    if not scenes_path.exists():
        _exit_on_error(f"Scenes file not found: {scenes_path}")
    fragments = load_scenes_from_json(scenes_path)

    # Parse user-edited Chinese script
    click.echo(f"Loading Chinese script from: {chs_script_path}")
    script_data = parse_chinese_script(chs_script_path)
    chinese_script = script_data["transcript"]
    title = script_data.get("title", "")
    tags = script_data.get("tags", [])

    # Restore config from metadata
    platform = metadata.get("platform", "tiktok")
    duration = metadata.get("duration", 30)
    config = get_platform_config(platform, duration=duration)
    image = metadata.get("image")
    # Use command-line tts_engine if provided, otherwise restore from metadata
    saved_tts_engine = metadata.get("tts_engine")
    if tts_engine is None and saved_tts_engine:
        tts_engine = saved_tts_engine

    # Setup output path
    output_path = checkpoint_dir.parent / f"{name}.mp4"

    api_config = get_api_config()
    if not api_config.llm_api_key:
        _exit_on_error("LLM_API_KEY not set. Please set it in .env file.")

    if not check_ffmpeg():
        _exit_on_error(FFMPEG_INSTALL_MSG)

    tts_config = get_tts_config()

    # Run remaining phases
    _run_remaining_phases(
        checkpoint_dir=checkpoint_dir,
        output_stem=name,
        output_path=output_path,
        raw_video_path=raw_video_path,
        fragments=fragments,
        chinese_script=chinese_script,
        config=config,
        platform=platform,
        tts_engine=tts_engine,
        tts_config=tts_config,
        title=title,
        image=image,
        api_config=api_config,
    )


def _run_remaining_phases(
    checkpoint_dir: Path,
    output_stem: str,
    output_path: Path,
    raw_video_path: Path,
    fragments: list[Scene],
    chinese_script: str,
    config,
    platform: str,
    tts_engine: str | None,
    tts_config,
    title: str,
    image: str | None,
    api_config,
) -> None:
    """Run remaining phases after Chinese script is ready.

    Phases:
    - TTS generation
    - Fragment selection
    - Video editing
    - Subtitle generation
    - Thumbnail generation
    - Final merge
    """
    output_parent = output_path.parent

    # Phase 5: Generate TTS
    dubbing_path = checkpoint_dir / f"{output_stem}_dubbing.wav"
    if dubbing_path.exists():
        click.echo(f"Skipping TTS: {dubbing_path} already exists")
    else:
        click.echo(f"Generating Chinese TTS audio (engine: {tts_engine or tts_config.engine})...")
        try:
            generate_audio(chinese_script, dubbing_path, engine=tts_engine)
        except Exception as e:
            _exit_on_error("generating TTS", e)

    # Get audio duration
    dubbing_duration = get_audio_duration(dubbing_path)
    click.echo(f"Dubbing audio duration: {dubbing_duration:.1f}s")

    # Phase 6: Select fragments
    # Use max of dubbing duration and target duration to ensure video is long enough
    video_target_duration = max(dubbing_duration, config.max_duration)
    click.echo(f"Selecting best fragments for {video_target_duration:.1f}s target...")
    selected = select_top_fragments(fragments, target_duration=video_target_duration) or fragments
    total_duration = sum(f.end - f.start for f in selected)
    click.echo(f"Selected {len(selected)} fragments ({total_duration:.1f}s total)")

    # Phase 7: Create short video
    nodub_video_path = checkpoint_dir / f"{output_stem}_nodub.mp4"
    if nodub_video_path.exists():
        click.echo(f"Skipping video editing: {nodub_video_path} already exists")
    else:
        click.echo(f"Creating short video for {platform}...")
        create_short(raw_video_path, selected, nodub_video_path, config)

    # Phase 8: Generate subtitles
    srt_path = checkpoint_dir / f"{output_stem}.srt"
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        if srt_path.exists():
            click.echo(f"Skipping subtitle generation: {srt_path} already exists")
        else:
            click.echo("Generating subtitles...")
            raw_srt_path = tmpdir / "subtitle.srt"
            try:
                generate_srt(dubbing_path, raw_srt_path, model=tts_config.whisper_model)
            except Exception as e:
                _exit_on_error("generating subtitles", e)

            # Align subtitles with offset if title exists (thumbnail will be generated)
            click.echo("Aligning subtitles...")
            subtitle_offset = 0.5 if title else 0.0
            try:
                align_subtitle(raw_srt_path, chinese_script, srt_path, time_offset=subtitle_offset)
            except Exception as e:
                _exit_on_error("aligning subtitles", e)

        # Phase 9: Generate thumbnail
        thumbnail_path = checkpoint_dir / f"{output_stem}_thumb.jpg"
        if thumbnail_path.exists():
            click.echo(f"Skipping thumbnail: {thumbnail_path} already exists")
        else:
            click.echo("Generating thumbnail...")

            # Handle image parameter
            image_path = None
            if image:
                if image.startswith(("http://", "https://")):
                    import urllib.request
                    downloaded_image = tmpdir / "cover_image.jpg"
                    try:
                        request = urllib.request.Request(image, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(request, timeout=30) as response:
                            downloaded_image.write_bytes(response.read())
                        click.echo(f"Downloaded cover image to: {downloaded_image}")
                        image_path = downloaded_image
                    except Exception as e:
                        click.echo(f"Warning: Failed to download cover image: {e}")
                else:
                    local_image = Path(image)
                    if local_image.exists():
                        image_path = local_image
                    else:
                        click.echo(f"Warning: Image file not found: {image}")

            try:
                generate_thumbnail(
                    video_path=raw_video_path,
                    title=title,
                    output_path=thumbnail_path,
                    platform=platform,
                    image_path=image_path
                )
            except RuntimeError as e:
                click.echo(f"Warning: Failed to generate thumbnail: {e}")

        # Phase 10: Merge final video
        click.echo("Extracting original audio for mixing...")
        original_audio_path = tmpdir / "original.wav"
        try:
            extract_audio_for_mixing(nodub_video_path, original_audio_path)
        except Exception as e:
            _exit_on_error("extracting original audio", e)

        click.echo("Merging video with dubbing and subtitles...")

        # Get logo path from config
        thumbnail_config = get_thumbnail_config()
        logo_path = Path(thumbnail_config.logo_path) if thumbnail_config.logo_path else None

        try:
            merge_video_audio_subtitle(
                nodub_video_path, original_audio_path, dubbing_path, srt_path, output_path,
                thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
                logo_path=logo_path
            )
        except Exception as e:
            _exit_on_error("merging video", e)

    click.echo(f"Done! Output saved to: {output_path}")


if __name__ == "__main__":
    main()
