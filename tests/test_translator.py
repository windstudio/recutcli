# tests/test_translator.py
"""Tests for translator module."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_translate_and_generate_metadata_with_title(monkeypatch):
    """Test metadata generation when English title is provided."""
    from recut.translator import translate_and_generate_metadata

    calls = []

    def mock_create(**kwargs):
        calls.append(kwargs)
        return type('Response', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': "---TITLE---\n测试标题\n---TRANSCRIPT---\n第一句\n第二句\n---TAGS---\n标签1,标签2,标签3"
                })
            })]
        })()

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    result = translate_and_generate_metadata(
        english_text="Hello world",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        duration=30,
        english_title="Test English Title"
    )

    assert result["title"] == "测试标题"
    assert result["transcript"] == "第一句\n第二句"
    assert result["tags"] == ["标签1", "标签2", "标签3"]


def test_translate_and_generate_metadata_without_title(monkeypatch):
    """Test metadata generation when no English title provided."""
    from recut.translator import translate_and_generate_metadata

    def mock_create(**kwargs):
        return type('Response', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': "---TITLE---\n自动生成标题\n---TRANSCRIPT---\n内容\n---TAGS---\n标签A,标签B"
                })
            })]
        })()

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    result = translate_and_generate_metadata(
        english_text="Some content",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        duration=30,
        english_title=None
    )

    assert result["title"] == "自动生成标题"
    assert result["transcript"] == "内容"
    assert result["tags"] == ["标签A", "标签B"]


def test_translate_and_generate_metadata_raises_on_error(monkeypatch):
    """Test that translate_and_generate_metadata raises on API error."""
    from recut.translator import translate_and_generate_metadata

    def mock_create(**kwargs):
        raise Exception("API Error")

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    with pytest.raises(RuntimeError, match="Metadata generation failed"):
        translate_and_generate_metadata(
            "test",
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model"
        )


def test_translate_and_generate_metadata_empty_response(monkeypatch):
    """Test that translate_and_generate_metadata raises on empty response."""
    from recut.translator import translate_and_generate_metadata

    def mock_create(**kwargs):
        return type('Response', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': None
                })
            })]
        })()

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    with pytest.raises(RuntimeError, match="empty response"):
        translate_and_generate_metadata(
            "test",
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model"
        )


# Tests for parse_metadata_response

def test_parse_metadata_response_normal():
    """Test normal response parsing."""
    from recut.translator import parse_metadata_response

    response = "---TITLE---\n标题\n---TRANSCRIPT---\n内容\n---TAGS---\n标签1,标签2"
    result = parse_metadata_response(response)
    assert result["title"] == "标题"
    assert result["transcript"] == "内容"
    assert result["tags"] == ["标签1", "标签2"]


def test_parse_metadata_response_missing_title():
    """Test error when TITLE section missing."""
    from recut.translator import parse_metadata_response

    with pytest.raises(ValueError, match="missing TITLE"):
        parse_metadata_response("---TRANSCRIPT---\n内容\n---TAGS---\n标签")


def test_parse_metadata_response_missing_transcript():
    """Test error when TRANSCRIPT section missing."""
    from recut.translator import parse_metadata_response

    with pytest.raises(ValueError, match="missing TRANSCRIPT"):
        parse_metadata_response("---TITLE---\n标题\n---TAGS---\n标签")


def test_parse_metadata_response_missing_tags():
    """Test error when TAGS section missing."""
    from recut.translator import parse_metadata_response

    with pytest.raises(ValueError, match="missing TAGS"):
        parse_metadata_response("---TITLE---\n标题\n---TRANSCRIPT---\n内容")


def test_parse_metadata_response_empty_tags():
    """Test handling of empty tags string."""
    from recut.translator import parse_metadata_response

    response = "---TITLE---\n标题\n---TRANSCRIPT---\n内容\n---TAGS---\n"
    result = parse_metadata_response(response)
    assert result["tags"] == []


def test_parse_metadata_response_tags_with_spaces():
    """Test tags with extra whitespace are trimmed."""
    from recut.translator import parse_metadata_response

    response = "---TITLE---\n标题\n---TRANSCRIPT---\n内容\n---TAGS---\n标签1 , 标签2 , 标签3"
    result = parse_metadata_response(response)
    assert result["tags"] == ["标签1", "标签2", "标签3"]


# Tests for save_chinese_script

def test_save_chinese_script():
    """Test saving Chinese script with title, transcript, and tags."""
    from recut.translator import save_chinese_script

    metadata = {
        "title": "测试标题",
        "transcript": "第一句文案\n第二句文案\n第三句文案",
        "tags": ["键盘", "机械键盘", "Keytron", "游戏外设", "办公设备", "无线键盘", "RGB灯光", "轻薄便携"]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_chs.md"
        save_chinese_script(output_path, metadata)

        content = output_path.read_text(encoding="utf-8")

        assert "# Title\n测试标题" in content
        assert "# Transcript\n第一句文案" in content
        assert "# Tags\n#键盘 #机械键盘 #Keytron" in content


def test_save_chinese_script_empty_tags():
    """Test saving Chinese script with empty tags."""
    from recut.translator import save_chinese_script

    metadata = {
        "title": "测试标题",
        "transcript": "内容",
        "tags": []
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_chs.md"
        save_chinese_script(output_path, metadata)

        content = output_path.read_text(encoding="utf-8")
        assert "# Tags\n" in content


def test_save_chinese_script_missing_keys():
    """Test that save_chinese_script raises on missing keys."""
    from recut.translator import save_chinese_script

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_chs.md"
        with pytest.raises(ValueError, match="missing required keys"):
            save_chinese_script(output_path, {"title": "test"})


def test_save_chinese_script_with_source_url():
    """Test saving Chinese script with source URL."""
    from recut.translator import save_chinese_script

    metadata = {
        "title": "测试标题",
        "transcript": "内容文案",
        "tags": ["标签1", "标签2"]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_chs.md"
        save_chinese_script(output_path, metadata, source_url="https://example.com/video/123")

        content = output_path.read_text(encoding="utf-8")

        assert "# Title\n测试标题" in content
        assert "# Transcript\n内容文案" in content
        assert "# Tags\n#标签1 #标签2" in content
        assert "# Source URL\nhttps://example.com/video/123" in content


def test_save_chinese_script_without_source_url():
    """Test saving Chinese script without source URL (backward compatibility)."""
    from recut.translator import save_chinese_script

    metadata = {
        "title": "测试标题",
        "transcript": "内容文案",
        "tags": ["标签1"]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_chs.md"
        save_chinese_script(output_path, metadata, source_url=None)

        content = output_path.read_text(encoding="utf-8")

        assert "# Title\n测试标题" in content
        assert "Source URL" not in content


# Tests for chs_title parameter

def test_translate_and_generate_metadata_with_chs_title_override(monkeypatch):
    """Test that chs_title overrides LLM-generated title."""
    from recut.translator import translate_and_generate_metadata

    def mock_create(**kwargs):
        return type('Response', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': "---TITLE---\nLLM生成的标题\n---TRANSCRIPT---\n第一句\n第二句\n---TAGS---\n标签1,标签2"
                })
            })]
        })()

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    result = translate_and_generate_metadata(
        english_text="Hello world",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        duration=30,
        chs_title="自定义中文标题"
    )

    # Title should be overridden by chs_title
    assert result["title"] == "自定义中文标题"
    assert result["transcript"] == "第一句\n第二句"
    assert result["tags"] == ["标签1", "标签2"]


def test_translate_and_generate_metadata_with_empty_chs_title(monkeypatch):
    """Test that empty chs_title does not override LLM-generated title."""
    from recut.translator import translate_and_generate_metadata

    def mock_create(**kwargs):
        return type('Response', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': "---TITLE---\nLLM生成的标题\n---TRANSCRIPT---\n内容\n---TAGS---\n标签"
                })
            })]
        })()

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    # Empty string should not override
    result = translate_and_generate_metadata(
        english_text="test",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        duration=30,
        chs_title=""
    )
    assert result["title"] == "LLM生成的标题"

    # Whitespace-only string should not override
    result = translate_and_generate_metadata(
        english_text="test",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        duration=30,
        chs_title="   "
    )
    assert result["title"] == "LLM生成的标题"


def test_translate_and_generate_metadata_without_chs_title(monkeypatch):
    """Test that None chs_title uses LLM-generated title."""
    from recut.translator import translate_and_generate_metadata

    def mock_create(**kwargs):
        return type('Response', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {
                    'content': "---TITLE---\nLLM生成的标题\n---TRANSCRIPT---\n内容\n---TAGS---\n标签"
                })
            })]
        })()

    monkeypatch.setattr("recut.translator.OpenAI", lambda **kw: type('Client', (), {
        'chat': type('Chat', (), {
            'completions': type('Completions', (), {'create': mock_create})
        })
    })())

    result = translate_and_generate_metadata(
        english_text="test",
        api_key="test-key",
        base_url="https://api.test.com/v1",
        model="test-model",
        duration=30,
        chs_title=None
    )
    assert result["title"] == "LLM生成的标题"
