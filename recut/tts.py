"""Text-to-speech using Piper TTS."""

from pathlib import Path

from piper import PiperVoice

from recut.config import get_tts_config


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
        # Load Piper voice model
        piper_voice = PiperVoice.load(voice)

        # Synthesize audio
        with open(output_path, "wb") as audio_file:
            piper_voice.synthesize(text, audio_file)

        return output_path
    except Exception as e:
        raise RuntimeError(f"TTS generation failed: {e}")
