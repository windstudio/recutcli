# tests/test_analyzer.py
from recut.analyzer import Scene, score_fragment, select_top_fragments


def test_score_fragment_prefers_medium_length():
    fragment = Scene(start=0.0, end=5.0, score_change_count=3)
    score = score_fragment(fragment)
    assert score > 0


def test_score_fragment_penalizes_short():
    short = Scene(start=0.0, end=1.0, score_change_count=1)
    medium = Scene(start=0.0, end=5.0, score_change_count=1)
    assert score_fragment(short) < score_fragment(medium)


def test_score_fragment_penalizes_long():
    long_frag = Scene(start=0.0, end=15.0, score_change_count=3)
    medium = Scene(start=0.0, end=5.0, score_change_count=3)
    assert score_fragment(long_frag) < score_fragment(medium)


def test_select_top_fragments_respects_duration():
    """Test that fragments try to reach target, adding more if initial selection insufficient."""
    # 3 fragments of 10s each = 30s total available
    # Requesting 15s: first fragment (10s) fits, but total < target
    # Second fragment (10s) is added to get closer to target
    fragments = [
        Scene(start=0.0, end=10.0, score_change_count=5),
        Scene(start=10.0, end=20.0, score_change_count=3),
        Scene(start=20.0, end=30.0, score_change_count=1),
    ]
    selected = select_top_fragments(fragments, target_duration=15.0)
    total = sum(f.end - f.start for f in selected)
    # First pass: 10s selected (< 15s target)
    # Second pass: adds 10s more to approach target
    assert total == 20.0  # Closest we can get without exceeding too much
    assert len(selected) == 2


def test_select_top_fragments_exact_fit():
    """Test that fragments fit exactly when enough small fragments available."""
    # Many small fragments - can fit target exactly
    fragments = [
        Scene(start=0.0, end=5.0, score_change_count=5),
        Scene(start=5.0, end=10.0, score_change_count=4),
        Scene(start=10.0, end=15.0, score_change_count=3),
        Scene(start=15.0, end=20.0, score_change_count=2),
        Scene(start=20.0, end=25.0, score_change_count=1),
    ]
    selected = select_top_fragments(fragments, target_duration=15.0)
    total = sum(f.end - f.start for f in selected)
    # Top 3 fragments (5s each) = 15s exactly
    assert total == 15.0
    assert len(selected) == 3


def test_select_top_fragments_adds_more_when_insufficient():
    """Test that lower-scoring fragments are added when high-scoring ones insufficient."""
    # 2 fragments of 5s each = 10s total available
    # Requesting 20s should select all fragments even though they don't fill target
    fragments = [
        Scene(start=0.0, end=5.0, score_change_count=5),
        Scene(start=5.0, end=10.0, score_change_count=3),
    ]
    selected = select_top_fragments(fragments, target_duration=20.0)
    total = sum(f.end - f.start for f in selected)
    # All fragments selected, total exceeds target but that's all we have
    assert total == 10.0
    assert len(selected) == 2


def test_select_top_fragments_returns_time_ordered():
    fragments = [
        Scene(start=20.0, end=25.0, score_change_count=5),  # High score, late
        Scene(start=0.0, end=5.0, score_change_count=1),    # Low score, early
    ]
    selected = select_top_fragments(fragments, target_duration=10.0)
    # Should be ordered by start time, not score
    assert selected[0].start < selected[1].start


def test_select_top_fragments_empty_input():
    assert select_top_fragments([], 25.0) == []
