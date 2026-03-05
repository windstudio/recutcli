"""Configuration for recut: platform settings, TTS, and API credentials."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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


@dataclass
class TTSConfig:
    """TTS configuration."""
    engine: str = "edge"  # "edge" (default), "coqui", or "piper"
    voice: str = "zh-CN-XiaoxiaoNeural"  # Edge TTS default (Chinese female)
    coqui_voice: str = "tts_models/zh-CN/baker/tacotron2-DDC"  # Coqui fallback
    piper_voice: str = "zh_CN-huayan-medium"  # Piper fallback
    whisper_model: str = "small"


@dataclass
class APIConfig:
    """API configuration for external services."""
    yuanjing_api_key: str = ""
    yuanjing_base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1"


def load_dotenv_config(env_path: Path | str | None = None) -> None:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, looks for .env in current directory.
    """
    if env_path is not None:
        load_dotenv(env_path)
    else:
        load_dotenv()


def get_api_config() -> APIConfig:
    """Get API configuration from environment."""
    return APIConfig(
        yuanjing_api_key=os.environ.get("YUANJING_API_KEY", ""),
    )


def get_tts_config() -> TTSConfig:
    """Get TTS configuration from environment."""
    return TTSConfig(
        engine=os.environ.get("TTS_ENGINE", "edge"),
        voice=os.environ.get("TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
        coqui_voice=os.environ.get("COQUI_VOICE", "tts_models/zh-CN/baker/tacotron2-DDC"),
        piper_voice=os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium"),
        whisper_model=os.environ.get("WHISPER_MODEL", "small"),
    )
