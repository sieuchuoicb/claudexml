"""Tests for Anthropic SDK integration."""

from dataclasses import dataclass

import pytest

from claudexml import XMLModel, XMLTag, parse_response


# Mock Anthropic response objects for testing
@dataclass
class MockTextBlock:
    text: str
    type: str = "text"


@dataclass
class MockMessage:
    content: list[MockTextBlock]
    role: str = "assistant"


class SimpleModel(XMLModel):
    answer: str = XMLTag("answer")
    thinking: str | None = XMLTag("thinking", default=None)


class TestParseResponse:
    def test_mock_message(self):
        response = MockMessage(
            content=[MockTextBlock(text="<thinking>hmm</thinking><answer>42</answer>")]
        )
        result = parse_response(response, SimpleModel)
        assert result.answer == "42"
        assert result.thinking == "hmm"

    def test_string_input(self):
        result = parse_response("<answer>42</answer>", SimpleModel)
        assert result.answer == "42"

    def test_multiple_text_blocks(self):
        response = MockMessage(
            content=[
                MockTextBlock(text="<thinking>step 1</thinking>"),
                MockTextBlock(text="<answer>42</answer>"),
            ]
        )
        result = parse_response(response, SimpleModel)
        assert result.answer == "42"

    def test_invalid_input_type(self):
        with pytest.raises(TypeError):
            parse_response(12345, SimpleModel)

    def test_dict_content_blocks(self):
        """Test with dict-style content blocks."""

        class FakeResponse:
            content = [{"text": "<answer>42</answer>", "type": "text"}]

        result = parse_response(FakeResponse(), SimpleModel)
        assert result.answer == "42"
