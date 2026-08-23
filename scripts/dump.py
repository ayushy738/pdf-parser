import json
with open('output/jesc101/jesc101_meta.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for child in data.get('children', [])[0].get('children', []):
    print(f"{child.get('block_type')}: {child.get('html', '')[:30]} | Hierarchy: {child.get('section_hierarchy')}")
