# tests/test_scraper.py
import pytest

from recut.scraper import extract_m3u8_url

def test_extract_m3u8_from_html():
    html = '''
    <html>
    <video class="z1">
        <source src="https://example.com/video.m3u8" type="application/x-mpegURL">
    </video>
    </html>
    '''
    url = extract_m3u8_url(html)
    assert url == "https://example.com/video.m3u8"


def test_extract_m3u8_returns_none_when_no_video():
    html = "<html><body>No video here</body></html>"
    assert extract_m3u8_url(html) is None


def test_extract_m3u8_returns_none_when_no_z1_class():
    html = '''
    <html>
    <video>
        <source src="https://example.com/video.m3u8" type="application/x-mpegURL">
    </video>
    </html>
    '''
    assert extract_m3u8_url(html) is None


def test_extract_m3u8_returns_none_when_no_m3u8_source():
    html = '''
    <html>
    <video class="z1">
        <source src="https://example.com/video.mp4" type="video/mp4">
    </video>
    </html>
    '''
    assert extract_m3u8_url(html) is None


from unittest.mock import patch
from recut.scraper import fetch_kickstarter_page


@patch("recut.scraper.requests.get")
def test_fetch_kickstarter_page_returns_html(mock_get):
    mock_get.return_value.text = "<html>test</html>"
    mock_get.return_value.raise_for_status = lambda: None

    html = fetch_kickstarter_page("https://kickstarter.com/projects/test")
    assert html == "<html>test</html>"
    mock_get.assert_called_once()
