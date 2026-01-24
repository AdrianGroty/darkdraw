# DarkDraw Design Overview

Brief architecture overview for understanding the codebase structure.

## Core Concept

DarkDraw is a VisiData plugin that treats art as data. The drawing you see is a visual representation of structured data you can manipulate directly.

## Three-Layer Architecture

### 1. DrawingSheet (Data Model)
**File**: `drawing.py` (~1200 lines)

JSON-based data layer storing drawing elements as rows.

**Row structure**:
```python
{
    'id': str,           # unique identifier
    'type': str,         # '', 'frame', 'group', 'ref'
    'x': int, 'y': int,  # position
    'text': str,         # character to display
    'color': str,        # 'fg on bg' format
    'tags': list,        # arbitrary tags
    'group': str,        # group membership
    'frame': str,        # frame(s) element appears in
    'rows': list         # child elements (for groups)
}
```

**Key methods**:
- `addRow(row)` - add element with undo support
- `iterdeep(rows)` - recursively traverse groups
- `group_selected(name)` - create group from selection

### 2. Drawing (Visual Layer)
Extends VisiData's `TextCanvas`. Renders DrawingSheet data to terminal.

**Responsibilities**:
- Cursor management and movement
- Element rendering with colors
- Selection handling
- Animation frame display
- Viewport scrolling

**Key properties**:
- `cursorBox` - current cursor bounds
- `selectedRows` - selected elements
- `currentFrame` - active animation frame

### 3. FramesSheet (Animation)
Manages animation frames as a sheet.

**Columns**: type, id, duration_ms, x, y

## Key Concepts

### Elements vs Objects
- **Element**: Single string rendered at (x,y) position with (one row)
- **Group**: Container element (type='group') with child rows
- **Frame**: Animation frame object (type='frame'; other elements frame='frame')

### Coordinate System
- Origin (0,0) at top-left
- X increases rightward
- Y increases downward
- Terminal-based coordinates

### Color System
Format: `'[attr] [fg] on [bg]'`
- Colors: named (red, blue) or numeric (0-255)
- Attributes: bold, underline
- Example: `'bold red on black'`

### Groups and Hierarchy
- Elements can be grouped
- Groups can contain groups (recursive)
- Groups have relative coordinates
- `iterdeep()` flattens hierarchy with absolute positions

### Frames and Animation
- Frames are special rows (type='frame')
- Elements tagged with frame ID(s)
- No frame id on element means always display (background/base frame)
- Element can appear in multiple frames
- Frame has duration_ms for playback timing

### References
- Type='ref' creates instance of a group
- References have position offset
- Enables reuse without duplication

## VisiData Integration

DarkDraw extends VisiData with:
- **Sheet types**: DrawingSheet, FramesSheet
- **Canvas type**: Drawing
- **Loaders**: .ddw, .dur, .scr
- **Savers**: .ddw, .png, .gif, .ansihtml
- **Commands**: ~100 keybindings for drawing operations
- **Menus**: Hierarchical menu structure

## Data Flow

```
User Input → Drawing (canvas)
           ↓
     Modifies DrawingSheet (data)
           ↓
     Triggers re-render
           ↓
     Drawing displays updated state
```

## File Format

Native `.ddw` format is JSON Lines:
```json
{"x": 5, "y": 3, "text": "A", "color": "red", "id": "e1", "type": ""}
{"x": 6, "y": 3, "text": "B", "color": "blue", "id": "e2", "type": ""}
{"type": "frame", "id": "0", "duration_ms": 100}
```

Each line is a complete JSON object. Easily parsed, human-readable, git-friendly.

## Extension Points

Add new capabilities by:
- New commands via `Drawing.addCommand()`
- New methods via `@Drawing.api` decorator
- New file formats via `vd.open_xyz()` and `vd.save_xyz()`
- New menu items via `vd.addMenuItems()`

## Performance Considerations

- `@drawcache_property` for expensive computations
- `vd.clearCaches()` invalidates the drawcache, which may be necessary after data changes asynchronously
