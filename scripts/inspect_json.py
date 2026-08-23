import json

with open('output/jesc101/jesc101_meta.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def find_all(block):
    html = block.get('html', '')
    if html:
        print(block.get("block_type") + ": " + html)
    for c in block.get('children') or []:
        find_all(c)

find_all(data)
