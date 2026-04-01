"""Tests for XMLStreamParser."""

import pytest

from claudexml import (
    ParseError,
    ValidationError,
    XMLModel,
    XMLStreamParser,
    XMLTag,
    field_validator,
)


class SimpleModel(XMLModel):
    thinking: str = XMLTag("thinking")
    answer: str = XMLTag("answer")


class OptionalModel(XMLModel):
    answer: str = XMLTag("answer")
    thinking: str | None = XMLTag("thinking", default=None)


class TestXMLStreamParser:
    def test_complete_in_one_chunk(self):
        parser = XMLStreamParser(SimpleModel)
        parser.feed("<thinking>hmm</thinking><answer>42</answer>")
        assert parser.is_complete()
        result = parser.result()
        assert result.thinking == "hmm"
        assert result.answer == "42"

    def test_incremental_feed(self):
        parser = XMLStreamParser(SimpleModel)

        parser.feed("<thinking>")
        assert not parser.is_complete()

        parser.feed("Let me think</thinking>")
        assert not parser.is_complete()  # answer still missing

        parser.feed("<answer>42</answer>")
        assert parser.is_complete()

        result = parser.result()
        assert result.thinking == "Let me think"
        assert result.answer == "42"

    def test_partial_returns_defaults(self):
        parser = XMLStreamParser(OptionalModel)
        partial = parser.partial()
        assert partial.answer is None  # required but not found -> None
        assert partial.thinking is None  # optional with default None

    def test_partial_fills_progressively(self):
        parser = XMLStreamParser(SimpleModel)

        parser.feed("<thinking>step 1</thinking>")
        partial = parser.partial()
        assert partial.thinking == "step 1"
        assert partial.answer is None

        parser.feed("<answer>42</answer>")
        partial = parser.partial()
        assert partial.thinking == "step 1"
        assert partial.answer == "42"

    def test_result_raises_when_incomplete(self):
        parser = XMLStreamParser(SimpleModel)
        parser.feed("<thinking>hmm</thinking>")

        with pytest.raises(ParseError, match="not complete"):
            parser.result()

    def test_tags_split_across_feeds(self):
        parser = XMLStreamParser(SimpleModel)
        parser.feed("<thin")
        parser.feed("king>hello</think")
        parser.feed("ing><answer>42</answer>")

        assert parser.is_complete()
        result = parser.result()
        assert result.thinking == "hello"
        assert result.answer == "42"

    def test_empty_feed(self):
        parser = XMLStreamParser(SimpleModel)
        parser.feed("")
        parser.feed("")
        assert not parser.is_complete()

    def test_reset(self):
        parser = XMLStreamParser(SimpleModel)
        parser.feed("<thinking>hmm</thinking><answer>42</answer>")
        assert parser.is_complete()

        parser.reset()
        assert not parser.is_complete()
        partial = parser.partial()
        assert partial.thinking is None
        assert partial.answer is None

    def test_matches_from_xml(self):
        """Stream result should match direct from_xml."""
        xml = "<thinking>deep thought</thinking><answer>42</answer>"

        direct = SimpleModel.from_xml(xml)
        parser = XMLStreamParser(SimpleModel)
        parser.feed(xml)
        streamed = parser.result()

        assert direct == streamed

    def test_type_coercion(self):
        class Scored(XMLModel):
            score: float = XMLTag("score")

        parser = XMLStreamParser(Scored)
        parser.feed("<score>0.95</score>")
        result = parser.result()
        assert result.score == 0.95
        assert isinstance(result.score, float)

    def test_partial_skips_validation(self):
        class Bounded(XMLModel):
            score: float = XMLTag("score")

            @field_validator("score")
            def check_range(cls, v):
                if not 0 <= v <= 1:
                    raise ValueError("out of range")
                return v

        parser = XMLStreamParser(Bounded)
        parser.feed("<score>5.0</score>")
        # partial() should NOT raise even though value is out of range
        partial = parser.partial()
        assert partial.score == 5.0

    def test_result_runs_validation(self):
        class Bounded(XMLModel):
            score: float = XMLTag("score")

            @field_validator("score")
            def check_range(cls, v):
                if not 0 <= v <= 1:
                    raise ValueError("out of range")
                return v

        parser = XMLStreamParser(Bounded)
        parser.feed("<score>5.0</score>")
        with pytest.raises(ValidationError):
            parser.result()

    def test_with_attributes(self):
        class Item(XMLModel):
            name: str = XMLTag("item")
            item_id: str = XMLTag("item", attribute="id")

        parser = XMLStreamParser(Item)
        parser.feed('<item id="123">Widget</item>')
        assert parser.is_complete()
        result = parser.result()
        assert result.name == "Widget"
        assert result.item_id == "123"

    def test_with_cdata(self):
        class Code(XMLModel):
            code: str = XMLTag("code")

        parser = XMLStreamParser(Code)
        parser.feed("<code><![CDATA[x < 5 && y > 3]]></code>")
        result = parser.result()
        assert result.code == "x < 5 && y > 3"

    def test_list_accumulation(self):
        class Review(XMLModel):
            issues: list[str] = XMLTag("issue")

        parser = XMLStreamParser(Review)
        parser.feed("<issue>bug 1</issue>")
        partial = parser.partial()
        assert partial.issues == ["bug 1"]

        parser.feed("<issue>bug 2</issue>")
        partial = parser.partial()
        assert partial.issues == ["bug 1", "bug 2"]

    def test_realistic_claude_stream(self):
        """Simulate a realistic token-by-token Claude stream."""

        class Analysis(XMLModel):
            thinking: str = XMLTag("thinking")
            answer: str = XMLTag("answer")
            confidence: float = XMLTag("confidence")

        parser = XMLStreamParser(Analysis)
        tokens = [
            "<thinking>",
            "The user asks about",
            " the meaning of life.",
            "</thinking>",
            "\n<answer>",
            "42",
            "</answer>",
            "\n<confidence>",
            "0.95",
            "</confidence>",
        ]

        for token in tokens:
            parser.feed(token)

        assert parser.is_complete()
        result = parser.result()
        assert "meaning of life" in result.thinking
        assert result.answer == "42"
        assert result.confidence == 0.95
