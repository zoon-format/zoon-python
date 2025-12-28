import zoon


def test_encode_simple_array():
    data = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Carol", "role": "user"},
    ]
    result = zoon.encode(data)
    assert result.startswith("#")
    assert "id:i+" in result
    assert "Alice" in result
    assert "Bob" in result


def test_encode_with_booleans():
    data = [
        {"id": 1, "active": True},
        {"id": 2, "active": False},
    ]
    result = zoon.encode(data)
    assert "active:b" in result
    assert "1" in result.split("\n")[1]


def test_encode_with_nulls():
    data = [
        {"id": 1, "value": "test"},
        {"id": 2, "value": None},
    ]
    result = zoon.encode(data)
    assert "~" in result





def test_encode_inline_object():
    data = {"name": "Alice", "age": 30, "active": True}
    result = zoon.encode(data)
    assert "name=Alice" in result or "name:Alice" in result
    assert "age:30" in result
    assert "active:y" in result


def test_encode_nested_object():
    data = {"user": {"name": "Alice", "settings": {"theme": "dark"}}}
    result = zoon.encode(data)
    assert "user:" in result
    assert "theme" in result


def test_encode_empty_array():
    data = []
    result = zoon.encode(data)
    assert result == "" or result == "[]"


def test_encode_spaces_in_strings():
    data = [
        {"id": 1, "name": "Hello World"},
        {"id": 2, "name": "Foo Bar"},
    ]
    result = zoon.encode(data)
    assert "Hello_World" in result
    assert "Foo_Bar" in result


def test_encode_nested_map():
    data = {
        "config": {"db": {"host": "localhost", "port": 5432}},
        "meta": {"version": "1.0"},
    }
    result = zoon.encode(data)
    assert "config:" in result
    assert "db:" in result
    assert "host=localhost" in result


def test_encode_floats():
    data = [
        {"name": "cpu", "value": 0.75},
        {"name": "mem", "value": 0.92},
    ]
    result = zoon.encode(data)
    assert "0.75" in result
    assert "0.92" in result
