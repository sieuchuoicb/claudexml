# claudexml

Pydantic-like XML parser for Claude's XML output.

## Quick Start

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Architecture

- `src/claudexml/` — main package
  - `model.py` — `XMLModel` base class, `XMLTag` field descriptor
  - `parser.py` — XML parsing logic (stdlib `xml.etree` + custom fault-tolerant parser)
  - `validators.py` — `field_validator` decorator, type coercion, `register_coercer`
  - `stream.py` — `XMLStreamParser` for incremental parsing
  - `prompts.py` — `xml_prompt()` helper for generating Claude instructions
  - `pydantic_compat.py` — optional Pydantic interop (`to_pydantic`, `from_pydantic_model`)
  - `extract.py` — `extract_tags()` schema-free utility
  - `integration.py` — `parse_response()` for Anthropic SDK
  - `exceptions.py` — custom error types
- `tests/` — mirrors source modules 1:1

## Conventions

- Python 3.10+
- Zero runtime dependencies (stdlib only; `anthropic`, `pydantic` optional)
- Type hints on all public APIs
- Tests with pytest
- Linting with ruff
- src/ layout packaging
