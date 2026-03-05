# tests/test_cli_integration.py
"""Integration tests for CLI dubbing workflow."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest


def test_cli_integration_dubbing_workflow():
    """Test full dubbing workflow from CLI."""
    from recut.cli import main
    from click.testing import CliRunner

    runner = CliRunner()

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Mock all external dependencies
        with patch("recut.cli.fetch_kickstarter_page") as mock_fetch, \
             patch("recut.cli.extract_m3u8_url") as mock_extract, \
             patch("recut.cli.download_and_merge_m3u8") as mock_download, \
             patch("recut.cli.detect_scenes") as mock_detect, \
             patch("recut.cli.select_top_fragments") as mock_select, \
             patch("recut.cli.create_short") as mock_create, \
             patch("recut.cli.extract_audio") as mock_extract_audio, \
             patch("recut.cli.transcribe_audio") as mock_transcribe, \
             patch("recut.cli.translate_and_refine") as mock_translate, \
             patch("recut.cli.generate_audio") as mock_tts, \
             patch("recut.cli.generate_srt") as mock_srt, \
             patch("recut.cli.align_subtitle") as mock_align, \
             patch("recut.cli.extract_audio_for_mixing") as mock_extract_mixing, \
             patch("recut.cli.merge_video_audio_subtitle") as mock_merge, \
             patch("recut.cli.save_transcript") as mock_save, \
             patch("recut.cli.get_api_config") as mock_api_config:

            # Setup mocks
            mock_fetch.return_value = "<html>test</html>"
            mock_extract.return_value = "https://test.m3u8"
            mock_download.return_value = tmpdir / "downloaded.mp4"
            mock_detect.return_value = []
            mock_select.return_value = []
            mock_create.return_value = tmpdir / "output.mp4"
            mock_extract_audio.return_value = tmpdir / "audio.wav"
            mock_transcribe.return_value = "English transcript"
            mock_translate.return_value = "中文口播文案"
            mock_tts.return_value = tmpdir / "dubbing.wav"
            mock_srt.return_value = tmpdir / "subtitle.srt"
            mock_align.return_value = tmpdir / "aligned.srt"
            mock_extract_mixing.return_value = tmpdir / "original.wav"
            mock_merge.return_value = tmpdir / "final.mp4"
            mock_api_config.return_value = MagicMock(yuanjing_api_key="test-key")

            # Create fake video file
            (tmpdir / "downloaded.mp4").write_bytes(b"fake video")

            output_path = tmpdir / "output.mp4"
            result = runner.invoke(main, ["https://test.com", "-o", str(output_path)])

            # Verify workflow was called
            mock_transcribe.assert_called_once()
            mock_translate.assert_called_once_with(
                "English transcript",
                api_key="test-key",
                base_url=mock_api_config.return_value.yuanjing_base_url,
                duration=30  # Default duration
            )
            mock_tts.assert_called_once()
            mock_srt.assert_called_once()
            mock_align.assert_called_once()
            mock_merge.assert_called_once()
