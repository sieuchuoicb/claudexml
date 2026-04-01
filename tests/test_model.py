"""Tests for XMLModel and XMLTag."""

import pytest

from claudexml import TagNotFoundError, XMLModel, XMLTag


class TestXMLModel:
    def test_simple_model(self):
        class Analysis(XMLModel):
            thinking: str = XMLTag("thinking")
            answer: str = XMLTag("answer")

        xml = "<thinking>Let me think</thinking><answer>42</answer>"
        result = Analysis.from_xml(xml)
        assert result.thinking == "Let me think"
        assert result.answer == "42"

    def test_type_coercion_float(self):
        class Scored(XMLModel):
            score: float = XMLTag("score")

        result = Scored.from_xml("<score>0.95</score>")
        assert result.score == 0.95
        assert isinstance(result.score, float)

    def test_type_coercion_int(self):
        class Counted(XMLModel):
            count: int = XMLTag("count")

        result = Counted.from_xml("<count>42</count>")
        assert result.count == 42
        assert isinstance(result.count, int)

    def test_type_coercion_bool(self):
        class Flagged(XMLModel):
            active: bool = XMLTag("active")

        assert Flagged.from_xml("<active>true</active>").active is True
        assert Flagged.from_xml("<active>false</active>").active is False
        assert Flagged.from_xml("<active>yes</active>").active is True
        assert Flagged.from_xml("<active>no</active>").active is False

    def test_optional_field_present(self):
        class Response(XMLModel):
            answer: str = XMLTag("answer")
            thinking: str | None = XMLTag("thinking", default=None)

        xml = "<thinking>hmm</thinking><answer>42</answer>"
        result = Response.from_xml(xml)
        assert result.thinking == "hmm"
        assert result.answer == "42"

    def test_optional_field_missing(self):
        class Response(XMLModel):
            answer: str = XMLTag("answer")
            thinking: str | None = XMLTag("thinking", default=None)

        result = Response.from_xml("<answer>42</answer>")
        assert result.thinking is None
        assert result.answer == "42"

    def test_default_value(self):
        class Response(XMLModel):
            answer: str = XMLTag("answer")
            confidence: float = XMLTag("confidence", default=0.5)

        result = Response.from_xml("<answer>42</answer>")
        assert result.confidence == 0.5

    def test_required_field_missing_raises(self):
        class Response(XMLModel):
            answer: str = XMLTag("answer")

        with pytest.raises(TagNotFoundError):
            Response.from_xml("<thinking>no answer here</thinking>")

    def test_nested_model(self):
        class Source(XMLModel):
            url: str = XMLTag("url")
            title: str = XMLTag("title")

        class Research(XMLModel):
            sources: Source = XMLTag("sources")
            summary: str = XMLTag("summary")

        xml = """
        <sources>
            <url>https://example.com</url>
            <title>Example</title>
        </sources>
        <summary>Found one source</summary>
        """
        result = Research.from_xml(xml)
        assert isinstance(result.sources, Source)
        assert result.sources.url == "https://example.com"
        assert result.sources.title == "Example"

    def test_list_field(self):
        class Review(XMLModel):
            issues: list[str] = XMLTag("issue")

        xml = "<issue>bug 1</issue><issue>bug 2</issue>"
        result = Review.from_xml(xml)
        assert result.issues == ["bug 1", "bug 2"]

    def test_single_item_as_list(self):
        class Review(XMLModel):
            issues: list[str] = XMLTag("issue")

        xml = "<issue>only one bug</issue>"
        result = Review.from_xml(xml)
        assert result.issues == ["only one bug"]

    def test_repr(self):
        class Simple(XMLModel):
            answer: str = XMLTag("answer")

        result = Simple.from_xml("<answer>42</answer>")
        assert "Simple" in repr(result)
        assert "42" in repr(result)

    def test_equality(self):
        class Simple(XMLModel):
            answer: str = XMLTag("answer")

        a = Simple.from_xml("<answer>42</answer>")
        b = Simple.from_xml("<answer>42</answer>")
        assert a == b

    def test_to_dict(self):
        class Analysis(XMLModel):
            thinking: str = XMLTag("thinking")
            answer: str = XMLTag("answer")

        result = Analysis.from_xml("<thinking>hmm</thinking><answer>42</answer>")
        d = result.to_dict()
        assert d == {"thinking": "hmm", "answer": "42"}

    def test_claude_style_output(self):
        """Test with realistic Claude output."""

        class CodeReview(XMLModel):
            thinking: str = XMLTag("thinking")
            verdict: str = XMLTag("verdict")
            confidence: float = XMLTag("confidence")

        xml = """
        <thinking>
        The code looks clean but I notice a potential null pointer
        dereference on line 42. The variable `user` could be None
        when the database query returns no results.
        </thinking>
        <verdict>needs_changes</verdict>
        <confidence>0.92</confidence>
        """
        result = CodeReview.from_xml(xml)
        assert "null pointer" in result.thinking
        assert result.verdict == "needs_changes"
        assert result.confidence == 0.92

    def test_attribute_extraction(self):
        class Item(XMLModel):
            name: str = XMLTag("item")
            item_id: str = XMLTag("item", attribute="id")

        xml = '<item id="123">Widget</item>'
        result = Item.from_xml(xml)
        assert result.name == "Widget"
        assert result.item_id == "123"

    def test_attribute_missing_with_default(self):
        class Item(XMLModel):
            name: str = XMLTag("item")
            item_id: str | None = XMLTag("item", attribute="id", default=None)

        xml = "<item>Widget</item>"
        result = Item.from_xml(xml)
        assert result.name == "Widget"
        assert result.item_id is None

    def test_attribute_type_coercion(self):
        class Item(XMLModel):
            priority: int = XMLTag("item", attribute="priority")

        xml = '<item priority="5">Widget</item>'
        result = Item.from_xml(xml)
        assert result.priority == 5
        assert isinstance(result.priority, int)

    def test_to_json_compact(self):
        class Analysis(XMLModel):
            answer: str = XMLTag("answer")

        result = Analysis.from_xml("<answer>42</answer>")
        json_str = result.to_json()
        import json

        assert json.loads(json_str) == {"answer": "42"}

    def test_to_json_pretty(self):
        class Analysis(XMLModel):
            answer: str = XMLTag("answer")

        result = Analysis.from_xml("<answer>42</answer>")
        json_str = result.to_json(indent=2)
        assert "\n" in json_str
        import json

        assert json.loads(json_str) == {"answer": "42"}

    def test_to_json_nested_model(self):
        class Inner(XMLModel):
            value: str = XMLTag("value")

        class Outer(XMLModel):
            inner: Inner = XMLTag("inner")

        xml = "<inner><value>hello</value></inner>"
        result = Outer.from_xml(xml)
        import json

        assert json.loads(result.to_json()) == {"inner": {"value": "hello"}}

    def test_to_json_list_field(self):
        class Review(XMLModel):
            issues: list[str] = XMLTag("issue")

        xml = "<issue>bug 1</issue><issue>bug 2</issue>"
        result = Review.from_xml(xml)
        import json

        assert json.loads(result.to_json()) == {"issues": ["bug 1", "bug 2"]}
