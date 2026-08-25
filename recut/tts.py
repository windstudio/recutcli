"""Text-to-speech using Edge TTS (default), Coqui TTS, or MiniMax TTS API."""

import asyncio
import subprocess
import wave
from pathlib import Path

from recut.config import get_tts_config
from recut.downloader import get_ffmpeg_path


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds from a WAV file.

    Args:
        audio_path: Path to the WAV audio file

    Returns:
        Duration in seconds

    Raises:
        RuntimeError: If the file cannot be read or is not a valid WAV file
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise RuntimeError(f"Audio file not found: {audio_path}")

    try:
        with wave.open(str(audio_path), 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except Exception as e:
        raise RuntimeError(f"Failed to read audio duration: {e}")


def _ensure_output_dir(output_path: Path) -> None:
    """Ensure output directory exists."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)


def _generate_edge_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Edge TTS."""
    import edge_tts

    output_path = Path(output_path)
    _ensure_output_dir(output_path)

    try:
        communicate = edge_tts.Communicate(text, voice)
        mp3_path = output_path.with_suffix(".mp3")
        asyncio.run(communicate.save(str(mp3_path)))

        # Convert MP3 to WAV
        result = subprocess.run(
            [get_ffmpeg_path(), "-y", "-i", str(mp3_path), "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", str(output_path)],
            capture_output=True, text=True
        )

        if mp3_path.exists():
            mp3_path.unlink()

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

        return output_path
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Edge TTS generation failed: {e}")


def _generate_coqui_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Coqui TTS."""
    try:
        from TTS.api import TTS
    except ImportError as e:
        raise RuntimeError(
            "Coqui TTS is not installed. Install it with: pip install recut[tts-coqui]"
        ) from e

    output_path = Path(output_path)
    _ensure_output_dir(output_path)

    try:
        tts = TTS(model_name=voice, progress_bar=False, gpu=False)
        tts.tts_to_file(text=text, file_path=str(output_path))
        return output_path
    except Exception as e:
        raise RuntimeError(
            f"Coqui TTS generation failed: {e}. "
            "If the package is missing, install it with: pip install recut[tts-coqui]"
        ) from e


def _generate_minimax_audio(text: str, output_path: Path, voice_id: str | None = None) -> Path:
    """Generate audio using MiniMax TTS API.

    Args:
        text: Chinese text to synthesize
        output_path: Output WAV file path
        voice_id: MiniMax voice ID (optional, uses config default if not provided)

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If API call fails or configuration is missing
    """
    import requests
    from recut.config import get_minimax_config

    config = get_minimax_config()
    if not config.api_key:
        raise RuntimeError("MINIMAX_API_KEY not set. Please set it in .env file.")

    voice = voice_id or config.voice_id

    try:
        response = requests.post(
            config.api_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "speech-2.8-hd",
                "text": text,
                "stream": False,
                "voice_setting": {
                    "voice_id": voice,
                    "speed": 1.0,
                    "vol": 3.0,
                },
                "audio_setting": {
                    "sample_rate": 22050,
                    "format": "wav",
                    "channel": 1,
                },
            },
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(f"MiniMax API HTTP error: {response.status_code} - {response.text}")

        data = response.json()
        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code") != 0:
            raise RuntimeError(f"MiniMax API error: {base_resp.get('status_msg', 'Unknown error')}")

        # Decode hex audio to binary
        audio_hex = data["data"]["audio"]
        audio_bytes = bytes.fromhex(audio_hex)

        output_path = Path(output_path)
        _ensure_output_dir(output_path)
        output_path.write_bytes(audio_bytes)

        return output_path
    except requests.RequestException as e:
        raise RuntimeError(f"MiniMax API request failed: {e}")


def generate_audio(
    text: str,
    output_path: Path,
    engine: str | None = None,
    voice: str | None = None
) -> Path:
    """Generate Chinese audio from text using TTS.

    Args:
        text: Chinese text to synthesize
        output_path: Output WAV file path
        engine: TTS engine ("edge", "coqui", or "minimax"). Default: edge
        voice: Voice model name. Default: engine-specific default

    Returns:
        Path to generated audio file
    """
    config = get_tts_config()
    engine = engine or config.engine

    if engine == "minimax":
        return _generate_minimax_audio(text, output_path, voice)
    elif engine == "coqui":
        voice = voice or config.coqui_voice
        return _generate_coqui_audio(text, output_path, voice)
    else:
        voice = voice or config.voice
        return _generate_edge_audio(text, output_path, voice)
