from darkdraw import Drawing, dispwidth
from copy import copy


@Drawing.api
def split_objects(sheet, rows):
### Split multi-character text objects into individual character objects.
    new_rows = []
    rows_to_delete = []
    
    for r in rows:
        # Only process text objects with actual text
        if not r.text or r.type:
            continue
            
        text_len = len(r.text)
        
        # Skip single-character objects
        if text_len <= 1:
            continue
            
        rows_to_delete.append(r)
        
        # Create new row for each character
        x_offset = 0
        for char in r.text:
            new_r = sheet.newRow()
            new_r.update(copy(r.__dict__))
            new_r.text = char
            new_r.x = r.x + x_offset
            new_r.y = r.y
            
            # Preserve all other attributes (color, tags, group, frame, etc.)
            new_rows.append(new_r)
            sheet.source.addRow(new_r)
            
            x_offset += dispwidth(char)
    
    # Delete original multi-char objects
    sheet.source.deleteBy(lambda row, rows=rows_to_delete: row in rows)
    
    return len(new_rows)


Drawing.addCommand('/', 'split-cursor', 
    'n = split_objects(sheet.cursorRows); '
    'status(f"split into {n} objects")', 
    'split multi-character objects under cursor into individual characters')

Drawing.addCommand('g/', 'split-selected', 
    'n = split_objects(sheet.source.someSelectedRows); '
    'status(f"split into {n} objects")', 
    'split selected multi-character objects into individual characters')
