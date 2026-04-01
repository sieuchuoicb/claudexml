# claudexml

Pydantic-like XML parser for Claude's XML output. Define a schema, parse Claude's response, get a validated Python object.

## Installation

```bash
pip install claudexml
```

With optional extras:

```bash
pip install claudexml[anthropic]  # Anthropic SDK integration
pip install claudexml[pydantic]   # Pydantic interop
```

## Quick Start

```python
from claudexml import XMLModel, XMLTag

class Analysis(XMLModel):
    thinking: str = XMLTag("thinking")
    answer: str = XMLTag("answer")
    confidence: float = XMLTag("confidence")

xml = """
<thinking>The user is asking about the meaning of life.</thinking>
<answer>42</answer>
<confidence>0.95</confidence>
"""

result = Analysis.from_xml(xml)
result.thinking   # "The user is asking about the meaning of life."
result.answer     # "42"
result.confidence # 0.95 (float, not string)
```

## Features

### Type Coercion

Automatically converts XML string content to Python types:

```python
class Metrics(XMLModel):
    count: int = XMLTag("count")        # "42" -> 42
    score: float = XMLTag("score")      # "0.95" -> 0.95
    active: bool = XMLTag("active")     # "true" -> True
```

### Optional Fields & Defaults

```python
class Response(XMLModel):
    answer: str = XMLTag("answer")
    thinking: str | None = XMLTag("thinking", default=None)
    confidence: float = XMLTag("confidence", default=0.5)
```

### Nested Models

```python
class Source(XMLModel):
    url: str = XMLTag("url")
    title: str = XMLTag("title")

class Research(XMLModel):
    sources: Source = XMLTag("sources")
    summary: str = XMLTag("summary")
```

### List Fields

```python
class Review(XMLModel):
    issues: list[str] = XMLTag("issue")

xml = "<issue>bug 1</issue><issue>bug 2</issue>"
result = Review.from_xml(xml)
result.issues  # ["bug 1", "bug 2"]
```

### Validators

```python
from claudexml import XMLModel, XMLTag, field_validator

class Scored(XMLModel):
    score: float = XMLTag("score")

    @field_validator("score")
    def check_range(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("score must be between 0 and 1")
        return v
```

### Attributes

Extract XML attribute values alongside text content:

```python
class Item(XMLModel):
    name: str = XMLTag("item")                    # text content
    item_id: str = XMLTag("item", attribute="id") # attribute value

xml = '<item id="123">Widget</item>'
result = Item.from_xml(xml)
result.name     # "Widget"
result.item_id  # "123"
```

### Streaming

Parse XML incrementally as Claude streams tokens:

```python
from claudexml import XMLStreamParser

parser = XMLStreamParser(Analysis)

for event in stream:
    parser.feed(event.text)
    partial = parser.partial()       # partially filled model (no validation)
    if parser.is_complete():
        result = parser.result()     # fully validated model
```

### CDATA Support

Handles `<![CDATA[...]]>` sections for raw content:

```python
class CodeBlock(XMLModel):
    code: str = XMLTag("code")

xml = "<code><![CDATA[if (x < 5 && y > 3) { return true; }]]></code>"
result = CodeBlock.from_xml(xml)
result.code  # "if (x < 5 && y > 3) { return true; }"
```

### JSON Export

Convert models to JSON:

```python
result = Analysis.from_xml(xml)
result.to_json()           # compact JSON string
result.to_json(indent=2)   # pretty-printed
result.to_dict()           # Python dictionary
```

### Schema-Free Extraction

For quick parsing without defining a model:

```python
from claudexml import extract_tags

tags = extract_tags("<thinking>Let me analyze...</thinking><answer>42</answer>")
tags["thinking"]  # "Let me analyze..."
tags["answer"]    # "42"
```

### Custom Type Coercers

Register custom type handlers for any Python type:

```python
from datetime import datetime
from claudexml import XMLModel, XMLTag, register_coercer

@register_coercer(datetime)
def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)

class Event(XMLModel):
    name: str = XMLTag("name")
    date: datetime = XMLTag("date")

result = Event.from_xml("<name>Launch</name><date>2026-04-01T10:00:00</date>")
result.date  # datetime(2026, 4, 1, 10, 0)
```

### Prompt Helpers

Auto-generate XML schema instructions for Claude:

```python
class CodeReview(XMLModel):
    thinking: str = XMLTag("thinking")
    verdict: str = XMLTag("verdict")
    confidence: float = XMLTag("confidence", default=0.5)

print(CodeReview.xml_prompt())
# Respond using the following XML structure:
#
# - <thinking>: string (required)
# - <verdict>: string (required)
# - <confidence>: number (optional, default: 0.5)
```

### Pydantic Interop

Convert between XMLModel and Pydantic (requires `pip install claudexml[pydantic]`):

```python
# XMLModel -> Pydantic BaseModel
pydantic_obj = result.to_pydantic()

# Pydantic BaseModel -> XMLModel
from pydantic import BaseModel

class MySchema(BaseModel):
    name: str
    score: float

MyXML = XMLModel.from_pydantic_model(MySchema)
result = MyXML.from_xml("<name>test</name><score>0.95</score>")
```

### Anthropic SDK Integration

```python
from anthropic import Anthropic
from claudexml import XMLModel, XMLTag, parse_response

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6-20250514",
    messages=[{"role": "user", "content": "Analyze this code..."}],
)

class CodeReview(XMLModel):
    thinking: str = XMLTag("thinking")
    verdict: str = XMLTag("verdict")
    confidence: float = XMLTag("confidence")

review = parse_response(response, CodeReview)
```

## Error Handling

```python
from claudexml import TagNotFoundError, ValidationError

try:
    result = MyModel.from_xml(xml)
except TagNotFoundError as e:
    print(f"Missing tag: {e.tag}")
except ValidationError as e:
    print(f"Invalid value for {e.field}: {e}")
```

## Fault Tolerance

claudexml gracefully handles imperfect XML from Claude:

- Unclosed tags
- Surrounding non-XML text
- Extra whitespace
- Partial output

## License

MIT
