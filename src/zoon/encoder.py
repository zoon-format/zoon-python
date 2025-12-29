from typing import Any
from collections import Counter
from .types import (
    TYPE_STRING, TYPE_TEXT, TYPE_INTEGER, TYPE_NUMBER, TYPE_BOOLEAN, TYPE_AUTO_INCREMENT,
    MARKER_NULL,
    BOOL_TRUE, BOOL_FALSE, INLINE_BOOL_TRUE, INLINE_BOOL_FALSE
)


def encode(data: Any) -> str:
    if isinstance(data, list) and len(data) > 0 and all(isinstance(item, dict) for item in data):
        return _encode_tabular(data)
    elif isinstance(data, dict):
        return _encode_inline(data)
    elif isinstance(data, list):
        return _encode_simple_list(data)
    else:
        return _encode_value(data)


def _infer_type(values: list[Any]) -> str:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return TYPE_STRING
    
    first = non_null[0]
    if isinstance(first, bool):
        return TYPE_BOOLEAN
    elif isinstance(first, int):
        if all(isinstance(v, int) for v in non_null):
            return TYPE_INTEGER
        return TYPE_NUMBER
    elif isinstance(first, float):
        return TYPE_NUMBER
    return TYPE_STRING


def _is_auto_increment(values: list[Any]) -> bool:
    if len(values) < 2:
        return False
    try:
        int_vals = [int(v) for v in values if v is not None]
        if len(int_vals) < 2:
            return False
        for i in range(1, len(int_vals)):
            if int_vals[i] != int_vals[i - 1] + 1:
                return False
        return True
    except (ValueError, TypeError):
        return False


def _detect_enum(values: list[Any], row_count: int) -> tuple[list[str] | None, bool]:
    if not values:
        return None, False
    str_values = [str(v) for v in values if v is not None]
    if len(str_values) < 2:
        return None, False
    unique = sorted(list(dict.fromkeys(str_values)))
    if len(unique) <= len(str_values) // 2 and len(unique) <= 10:
        avg_len = sum(len(o) for o in unique) / len(unique)
        literal_cost = avg_len * row_count
        index_cost = len("|".join(unique)) + row_count * 2
        use_indexed = len(unique) >= 3 and literal_cost > index_cost
        return unique, use_indexed
    return None, False


def _encode_string(value: str) -> str:
    return value.replace(" ", "_")


def _encode_value(value: Any, for_inline: bool = False) -> str:
    if value is None:
        return MARKER_NULL
    if isinstance(value, bool):
        if for_inline:
            return INLINE_BOOL_TRUE if value else INLINE_BOOL_FALSE
        return BOOL_TRUE if value else BOOL_FALSE
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, dict):
        return _encode_inline(value)
    if isinstance(value, list):
        return _encode_simple_list(value)
    return str(value)


def _encode_simple_list(data: list) -> str:
    items = [_encode_value(v, for_inline=True) for v in data]
    return "[" + ",".join(items) + "]"


def _encode_inline(data: dict) -> str:
    parts = []
    for key, value in data.items():
        if isinstance(value, dict):
            parts.append(f"{key}:{{{_encode_inline_content(value)}}}")
        elif isinstance(value, bool):
            parts.append(f"{key}:{INLINE_BOOL_TRUE if value else INLINE_BOOL_FALSE}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key}:{value}")
        elif value is None:
            parts.append(f"{key}:{MARKER_NULL}")
        else:
            parts.append(f"{key}={_encode_string(str(value))}")
    return " ".join(parts)


def _encode_inline_content(data: dict) -> str:
    return _encode_inline(data)


def _flatten_object(obj: dict, prefix: str = "") -> dict:
    result = {}
    for key, value in obj.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_object(value, new_key))
        elif isinstance(value, list) and not value: # Empty list
            result[new_key] = value
        elif isinstance(value, list) and isinstance(value[0], dict):
             # Keep list of objects as is? Or recursive flatten?
             # For now, lists are keeping their structure (inline or array type)
             result[new_key] = value
        else:
            result[new_key] = value
    return result


def _detect_aliases(fields: list[str]) -> dict[str, str]:
    prefix_counts = Counter()
    for field in fields:
        parts = field.split('.')
        if len(parts) > 1:
            for i in range(1, len(parts)):
                prefix = '.'.join(parts[:i])
                prefix_counts[prefix] += 1
    
    # Calculate savings
    # Savings = (prefix_len - 2) * count - (prefix_len + 4)
    # alias len = 2. prefix definition = prefix_len + 1 (=) + 2 (alias) + 1 (space) = prefix_len + 4
    
    savings_list = []
    for prefix, count in prefix_counts.items():
        prefix_len = len(prefix)
        char_saved_per_use = prefix_len - 2
        total_saved = char_saved_per_use * count
        cost = prefix_len + 4
        net_savings = total_saved - cost
        if net_savings > 0:
            savings_list.append((prefix, net_savings))
            
    savings_list.sort(key=lambda x: x[1], reverse=True)
    
    aliases = {}
    used_aliases = set()
    aliased_fields = set()
    
    alias_index = 0
    
    for prefix, savings in savings_list:
        # Check if fields using this prefix are already covered?
        # Actually we can nested alias but simple logic for now:
        # If we aliased 'services', we might not need 'services.postgres' unless big savings?
        # Let's simple check: if less than 2 valid fields remaining, skip.
        
        candidates = [f for f in fields if f.startswith(prefix + '.') and f not in aliased_fields]
        if len(candidates) < 2:
            continue
            
        parts = prefix.split('.')
        alias = "".join(p[0] for p in parts).lower()
        
        while alias in used_aliases or len(alias) < 2:
             alias = chr(97 + alias_index) # a, b, c...
             alias_index += 1
             if alias_index > 25: break 
             
        used_aliases.add(alias)
        aliases[prefix] = alias
        for c in candidates:
            aliased_fields.add(c)
            
        if len(aliases) >= 10: break
        
    return aliases


