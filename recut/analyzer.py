"""Scene detection and fragment scoring."""

import subprocess
import json
from dataclasses import dataclass
from pathlib import Path


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
        "ffmpeg",
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

    for i, scene_time in enumerate(scenes):
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
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def select_top_fragments(fragments: list[Scene], target_duration: float) -> list[Scene]:
    """Select top-scoring fragments that fit within target duration.

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

    for frag in sorted_fragments:
        frag_duration = frag.end - frag.start
        if total_duration + frag_duration <= target_duration:
            selected.append(frag)
            total_duration += frag_duration

        if total_duration >= target_duration:
            break

    # Sort by start time to maintain original order
    return sorted(selected, key=lambda f: f.start)
