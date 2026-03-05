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

        # Create side effects that also create files
        def mock_download(url, output):
            Path(output).write_bytes(b"fake video")
            return output

        def mock_generate_audio(text, path, engine=None):
            Path(path).write_bytes(b"fake audio")
            return path

        def mock_create_short(video, fragments, output, config):
            Path(output).write_bytes(b"fake video")
            return output

        def mock_extract_audio(video, output):
            Path(output).write_bytes(b"fake audio")
            return output

        def mock_extract_mixing(video, output):
            Path(output).write_bytes(b"fake audio")
            return output

        def mock_srt(audio, output, model=None):
            Path(output).write_text("1\n00:00:00,000 --> 00:00:01,000\ntest")
            return output

        def mock_align(srt, text, output):
            Path(output).write_text("1\n00:00:00,000 --> 00:00:01,000\ntest")
            return output

        def mock_merge(video, orig, dub, srt, output):
            Path(output).write_bytes(b"fake video")
            return output

        # Mock all external dependencies
        with patch("recut.cli.fetch_kickstarter_page", return_value="<html>test</html>"), \
             patch("recut.cli.extract_m3u8_url", return_value="https://test.m3u8"), \
             patch("recut.cli.download_and_merge_m3u8", side_effect=mock_download), \
             patch("recut.cli.detect_scenes", return_value=[]), \
             patch("recut.cli.select_top_fragments", return_value=[]), \
             patch("recut.cli.create_short", side_effect=mock_create_short), \
             patch("recut.cli.extract_audio", side_effect=mock_extract_audio), \
             patch("recut.cli.transcribe_audio", return_value="English transcript"), \
             patch("recut.cli.translate_and_refine", return_value="中文口播文案"), \
             patch("recut.cli.generate_audio", side_effect=mock_generate_audio), \
             patch("recut.cli.generate_srt", side_effect=mock_srt), \
             patch("recut.cli.align_subtitle", side_effect=mock_align), \
             patch("recut.cli.extract_audio_for_mixing", side_effect=mock_extract_mixing), \
             patch("recut.cli.merge_video_audio_subtitle", side_effect=mock_merge), \
             patch("recut.cli.get_api_config", return_value=MagicMock(yuanjing_api_key="test-key", yuanjing_base_url="http://test")):

            output_path = tmpdir / "output.mp4"
            result = runner.invoke(main, ["https://test.com", "-o", str(output_path)])

            # Verify workflow was called
            assert result.exit_code == 0, f"CLI failed: {result.output}"

            # Verify dubbing audio was saved
            dubbing_output = tmpdir / "output_dubbing.wav"
            assert dubbing_output.exists(), "Dubbing audio file should be saved"

            # Verify Chinese script uses _chs suffix
            chs_script = tmpdir / "output_chs.md"
            assert chs_script.exists(), "Chinese script should use _chs suffix"
