import json

with open('output/jesc101/jesc101_meta.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

page = data['children'][0]
print(f"Page bbox: {page['bbox']}")
print(f"Page dimensions: {page['bbox'][2] - page['bbox'][0]} x {page['bbox'][3] - page['bbox'][1]}")
print()

for child in page.get('children', []):
    bbox = child.get('bbox', [])
    if len(bbox) == 4:
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    else:
        w = h = 0
    html = child.get('html', '') or ''
    text_len = len(html)
    hierarchy = child.get('section_hierarchy', {})
    deepest = ''
    if hierarchy:
        deepest = hierarchy[str(max(int(k) for k in hierarchy.keys()))]
    
    print(f"ID: {child['id']}")
    print(f"  Type: {child['block_type']}")
    print(f"  bbox: [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}]")
    print(f"  size: {w:.1f} x {h:.1f}")
    print(f"  hierarchy: {deepest}")
    print(f"  html_len: {text_len}")
    print(f"  html: {html[:120]}")
    print()
