"""Text-to-speech using Piper TTS."""

import os
import wave
from pathlib import Path

from piper import PiperVoice

from recut.config import get_tts_config

# Default directory for Piper models
PIPER_MODELS_DIR = Path(os.environ.get("PIPER_MODELS_DIR", "C:/piper_models"))

# Hugging Face URLs for downloading models
PIPER_VOICE_URLS = {
    "zh_CN-huayan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
}


def _ensure_model_files(voice: str) -> tuple[Path, Path]:
    """Ensure model files exist, download if necessary.

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


def generate_audio(
    text: str,
    output_path: Path,
    voice: str | None = None
) -> Path:
    """Generate Chinese audio from text using Piper TTS.

    Args:
        text: Chinese text to synthesize
        output_path: Output WAV file path
        voice: Piper voice model name (optional, uses config default)

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If TTS generation fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if voice is None:
        config = get_tts_config()
        voice = config.voice

    try:
        # Ensure model files exist
        onnx_path, json_path = _ensure_model_files(voice)

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
        raise RuntimeError(f"TTS generation failed: {e}")
