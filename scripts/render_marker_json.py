import os
import json
import base64
import argparse
import re

def load_marker_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_pages(data):
    pages = []
    for child in data.get("children", []):
        if child.get("block_type") == "Page":
            pages.append(child)
    return pages

def extract_assets_recursive(block, assets_dir, asset_map):
    if not block:
        return
    images = block.get("images") or {}
    for img_id, img_data in images.items():
        if img_data.startswith("/9j/"):
            ext = "jpg"
        elif img_data.startswith("iVBORw0KGgo"):
            ext = "png"
        else:
            ext = "bin"
        clean_id = img_id.replace("/", "_").strip("_")
        filename = f"{clean_id}.{ext}"
        filepath = os.path.join(assets_dir, filename)
        try:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(img_data))
            asset_map[img_id] = f"../assets/{filename}"
        except Exception as e:
            print(f"Error saving image {img_id}: {e}")
    for child in block.get("children") or []:
        extract_assets_recursive(child, assets_dir, asset_map)

def extract_assets(pages, output_dir):
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    asset_map = {}
    for page in pages:
        extract_assets_recursive(page, assets_dir, asset_map)
    return asset_map

def clean_html(html_str):
    if not html_str:
        return ""
    cleaned = re.sub(r'<content-ref[^>]*></content-ref>', '', html_str)
    return cleaned.strip()

def transform_sup_bullets(html_str):
    """Convert Marker's <sup>n</sup> bullet markers into visible bullet list items."""
    if not html_str:
        return html_str
    # Marker uses <sup>n</sup> as bullet point markers within a <p> block.
    parts = re.split(r'<sup>n</sup>\s*', html_str)
    if len(parts) <= 1:
        return html_str  # No bullet markers found
    
    result_parts = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if i == 0:
            result_parts.append(part)
        else:
            # Use a span with display:block to create line breaks without extra height
            result_parts.append(f'<span style="display:block;">\u2022 {part}</span>')
    
    return ''.join(result_parts)

def get_block_bbox(block):
    b = block.get("bbox")
    if b and len(b) == 4:
        return b
    return None

def get_activity_sections(blocks):
    """Identify activity sections from section_hierarchy and compute their background bboxes."""
    activity_sections = {}
    for block in blocks:
        hierarchy = block.get("section_hierarchy", {})
        if not hierarchy:
            continue
        deepest_key = str(max(int(k) for k in hierarchy.keys()))
        group_id = hierarchy[deepest_key]
        if group_id not in activity_sections:
            activity_sections[group_id] = {"is_activity": False, "blocks": []}
        activity_sections[group_id]["blocks"].append(block)

    # Check which groups are Activity sections
    for group_id, info in activity_sections.items():
        for b in info["blocks"]:
            if b.get("block_type") == "SectionHeader" and "Activity" in (b.get("html") or ""):
                info["is_activity"] = True
                break

    # Compute union bboxes for activity groups (excluding PageFooter)
    result = []
    for group_id, info in activity_sections.items():
        if info["is_activity"]:
            content_blocks = [b for b in info["blocks"] if b.get("block_type") != "PageFooter"]
            if content_blocks:
                bboxes = [get_block_bbox(b) for b in content_blocks if get_block_bbox(b)]
                if bboxes:
                    x1 = min(b[0] for b in bboxes)
                    y1 = min(b[1] for b in bboxes)
                    x2 = max(b[2] for b in bboxes)
                    y2 = max(b[3] for b in bboxes)
                    result.append([x1, y1, x2, y2])
    return result

