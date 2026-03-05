# tests/test_translator.py
"""Tests for translator module."""

import os
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
