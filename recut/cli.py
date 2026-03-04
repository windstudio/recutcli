# recut/cli.py
"""Command-line interface for recut."""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from recut import __version__
from recut.analyzer import detect_scenes, select_top_fragments, Scene, get_video_duration
from recut.config import get_platform_config, PLATFORMS
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, FFMPEG_INSTALL_MSG
from recut.editor import create_short
from recut.scraper import fetch_kickstarter_page, extract_m3u8_url


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
    # Check ffmpeg
    if not check_ffmpeg():
        click.echo(f"Error: {FFMPEG_INSTALL_MSG}", err=True)
        raise SystemExit(1)

    output_path = Path(output)
    config = get_platform_config(platform)

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

        # Save original downloaded video with "_orig" suffix
        orig_path = output_path.with_stem(output_path.stem + "_orig")
        click.echo(f"Saving original video to: {orig_path}")
        shutil.copy2(downloaded_video, orig_path)

    click.echo(f"Done! Output saved to: {output_path}")


if __name__ == "__main__":
    main()
