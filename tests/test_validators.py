"""Tests for validators and type coercion."""

from datetime import datetime

import pytest

from claudexml import (
    ValidationError,
    XMLModel,
    XMLStreamParser,
    XMLTag,
    field_validator,
    register_coercer,
)
from claudexml.validators import _coercer_registry, coerce_value


class TestCoerceValue:
    def test_str(self):
        assert coerce_value("hello", str) == "hello"
        assert coerce_value(42, str) == "42"

    def test_int(self):
        assert coerce_value("42", int) == 42
        assert coerce_value("3.7", int) == 3

    def test_float(self):
        assert coerce_value("3.14", float) == 3.14
        assert coerce_value("42", float) == 42.0

    def test_bool(self):
        assert coerce_value("true", bool) is True
        assert coerce_value("false", bool) is False
        assert coerce_value("yes", bool) is True
        assert coerce_value("no", bool) is False
        assert coerce_value("1", bool) is True
        assert coerce_value("0", bool) is False

    def test_bool_invalid(self):
        with pytest.raises(ValidationError):
            coerce_value("maybe", bool)

    def test_int_invalid(self):
        with pytest.raises(ValidationError):
            coerce_value("not_a_number", int)

    def test_list_from_list(self):
        assert coerce_value(["a", "b"], list[str]) == ["a", "b"]

    def test_list_from_single(self):
        assert coerce_value("a", list[str]) == ["a"]

    def test_none(self):
        assert coerce_value(None, str) is None


class TestFieldValidator:
    def test_validator_passes(self):
        class Scored(XMLModel):
            score: float = XMLTag("score")

            @field_validator("score")
            def check_score(cls, v):
                if not 0 <= v <= 1:
                    raise ValueError("score must be between 0 and 1")
                return v

        result = Scored.from_xml("<score>0.5</score>")
        assert result.score == 0.5

    def test_validator_fails(self):
        class Scored(XMLModel):
            score: float = XMLTag("score")

            @field_validator("score")
            def check_score(cls, v):
                if not 0 <= v <= 1:
                    raise ValueError("score must be between 0 and 1")
                return v

        with pytest.raises(ValidationError):
            Scored.from_xml("<score>1.5</score>")

    def test_validator_transforms_value(self):
        class Normalized(XMLModel):
            name: str = XMLTag("name")

            @field_validator("name")
            def normalize_name(cls, v):
                return v.strip().lower()

        result = Normalized.from_xml("<name>  HELLO  </name>")
        assert result.name == "hello"

    def test_multiple_fields(self):
        class Range(XMLModel):
            low: float = XMLTag("low")
            high: float = XMLTag("high")

            @field_validator("low", "high")
            def check_positive(cls, v):
                if v < 0:
                    raise ValueError("must be positive")
                return v

        result = Range.from_xml("<low>1.0</low><high>2.0</high>")
        assert result.low == 1.0
        assert result.high == 2.0

        with pytest.raises(ValidationError):
            Range.from_xml("<low>-1.0</low><high>2.0</high>")


class TestCustomCoercers:
    def setup_method(self):
        """Save and restore coercer registry between tests."""
        self._saved = dict(_coercer_registry)

    def teardown_method(self):
        _coercer_registry.clear()
        _coercer_registry.update(self._saved)

    def test_datetime_coercer(self):
        @register_coercer(datetime)
        def parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value)

        class Event(XMLModel):
            name: str = XMLTag("name")
            date: datetime = XMLTag("date")

        result = Event.from_xml("<name>Launch</name><date>2026-04-01T10:00:00</date>")
        assert result.name == "Launch"
        assert isinstance(result.date, datetime)
        assert result.date.year == 2026

    def test_coercer_with_optional(self):
        @register_coercer(datetime)
        def parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value)

        class Event(XMLModel):
            name: str = XMLTag("name")
            date: datetime | None = XMLTag("date", default=None)

        result = Event.from_xml("<name>Launch</name>")
        assert result.date is None

    def test_coercer_with_list(self):
        @register_coercer(datetime)
        def parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value)

        class Schedule(XMLModel):
            dates: list[datetime] = XMLTag("date")

        xml = "<date>2026-01-01</date><date>2026-06-01</date>"
        result = Schedule.from_xml(xml)
        assert len(result.dates) == 2
        assert all(isinstance(d, datetime) for d in result.dates)

    def test_coercer_error_becomes_validation_error(self):
        @register_coercer(datetime)
        def parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value)

        class Event(XMLModel):
            date: datetime = XMLTag("date")

        with pytest.raises(ValidationError, match="Custom coercer failed"):
            Event.from_xml("<date>not-a-date</date>")

    def test_coercer_with_streaming(self):
        @register_coercer(datetime)
        def parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value)

        class Event(XMLModel):
            date: datetime = XMLTag("date")

        parser = XMLStreamParser(Event)
        parser.feed("<date>2026-04-01</date>")
        assert parser.is_complete()
        result = parser.result()
        assert isinstance(result.date, datetime)

    def test_coerce_value_uses_registry(self):
        @register_coercer(datetime)
        def parse_dt(value: str) -> datetime:
            return datetime.fromisoformat(value)

        result = coerce_value("2026-01-01", datetime)
        assert isinstance(result, datetime)
