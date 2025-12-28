import zoon


def test_decode_simple_tabular():
    encoded = """# id:i+ name:s role=admin|user
Alice admin
Bob user
Carol user"""
    result = zoon.decode(encoded)
    assert len(result) == 3
    assert result[0]["name"] == "Alice"
    assert result[0]["role"] == "admin"
    assert result[1]["role"] == "user"





def test_decode_with_null():
    encoded = """# name:s value:s
Alice test
Bob ~"""
    result = zoon.decode(encoded)
    assert result[0]["value"] == "test"
    assert result[1]["value"] is None


def test_decode_booleans():
    encoded = """# name:s active:b
Alice 1
Bob 0"""
    result = zoon.decode(encoded)
    assert result[0]["active"] is True
    assert result[1]["active"] is False


def test_decode_numbers():
    encoded = """# name:s price:n
Widget 19.99
Gadget 29.50"""
    result = zoon.decode(encoded)
    assert result[0]["price"] == 19.99
    assert result[1]["price"] == 29.50