def render_block(block, asset_map, debug=False):
    """Render a single block positioned directly on the page (no parent offset)."""
    block_type = block.get("block_type", "Unknown")
    bbox = get_block_bbox(block)

    if not bbox:
        return ""

    left = bbox[0]
    top = bbox[1]
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    # Build content
    content_html = block.get("html", "") or ""
    is_content_empty = not clean_html(content_html)

    # Handle image blocks
    if is_content_empty:
        images = block.get("images") or {}
        for img_id in images:
            if img_id in asset_map:
                content_html += f'<img src="{asset_map[img_id]}" style="width:100%; height:100%; object-fit:contain; display:block;">'
                is_content_empty = False

    if is_content_empty and not debug:
        return ""

    # Transform <sup>n</sup> bullet markers into visual line breaks
    if block_type == "Text":
        content_html = transform_sup_bullets(content_html)

    # CSS class based on block type
    css_class = f"marker-block marker-{block_type.lower()}"

    # Style: position directly on the page
    extra_style = ""
    if block_type in ("Picture",):
        # Images get fixed dimensions
        style = f"position:absolute; left:{left}px; top:{top}px; width:{width}px; height:{height}px;"
    elif block_type == "SectionHeader":
        # Auto-size heading font to fit within bbox
        # Estimate: for a single-line heading, font-size ~ height * 0.7
        # For multi-line, use a smaller ratio
        heading_font_size = min(height * 0.45, 22)  # cap at 22px
        heading_font_size = max(heading_font_size, 10)  # floor at 10px
        style = f"position:absolute; left:{left}px; top:{top}px; width:{width}px; height:{height}px; overflow:hidden;"
        extra_style = f" font-size:{heading_font_size:.1f}px;"
    else:
        # Text blocks: use bbox dimensions and clip overflow
        style = f"position:absolute; left:{left}px; top:{top}px; width:{width}px; height:{height}px; overflow:hidden;"

    # Debug overlays
    debug_html = ""
    if debug:
        style += " outline: 1px solid red;"
        debug_html = (
            f'<div style="position:absolute; top:-14px; left:0; background:red; color:white;'
            f' font-size:9px; z-index:9999; padding:1px 3px; white-space:nowrap;'
            f' pointer-events:none;">[{block_type}] {block.get("id","")}</div>'
        )

    return f'<div class="{css_class}" style="{style}{extra_style}">{debug_html}{content_html}</div>\n'


def render_page(page, page_idx, total_pages, asset_map, debug=False):
    bbox = get_block_bbox(page)
    if bbox:
        page_width = bbox[2] - bbox[0]
        page_height = bbox[3] - bbox[1]
    else:
        page_width = 576
        page_height = 785

    blocks = page.get("children", []) or []

    # --- Activity background divs (decorative, behind content) ---
    activity_bboxes = get_activity_sections(blocks)
    activity_bg_html = ""
    for ab in activity_bboxes:
        pad = 8
        ax, ay, ax2, ay2 = ab
        activity_bg_html += (
            f'<div class="marker-activity-bg" style="position:absolute;'
            f' left:{ax - pad}px; top:{ay - pad}px;'
            f' width:{ax2 - ax + 2*pad}px; height:{ay2 - ay + 2*pad}px;'
            f' background:#E8F6F8; border:1px solid #B8DEE6; border-radius:6px;'
            f' z-index:0; box-sizing:border-box;"></div>\n'
        )

    # --- Render each block directly on the page ---
    blocks_html = []
    for block in blocks:
        html = render_block(block, asset_map, debug)
        if html:
            blocks_html.append(html)

    blocks_joined = "\n".join(blocks_html)

    # --- Navigation (outside page area) ---
    nav_html = "<div class='nav-buttons'>"
    if page_idx > 0:
        nav_html += f"<a href='page-{page_idx-1}.html'>&laquo; Previous</a>"
    nav_html += f"<span>Page {page_idx} of {total_pages - 1}</span>"
    if page_idx < total_pages - 1:
        nav_html += f"<a href='page-{page_idx+1}.html'>Next &raquo;</a>"
    nav_html += "</div>"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Page {page_idx}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            background: #e0e0e0;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            font-family: serif;
        }}

        .nav-buttons {{
            text-align: center;
            margin: 16px 0;
            font-family: sans-serif;
            font-size: 14px;
        }}
        .nav-buttons a {{
            margin: 0 12px;
            padding: 8px 16px;
            background: #ddd;
            text-decoration: none;
            border-radius: 4px;
            color: #333;
        }}
        .nav-buttons a:hover {{ background: #ccc; }}

        #viewer-wrapper {{
            background: white;
            box-shadow: 0 4px 16px rgba(0,0,0,0.18);
            width: 100%;
            max-width: {page_width}px;
            margin: 0 auto;
            overflow: hidden;
            position: relative;
        }}
        #viewer-container {{
            width: {page_width}px;
            height: {page_height}px;
            transform-origin: top left;
        }}
        .pdf-page {{
            position: relative;
            background: white;
            width: {page_width}px;
            height: {page_height}px;
        }}

        /* ---- Block base ---- */
        .marker-block {{
            box-sizing: border-box;
            z-index: 1;
        }}

        /* ---- Text blocks ---- */
        .marker-text {{
            font-family: "Times New Roman", "Noto Serif", Georgia, serif;
            font-size: 10px;
            line-height: 1.22;
            color: #222;
        }}
        .marker-text p {{
            margin: 0;
        }}

        /* ---- Section headers ---- */
        .marker-sectionheader {{
            font-family: Arial, Helvetica, sans-serif;
        }}
        .marker-sectionheader h2 {{
            font-family: Arial, Helvetica, sans-serif;
            font-weight: bold;
            color: #007A99;
            line-height: 1.15;
            margin: 0;
        }}

        /* ---- Captions ---- */
        .marker-caption {{
            font-family: "Times New Roman", serif;
            font-size: 9.5px;
            line-height: 1.25;
            color: #333;
        }}
        .marker-caption p {{ margin: 0; }}

        /* ---- Page header / footer ---- */
        .marker-pageheader, .marker-pagefooter {{
            font-family: "Times New Roman", serif;
            font-size: 10px;
            color: #555;
        }}

        /* ---- Lists ---- */
        .marker-block ul, .marker-block ol {{
            padding-left: 18px;
            margin: 0;
        }}
        .marker-block li {{
            margin: 0;
        }}

        /* ---- Inline formatting preservation ---- */
        .marker-block sup {{ font-size: 0.7em; vertical-align: super; }}
        .marker-block sub {{ font-size: 0.7em; vertical-align: sub; }}

    </style>
