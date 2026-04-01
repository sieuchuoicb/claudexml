"""Tests for Pydantic interop."""

import pytest

pydantic = pytest.importorskip("pydantic")

from pydantic import BaseModel  # noqa: E402

from claudexml import XMLModel, XMLTag  # noqa: E402


class TestToPydantic:
    def test_basic(self):
        class Analysis(XMLModel):
            thinking: str = XMLTag("thinking")
            answer: str = XMLTag("answer")

        result = Analysis.from_xml("<thinking>hmm</thinking><answer>42</answer>")
        pydantic_obj = result.to_pydantic()

        assert isinstance(pydantic_obj, BaseModel)
        assert pydantic_obj.thinking == "hmm"
        assert pydantic_obj.answer == "42"

    def test_with_types(self):
        class Scored(XMLModel):
            score: float = XMLTag("score")
            count: int = XMLTag("count")

        result = Scored.from_xml("<score>0.95</score><count>42</count>")
        pydantic_obj = result.to_pydantic()
        assert pydantic_obj.score == 0.95
        assert pydantic_obj.count == 42

    def test_optional_field(self):
        class Response(XMLModel):
            answer: str = XMLTag("answer")
            thinking: str | None = XMLTag("thinking", default=None)

        result = Response.from_xml("<answer>42</answer>")
        pydantic_obj = result.to_pydantic()
        assert pydantic_obj.answer == "42"
        assert pydantic_obj.thinking is None


class TestFromPydanticModel:
    def test_basic(self):
        class MyPydantic(BaseModel):
            name: str
            score: float

        MyXML = XMLModel.from_pydantic_model(MyPydantic)
        result = MyXML.from_xml("<name>test</name><score>0.95</score>")
        assert result.name == "test"
        assert result.score == 0.95

    def test_optional_fields(self):
        class MyPydantic(BaseModel):
            name: str
            nickname: str | None = None

        MyXML = XMLModel.from_pydantic_model(MyPydantic)
        result = MyXML.from_xml("<name>Alice</name>")
        assert result.name == "Alice"
        assert result.nickname is None

    def test_with_defaults(self):
        class MyPydantic(BaseModel):
            name: str
            score: float = 0.5

        MyXML = XMLModel.from_pydantic_model(MyPydantic)
        result = MyXML.from_xml("<name>test</name>")
        assert result.name == "test"
        assert result.score == 0.5

    def test_roundtrip(self):
        class MyPydantic(BaseModel):
            name: str
            score: float

        MyXML = XMLModel.from_pydantic_model(MyPydantic)
        result = MyXML.from_xml("<name>test</name><score>0.95</score>")
        pydantic_obj = result.to_pydantic()

        assert pydantic_obj.name == "test"
        assert pydantic_obj.score == 0.95

    def test_not_a_base_model(self):
        with pytest.raises(TypeError, match="not a Pydantic BaseModel"):
            XMLModel.from_pydantic_model(dict)
