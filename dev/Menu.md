# Converting Menu Items from Old-Style to New-Style String Format

## Overview

This guide explains how to convert menu definitions from the old nested `Menu()` object syntax to the new string-based `vd.addMenuItems()` format. The new format is more concise, readable, and easier to maintain.

### Rules for Menu Commands

- the addMenuItem for a command should be in the file as the command is defined in.

## Syntax Comparison

### Old Style
```python
# Individual top-level menu items
vd.addMenuItem('File', 'New drawing', 'new-drawing')
vd.addMenuItem('View', 'Unicode browser', 'open-unicode')

# Nested menu structure
vd.addMenu(Menu('DarkDraw',
    Menu('New drawing', 'new-drawing'),
    Menu('View',
        Menu('Colors sheet', 'open-colors'),
        Menu('Unicode characters', 'open-unicode'),
    ),
    Menu('Animation',
        Menu('Go to frame',
            Menu('first', 'first-frame'),
            Menu('next', 'next-frame'),
        ),
    ),
))
```

### New Style
```python
vd.addMenuItems('''
    File > New drawing > new-drawing
    View > Unicode browser > open-unicode
    DarkDraw > New drawing > new-drawing
    DarkDraw > View > Colors sheet > open-colors
    DarkDraw > View > Unicode characters > open-unicode
    DarkDraw > Animation > Go to frame > first > first-frame
    DarkDraw > Animation > Go to frame > next > next-frame
''')
```

## Conversion Steps

### 1. Convert Top-Level `addMenuItem()` Calls

**Pattern:**
```python
vd.addMenuItem('MenuName', 'Item Label', 'command-name')
```

**Converts to:**
```python
MenuName > Item Label > command-name
```

### 2. Convert Nested `Menu()` Structures

**Pattern:**
```python
vd.addMenu(Menu('TopMenu',
    Menu('Submenu',
        Menu('Item', 'command-name'),
    ),
))
```

**Converts to:**
```python
TopMenu > Submenu > Item > command-name
```

**Rule:** Join all menu levels with ` > ` (space-greater-than-space), ending with the command name.

### 3. Handle Multiple Items at Same Level

Each menu path becomes a separate line in the string:

```python
# Old
Menu('Color',
    Menu('Set default from cursor', 'set-default-cursor'),
    Menu('Set to input', 'set-color-input'),
)

# New
DarkDraw > Color > Set default from cursor > set-default-cursor
DarkDraw > Color > Set to input > set-color-input
```

### 4. Flatten Deeply Nested Menus

```python
# Old
Menu('Animation',
    Menu('Go to frame',
        Menu('first', 'first-frame'),
        Menu('last', 'last-frame'),
    ),
)

# New
DarkDraw > Animation > Go to frame > first > first-frame
DarkDraw > Animation > Go to frame > last > last-frame
```

## Common Pitfalls and How to Avoid Them

### 1. Duplicate Menu Items
Watch for duplicate paths when consolidating multiple old-style calls:
```python
# BAD - duplicate entry
DarkDraw > View > Colors sheet > open-colors
DarkDraw > View > Colors sheet > open-colors

# GOOD - single entry
DarkDraw > View > Colors sheet > open-colors
```

### 2. Typos in Command Names
Verify that command names match their definitions:
```python
# Search for the actual command definition
Drawing.addCommand('g>', 'color-selected-next', ...)
Drawing.addCommand('g<', 'color-selected-prev', ...)

# Use the exact command name in the menu
DarkDraw > Color > Cycle > selected > up > color-selected-prev  # NOT color-selected-up
```

### 3. Incorrect Nesting Levels
Ensure the menu path accurately reflects the original hierarchy. Count the nesting levels carefully:
```python
# Old - 4 levels: DarkDraw > Color > Cycle > cursor > down
Menu('Color',
    Menu('Cycle',
        Menu('cursor',
            Menu('down', 'cycle-cursor-prev'),
        ),
    ),
)

# New - maintain the same 4 levels
DarkDraw > Color > Cycle > cursor > down > cycle-cursor-prev
```

## Verification Checklist

After conversion, verify:

1. **No duplicates** - Each menu path should appear only once
2. **Command names exist** - Search codebase for each command to verify it's defined:
   ```bash
   grep -r "command-name" . --include="*.py"
   ```
3. **Hierarchy preserved** - Menu nesting matches the original structure
4. **All items converted** - Count menu items in old code and verify same count in new code
5. **Structural changes intentional** - If menu hierarchy was flattened (e.g., moving items up a level), verify this was intentional

## Testing

After conversion:
1. Run the application and open the menu system
2. Navigate through each menu path to ensure it works
3. Verify each command executes correctly when selected
4. Check for any missing or misplaced menu items

## Benefits of New Format

- **Conciseness**: ~40% reduction in lines of code
- **Readability**: Clear visual hierarchy without nested parentheses
- **Maintainability**: Easier to add, remove, or reorder menu items
- **Less error-prone**: Simpler syntax reduces chance of bracket matching errors
- **Greppable**: Easy to search for specific menu paths

## Example: Complete Conversion

See commit `bc20cb7` in the darkdraw repository for a real-world example of this conversion, which converted 61 lines of old-style menu code to 36 lines of new-style string format.
