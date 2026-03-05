"""Text-to-speech using Edge TTS (default), Coqui TTS, or Piper TTS."""

import asyncio
import os
import wave
from pathlib import Path

from recut.config import get_tts_config

# Default directory for Piper models
PIPER_MODELS_DIR = Path(os.environ.get("PIPER_MODELS_DIR", "C:/piper_models"))

# Hugging Face URLs for downloading Piper models
PIPER_VOICE_URLS = {
    "zh_CN-huayan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
}


def _ensure_piper_model_files(voice: str) -> tuple[Path, Path]:
    """Ensure Piper model files exist, download if necessary.

    Args:
        voice: Voice model name

    Returns:
        Tuple of (onnx_path, json_path)

    Raises:
        RuntimeError: If model files cannot be found or downloaded
    """
    onnx_path = PIPER_MODELS_DIR / f"{voice}.onnx"
    json_path = PIPER_MODELS_DIR / f"{voice}.onnx.json"

    # If files already exist locally, use them
    if onnx_path.exists() and json_path.exists():
        return onnx_path, json_path

    # Try to download if we know the URL
    if voice in PIPER_VOICE_URLS:
        PIPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)

        import urllib.request

        # Download ONNX model
        onnx_url = PIPER_VOICE_URLS[voice]
        print(f"Downloading voice model: {voice}...")
        urllib.request.urlretrieve(onnx_url, onnx_path)

        # Download JSON config
        json_url = f"{onnx_url}.json"
        urllib.request.urlretrieve(json_url, json_path)

        print(f"Downloaded model to: {PIPER_MODELS_DIR}")
        return onnx_path, json_path

    # Try to find model in current directory or as absolute path
    voice_path = Path(voice)
    if voice_path.suffix == ".onnx":
        onnx_path = voice_path
        json_path = voice_path.with_suffix(".onnx.json")
        if onnx_path.exists() and json_path.exists():
            return onnx_path, json_path

    raise RuntimeError(
        f"Voice model not found: {voice}. "
        f"Available for download: {list(PIPER_VOICE_URLS.keys())}. "
        f"Or provide path to existing .onnx file."
    )


def _generate_edge_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Edge TTS.

    Args:
        text: Text to synthesize
        output_path: Output file path (will be MP3, converted to WAV)
        voice: Edge TTS voice name

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If TTS generation fails
    """
    import edge_tts

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Create communicate instance
        communicate = edge_tts.Communicate(text, voice)

        # Edge TTS outputs MP3, save to temp file first
        mp3_path = output_path.with_suffix(".mp3")

        # Generate audio
        asyncio.run(communicate.save(str(mp3_path)))

        # Convert MP3 to WAV using ffmpeg
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path), "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", str(output_path)],
            capture_output=True,
            text=True
        )

        # Clean up MP3
        if mp3_path.exists():
            mp3_path.unlink()

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

        return output_path
    except Exception as e:
        raise RuntimeError(f"Edge TTS generation failed: {e}")


def _generate_coqui_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Coqui TTS.

    Args:
        text: Text to synthesize
        output_path: Output WAV file path
        voice: Coqui TTS model name

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If TTS generation fails
    """
    from TTS.api import TTS

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize TTS with the specified model
        tts = TTS(model_name=voice, progress_bar=False, gpu=False)

        # Generate audio
        tts.tts_to_file(text=text, file_path=str(output_path))

        return output_path
    except Exception as e:
        raise RuntimeError(f"Coqui TTS generation failed: {e}")


def _generate_piper_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Piper TTS.

    Args:
        text: Text to synthesize
        output_path: Output WAV file path
        voice: Piper voice model name

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If TTS generation fails
    """
    from piper import PiperVoice

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Ensure model files exist
        onnx_path, json_path = _ensure_piper_model_files(voice)

        # Load Piper voice model
        piper_voice = PiperVoice.load(str(onnx_path), config_path=str(json_path))

        # Synthesize audio and collect all chunks
        audio_chunks = []
        sample_rate = 22050  # Default for Piper
        sample_width = 2  # 16-bit
        channels = 1  # Mono

        for chunk in piper_voice.synthesize(text):
            audio_chunks.append(chunk.audio_int16_bytes)
            if hasattr(chunk, 'sample_rate'):
                sample_rate = chunk.sample_rate
            if hasattr(chunk, 'sample_width'):
                sample_width = chunk.sample_width
            if hasattr(chunk, 'sample_channels'):
                channels = chunk.sample_channels

        # Write standard WAV file
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            for chunk_bytes in audio_chunks:
                wav_file.writeframes(chunk_bytes)

        return output_path
    except Exception as e:
        raise RuntimeError(f"Piper TTS generation failed: {e}")


def generate_audio(
    text: str,
    output_path: Path,
    engine: str | None = None,
    voice: str | None = None
) -> Path:
    """Generate Chinese audio from text using TTS.

    Uses Edge TTS as default for better quality and reliability.
    Coqui TTS and Piper TTS are available as alternatives.

    Args:
        text: Chinese text to synthesize
        output_path: Output WAV file path
        engine: TTS engine to use ("edge", "coqui", or "piper"). If None, uses config.
        voice: Voice model name. If None, uses config default.

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If TTS generation fails
    """
    config = get_tts_config()

    if engine is None:
        engine = config.engine

    if engine == "piper":
        voice = voice or config.piper_voice
        return _generate_piper_audio(text, output_path, voice)
    elif engine == "coqui":
        voice = voice or config.coqui_voice
        return _generate_coqui_audio(text, output_path, voice)
    else:
        # Default to Edge TTS
        voice = voice or config.voice
        return _generate_edge_audio(text, output_path, voice)
