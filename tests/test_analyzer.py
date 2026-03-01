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
    fragments = [
        Scene(start=0.0, end=10.0, score_change_count=5),
        Scene(start=10.0, end=20.0, score_change_count=3),
        Scene(start=20.0, end=30.0, score_change_count=1),
    ]
    selected = select_top_fragments(fragments, target_duration=15.0)
    total = sum(f.end - f.start for f in selected)
    assert total <= 15.0


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
