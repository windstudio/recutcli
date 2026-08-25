"""Scene detection and fragment scoring."""

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from recut.downloader import get_ffmpeg_path, run_ffmpeg


@dataclass
class Scene:
    """A video scene/fragment."""
    start: float
    end: float
    motion_intensity: int = 0  # Motion intensity score (multiplied by 100 for int storage)


def score_fragment(fragment: Scene) -> float:
    """Score a video fragment based on motion intensity and duration.

    Higher scores indicate more interesting content.
    motion_intensity stores motion intensity * 100.
    """
    duration = fragment.end - fragment.start

    if duration <= 0:
        return 0.0

    # Motion score (stored as int * 100, convert back to float)
    motion_score = fragment.motion_intensity / 100.0

    # Duration penalty (too short or too long is less ideal)
    if duration < 2:
        duration_penalty = duration / 2  # Penalize very short clips
    elif duration > 10:
        duration_penalty = 10 / duration  # Penalize very long clips
    else:
        duration_penalty = 1.0  # No penalty for ideal range

    return motion_score * duration_penalty


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

    result = run_ffmpeg(cmd)

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
            fragments.append(Scene(start=prev_time, end=scene_time))
        prev_time = scene_time

    # Add final fragment
    if prev_time < duration:
        fragments.append(Scene(start=prev_time, end=duration))

    # Calculate motion score for each fragment
    for i, frag in enumerate(fragments):
        motion_score = calculate_motion_score(video_path, frag.start, frag.end)
        # Multiply by 100 to store as integer (preserves 2 decimal places)
        fragments[i] = Scene(
            start=frag.start,
            end=frag.end,
            motion_intensity=int(motion_score * 100)
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

    result = run_ffmpeg(cmd)
    # Parse duration from stderr (ffmpeg outputs info to stderr)
    # Look for "Duration: HH:MM:SS.mmm" in the output
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    return 0.0


def calculate_motion_score(video_path: Path, start: float, end: float) -> float:
    """Calculate motion intensity for a video segment.

    Samples frames and calculates average pixel difference between consecutive frames.

    Args:
        video_path: Path to video file
        start: Start time in seconds
        end: End time in seconds

    Returns:
        Average frame difference (0.0-255.0), 0.0 if calculation fails
    """
    duration = end - start
    if duration <= 0:
        return 0.0

    # Sample up to 10 frames (~2 per second, max 10)
    num_samples = min(10, max(2, int(duration * 2)))

    with tempfile.TemporaryDirectory() as tmpdir:
        output_pattern = os.path.join(tmpdir, "frame_%03d.png")

        # Extract evenly spaced frames
        cmd = [
            get_ffmpeg_path(), "-ss", str(start), "-i", str(video_path),
            "-t", str(duration),
            "-vf", f"fps=1/{duration/(num_samples-1):.3f}",
            "-vsync", "vfr", "-q:v", "2",
            output_pattern
        ]
        run_ffmpeg(cmd)

        frames = sorted(f for f in os.listdir(tmpdir) if f.startswith("frame_") and f.endswith(".png"))

        if len(frames) < 2:
            # Fallback: extract every 10th frame
            cmd = [
                get_ffmpeg_path(), "-ss", str(start), "-i", str(video_path),
                "-t", str(duration),
                "-vf", r"select='not(mod(n\,10))'",
                "-vsync", "vfr", "-q:v", "2",
                output_pattern
            ]
            run_ffmpeg(cmd)
            frames = sorted(f for f in os.listdir(tmpdir) if f.startswith("frame_") and f.endswith(".png"))

        if len(frames) < 2:
            return 0.0

        # Calculate average difference between consecutive frames
        try:
            from PIL import Image
            import numpy as np

            diffs = []
            prev_frame = None
            for frame_file in frames:
                img = Image.open(os.path.join(tmpdir, frame_file)).convert('L')
                arr = np.array(img, dtype=np.float32)
                if prev_frame is not None:
                    diffs.append(np.mean(np.abs(arr - prev_frame)))
                prev_frame = arr

            return sum(diffs) / len(diffs) if diffs else 0.0

        except ImportError:
            return _calculate_motion_via_ffmpeg(video_path, start, end)


def _calculate_motion_via_ffmpeg(video_path: Path, start: float, end: float) -> float:
    """Fallback motion calculation using ffmpeg's tblend filter."""
    duration = end - start
    if duration <= 0:
        return 0.0

    cmd = [
        get_ffmpeg_path(), "-ss", str(start), "-i", str(video_path),
        "-t", str(duration),
        "-vf", "tblend=all_mode=difference,signalstats",
        "-f", "null", "-"
    ]
    result = run_ffmpeg(cmd)

    # Parse YAVG from signalstats (average luma after difference = motion intensity)
    yavg_values = []
    for line in result.stderr.split("\n"):
        if "YAVG:" in line:
            try:
                yavg_values.append(float(line.split("YAVG:")[1].split()[0]))
            except (IndexError, ValueError):
                continue

    return sum(yavg_values) / len(yavg_values) if yavg_values else 0.0


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
            {"start": s.start, "end": s.end, "motion_intensity": s.motion_intensity}
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
            # Accept legacy field name score_change_count from older scenes.json files
            motion_intensity=f.get("motion_intensity", f.get("score_change_count", 0))
        )
        for f in data["fragments"]
    ]
