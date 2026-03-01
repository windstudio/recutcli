# tests/test_config.py
from recut.config import get_platform_config, PlatformConfig
import pytest


def test_get_tiktok_config():
    config = get_platform_config("tiktok")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 25


def test_get_instagram_config():
    config = get_platform_config("instagram")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 25


def test_get_reels_config():
    config = get_platform_config("reels")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 25


def test_invalid_platform_raises():
    with pytest.raises(ValueError, match="Unknown platform"):
        get_platform_config("youtube")
