# recut/cli.py
"""Command-line interface for recut."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from urllib.parse import urlparse

from recut import __version__
from recut.analyzer import detect_scenes, select_top_fragments, Scene, get_video_duration
from recut.config import get_platform_config, PLATFORMS, load_dotenv_config, get_api_config, get_tts_config, get_thumbnail_config
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, download_video, FFMPEG_INSTALL_MSG
from recut.editor import create_short, extract_audio_for_mixing, merge_video_audio_subtitle
from recut.scraper import fetch_kickstarter_page, extract_m3u8_url
from recut.transcriber import extract_audio, transcribe_audio, save_transcript
from recut.translator import translate_and_generate_metadata, save_chinese_script
from recut.tts import generate_audio, get_audio_duration
from recut.subtitle import generate_srt, align_subtitle
from recut.thumbnail import generate_thumbnail


def _exit_on_error(message: str, error: Exception | None = None) -> None:
    """Print error message and exit."""
    detail = f": {error}" if error else ""
    click.echo(f"Error {message}{detail}", err=True)
    raise SystemExit(1)


@click.command()
@click.argument("url")
@click.option("-o", "--output", required=True, help="Output video file path")
@click.option("--platform", type=click.Choice(list(PLATFORMS.keys())), default="tiktok", help="Target platform")
@click.option("--scene-threshold", type=float, default=0.3, help="Scene change detection threshold")
@click.option("--video-url", help="Direct video URL (mp4, avi, m3u8, etc.)")
@click.option("--tts-engine", type=click.Choice(["edge", "coqui", "piper"]), default=None, help="TTS engine")
@click.option("--duration", type=int, default=None, help="Video duration in seconds (default: 30)")
@click.option("--title", help="English title from video page (optional)")
@click.option("--chs-title", help="Chinese title (skip LLM title generation)")
@click.option("--image", type=str, help="主素材图路径或URL（用于封面图生成）")
@click.version_option(version=__version__)
def main(
    url: str,
    output: str,
    platform: str,
    scene_threshold: float,
    video_url: str | None,
    tts_engine: str | None,
    duration: int | None,
    title: str | None,
    chs_title: str | None,
    image: str | None
):
    """Download video from URL and create a short social media video with Chinese dubbing."""
    load_dotenv_config()

    # Convert literal \n to actual newlines in chs_title
    if chs_title:
        chs_title = chs_title.replace('\\n', '\n')

    api_config = get_api_config()
    if not api_config.llm_api_key:
        _exit_on_error("LLM_API_KEY not set. Please set it in .env file.")

    if not check_ffmpeg():
        _exit_on_error(FFMPEG_INSTALL_MSG)

    output_path = Path(output)
    config = get_platform_config(platform, duration=duration)
    tts_config = get_tts_config()

    # Define output structure early
    output_parent = output_path.parent
    output_stem = output_path.stem
    intermediate_dir = output_parent / output_stem
    intermediate_dir.mkdir(parents=True, exist_ok=True)

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

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        downloaded_video = tmpdir / "downloaded.mp4"

        # Download video
        click.echo("Downloading video...")
        try:
            # Use urlparse to handle URLs with query parameters correctly
            parsed_url = urlparse(video_url)
            if parsed_url.path.endswith(".m3u8"):
                download_and_merge_m3u8(video_url, downloaded_video)
            else:
                download_video(video_url, downloaded_video)
        except Exception as e:
            _exit_on_error("downloading video", e)

        # Analyze scenes
        click.echo("Analyzing scenes...")
        fragments = detect_scenes(downloaded_video, threshold=scene_threshold)
        if not fragments:
            click.echo("Warning: No scenes detected. Using fixed intervals.")
            video_duration = get_video_duration(downloaded_video)
            fragments = [
                Scene(start=i * 5.0, end=min((i + 1) * 5.0, video_duration))
                for i in range(int(video_duration / 5.0))
            ]
        click.echo(f"Found {len(fragments)} scenes.")

        # Transcribe
        click.echo("Extracting audio...")
        audio_path = tmpdir / "audio.wav"
        try:
            extract_audio(downloaded_video, audio_path)
        except Exception as e:
            _exit_on_error("extracting audio", e)

        click.echo("Transcribing with Whisper...")
        try:
            transcript = transcribe_audio(audio_path)
        except Exception as e:
            _exit_on_error("transcribing audio", e)

        # Save transcript
        script_path = intermediate_dir / f"{output_stem}_script.md"
        click.echo(f"Saving transcript to: {script_path}")
        try:
            save_transcript(transcript, script_path)
        except Exception as e:
            _exit_on_error("saving transcript", e)

        # Translate to Chinese and generate metadata
        click.echo("Generating Chinese script with metadata...")
        try:
            metadata = translate_and_generate_metadata(
                transcript,
                api_key=api_config.llm_api_key,
                base_url=api_config.llm_api_url,
                model=api_config.llm_model,
                duration=config.max_duration,
                english_title=title,
                chs_title=chs_title
            )
        except Exception as e:
            _exit_on_error("generating metadata", e)

        chs_script_path = output_parent / f"{output_stem}.md"
        click.echo(f"Saving Chinese script to: {chs_script_path}")
        try:
            save_chinese_script(chs_script_path, metadata, source_url=url)
        except Exception as e:
            _exit_on_error("saving Chinese script", e)

        # Extract transcript for TTS
        chinese_script = metadata["transcript"]

        # Generate TTS
        click.echo(f"Generating Chinese TTS audio (engine: {tts_engine or tts_config.engine})...")
        dubbing_path = tmpdir / "dubbing.wav"
        try:
            generate_audio(chinese_script, dubbing_path, engine=tts_engine)
        except Exception as e:
            _exit_on_error("generating TTS", e)

        # Get audio duration and select fragments based on it
        dubbing_duration = get_audio_duration(dubbing_path)
        click.echo(f"Dubbing audio duration: {dubbing_duration:.1f}s")

        click.echo("Selecting best fragments based on dubbing duration...")
        selected = select_top_fragments(fragments, target_duration=dubbing_duration) or fragments
        total_duration = sum(f.end - f.start for f in selected)
        click.echo(f"Selected {len(selected)} fragments ({total_duration:.1f}s total)")

        # Create short video
        click.echo(f"Creating short video for {platform}...")
        nodub_video_path = intermediate_dir / f"{output_stem}_nodub.mp4"
        create_short(downloaded_video, selected, nodub_video_path, config)

        dubbing_output_path = intermediate_dir / f"{output_stem}_dubbing.wav"
        click.echo(f"Saving dubbing audio to: {dubbing_output_path}")
        shutil.copy2(dubbing_path, dubbing_output_path)

        # Generate subtitles
        click.echo("Generating subtitles...")
        srt_path = tmpdir / "subtitle.srt"
        try:
            generate_srt(dubbing_path, srt_path, model=tts_config.whisper_model)
        except Exception as e:
            _exit_on_error("generating subtitles", e)

        # Generate thumbnail from original video's first frame or main image
        click.echo("Generating thumbnail...")
        thumbnail_path = tmpdir / "thumbnail.jpg"

        # Handle image parameter: download if URL, use directly if local path
        if image:
            if image.startswith(("http://", "https://")):
                import urllib.request
                image_path = tmpdir / "cover_image.jpg"
                try:
                    # Add User-Agent header to avoid 403 Forbidden
                    request = urllib.request.Request(image, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(request, timeout=30) as response:
                        image_path.write_bytes(response.read())
                    click.echo(f"Downloaded cover image to: {image_path}")
                except Exception as e:
                    click.echo(f"Warning: Failed to download cover image: {e}")
                    image_path = None
            else:
                image_path = Path(image)
        else:
            image_path = None

        try:
            generate_thumbnail(
                video_path=downloaded_video,
                title=metadata["title"],
                output_path=thumbnail_path,
                platform=platform,
                image_path=image_path
            )
        except RuntimeError as e:
            click.echo(f"Warning: Failed to generate thumbnail: {e}")
            thumbnail_path = None

        # Align subtitles with offset if thumbnail was generated
        click.echo("Aligning subtitles...")
        aligned_srt_path = tmpdir / "aligned.srt"
        subtitle_offset = 0.5 if thumbnail_path and thumbnail_path.exists() else 0.0
        try:
            align_subtitle(srt_path, chinese_script, aligned_srt_path, time_offset=subtitle_offset)
        except Exception as e:
            _exit_on_error("aligning subtitles", e)

        # Merge final video
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
                nodub_video_path, original_audio_path, dubbing_path, aligned_srt_path, output_path,
                thumbnail_path=thumbnail_path,
                logo_path=logo_path
            )
        except Exception as e:
            _exit_on_error("merging video", e)

        # Save output files
        srt_output_path = intermediate_dir / f"{output_stem}.srt"
        shutil.copy2(aligned_srt_path, srt_output_path)

        raw_video_path = intermediate_dir / f"{output_stem}_raw.mp4"
        shutil.copy2(downloaded_video, raw_video_path)

        # Save thumbnail to output directory
        if thumbnail_path and thumbnail_path.exists():
            thumbnail_output_path = intermediate_dir / f"{output_stem}_thumb.jpg"
            shutil.copy2(thumbnail_path, thumbnail_output_path)
            click.echo(f"Thumbnail saved to: {thumbnail_output_path}")

    click.echo(f"Done! Output saved to: {output_path}")


if __name__ == "__main__":
    main()
