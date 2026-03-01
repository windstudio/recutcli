import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from recut.downloader import check_ffmpeg, download_and_merge_m3u8


def test_download_returns_output_path():
    # This is an integration test that requires ffmpeg
    # For unit testing, we'll mock the subprocess calls
    pass


@patch("recut.downloader.subprocess.run")
def test_check_ffmpeg_returns_true_when_available(mock_run):
    mock_run.return_value = MagicMock()
    assert check_ffmpeg() is True


@patch("recut.downloader.subprocess.run")
def test_check_ffmpeg_returns_false_when_not_available(mock_run):
    mock_run.side_effect = FileNotFoundError()
    assert check_ffmpeg() is False


@patch("recut.downloader.check_ffmpeg")
@patch("recut.downloader.subprocess.run")
def test_download_and_merge_calls_ffmpeg(mock_subprocess, mock_check):
    mock_check.return_value = True
    mock_subprocess.return_value = MagicMock()

    result = download_and_merge_m3u8(
        "https://example.com/video.m3u8",
        Path("/tmp/output.mp4")
    )

    assert result == Path("/tmp/output.mp4")
    mock_subprocess.assert_called_once()


@patch("recut.downloader.check_ffmpeg")
def test_download_raises_when_ffmpeg_missing(mock_check):
    mock_check.return_value = False

    with pytest.raises(RuntimeError, match="ffmpeg is not installed"):
        download_and_merge_m3u8("https://example.com/video.m3u8", Path("/tmp/output.mp4"))


@patch("recut.downloader.check_ffmpeg")
@patch("recut.downloader.subprocess.run")
def test_download_retries_on_failure(mock_subprocess, mock_check):
    mock_check.return_value = True
    # First two attempts fail, third succeeds
    mock_subprocess.side_effect = [
        subprocess.CalledProcessError(1, "ffmpeg", stderr=b"error1"),
        subprocess.CalledProcessError(1, "ffmpeg", stderr=b"error2"),
        MagicMock()  # Success on third attempt
    ]

    result = download_and_merge_m3u8(
        "https://example.com/video.m3u8",
        Path("/tmp/output.mp4"),
        retries=3
    )

    assert result == Path("/tmp/output.mp4")
    assert mock_subprocess.call_count == 3


@patch("recut.downloader.check_ffmpeg")
@patch("recut.downloader.subprocess.run")
def test_download_raises_after_max_retries(mock_subprocess, mock_check):
    mock_check.return_value = True
    mock_subprocess.side_effect = subprocess.CalledProcessError(
        1, "ffmpeg", stderr=b"download failed"
    )

    with pytest.raises(RuntimeError, match="Failed to download video after 3 attempts"):
        download_and_merge_m3u8(
            "https://example.com/video.m3u8",
            Path("/tmp/output.mp4"),
            retries=3
        )

    assert mock_subprocess.call_count == 3


@patch("recut.downloader.subprocess.run")
def test_check_ffmpeg_returns_false_on_called_process_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
    assert check_ffmpeg() is False