</head>
<body>
    {nav_html}

    <div id="viewer-wrapper">
        <div id="viewer-container">
            <div class="pdf-page">
                {activity_bg_html}
                {blocks_joined}
            </div>
        </div>
    </div>

    {nav_html}

    <script>
        function resize() {{
            const wrapper = document.getElementById('viewer-wrapper');
            const container = document.getElementById('viewer-container');
            const targetWidth = {page_width};
            const targetHeight = {page_height};
            const availableWidth = wrapper.clientWidth;
            const scale = availableWidth / targetWidth;
            container.style.transform = 'scale(' + scale + ')';
            wrapper.style.height = (targetHeight * scale) + 'px';
        }}
        window.addEventListener('resize', resize);
        resize();
    </script>
</body>
</html>
"""
    return html


def parse_range(range_str, max_val):
    if not range_str:
        return 0, max_val
    parts = range_str.split('-')
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if len(parts) > 1 and parts[1] else max_val - 1
    return start, end

def get_block_types_recursive(block, type_set):
    if block:
        btype = block.get("block_type")
        if btype:
            type_set.add(btype)
        for child in block.get("children") or []:
            get_block_types_recursive(child, type_set)

def main():
    parser = argparse.ArgumentParser(description="Render Marker JSON to HTML")
    parser.add_argument("input_json", help="Path to Marker JSON file")
    parser.add_argument("output_dir", help="Directory to save HTML and assets")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--page-range", help="Page range to render (e.g., 0-2)")

    args = parser.parse_args()

    print(f"Loading JSON from {args.input_json}...")
    data = load_marker_json(args.input_json)

    print("Parsing pages...")
    pages = parse_pages(data)
    total_pages = len(pages)
    print(f"Found {total_pages} pages.")

    start_idx, end_idx = parse_range(args.page_range, total_pages)
    end_idx = min(end_idx, total_pages - 1)

    pages_to_render = pages[start_idx:end_idx+1]
    print(f"Rendering pages {start_idx} to {end_idx}...")

    print("Extracting assets...")
    asset_map = extract_assets(pages_to_render, args.output_dir)
    print(f"Extracted {len(asset_map)} assets.")

    pages_dir = os.path.join(args.output_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    block_types = set()

    for i, page in enumerate(pages_to_render):
        actual_idx = start_idx + i
        html = render_page(page, actual_idx, total_pages, asset_map, args.debug)
        get_block_types_recursive(page, block_types)
        out_path = os.path.join(pages_dir, f"page-{actual_idx}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

    index_path = os.path.join(args.output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f'<meta http-equiv="refresh" content="0; url=pages/page-{start_idx}.html" />')

    print(f"Stats:")
    print(f"  Pages rendered: {len(pages_to_render)}")
    print(f"  Assets extracted: {len(asset_map)}")
    print(f"  Block types encountered: {', '.join(sorted(block_types))}")
    print(f"Done! Output saved to {args.output_dir}")

if __name__ == "__main__":
    main()
