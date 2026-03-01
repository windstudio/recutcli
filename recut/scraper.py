"""Kickstarter page scraper for extracting video URLs."""

import requests
from bs4 import BeautifulSoup

# Default HTTP headers for requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def extract_m3u8_url(html: str) -> str | None:
    """Extract m3u8 URL from Kickstarter page HTML.

    Looks for video tag with class 'z1' and extracts the m3u8 source URL.
    """
    soup = BeautifulSoup(html, "html.parser")
    video = soup.find("video", class_="z1")
    if not video:
        return None

    source = video.find("source", type="application/x-mpegURL")
    if not source:
        return None

    return source.get("src")


def fetch_kickstarter_page(url: str) -> str:
    """Fetch Kickstarter project page HTML."""
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()
    return response.text
