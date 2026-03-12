"""Scene detection and fragment scoring."""

import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

from recut.downloader import get_ffmpeg_path


@dataclass
class Scene:
    """A video scene/fragment."""
    start: float
    end: float
    score_change_count: int = 0


def score_fragment(fragment: Scene) -> float:
    """Score a video fragment based on scene changes and duration.

    Higher scores indicate more interesting content.
    """
    duration = fragment.end - fragment.start

    if duration <= 0:
        return 0.0

    # Scene change count (more changes = more interesting)
    scene_score = float(fragment.score_change_count)

    # Duration penalty (too short or too long is less ideal)
    if duration < 2:
        duration_penalty = duration / 2  # Penalize very short clips
    elif duration > 10:
        duration_penalty = 10 / duration  # Penalize very long clips
    else:
        duration_penalty = 1.0  # No penalty for ideal range

    return scene_score * duration_penalty


def detect_scenes(video_path: Path, threshold: float = 0.3) -> list[Scene]:
    """Detect scene changes in video using ffmpeg.

    Args:
        video_path: Path to video file
        threshold: Scene change detection threshold (0-1)

    Returns:
        List of Scene objects with timestamps
    """
    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse scene change timestamps from stderr
    scenes = []
    lines = result.stderr.split("\n")

    for line in lines:
        if "pts_time:" in line:
            # Extract timestamp from showinfo output
            try:
                time_str = line.split("pts_time:")[1].split()[0]
                timestamp = float(time_str)
                scenes.append(timestamp)
            except (IndexError, ValueError):
                continue

    # Convert timestamps to scenes (intervals between scene changes)
    if not scenes:
        return []

    # Get video duration to create final scene
    duration = get_video_duration(video_path)

    fragments = []
    prev_time = 0.0

    for scene_time in scenes:
        if scene_time > prev_time:
            fragments.append(Scene(start=prev_time, end=scene_time, score_change_count=1))
        prev_time = scene_time

    # Add final fragment
    if prev_time < duration:
        fragments.append(Scene(start=prev_time, end=duration, score_change_count=0))

    # Score each fragment based on scene changes within it
    for i, frag in enumerate(fragments):
        # Count how many scene changes fall within this fragment
        changes = sum(1 for s in scenes if frag.start < s < frag.end)
        fragments[i] = Scene(
            start=frag.start,
            end=frag.end,
            score_change_count=changes + 1  # +1 for the scene that created this fragment
        )

    return fragments


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffmpeg."""
    # Use ffmpeg to get duration from the input file
    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-f", "null",
        "-"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse duration from stderr (ffmpeg outputs info to stderr)
    # Look for "Duration: HH:MM:SS.mmm" in the output
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


def select_top_fragments(fragments: list[Scene], target_duration: float) -> list[Scene]:
    """Select top-scoring fragments that fit within target duration.

    If high-scoring fragments don't fill the target duration, continues adding
    lower-scoring fragments until target is reached or all fragments are used.

    Args:
        fragments: List of scored fragments
        target_duration: Target total duration in seconds

    Returns:
        List of selected fragments, sorted by original time order
    """
    if not fragments:
        return []

    # Sort by score (descending)
    sorted_fragments = sorted(fragments, key=lambda f: score_fragment(f), reverse=True)

    selected = []
    total_duration = 0.0

    # First pass: greedily add fragments that fit
    for frag in sorted_fragments:
        frag_duration = frag.end - frag.start
        if total_duration + frag_duration <= target_duration:
            selected.append(frag)
            total_duration += frag_duration

        if total_duration >= target_duration:
            break

    # If target duration not reached, add remaining fragments even if they exceed target
    if total_duration < target_duration:
        for frag in sorted_fragments:
            if frag not in selected:
                selected.append(frag)
                total_duration += frag.end - frag.start
                if total_duration >= target_duration:
                    break

    # Sort by start time to maintain original order
    return sorted(selected, key=lambda f: f.start)


def save_scenes_to_json(scenes: list[Scene], path: Path) -> None:
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


def load_scenes_from_json(path: Path) -> list[Scene]:
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

    data = json.loads(path.read_text(encoding="utf-8"))
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
