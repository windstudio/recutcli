# tests/test_editor.py
from recut.editor import format_timestamp

def test_format_timestamp_seconds():
    assert format_timestamp(5.5) == "00:00:05.500"

def test_format_timestamp_minutes():
    assert format_timestamp(65.5) == "00:01:05.500"

def test_format_timestamp_hours():
    assert format_timestamp(3661.5) == "01:01:01.500"
