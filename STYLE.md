# DarkDraw Style Guide

This document defines the coding conventions for DarkDraw, following VisiData patterns and Python best practices.

## Code Organization

### Import Order

Always order imports in this sequence, with groups separated by a single blank line:
1. Standard library imports
2. VisiData imports
3. Third-party imports (if any)
4. Internal darkdraw imports

Example:
```python
import itertools
from collections import defaultdict
from copy import copy

from visidata import vd, CharBox, dispwidth
from visidata.bezier import bezier

from darkdraw import Drawing
```

### File Structure
- Module-level constants and configuration first (vd.option, globals)
- Helper functions and utilities
- Class definitions
- Command/menu registrations at end

## Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `CamelCase`
- **Private/internal**: Leading underscore `_private_var`

## VisiData Patterns

### Extending Classes
Use the `@ClassName.api` decorator to add methods to VisiData or DarkDraw classes in other modules:

```python
@Drawing.api
def my_method(sheet, arg):
    # method implementation
```

#### Properties
- Use `@ClassName.property` for computed values
- Use `@functools.cached_property` for expensive computations
- Use `@drawcache_property` to cache properties that don't change within one draw cycle

### Commands
Register commands with `addCommand()`:
```python
Sheet.addCommand('gCtrl+S', 'save-selected', 'save_selected()', 'save selected rows')
```

Format: `addCommand(keystrokes, longname, execstr, helpstr)`

Prefer prettykeys format like `gCtrl+S` to `g^S`.

### Menus
Use `vd.addMenuItems()` with multi-line string format:
```python
vd.addMenuItems('''
    DarkDraw > Action > Subaction > context > command-name
''')

When several actions are variants of the same thing, the core concept should be a capitalized word on its own, while subactions or context should be lowercase.
The Action/Subaction and context should form a logical cascade of words or concepts, from more general to more specific.
```

### User Feedback
- `vd.status('message')` - informational messages
- `vd.warning('message')` - warnings
- `vd.fail('message')` - usage errors (raise exception, don't need return)
- `vd.error('message')` - internal errors (raise exception, don't need return)
- `vd.exceptionCaught(e)` - show exception traceback within an `except:` block

### Undo Support
Always add undo for state changes:
```python
vd.addUndo(setattr, obj, 'attr', old_value)
vd.addUndo(list.remove, mylist, item)
```

`vd.addUndo(func, *args, *kwargs)` will call `func(*args, *kwargs)` to undo the action.
Where reasonable, call addUndo before making the change that will be undone.

## Code Style

- Indentation: 4 spaces (no tabs)
- Line Length: Aim for <100 characters (no hard limit, prefer readability)
- Comments: use `# ` (space after hash) for inline comments
- Reference issues with `#123` format as needed
- Keep comments concise and meaningful
- Prefer f-strings for new code: `f"value: {x}"`

## Data Structures

### Row Objects
`AttrDict` is used for more convenient dict key access:
```python
row = AttrDict(x=0, y=0, text='', color='', tags=[], group='')
if row.x == 0:
    ...
```

### Type Hints
- Not currently used extensively
- Optional for new code
- Focus on clarity over type completeness
- type imports not preferred; use type strings when necessary

## Documentation

### Docstrings
- Use for complex functions and classes
- Inline rowdef documentation: `rowtype='elements'  # rowdef: { .x, .y, .text }`
- Keep docstrings brief and practical

### Code Comments
- Explain *why*, not *what*
- Use for non-obvious logic
- Avoid over-commenting obvious code

## Best Practices

### Simplicity
- Avoid over-engineering
- Don't add features not explicitly needed
- Keep functions focused and single-purpose

### Performance
- Use `Progress()` wrapper on iterators in loops within `@asyncthread` functions (or called by asyncthread functions)

### State Management
- Mark sheets as modified: `self.setModified()`
- Prefer immutable operations where practical
