# tests/test_cli_integration.py
"""Integration tests for CLI dubbing workflow."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest


def test_cli_integration_dubbing_workflow():
    """Test full dubbing workflow from CLI with explicit output path."""
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

        def mock_get_audio_duration(path):
            return 30.0  # Return 30 seconds for testing

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

        def mock_align(srt, text, output, time_offset=0.0):
            Path(output).write_text("1\n00:00:00,000 --> 00:00:01,000\ntest")
            return output

        def mock_merge(video, orig, dub, srt, output, thumbnail_path=None, logo_path=None):
            Path(output).write_bytes(b"fake video")
            return output

        def mock_save_chinese_script(path, metadata, source_url=None):
            Path(path).write_text("# Title\nTest\n\n# Transcript\nTest transcript\n\n# Tags\n#tag1 #tag2\n")
            return path

        def mock_generate_thumbnail(video_path, title, output_path, platform="tiktok", font_path=None, image_path=None):
            # Create a fake thumbnail file
            Path(output_path).write_bytes(b"fake thumbnail")
            return output_path

        # Mock metadata response
        mock_metadata = {
            "title": "测试标题",
            "transcript": "中文口播文案",
            "tags": ["标签1", "标签2"]
        }

        # Mock all external dependencies
        with patch("recut.cli.fetch_kickstarter_page", return_value="<html>test</html>"), \
             patch("recut.cli.extract_m3u8_url", return_value="https://test.com/video.m3u8"), \
             patch("recut.cli.download_and_merge_m3u8", side_effect=mock_download), \
             patch("recut.cli.detect_scenes", return_value=[]), \
             patch("recut.cli.select_top_fragments", return_value=[]), \
             patch("recut.cli.create_short", side_effect=mock_create_short), \
             patch("recut.cli.extract_audio", side_effect=mock_extract_audio), \
             patch("recut.cli.transcribe_audio", return_value="English transcript"), \
             patch("recut.cli.translate_and_generate_metadata", return_value=mock_metadata), \
             patch("recut.cli.save_chinese_script", side_effect=mock_save_chinese_script), \
             patch("recut.cli.generate_audio", side_effect=mock_generate_audio), \
             patch("recut.cli.get_audio_duration", side_effect=mock_get_audio_duration), \
             patch("recut.cli.generate_srt", side_effect=mock_srt), \
             patch("recut.cli.align_subtitle", side_effect=mock_align), \
             patch("recut.cli.extract_audio_for_mixing", side_effect=mock_extract_mixing), \
             patch("recut.cli.merge_video_audio_subtitle", side_effect=mock_merge), \
             patch("recut.cli.generate_thumbnail", side_effect=mock_generate_thumbnail), \
             patch("recut.cli.get_api_config", return_value=MagicMock(llm_api_key="test-key", llm_api_url="http://test", llm_model="test-model")), \
             patch("recut.cli.get_thumbnail_config", return_value=MagicMock(logo_path=None)):

            output_path = tmpdir / "output" / "test.mp4"
            result = runner.invoke(main, ["https://test.com", "-o", str(output_path)])

            # Verify workflow was called
            assert result.exit_code == 0, f"CLI failed: {result.output}"

            # Verify dubbing audio was saved in intermediate directory
            intermediate_dir = tmpdir / "output" / "test"
            dubbing_output = intermediate_dir / "test_dubbing.wav"
            assert dubbing_output.exists(), "Dubbing audio file should be saved in intermediate directory"

            # Verify Chinese script uses output.md naming (no _chs suffix) in parent directory
            chs_script = tmpdir / "output" / "test.md"
            assert chs_script.exists(), "Chinese script should be saved as test.md in parent directory"


def test_cli_integration_default_output_path():
    """Test CLI with auto-generated output path from URL."""
    from recut.cli import main
    from click.testing import CliRunner

    runner = CliRunner()

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        def mock_download(url, output):
            Path(output).write_bytes(b"fake video")
            return output

        def mock_generate_audio(text, path, engine=None):
            Path(path).write_bytes(b"fake audio")
            return path

        def mock_get_audio_duration(path):
            return 30.0

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

        def mock_align(srt, text, output, time_offset=0.0):
            Path(output).write_text("1\n00:00:00,000 --> 00:00:01,000\ntest")
            return output

        def mock_merge(video, orig, dub, srt, output, thumbnail_path=None, logo_path=None):
            Path(output).write_bytes(b"fake video")
            return output

        def mock_save_chinese_script(path, metadata, source_url=None):
            Path(path).write_text("# Title\nTest\n\n# Transcript\nTest transcript\n\n# Tags\n#tag1 #tag2\n")
            return path

        def mock_generate_thumbnail(video_path, title, output_path, platform="tiktok", font_path=None, image_path=None):
            Path(output_path).write_bytes(b"fake thumbnail")
            return output_path

        mock_metadata = {
            "title": "测试标题",
            "transcript": "中文口播文案",
            "tags": ["标签1", "标签2"]
        }

        with patch("recut.cli.fetch_kickstarter_page", return_value="<html>test</html>"), \
             patch("recut.cli.extract_m3u8_url", return_value="https://test.com/video.m3u8"), \
             patch("recut.cli.download_and_merge_m3u8", side_effect=mock_download), \
             patch("recut.cli.detect_scenes", return_value=[]), \
             patch("recut.cli.select_top_fragments", return_value=[]), \
             patch("recut.cli.create_short", side_effect=mock_create_short), \
             patch("recut.cli.extract_audio", side_effect=mock_extract_audio), \
             patch("recut.cli.transcribe_audio", return_value="English transcript"), \
             patch("recut.cli.translate_and_generate_metadata", return_value=mock_metadata), \
             patch("recut.cli.save_chinese_script", side_effect=mock_save_chinese_script), \
             patch("recut.cli.generate_audio", side_effect=mock_generate_audio), \
             patch("recut.cli.get_audio_duration", side_effect=mock_get_audio_duration), \
             patch("recut.cli.generate_srt", side_effect=mock_srt), \
             patch("recut.cli.align_subtitle", side_effect=mock_align), \
             patch("recut.cli.extract_audio_for_mixing", side_effect=mock_extract_mixing), \
             patch("recut.cli.merge_video_audio_subtitle", side_effect=mock_merge), \
             patch("recut.cli.generate_thumbnail", side_effect=mock_generate_thumbnail), \
             patch("recut.cli.get_api_config", return_value=MagicMock(llm_api_key="test-key", llm_api_url="http://test", llm_model="test-model")), \
             patch("recut.cli.get_thumbnail_config", return_value=MagicMock(logo_path=None)):

            # No -o parameter - should auto-generate from URL
            result = runner.invoke(main, ["https://kickstarter.com/projects/user/my-project-name"])

            assert result.exit_code == 0, f"CLI failed: {result.output}"

            # Output should be in output/my-project-name.mp4
            expected_output = Path("output/my-project-name.mp4")
            assert expected_output.exists(), f"Output file should be at {expected_output}"

            # Cleanup
            import shutil
            if Path("output").exists():
                shutil.rmtree("output")
