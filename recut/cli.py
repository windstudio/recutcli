# recut/cli.py
"""Command-line interface for recut."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from recut import __version__
from recut.analyzer import detect_scenes, select_top_fragments, Scene, get_video_duration
from recut.config import (
    get_platform_config,
    PLATFORMS,
    load_dotenv_config,
    get_api_config,
    get_tts_config,
)
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, FFMPEG_INSTALL_MSG
from recut.editor import (
    create_short,
    extract_audio_for_mixing,
    merge_video_audio_subtitle,
)
from recut.scraper import fetch_kickstarter_page, extract_m3u8_url
from recut.transcriber import extract_audio, transcribe_audio, save_transcript
from recut.translator import translate_and_refine
from recut.tts import generate_audio
from recut.subtitle import generate_srt, align_subtitle


@click.command()
@click.argument("url")
@click.option("-o", "--output", required=True, help="Output video file path")
@click.option(
    "--platform",
    type=click.Choice(list(PLATFORMS.keys())),
    default="tiktok",
    help="Target platform (default: tiktok)"
)
@click.option(
    "--scene-threshold",
    type=float,
    default=0.3,
    help="Scene change detection threshold 0-1 (default: 0.3)"
)
@click.option(
    "--m3u8-url",
    help="Direct m3u8 URL (skip Kickstarter scraping)"
)
@click.version_option(version=__version__)
def main(url: str, output: str, platform: str, scene_threshold: float, m3u8_url: str | None):
    """Download Kickstarter video and create a 25-second social media short.

    URL: Kickstarter project URL (ignored if --m3u8-url is provided)
    """
    # Load environment variables
    load_dotenv_config()

    # Check API key
    api_config = get_api_config()
    if not api_config.yuanjing_api_key:
        click.echo("Error: YUANJING_API_KEY not set. Please set it in .env file.", err=True)
        raise SystemExit(1)

    # Check ffmpeg
    if not check_ffmpeg():
        click.echo(f"Error: {FFMPEG_INSTALL_MSG}", err=True)
        raise SystemExit(1)

    output_path = Path(output)
    config = get_platform_config(platform)
    tts_config = get_tts_config()

    # Use direct m3u8 URL if provided, otherwise scrape from Kickstarter
    if not m3u8_url:
        click.echo(f"Fetching Kickstarter page: {url}")
        try:
            html = fetch_kickstarter_page(url)
        except Exception as e:
            click.echo(f"Error fetching page: {e}", err=True)
            raise SystemExit(1)

        click.echo("Extracting video URL...")
        m3u8_url = extract_m3u8_url(html)
        if not m3u8_url:
            click.echo("Error: Could not find video URL in page", err=True)
            raise SystemExit(1)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        downloaded_video = tmpdir / "downloaded.mp4"

        click.echo("Downloading video...")
        try:
            download_and_merge_m3u8(m3u8_url, downloaded_video)
        except Exception as e:
            click.echo(f"Error downloading video: {e}", err=True)
            raise SystemExit(1)

        click.echo("Analyzing scenes...")
        fragments = detect_scenes(downloaded_video, threshold=scene_threshold)

        if not fragments:
            click.echo("Warning: No scenes detected. Using fixed intervals.")
            # Fallback: create fixed intervals
            duration = get_video_duration(downloaded_video)
            interval = 5.0
            fragments = [
                Scene(start=i * interval, end=min((i + 1) * interval, duration))
                for i in range(int(duration / interval))
            ]

        click.echo(f"Found {len(fragments)} scenes. Selecting best fragments...")
        selected = select_top_fragments(fragments, target_duration=config.max_duration)

        if not selected:
            click.echo("Warning: Video too short. Using original video.")
            selected = fragments

        total_duration = sum(f.end - f.start for f in selected)
        click.echo(f"Selected {len(selected)} fragments ({total_duration:.1f}s total)")

        click.echo(f"Creating short video for {platform}...")
        create_short(downloaded_video, selected, output_path, config)

        # Extract audio and transcribe
        click.echo("Extracting audio...")
        audio_path = tmpdir / "audio.wav"
        try:
            extract_audio(downloaded_video, audio_path)
        except Exception as e:
            click.echo(f"Error extracting audio: {e}", err=True)
            raise SystemExit(1)

        click.echo("Transcribing with Whisper...")
        try:
            transcript = transcribe_audio(audio_path)
        except Exception as e:
            click.echo(f"Error transcribing audio: {e}", err=True)
            raise SystemExit(1)

        # Save transcript
        script_path = output_path.with_stem(output_path.stem + "_script").with_suffix(".md")
        click.echo(f"Saving transcript to: {script_path}")
        try:
            save_transcript(transcript, script_path)
        except Exception as e:
            click.echo(f"Error saving transcript: {e}", err=True)
            raise SystemExit(1)

        # Translate and refine to Chinese script
        click.echo("Translating and refining to Chinese script...")
        try:
            chinese_script = translate_and_refine(
                transcript,
                api_key=api_config.yuanjing_api_key,
                base_url=api_config.yuanjing_base_url
            )
        except Exception as e:
            click.echo(f"Error translating: {e}", err=True)
            raise SystemExit(1)

        # Save Chinese script
        chinese_script_path = output_path.with_stem(output_path.stem + "_chinese").with_suffix(".md")
        click.echo(f"Saving Chinese script to: {chinese_script_path}")
        try:
            save_transcript(chinese_script, chinese_script_path)
        except Exception as e:
            click.echo(f"Error saving Chinese script: {e}", err=True)
            raise SystemExit(1)

        # Generate Chinese TTS audio
        click.echo("Generating Chinese TTS audio...")
        dubbing_path = tmpdir / "dubbing.wav"
        try:
            generate_audio(chinese_script, dubbing_path, voice=tts_config.voice)
        except Exception as e:
            click.echo(f"Error generating TTS: {e}", err=True)
            raise SystemExit(1)

        # Generate SRT subtitles from dubbing audio
        click.echo("Generating subtitles...")
        srt_path = tmpdir / "subtitle.srt"
        try:
            generate_srt(dubbing_path, srt_path, model=tts_config.whisper_model)
        except Exception as e:
            click.echo(f"Error generating subtitles: {e}", err=True)
            raise SystemExit(1)

        # Align subtitles with Chinese script
        click.echo("Aligning subtitles...")
        aligned_srt_path = tmpdir / "aligned.srt"
        try:
            align_subtitle(srt_path, chinese_script, aligned_srt_path)
        except Exception as e:
            click.echo(f"Error aligning subtitles: {e}", err=True)
            raise SystemExit(1)

        # Extract original audio for mixing
        click.echo("Extracting original audio for mixing...")
        original_audio_path = tmpdir / "original.wav"
        try:
            extract_audio_for_mixing(downloaded_video, original_audio_path)
        except Exception as e:
            click.echo(f"Error extracting original audio: {e}", err=True)
            raise SystemExit(1)

        # Merge video + original audio + dubbing + subtitles
        click.echo("Merging video with dubbing and subtitles...")
        final_output_path = output_path.with_stem(output_path.stem + "_final")
        try:
            merge_video_audio_subtitle(
                output_path,
                original_audio_path,
                dubbing_path,
                aligned_srt_path,
                final_output_path
            )
        except Exception as e:
            click.echo(f"Error merging: {e}", err=True)
            raise SystemExit(1)

        # Save subtitle file
        final_srt_path = output_path.with_suffix(".srt")
        click.echo(f"Saving subtitles to: {final_srt_path}")
        shutil.copy2(aligned_srt_path, final_srt_path)

        # Save original downloaded video with "_orig" suffix
        orig_path = output_path.with_stem(output_path.stem + "_orig")
        click.echo(f"Saving original video to: {orig_path}")
        shutil.copy2(downloaded_video, orig_path)

    click.echo(f"Done! Output saved to: {final_output_path}")


if __name__ == "__main__":
    main()
