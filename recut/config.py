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
    max_duration: int  # Default max duration in seconds


# Default platform configurations (duration can be overridden via --duration flag)
PLATFORMS = {
    "tiktok": PlatformConfig(width=1080, height=1920, max_duration=30),
    "instagram": PlatformConfig(width=1080, height=1920, max_duration=30),
    "reels": PlatformConfig(width=1080, height=1920, max_duration=30),
}


def get_platform_config(platform: str, duration: int | None = None) -> PlatformConfig:
    """Get video configuration for a platform.

    Args:
        platform: Platform name (tiktok, instagram, reels)
        duration: Custom duration in seconds (overrides default)

    Returns:
        PlatformConfig with specified or default duration
    """
    if platform not in PLATFORMS:
        raise ValueError(f"Unknown platform: {platform}. Valid options: {list(PLATFORMS.keys())}")
    config = PLATFORMS[platform]
    if duration is not None:
        return PlatformConfig(width=config.width, height=config.height, max_duration=duration)
    return config


@dataclass
class TTSConfig:
    """TTS configuration."""
    engine: str = ""  # "edge" (default), "coqui", or "minimax"
    voice: str = ""  # Edge TTS default: zh-CN-XiaoxiaoNeural (Chinese female)
    coqui_voice: str = ""  # Coqui default: tts_models/zh-CN/baker/tacotron2-DDC
    whisper_model: str = ""  # Whisper model size: small, medium, large


@dataclass
class APIConfig:
    """API configuration for external services."""
    llm_api_key: str = ""
    llm_api_url: str = ""
    llm_model: str = ""


@dataclass
class MinimaxConfig:
    """MiniMax TTS API configuration."""
    api_key: str = ""
    api_url: str = ""
    voice_id: str = ""


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
        llm_api_key=os.environ.get("LLM_API_KEY", ""),
        llm_api_url=os.environ.get("LLM_API_URL", "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1"),
        llm_model=os.environ.get("LLM_MODEL", "glm-5"),
    )


def get_minimax_config() -> MinimaxConfig:
    """Get MiniMax TTS configuration from environment."""
    return MinimaxConfig(
        api_key=os.environ.get("MINIMAX_API_KEY", ""),
        api_url=os.environ.get("MINIMAX_API_URL", "https://api.minimaxi.com/v1/t2a_v2"),
        voice_id=os.environ.get("MINIMAX_VOICE_ID", "moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85"),
    )


def get_tts_config() -> TTSConfig:
    """Get TTS configuration from environment."""
    return TTSConfig(
        engine=os.environ.get("TTS_ENGINE", "edge"),
        voice=os.environ.get("TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
        coqui_voice=os.environ.get("COQUI_VOICE", "tts_models/zh-CN/baker/tacotron2-DDC"),
        whisper_model=os.environ.get("WHISPER_MODEL", "small"),
    )


@dataclass
class ThumbnailConfig:
    """Thumbnail generation configuration."""
    font_path: str = ""  # Path to Chinese font file
    font_size_title: int = 72  # Font size for title
    font_size_subtitle: int = 14  # Font size for video subtitles
    logo_path: str = ""  # Path to logo image file
    outro_path: str = ""  # Path to outro video file


def find_chinese_font() -> Path | None:
    """Find an available Chinese font on the system.

    Returns:
        Path to font file, or None if not found
    """
    # Check environment variable first
    env_font = os.environ.get("THUMBNAIL_FONT", "")
    if env_font and Path(env_font).exists():
        return Path(env_font)

    # Default Chinese fonts (in order of preference)
    default_fonts = os.environ.get(
        "THUMBNAIL_DEFAULT_FONTS",
        "ZCOOLGaoDuanHei-Regular.ttf,NotoSansSC-Bold.ttf,SourceHanSansSC-Bold.ttf"
    ).split(",")

    # Common font directories on Windows
    font_dirs = [
        Path("C:/Windows/Fonts"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
        Path(os.environ.get("USERPROFILE", "")) / ".local/share/fonts",
    ]

    # Search in common font directories
    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        for font_name in default_fonts:
            font_path = font_dir / font_name.strip()
            if font_path.exists():
                return font_path

    # Try to find any Chinese-capable font
    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        for font_file in font_dir.glob("*.ttf"):
            name_lower = font_file.name.lower()
            if any(kw in name_lower for kw in ["simhei", "simsun", "yahei", "noto", "source", "hei", "song"]):
                return font_file

    return None


def get_thumbnail_config() -> ThumbnailConfig:
    """Get thumbnail configuration from environment."""
    font_path = os.environ.get("THUMBNAIL_FONT", "")

    # Try to find a font if not specified
    if not font_path:
        found_font = find_chinese_font()
        if found_font:
            font_path = str(found_font)

    return ThumbnailConfig(
        font_path=font_path,
        font_size_title=int(os.environ.get("THUMBNAIL_FONT_SIZE_TITLE", "72")),
        font_size_subtitle=int(os.environ.get("THUMBNAIL_FONT_SIZE_SUBTITLE", "14")),
        logo_path=os.environ.get("THUMBNAIL_LOGO_PATH", "material/logo.png"),
        outro_path=os.environ.get("THUMBNAIL_OUTRO_PATH", "material/outro.mp4"),
    )
