import json
import zoon


def test_roundtrip_simple_array():
    data = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Carol", "role": "user"},
    ]
    encoded = zoon.encode(data)
    decoded = zoon.decode(encoded)
    
    for i, row in enumerate(decoded):
        assert row["name"] == data[i]["name"]
        assert row["role"] == data[i]["role"]


def test_roundtrip_with_numbers():
    data = [
        {"product": "Widget", "price": 19.99, "stock": 100},
        {"product": "Gadget", "price": 29.50, "stock": 50},
    ]
    encoded = zoon.encode(data)
    decoded = zoon.decode(encoded)
    
    assert decoded[0]["price"] == data[0]["price"]
    assert decoded[1]["stock"] == data[1]["stock"]


def test_roundtrip_with_booleans():
    data = [
        {"name": "Alice", "active": True},
        {"name": "Bob", "active": False},
    ]
    encoded = zoon.encode(data)
    decoded = zoon.decode(encoded)
    
    assert decoded[0]["active"] is True
    assert decoded[1]["active"] is False


def test_roundtrip_with_nulls():
    data = [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": None},
    ]
    encoded = zoon.encode(data)
    decoded = zoon.decode(encoded)
    
    assert decoded[0]["email"] == "alice@example.com"
    assert decoded[1]["email"] is None


def test_token_reduction():
    data = [
        {"id": i, "name": f"User_{i}", "status": "active", "level": 1}
        for i in range(1, 11)
    ]
    
    json_str = json.dumps(data, separators=(',', ':'))
    zoon_str = zoon.encode(data)
    
    assert len(zoon_str) < len(json_str)
    reduction = (1 - len(zoon_str) / len(json_str)) * 100
    print(f"Token reduction: {reduction:.1f}%")
    assert reduction > 30


def test_roundtrip_with_aliases():
    data = [
        {"infrastructure": {"postgres": {"status": "up"}, "redis": {"status": "up"}}},
        {"infrastructure": {"postgres": {"status": "down"}, "redis": {"status": "down"}}}
    ]
    encoded = zoon.encode(data)
    assert "%" in encoded
    assert "infrastructure" in encoded
    decoded = zoon.decode(encoded)
    assert decoded == data


def test_roundtrip_with_constants():
    data = [
        {"status": "ok", "id": 1, "region": "us-east-1"},
        {"status": "ok", "id": 2, "region": "us-east-1"},
        {"status": "ok", "id": 3, "region": "us-east-1"}
    ]
    encoded = zoon.encode(data)
    assert "@status=ok" in encoded
    assert "@region=us-east-1" in encoded
    decoded = zoon.decode(encoded)
    assert decoded == data


def test_implicit_rows_with_row_count():
    # Only constants and auto-increment
    data = [
        {"status": "static", "id": 1},
        {"status": "static", "id": 2},
        {"status": "static", "id": 3}
    ]
    encoded = zoon.encode(data)
    assert "+3" in encoded
    decoded = zoon.decode(encoded)
    assert decoded == data
