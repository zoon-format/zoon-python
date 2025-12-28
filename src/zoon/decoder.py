import re
from typing import Any
from .types import (
    TYPE_STRING, TYPE_INTEGER, TYPE_NUMBER, TYPE_BOOLEAN, TYPE_AUTO_INCREMENT,
    MARKER_NULL,
    BOOL_TRUE, BOOL_FALSE
)


def decode(zoon_string: str) -> Any:
    zoon_string = zoon_string.strip()
    if not zoon_string:
        return None
        
    lines = zoon_string.split('\n')
    if not lines:
        return None
        
    aliases = {}
    header_index = -1
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('%'):
            parts = line.split(' ')
            for part in parts:
                if '=' in part:
                    alias_def, prefix = part.split('=', 1)
                    if alias_def.startswith('%'):
                        aliases[alias_def[1:]] = prefix
        elif line.startswith('#'):
            header_index = i
            break
        elif aliases:
            # Aliases found but no header? Just assume inline/other
            break
        else:
            # Data found first
            break
            
    if header_index != -1:
        # Reconstruct tabular part
        return _decode_tabular(lines[header_index:], aliases)
    elif zoon_string.startswith("["):
        return _decode_simple_list(zoon_string)
    else:
        return _decode_inline(zoon_string)


def _unflatten_object(flat: dict) -> dict:
    result = {}
    for key, value in flat.items():
        parts = key.split('.')
        current = result
        for i in range(len(parts) - 1):
            part = parts[i]
            if part not in current:
                current[part] = {}
            current = current[part]
            if not isinstance(current, dict):
                 # Conflict: path segment is not a dict (shouldn't happen in valid ZOON)
                 # Force over-write or error? overwrite for now
                 current = {}
                 result[parts[0]] = current # Reset? No this logic is fragile if conflict
                 # Proper unflattening handles conflicts or assumes valid input
        
        current[parts[-1]] = value
    return result


def _deep_merge(target: dict, source: dict):
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def _decode_string(value: str) -> str:
    return value.replace("_", " ")


def _decode_value(value: str, expected_type: str = TYPE_STRING) -> Any:
    if value == MARKER_NULL:
        return None
    
    if expected_type == TYPE_BOOLEAN:
        return value == BOOL_TRUE or value.lower() in ("true", "yes", "y", "1")
    elif expected_type == TYPE_INTEGER:
        try:
            return int(value)
        except ValueError:
            return value
    elif expected_type == TYPE_NUMBER:
        try:
            if "." in value or "e" in value.lower():
                return float(value)
            return int(value)
        except ValueError:
            return value
    else:
        return _decode_string(value)


def _decode_simple_list(zoon_string: str) -> list:
    content = zoon_string[1:-1]
    if not content:
        return []
    items = content.split(",")
    return [_decode_value(item.strip()) for item in items]


def _decode_inline(zoon_string: str) -> dict:
    result = {}
    pattern = r'(\w+)(?:[:=])(?:\{([^}]*)\}|([^\s]+))'
    
    for match in re.finditer(pattern, zoon_string):
        key = match.group(1)
        nested_value = match.group(2)
        simple_value = match.group(3)
        
        if nested_value is not None:
            result[key] = _decode_inline(nested_value)
        elif simple_value is not None:
            if simple_value in ("y", "yes", "true"):
                result[key] = True
            elif simple_value in ("n", "no", "false"):
                result[key] = False
            elif simple_value == MARKER_NULL:
                result[key] = None
            else:
                try:
                    if "." in simple_value:
                        result[key] = float(simple_value)
                    else:
                        result[key] = int(simple_value)
                except ValueError:
                    result[key] = _decode_string(simple_value)
    
    return result


