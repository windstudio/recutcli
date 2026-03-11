# tests/test_cli.py
"""Unit tests for CLI helper functions."""

import pytest
from recut.cli import _extract_filename_from_url


class TestExtractFilenameFromUrl:
    """Tests for _extract_filename_from_url function."""

    def test_kickstarter_url(self):
        """Test extracting filename from Kickstarter URL."""
        url = "https://www.kickstarter.com/projects/hozodesign/neosander-mini-electric-reciprocating-detail-sander?ref=discovery"
        result = _extract_filename_from_url(url)
        assert result == "neosander-mini-electric-reciprocating-detail-sander"

    def test_simple_path(self):
        """Test extracting filename from simple path."""
        url = "https://example.com/projects/user/my-project-name"
        result = _extract_filename_from_url(url)
        assert result == "my-project-name"

    def test_trailing_slash(self):
        """Test URL with trailing slash."""
        url = "https://example.com/path/to/video/"
        result = _extract_filename_from_url(url)
        assert result == "video"

    def test_root_url(self):
        """Test URL with no path segments."""
        url = "https://example.com/"
        result = _extract_filename_from_url(url)
        assert result == "output"

    def test_empty_path(self):
        """Test URL with empty path."""
        url = "https://example.com"
        result = _extract_filename_from_url(url)
        assert result == "output"

    def test_special_characters(self):
        """Test URL with special characters in last segment."""
        url = "https://example.com/path/My Project@2024!"
        result = _extract_filename_from_url(url)
        # Special chars replaced with hyphens
        assert result == "My-Project-2024-"

    def test_url_encoded_characters(self):
        """Test URL with encoded characters."""
        url = "https://example.com/path/my%20project%20name"
        result = _extract_filename_from_url(url)
        # %20 decoded to space, then space replaced with hyphen
        assert result == "my-project-name"

    def test_underscores_preserved(self):
        """Test that underscores are preserved."""
        url = "https://example.com/path/my_project_name"
        result = _extract_filename_from_url(url)
        assert result == "my_project_name"

    def test_multiple_hyphens(self):
        """Test multiple hyphens preserved."""
        url = "https://example.com/path/my--project--name"
        result = _extract_filename_from_url(url)
        assert result == "my--project--name"
