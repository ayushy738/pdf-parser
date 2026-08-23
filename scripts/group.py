import json
with open('output/jesc101/jesc101_meta.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

blocks = data.get('children', [])[0].get('children', [])
groups = {}
for b in blocks:
    hierarchy = b.get('section_hierarchy', {})
    if hierarchy:
        deepest = hierarchy[str(max(int(k) for k in hierarchy.keys()))]
    else:
        deepest = 'root'
    
    if deepest not in groups:
        groups[deepest] = []
    groups[deepest].append(b)

for k, v in groups.items():
    print(f'Group: {k}')
    for b in v:
        print(f'  {b.get("block_type")}: {b.get("id")}')