def _parse_header(header_line: str, aliases: dict) -> tuple[list[dict], dict, int]:
    header_line = header_line.lstrip("#").strip()
    columns = []
    constants = {}
    explicit_rows = 0
    
    parts = header_line.split()
    for part in parts:
        if part.startswith('+'):
            try:
                explicit_rows = int(part[1:])
                continue
            except ValueError:
                pass
                
        is_constant = False
        const_val = None
        
        if part.startswith('@'):
            is_constant = True
            part_content = part[1:]
            if '=' in part_content:
                key, val = part_content.split('=', 1)
                const_val = val # String
                type_hint = TYPE_STRING
            elif ':' in part_content:
                key, val = part_content.split(':', 1)
                const_val = val
                type_hint = 'inferred'
            else:
                 continue # Invalid
        elif ':i+' in part:
             key = part.split(":")[0]
             type_hint = TYPE_AUTO_INCREMENT
        elif '!' in part:
             key, enum_str = part.split("!", 1)
             const_val = enum_str
             type_hint = 'indexed_enum'
        elif '=' in part:
             key, enum_str = part.split("=", 1)
             const_val = enum_str
             type_hint = 'enum'
        elif ':' in part:
             key, type_hint = part.split(":")
        else:
             continue
             
        # Expand aliases
        if key.startswith('%'):
            if '.' in key:
                alias, suffix = key[1:].split('.', 1)
                if alias in aliases:
                    key = f"{aliases[alias]}.{suffix}"
            elif key[1:] in aliases:
                key = aliases[key[1:]]
                
        if is_constant:
            if type_hint == TYPE_STRING:
                constants[key] = _decode_string(const_val)
            else:
                # Infer type
                if const_val in ('y', '1'): constants[key] = True
                elif const_val in ('n', '0'): constants[key] = False
                else:
                    try:
                        constants[key] = int(const_val)
                    except ValueError:
                         try:
                             constants[key] = float(const_val)
                         except ValueError:
                             constants[key] = const_val
        else:
            if type_hint == TYPE_AUTO_INCREMENT:
                columns.append({"key": key, "type": TYPE_AUTO_INCREMENT, "enum": None, "indexed": False})
            elif type_hint == 'indexed_enum':
                columns.append({"key": key, "type": TYPE_STRING, "enum": const_val.split('|'), "indexed": True})
            elif type_hint == 'enum':
                columns.append({"key": key, "type": TYPE_STRING, "enum": const_val.split('|'), "indexed": False})
            else:
                columns.append({"key": key, "type": type_hint, "enum": None, "indexed": False})

    return columns, constants, explicit_rows


def _decode_tabular(lines: list[str], aliases: dict) -> list[dict]:
    columns, constants, explicit_rows = _parse_header(lines[0], aliases)
    
    data = []
    auto_inc_counters = {col["key"]: 0 for col in columns if col["type"] == TYPE_AUTO_INCREMENT}
    
    constant_obj = _unflatten_object(constants)
    
    def process_row(tokens: list[str]) -> dict:
        flat_row = {}
        token_idx = 0
        
        for col in columns:
            key = col["key"]
            if col["type"] == TYPE_AUTO_INCREMENT:
                 auto_inc_counters[key] += 1
                 flat_row[key] = auto_inc_counters[key]
                 continue
                 
            if token_idx < len(tokens):
                token = tokens[token_idx]
                token_idx += 1
                
                if token == MARKER_NULL:
                    flat_row[key] = None
                elif col["enum"]:
                    if col.get("indexed"):
                        try:
                            idx = int(token)
                            flat_row[key] = _decode_string(col["enum"][idx]) if idx < len(col["enum"]) else token
                        except ValueError:
                            flat_row[key] = _decode_string(token)
                    else:
                        flat_row[key] = _decode_string(token)
                elif col["type"] == TYPE_BOOLEAN:
                    flat_row[key] = token == '1'
                elif col["type"] in (TYPE_INTEGER, TYPE_NUMBER):
                    try:
                        if key not in flat_row: # Don't overwrite if auto-inc (logic separation)
                             flat_row[key] = float(token) if '.' in token else int(token)
                    except ValueError:
                        flat_row[key] = token
                else:
                    flat_row[key] = _decode_string(token)
            else:
                flat_row[key] = None # Output exhausted?
                
        row_obj = _unflatten_object(flat_row)
        _deep_merge(row_obj, constant_obj)
        return row_obj

    if explicit_rows > 0:
        # Generate N rows (only auto-incs and constants typically)
        for _ in range(explicit_rows):
            data.append(process_row([]))
    else:
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            tokens = line.split()
            data.append(process_row(tokens))
            
    return data
