# ZOON Python

> **ZOON** - Zero Overhead Object Notation

A Python implementation of the [ZOON format](https://github.com/zoon-format/zoon/blob/main/SPEC.md) for LLM context optimization. Achieves ~60% token reduction compared to JSON while maintaining 100% data fidelity.

[![PyPI](https://img.shields.io/pypi/v/zoon-format)](https://pypi.org/project/zoon-format/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Installation

```bash
pip install zoon-format
```

Or with uv:

```bash
uv add zoon-format
```

## Quick Start

```python
import zoon

data = [
    {"id": 1, "name": "Alice", "role": "admin", "active": True},
    {"id": 2, "name": "Bob", "role": "user", "active": True},
    {"id": 3, "name": "Carol", "role": "user", "active": False},
]

encoded = zoon.encode(data)
print(encoded)
# # id:i+ name:s role=admin|user active:b
# Alice admin 1
# Bob user 1
# Carol user 0

decoded = zoon.decode(encoded)
assert decoded == data
```

## Features

- **~60% Token Reduction**: Reduced LLM context usage vs JSON
- **100% Lossless**: Perfect round-trip encoding/decoding
- **Type-Safe**: Preserves integers, floats, booleans, nulls, and strings
- **Auto-Increment IDs**: `i+` columns are omitted from data rows
- **Smart Enums**: Automatic header-based typing for repeated values

## API Reference

### `zoon.encode(data: Any) -> str`

Encode Python data to ZOON format.

### `zoon.decode(zoon_string: str) -> Any`

Decode ZOON string back to Python data.

## License

MIT License. © 2025-PRESENT Carsen Klock
