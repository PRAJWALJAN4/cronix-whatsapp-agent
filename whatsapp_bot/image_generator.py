import os
from PIL import Image, ImageDraw, ImageFont

# Same mapping as index.html
CODE_PREFIX = {'s':'S', 'm':'M', 'l':'L', 'xl':'XL'}
LABEL_MAP = {'s':'SMALL', 'm':'MEDIUM', 'l':'LARGE', 'xl':'EXTRA LARGE'}
STATUS_COLORS = {
    'available': ((187, 247, 208), (20, 83, 45)), # Light Green BG, Dark Green Text
    'occupied': ((254, 202, 202), (127, 29, 29)), # Light Red BG, Dark Red Text
    'opened': ((254, 240, 138), (113, 63, 18))    # Yellow BG, Dark Yellow Text
}
SIZE_MAPPING = {'s':[1,2], 'm':[2,2], 'l':[2,3], 'xl':[2,4]}

def calculate_display_blocks(template_data):
    # Depending on new vs old JSON format
    setup = template_data.get('setupData', template_data)
    grid_data = setup.get('gridData', {})
    shape = setup.get('shape', '5x4')
    rows, cols = map(int, shape.split('x'))
    
    status = template_data.get('lockerStatus', {})
    
    block_map = {}
    for r in range(rows):
        for c in range(cols):
            cell_key = f"{r}-{c}"
            if cell_key in grid_data:
                cell = grid_data[cell_key]
                b_id = cell['blockId']
                if b_id not in block_map:
                    block_map[b_id] = {
                        'size': cell['size'],
                        'blockId': b_id,
                        'minR': r, 'maxR': r,
                        'minC': c, 'maxC': c
                    }
                b = block_map[b_id]
                b['minR'] = min(b['minR'], r)
                b['maxR'] = max(b['maxR'], r)
                b['minC'] = min(b['minC'], c)
                b['maxC'] = max(b['maxC'], c)
    
    # Sort and assign display codes
    blocks = list(block_map.values())
    blocks.sort(key=lambda x: (x['minR'], x['minC']))
    
    size_counts = {'s':0, 'm':0, 'l':0, 'xl':0}
    for b in blocks:
        sz = b['size']
        size_counts[sz] += 1
        # E.g. M2
        b['displayCode'] = f"{CODE_PREFIX[sz]}{size_counts[sz]}"
        b['status'] = status.get(b['blockId'], 'available')
        
    return blocks

def generate_grid_image(template_data, output_path, opened_block=None):
    setup = template_data.get('setupData', template_data)
    shape = setup.get('shape', '5x4')
    rows, cols = map(int, shape.split('x'))
    
    blocks = calculate_display_blocks(template_data)
    
    CELL_SIZE = 120
    PADDING = 20
    GAP = 10
    
    width = cols * CELL_SIZE + (cols - 1) * GAP + PADDING * 2
    height = rows * CELL_SIZE + (rows - 1) * GAP + PADDING * 2
    
    img = Image.new('RGB', (width, height), color=(203, 213, 225)) # slate-300
    draw = ImageDraw.Draw(img)
    
    # Try loading a font, fallback to default
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 32)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    for r in range(rows):
        for c in range(cols):
            x1 = PADDING + c * (CELL_SIZE + GAP)
            y1 = PADDING + r * (CELL_SIZE + GAP)
            x2 = x1 + CELL_SIZE
            y2 = y1 + CELL_SIZE
            
            draw.rectangle([x1, y1, x2, y2], fill=(248, 250, 252)) # empty cell color
    
    for b in blocks:
        x1 = PADDING + b['minC'] * (CELL_SIZE + GAP)
        y1 = PADDING + b['minR'] * (CELL_SIZE + GAP)
        x2 = PADDING + b['maxC'] * (CELL_SIZE + GAP) + CELL_SIZE
        y2 = PADDING + b['maxR'] * (CELL_SIZE + GAP) + CELL_SIZE
        
        stat = b['status']
        if opened_block and b['blockId'] == opened_block:
            stat = 'opened'
        
        bg_col, txt_col = STATUS_COLORS.get(stat, STATUS_COLORS['available'])
        
        # Draw block
        draw.rounded_rectangle([x1, y1, x2, y2], radius=16, fill=bg_col, outline=txt_col, width=4)
        
        # Draw text centered
        center_x = x1 + (x2 - x1) / 2
        center_y = y1 + (y2 - y1) / 2
        
        # Display Code e.g. M2
        code = b['displayCode']
        bbox = draw.textbbox((0, 0), code, font=font_large)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((center_x - tw/2, center_y - th/2), code, fill=txt_col, font=font_large)
        
        # Small Status / Size underneath
        stat_lbl = "UNLOCKED 🔓" if stat == 'opened' else "RESERVED 🔒" if stat == 'occupied' else "FREE ✅"
        bbox_s = draw.textbbox((0, 0), stat_lbl, font=font_small)
        sw = bbox_s[2] - bbox_s[0]
        st_h = bbox_s[3] - bbox_s[1]
        draw.text((center_x - sw/2, center_y + th/2 + 8), stat_lbl, fill=txt_col, font=font_small)

    img.save(output_path)
    return output_path
