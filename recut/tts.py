"""Text-to-speech using Edge TTS (default), Coqui TTS, or Piper TTS."""

import asyncio
import os
import subprocess
import wave
from pathlib import Path

from recut.config import get_tts_config


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

# Default directory for Piper models
PIPER_MODELS_DIR = Path(os.environ.get("PIPER_MODELS_DIR", "C:/piper_models"))

# Hugging Face URLs for downloading Piper models
PIPER_VOICE_URLS = {
    "zh_CN-huayan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
}


def _ensure_output_dir(output_path: Path) -> None:
    """Ensure output directory exists."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)


def _ensure_piper_model_files(voice: str) -> tuple[Path, Path]:
    """Ensure Piper model files exist, download if necessary."""
    onnx_path = PIPER_MODELS_DIR / f"{voice}.onnx"
    json_path = PIPER_MODELS_DIR / f"{voice}.onnx.json"

    if onnx_path.exists() and json_path.exists():
        return onnx_path, json_path

    if voice in PIPER_VOICE_URLS:
        import urllib.request

        PIPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        onnx_url = PIPER_VOICE_URLS[voice]
        print(f"Downloading voice model: {voice}...")
        urllib.request.urlretrieve(onnx_url, onnx_path)
        urllib.request.urlretrieve(f"{onnx_url}.json", json_path)
        print(f"Downloaded model to: {PIPER_MODELS_DIR}")
        return onnx_path, json_path

    # Try as absolute path
    voice_path = Path(voice)
    if voice_path.suffix == ".onnx":
        json_path = voice_path.with_suffix(".onnx.json")
        if voice_path.exists() and json_path.exists():
            return voice_path, json_path

    raise RuntimeError(
        f"Voice model not found: {voice}. "
        f"Available for download: {list(PIPER_VOICE_URLS.keys())}. "
        f"Or provide path to existing .onnx file."
    )


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
            ["ffmpeg", "-y", "-i", str(mp3_path), "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", str(output_path)],
            capture_output=True, text=True
        )

        if mp3_path.exists():
            mp3_path.unlink()

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {result.stderr}")

        return output_path
    except Exception as e:
        raise RuntimeError(f"Edge TTS generation failed: {e}")


def _generate_coqui_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Coqui TTS."""
    from TTS.api import TTS

    output_path = Path(output_path)
    _ensure_output_dir(output_path)

    try:
        tts = TTS(model_name=voice, progress_bar=False, gpu=False)
        tts.tts_to_file(text=text, file_path=str(output_path))
        return output_path
    except Exception as e:
        raise RuntimeError(f"Coqui TTS generation failed: {e}")


def _generate_piper_audio(text: str, output_path: Path, voice: str) -> Path:
    """Generate audio using Piper TTS."""
    from piper import PiperVoice

    output_path = Path(output_path)
    _ensure_output_dir(output_path)

    try:
        onnx_path, json_path = _ensure_piper_model_files(voice)
        piper_voice = PiperVoice.load(str(onnx_path), config_path=str(json_path))

        audio_chunks = []
        sample_rate, sample_width, channels = 22050, 2, 1

        for chunk in piper_voice.synthesize(text):
            audio_chunks.append(chunk.audio_int16_bytes)
            if hasattr(chunk, 'sample_rate'):
                sample_rate = chunk.sample_rate
            if hasattr(chunk, 'sample_width'):
                sample_width = chunk.sample_width
            if hasattr(chunk, 'sample_channels'):
                channels = chunk.sample_channels

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

    Args:
        text: Chinese text to synthesize
        output_path: Output WAV file path
        engine: TTS engine ("edge", "coqui", or "piper"). Default: edge
        voice: Voice model name. Default: engine-specific default

    Returns:
        Path to generated audio file
    """
    config = get_tts_config()
    engine = engine or config.engine

    if engine == "piper":
        voice = voice or config.piper_voice
        return _generate_piper_audio(text, output_path, voice)
    elif engine == "coqui":
        voice = voice or config.coqui_voice
        return _generate_coqui_audio(text, output_path, voice)
    else:
        voice = voice or config.voice
        return _generate_edge_audio(text, output_path, voice)
