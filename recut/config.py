"""Platform-specific video output configurations."""

from dataclasses import dataclass


@dataclass
class PlatformConfig:
    """Video configuration for a social media platform."""
    width: int
    height: int
    max_duration: int


PLATFORMS = {
    "tiktok": PlatformConfig(width=1080, height=1920, max_duration=25),
    "instagram": PlatformConfig(width=1080, height=1920, max_duration=25),
    "reels": PlatformConfig(width=1080, height=1920, max_duration=25),
}


def get_platform_config(platform: str) -> PlatformConfig:
    """Get video configuration for a platform."""
    if platform not in PLATFORMS:
        raise ValueError(f"Unknown platform: {platform}. Valid options: {list(PLATFORMS.keys())}")
    return PLATFORMS[platform]
