import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, download_video


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


@patch("recut.downloader.subprocess.run")
def test_download_and_merge_calls_ffmpeg(mock_subprocess):
    mock_subprocess.return_value = MagicMock()

    result = download_and_merge_m3u8(
        "https://example.com/video.m3u8",
        Path("/tmp/output.mp4")
    )

    assert result == Path("/tmp/output.mp4")
    mock_subprocess.assert_called_once()


@patch("recut.downloader.subprocess.run")
def test_download_retries_on_failure(mock_subprocess):
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


@patch("recut.downloader.subprocess.run")
def test_download_raises_after_max_retries(mock_subprocess):
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


# Tests for download_video

@patch("recut.downloader.urllib.request.urlopen")
@patch("recut.downloader.urllib.request.Request")
def test_download_video_creates_parent_directory(mock_request, mock_urlopen, tmp_path):
    """Test that download_video creates parent directory and saves content."""
    mock_response = MagicMock()
    mock_response.read.return_value = b"fake video content"
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    output_path = tmp_path / "subdir" / "video.mp4"

    result = download_video("https://example.com/video.mp4", output_path)

    assert result == output_path
    assert output_path.parent.exists()
    assert output_path.read_bytes() == b"fake video content"


@patch("recut.downloader.urllib.request.urlopen")
@patch("recut.downloader.urllib.request.Request")
def test_download_video_retries_on_failure(mock_request, mock_urlopen, tmp_path):
    """Test that download_video retries on failure."""
    # First two attempts fail, third succeeds
    mock_response_success = MagicMock()
    mock_response_success.read.return_value = b"success content"
    mock_response_success.__enter__ = MagicMock(return_value=mock_response_success)
    mock_response_success.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [
        Exception("Network error 1"),
        Exception("Network error 2"),
        mock_response_success
    ]

    output_path = tmp_path / "video.mp4"
    result = download_video("https://example.com/video.mp4", output_path, retries=3)

    assert result == output_path
    assert mock_urlopen.call_count == 3


@patch("recut.downloader.urllib.request.urlopen")
@patch("recut.downloader.urllib.request.Request")
def test_download_video_raises_after_max_retries(mock_request, mock_urlopen, tmp_path):
    """Test that download_video raises RuntimeError after max retries."""
    mock_urlopen.side_effect = Exception("Network error")

    output_path = tmp_path / "video.mp4"

    with pytest.raises(RuntimeError, match="Failed to download video after 3 attempts"):
        download_video("https://example.com/video.mp4", output_path, retries=3)

    assert mock_urlopen.call_count == 3


@patch("recut.downloader.urllib.request.urlopen")
@patch("recut.downloader.urllib.request.Request")
def test_download_video_with_user_agent_header(mock_request, mock_urlopen, tmp_path):
    """Test that download_video sends User-Agent header."""
    mock_response = MagicMock()
    mock_response.read.return_value = b"content"
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    output_path = tmp_path / "video.mp4"
    download_video("https://example.com/video.mp4", output_path)

    # Verify Request was created with User-Agent header
    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert args[0] == "https://example.com/video.mp4"
    assert kwargs["headers"]["User-Agent"] == "Mozilla/5.0"