def _apply_alias(field: str, aliases: dict[str, str]) -> str:
    for prefix, alias in aliases.items():
        if field.startswith(prefix + '.'):
            return f"%{alias}{field[len(prefix):]}"
        if field == prefix:
            return f"%{alias}"
    return field


def _encode_tabular(data: list[dict]) -> str:
    if not data:
        return ""
    
    flattened_data = [_flatten_object(row) for row in data]
    # Infer schema from all keys (union)
    all_keys = set()
    for row in flattened_data:
        all_keys.update(row.keys())
    keys = sorted(list(all_keys))
    
    # 1. Detect Constants
    constant_fields = {}
    active_keys = []
    
    if len(flattened_data) > 1:
        for key in keys:
            first_val = flattened_data[0].get(key)
            is_constant = True
            for row in flattened_data:
                if row.get(key) != first_val:
                    is_constant = False
                    break
            
            # Don't hoist IDs if they look like auto-inc candidates?
            # Actually constant ID is constant. Auto-inc is handled later.
            if is_constant and first_val is not None:
                constant_fields[key] = first_val
            else:
                active_keys.append(key)
    else:
        active_keys = keys

    # 2. Type Inference on Active Keys
    column_info = {}
    for key in active_keys:
        values = [row.get(key) for row in flattened_data]
        base_type = _infer_type(values)
        
        if base_type == TYPE_INTEGER and _is_auto_increment(values):
            column_info[key] = {"type": TYPE_AUTO_INCREMENT, "enum": None}
        elif base_type == TYPE_STRING:
            enum_values, indexed = _detect_enum(values, len(flattened_data))
            if enum_values:
                column_info[key] = {"type": TYPE_STRING, "enum": enum_values, "indexed": indexed}
            else:
                avg_len = sum(len(str(v)) for v in values if v is not None) / max(1, len([v for v in values if v is not None]))
                if avg_len > 30:
                    column_info[key] = {"type": TYPE_TEXT, "enum": None}
                else:
                    column_info[key] = {"type": TYPE_STRING, "enum": None}
        else:
            column_info[key] = {"type": base_type, "enum": None}

    # 3. Detect Aliases on Active Keys
    aliases = _detect_aliases(active_keys)
    
    # 4. Generate Header
    lines = []
    
    # Alias definitions
    if aliases:
        alias_parts = []
        for prefix, alias in aliases.items():
            alias_parts.append(f"%{alias}={prefix}")
        lines.append(" ".join(alias_parts))
    
    header_parts = ["#"]
    
    # Constants
    if constant_fields:
        for key, val in constant_fields.items():
            aliased = _apply_alias(key, aliases).replace(" ", "_")
            if isinstance(val, bool):
                header_parts.append(f"@{aliased}:{INLINE_BOOL_TRUE if val else INLINE_BOOL_FALSE}")
            elif isinstance(val, (int, float)):
                header_parts.append(f"@{aliased}:{val}")
            else:
                header_parts.append(f"@{aliased}={_encode_string(str(val))}")

    # Columns
    for key in active_keys:
        info = column_info[key]
        aliased = _apply_alias(key, aliases).replace(" ", "_")
        
        if info["type"] == TYPE_AUTO_INCREMENT:
            header_parts.append(f"{aliased}:{TYPE_AUTO_INCREMENT}")
        elif info["enum"]:
            separator = "!" if info.get("indexed") else "="
            enum_str = "|".join(info["enum"])
            header_parts.append(f"{aliased}{separator}{enum_str}")
        else:
            header_parts.append(f"{aliased}:{info['type']}")

    # Row Count +N
    has_consuming = any(column_info[k]["type"] != TYPE_AUTO_INCREMENT for k in active_keys)
    if not has_consuming and len(flattened_data) > 0:
        header_parts.append(f"+{len(flattened_data)}")
    
    lines.append(" ".join(header_parts))
    
    header_block = "\n".join(lines)
    
    if not has_consuming:
        return header_block + "\n"

    rows = []
    for row in flattened_data:
        row_parts = []
        for key in active_keys:
            info = column_info[key]
            if info["type"] == TYPE_AUTO_INCREMENT:
                continue
                
            value = row.get(key)
            if value is None:
                row_parts.append(MARKER_NULL)
            elif info["enum"]:
                if info.get("indexed"):
                    idx = info["enum"].index(str(value)) if str(value) in info["enum"] else -1
                    row_parts.append(str(idx) if idx >= 0 else _encode_value(value))
                else:
                    row_parts.append(_encode_value(value))
            elif info["type"] == TYPE_BOOLEAN:
                row_parts.append(BOOL_TRUE if value else BOOL_FALSE)
            elif info["type"] in (TYPE_INTEGER, TYPE_NUMBER):
                row_parts.append(str(value))
            elif isinstance(value, list):
                 row_parts.append(_encode_simple_list(value))
            elif info["type"] == TYPE_TEXT:
                row_parts.append('"' + str(value).replace('"', '\\"') + '"')
            else:
                row_parts.append(_encode_value(value))
        
        if row_parts:
            rows.append(" ".join(row_parts))
        else:
            rows.append("") # Empty row

    return header_block + "\n" + "\n".join(rows)
