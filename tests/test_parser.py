"""Tests for the XML parser."""

from claudexml.parser import extract_tag, parse_xml_string


class TestParseXMLString:
    def test_simple_tags(self):
        xml = "<thinking>hello</thinking><answer>world</answer>"
        result = parse_xml_string(xml)
        assert result["thinking"] == "hello"
        assert result["answer"] == "world"

    def test_nested_tags(self):
        xml = "<response><thinking>step 1</thinking><answer>42</answer></response>"
        result = parse_xml_string(xml)
        assert result["response"]["thinking"] == "step 1"
        assert result["response"]["answer"] == "42"

    def test_multiple_same_tags(self):
        xml = "<issue>bug 1</issue><issue>bug 2</issue><issue>bug 3</issue>"
        result = parse_xml_string(xml)
        assert result["issue"] == ["bug 1", "bug 2", "bug 3"]

    def test_whitespace_handling(self):
        xml = """
        <thinking>
            Let me think about this carefully.
        </thinking>
        <answer>  42  </answer>
        """
        result = parse_xml_string(xml)
        assert "think about this carefully" in result["thinking"]
        assert result["answer"] == "42"

    def test_surrounding_text(self):
        xml = "Here is my analysis: <answer>42</answer> Hope that helps!"
        result = parse_xml_string(xml)
        assert result["answer"] == "42"

    def test_empty_tags(self):
        xml = "<thinking></thinking><answer>yes</answer>"
        result = parse_xml_string(xml)
        assert result["thinking"] == ""
        assert result["answer"] == "yes"

    def test_malformed_xml_fallback(self):
        xml = "<thinking>partial output<answer>42</answer>"
        result = parse_xml_string(xml)
        assert result["answer"] == "42"

    def test_empty_string(self):
        result = parse_xml_string("")
        assert result == {}


class TestExtractTag:
    def test_simple_path(self):
        xml = "<thinking>hello</thinking>"
        assert extract_tag(xml, "thinking") == "hello"

    def test_nested_path(self):
        xml = "<response><answer>42</answer></response>"
        assert extract_tag(xml, "response/answer") == "42"

    def test_missing_tag(self):
        xml = "<thinking>hello</thinking>"
        assert extract_tag(xml, "answer") is None

    def test_dot_path(self):
        xml = "<response><answer>42</answer></response>"
        assert extract_tag(xml, "response.answer") == "42"


class TestAttributes:
    def test_etree_single_attribute(self):
        xml = '<item id="123">Widget</item>'
        result = parse_xml_string(xml)
        assert result["item"]["_text"] == "Widget"
        assert result["item"]["_attrs"]["id"] == "123"

    def test_etree_multiple_attributes(self):
        xml = '<item id="1" type="book">Title</item>'
        result = parse_xml_string(xml)
        assert result["item"]["_attrs"]["id"] == "1"
        assert result["item"]["_attrs"]["type"] == "book"
        assert result["item"]["_text"] == "Title"

    def test_no_attributes_unchanged(self):
        xml = "<item>Widget</item>"
        result = parse_xml_string(xml)
        assert result["item"] == "Widget"

    def test_regex_attributes(self):
        """Force regex path with surrounding text."""
        xml = 'Hello <item id="123">Widget</item> bye'
        result = parse_xml_string(xml)
        assert result["item"]["_text"] == "Widget"
        assert result["item"]["_attrs"]["id"] == "123"

    def test_attribute_empty_content(self):
        xml = '<item id="123"></item>'
        result = parse_xml_string(xml)
        assert result["item"]["_text"] == ""
        assert result["item"]["_attrs"]["id"] == "123"


class TestCDATA:
    def test_cdata_simple(self):
        xml = "<code><![CDATA[x < 5 && y > 3]]></code>"
        result = parse_xml_string(xml)
        assert result["code"] == "x < 5 && y > 3"

    def test_cdata_with_xml_chars(self):
        xml = '<snippet><![CDATA[<div class="test">&amp;</div>]]></snippet>'
        result = parse_xml_string(xml)
        assert "<div" in result["snippet"]
        assert "&amp;" in result["snippet"]

    def test_cdata_multiline(self):
        xml = """<code><![CDATA[
def hello():
    if x < 5:
        print("world")
]]></code>"""
        result = parse_xml_string(xml)
        assert "def hello():" in result["code"]
        assert "x < 5" in result["code"]

    def test_cdata_empty(self):
        xml = "<code><![CDATA[]]></code>"
        result = parse_xml_string(xml)
        assert result["code"] == ""

    def test_cdata_mixed_with_regular_tags(self):
        xml = "<thinking>normal text</thinking><code><![CDATA[x < 5]]></code>"
        result = parse_xml_string(xml)
        assert result["thinking"] == "normal text"
        assert result["code"] == "x < 5"
