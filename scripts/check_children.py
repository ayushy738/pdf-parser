import json
with open('output/jesc101/jesc101_meta.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def find_deep_text(block):
    if block.get('block_type') == 'Text' and block.get('children'):
        print(f"TEXT BLOCK HTML: {block.get('html')}")
        print("CHILDREN:")
        for c in block.get('children'):
            print(f"  {c.get('block_type')}: bbox={c.get('bbox')} html={c.get('html')}")
        return True
    for c in block.get('children') or []:
        if find_deep_text(c): return True
    return False

find_deep_text(data)
