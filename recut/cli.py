# recut/cli.py
"""Command-line interface for recut."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from recut import __version__
from recut.analyzer import detect_scenes, select_top_fragments, Scene, get_video_duration
from recut.config import get_platform_config, PLATFORMS, load_dotenv_config, get_api_config, get_tts_config
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, FFMPEG_INSTALL_MSG
from recut.editor import create_short, extract_audio_for_mixing, merge_video_audio_subtitle
from recut.scraper import fetch_kickstarter_page, extract_m3u8_url
from recut.transcriber import extract_audio, transcribe_audio, save_transcript
from recut.translator import translate_and_refine
from recut.tts import generate_audio
from recut.subtitle import generate_srt, align_subtitle


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
@click.option("--m3u8-url", help="Direct m3u8 URL (skip Kickstarter scraping)")
@click.option("--tts-engine", type=click.Choice(["edge", "coqui", "piper"]), default=None, help="TTS engine")
@click.option("--duration", type=int, default=None, help="Video duration in seconds (default: 30)")
@click.version_option(version=__version__)
def main(
    url: str,
    output: str,
    platform: str,
    scene_threshold: float,
    m3u8_url: str | None,
    tts_engine: str | None,
    duration: int | None
):
    """Download Kickstarter video and create a short social media video."""
    load_dotenv_config()

    api_config = get_api_config()
    if not api_config.yuanjing_api_key:
        _exit_on_error("YUANJING_API_KEY not set. Please set it in .env file.")

    if not check_ffmpeg():
        _exit_on_error(FFMPEG_INSTALL_MSG)

    output_path = Path(output)
    config = get_platform_config(platform, duration=duration)
    tts_config = get_tts_config()

    # Get video URL
    if not m3u8_url:
        click.echo(f"Fetching Kickstarter page: {url}")
        try:
            html = fetch_kickstarter_page(url)
        except Exception as e:
            _exit_on_error("fetching page", e)

        click.echo("Extracting video URL...")
        m3u8_url = extract_m3u8_url(html)
        if not m3u8_url:
            _exit_on_error("Could not find video URL in page")

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        downloaded_video = tmpdir / "downloaded.mp4"

        # Download video
        click.echo("Downloading video...")
        try:
            download_and_merge_m3u8(m3u8_url, downloaded_video)
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

        click.echo(f"Found {len(fragments)} scenes. Selecting best fragments...")
        selected = select_top_fragments(fragments, target_duration=config.max_duration) or fragments
        total_duration = sum(f.end - f.start for f in selected)
        click.echo(f"Selected {len(selected)} fragments ({total_duration:.1f}s total)")

        # Create short video
        click.echo(f"Creating short video for {platform}...")
        create_short(downloaded_video, selected, output_path, config)

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
        script_path = output_path.with_stem(output_path.stem + "_script").with_suffix(".md")
        click.echo(f"Saving transcript to: {script_path}")
        try:
            save_transcript(transcript, script_path)
        except Exception as e:
            _exit_on_error("saving transcript", e)

        # Translate to Chinese
        click.echo("Translating and refining to Chinese script...")
        try:
            chinese_script = translate_and_refine(
                transcript,
                api_key=api_config.yuanjing_api_key,
                base_url=api_config.yuanjing_base_url,
                duration=config.max_duration
            )
        except Exception as e:
            _exit_on_error("translating", e)

        chs_script_path = output_path.with_stem(output_path.stem + "_chs").with_suffix(".md")
        click.echo(f"Saving Chinese script to: {chs_script_path}")
        try:
            save_transcript(chinese_script, chs_script_path)
        except Exception as e:
            _exit_on_error("saving Chinese script", e)

        # Generate TTS
        click.echo(f"Generating Chinese TTS audio (engine: {tts_engine or tts_config.engine})...")
        dubbing_path = tmpdir / "dubbing.wav"
        try:
            generate_audio(chinese_script, dubbing_path, engine=tts_engine)
        except Exception as e:
            _exit_on_error("generating TTS", e)

        dubbing_output_path = output_path.with_stem(output_path.stem + "_dubbing").with_suffix(".wav")
        click.echo(f"Saving dubbing audio to: {dubbing_output_path}")
        shutil.copy2(dubbing_path, dubbing_output_path)

        # Generate subtitles
        click.echo("Generating subtitles...")
        srt_path = tmpdir / "subtitle.srt"
        try:
            generate_srt(dubbing_path, srt_path, model=tts_config.whisper_model)
        except Exception as e:
            _exit_on_error("generating subtitles", e)

        click.echo("Aligning subtitles...")
        aligned_srt_path = tmpdir / "aligned.srt"
        try:
            align_subtitle(srt_path, chinese_script, aligned_srt_path)
        except Exception as e:
            _exit_on_error("aligning subtitles", e)

        # Merge final video
        click.echo("Extracting original audio for mixing...")
        original_audio_path = tmpdir / "original.wav"
        try:
            extract_audio_for_mixing(output_path, original_audio_path)
        except Exception as e:
            _exit_on_error("extracting original audio", e)

        click.echo("Merging video with dubbing and subtitles...")
        final_output_path = output_path.with_stem(output_path.stem + "_final")
        try:
            merge_video_audio_subtitle(output_path, original_audio_path, dubbing_path, aligned_srt_path, final_output_path)
        except Exception as e:
            _exit_on_error("merging video", e)

        # Save output files
        shutil.copy2(aligned_srt_path, output_path.with_suffix(".srt"))
        shutil.copy2(downloaded_video, output_path.with_stem(output_path.stem + "_raw"))

    click.echo(f"Done! Output saved to: {final_output_path}")


if __name__ == "__main__":
    main()
