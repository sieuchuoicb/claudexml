"""Tests for prompt helpers."""

from claudexml import XMLModel, XMLTag


class TestXmlPrompt:
    def test_basic_model(self):
        class Analysis(XMLModel):
            thinking: str = XMLTag("thinking")
            answer: str = XMLTag("answer")

        prompt = Analysis.xml_prompt()
        assert "<thinking>" in prompt
        assert "<answer>" in prompt
        assert "string" in prompt
        assert "required" in prompt

    def test_optional_fields(self):
        class Response(XMLModel):
            answer: str = XMLTag("answer")
            thinking: str | None = XMLTag("thinking", default=None)
            confidence: float = XMLTag("confidence", default=0.5)

        prompt = Response.xml_prompt()
        assert "required" in prompt
        assert "optional" in prompt
        assert "0.5" in prompt

    def test_list_field(self):
        class Review(XMLModel):
            issues: list[str] = XMLTag("issue")

        prompt = Review.xml_prompt()
        assert "<issue>" in prompt
        assert "list" in prompt

    def test_float_and_int_types(self):
        class Metrics(XMLModel):
            count: int = XMLTag("count")
            score: float = XMLTag("score")
            active: bool = XMLTag("active")

        prompt = Metrics.xml_prompt()
        assert "integer" in prompt
        assert "number" in prompt
        assert "boolean" in prompt

    def test_attribute_field(self):
        class Item(XMLModel):
            item_id: str = XMLTag("item", attribute="id")

        prompt = Item.xml_prompt()
        assert 'id="..."' in prompt

    def test_returns_string(self):
        class Simple(XMLModel):
            answer: str = XMLTag("answer")

        assert isinstance(Simple.xml_prompt(), str)

    def test_contains_instruction_header(self):
        class Simple(XMLModel):
            answer: str = XMLTag("answer")

        prompt = Simple.xml_prompt()
        assert "Respond using the following XML structure" in prompt
