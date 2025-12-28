import sys
import json
import difflib
import pprint
from src.zoon import encode, decode

def debug():
    data = [
        {"infrastructure": {"postgres": {"status": "up"}, "redis": {"status": "up"}}},
        {"infrastructure": {"postgres": {"status": "down"}, "redis": {"status": "down"}}}
    ]
    
    print("--- Original Data ---")
    pprint.pprint(data)
    
    encoded = encode(data)
    print("\n--- Encoded ---")
    print(encoded)
    
    if "%" not in encoded:
        print("\nERROR: Header aliases not used!")
        
    decoded = decode(encoded)
    print("\n--- Decoded ---")
    pprint.pprint(decoded)
    
    if decoded != data:
        print("\n--- Mismatch ---")
        # Ensure pretty printed strings for diff
        s1 = json.dumps(data, indent=2, sort_keys=True)
        s2 = json.dumps(decoded, indent=2, sort_keys=True)
        for line in difflib.unified_diff(s1.splitlines(), s2.splitlines(), fromfile='expected', tofile='actual'):
            print(line)
        sys.exit(1)
    else:
        print("\nSUCCESS: Match!")

if __name__ == "__main__":
    debug()
