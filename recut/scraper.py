"""Kickstarter page scraper for extracting video URLs."""

import requests
from bs4 import BeautifulSoup


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
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text
