# tests/test_translator.py
"""Tests for translator module."""

from unittest.mock import patch, MagicMock

import pytest


def test_translate_and_refine_returns_chinese_text():
    """Test translate_and_refine returns Chinese text."""
    from recut.translator import translate_and_refine

    with patch("recut.translator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = client = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="这是一个测试文案"))]
        )

        result = translate_and_refine(
            "Hello world",
            api_key="test-key",
            base_url="https://test.com/v1"
        )

        assert "测试" in result
        mock_client.chat.completions.create.assert_called_once()


def test_translate_and_refine_structure():
    """Test that API call uses correct model and prompt structure."""
    from recut.translator import translate_and_refine

    with patch("recut.translator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="结果"))]
        )

        translate_and_refine(
            "English text here",
            api_key="test-key",
            base_url="https://test.com/v1"
        )

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "glm-5"
        assert "English text here" in str(call_args.kwargs["messages"])


def test_translate_and_refine_raises_on_error():
    """Test that translate_and_refine raises on API error."""
    from recut.translator import translate_and_refine

    with patch("recut.translator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Translation failed"):
            translate_and_refine("test", api_key="test-key")


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
        translate_and_generate_metadata("test", api_key="test-key")


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
        translate_and_generate_metadata("test", api_key="test-key")


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
