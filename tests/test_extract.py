"""Tests for extract_tags utility."""

from claudexml import extract_tags


class TestExtractTags:
    def test_simple(self):
        tags = extract_tags("<thinking>Let me analyze...</thinking><answer>42</answer>")
        assert tags["thinking"] == "Let me analyze..."
        assert tags["answer"] == "42"

    def test_nested(self):
        tags = extract_tags("<response><answer>42</answer></response>")
        assert tags["response"]["answer"] == "42"

    def test_empty_string(self):
        assert extract_tags("") == {}

    def test_no_xml(self):
        assert extract_tags("just plain text") == {}

    def test_claude_output_with_surrounding_text(self):
        text = "Sure, here's my analysis:\n<answer>42</answer>\nHope that helps!"
        tags = extract_tags(text)
        assert tags["answer"] == "42"

    def test_multiple_same_tags(self):
        tags = extract_tags("<item>a</item><item>b</item><item>c</item>")
        assert tags["item"] == ["a", "b", "c"]
