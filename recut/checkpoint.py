# recut/checkpoint.py
"""Checkpoint management for resumable recut workflow."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from recut.analyzer import Scene


def get_checkpoint_dir(output_path: Path) -> Path:
    """Get the checkpoint directory for an output path.

    Args:
        output_path: Path to output video file (e.g., output/name.mp4)

    Returns:
        Path to checkpoint directory (e.g., output/name/)
    """
    return output_path.parent / output_path.stem


def get_name_from_path(path: Path) -> str:
    """Extract name from a directory or file path.

    Args:
        path: Path to checkpoint directory or .md file

    Returns:
        Extracted name (directory name or .md file stem)
    """
    path = Path(path)
    if path.suffix.lower() == ".md":
        return path.stem
    return path.name


def check_progress(checkpoint_dir: Path, name: str) -> dict:
    """Check which steps have been completed based on file existence.

    Args:
        checkpoint_dir: Path to checkpoint directory
        name: Base name for files

    Returns:
        dict with progress flags: raw_video, scenes, transcript, script, dubbing, nodub_video, subtitle, thumbnail
    """
    return {
        "raw_video": (checkpoint_dir / f"{name}_raw.mp4").exists(),
        "scenes": (checkpoint_dir / f"{name}_scenes.json").exists(),
        "transcript": (checkpoint_dir / f"{name}_script.md").exists(),
        "script": (checkpoint_dir.parent / f"{name}.md").exists(),
        "metadata": (checkpoint_dir / f"{name}_metadata.json").exists(),
        "dubbing": (checkpoint_dir / f"{name}_dubbing.wav").exists(),
        "nodub_video": (checkpoint_dir / f"{name}_nodub.mp4").exists(),
        "subtitle": (checkpoint_dir / f"{name}.srt").exists(),
        "thumbnail": (checkpoint_dir / f"{name}_thumb.jpg").exists(),
    }


def save_scenes(scenes: list[Scene], path: Path) -> None:
    """Save scenes to JSON file.

    Args:
        scenes: List of Scene objects
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "fragments": [
            {"start": s.start, "end": s.end, "score_change_count": s.score_change_count}
            for s in scenes
        ]
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_scenes(path: Path) -> list[Scene]:
    """Load scenes from JSON file.

    Args:
        path: Input file path

    Returns:
        List of Scene objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Scenes file not found: {path}")

    raw_bytes = path.read_bytes()
    encodings = ["utf-8", "gbk", "gb18030"]

    data = None
    for encoding in encodings:
        try:
            data = json.loads(raw_bytes.decode(encoding))
            break
        except UnicodeDecodeError:
            continue

    if data is None:
        raise ValueError(f"Failed to decode scenes file: {path}")
    if "fragments" not in data:
        raise ValueError(f"Invalid scenes file format: missing 'fragments' key")

    return [
        Scene(
            start=f["start"],
            end=f["end"],
            score_change_count=f.get("score_change_count", 0)
        )
        for f in data["fragments"]
    ]


def save_metadata(metadata: dict, path: Path) -> None:
    """Save metadata to JSON file.

    Args:
        metadata: Metadata dictionary
        path: Output file path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def load_metadata(path: Path) -> dict:
    """Load metadata from JSON file.

    Args:
        path: Input file path

    Returns:
        Metadata dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file cannot be decoded or parsed
    """
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    raw_bytes = path.read_bytes()
    encodings = ["utf-8", "gbk", "gb18030"]

    for encoding in encodings:
        try:
            return json.loads(raw_bytes.decode(encoding))
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Failed to decode metadata file: {path}")


def create_metadata(
    source_url: str,
    platform: str,
    scene_threshold: float,
    duration: int,
    title: str | None = None,
    chs_title: str | None = None,
    image: str | None = None,
    tts_engine: str | None = None,
) -> dict:
    """Create metadata dictionary.

    Args:
        source_url: Source video URL
        platform: Target platform
        scene_threshold: Scene detection threshold
        duration: Target duration in seconds
        title: Optional English title
        chs_title: Optional Chinese title
        image: Optional image URL/path
        tts_engine: Optional TTS engine name

    Returns:
        Metadata dictionary
    """
    metadata = {
        "source_url": source_url,
        "platform": platform,
        "scene_threshold": scene_threshold,
        "duration": duration,
        "created_at": datetime.now().isoformat(),
    }
    if title:
        metadata["title"] = title
    if chs_title:
        metadata["chs_title"] = chs_title
    if image:
        metadata["image"] = image
    if tts_engine:
        metadata["tts_engine"] = tts_engine
    return metadata
