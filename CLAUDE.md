# DarkDraw

## Project Context

- DarkDraw is a VisiData plugin for terminal art and animation
- ~2200 lines across ~12 Python modules
- Core: DrawingSheet (data model) + Drawing (visual layer) + FramesSheet (animation)
- Main file: `darkdraw/drawing.py` (~1200 lines)
- Native format: JSON Lines (.ddw)
- Export formats: PNG, GIF, ANSI, HTML

- Look in dev/ for rules about specific domains.
- Code Style: follow VisiData patterns (see STYLE.md)

## Import Ordering

Always order imports in this sequence, with groups separated by a single blank line:
1. Standard library imports (itertools, math, copy, etc.)
2. VisiData imports (from visidata import ...)
3. Third-party imports (if any)
4. Internal darkdraw imports (from darkdraw import ...)

## Parameter Naming Conventions

Drawing and DrawingSheet are conceptually distinct:
- **Drawing** (visual layer): Use `dwg` as the self parameter
- **DrawingSheet** (data model): Use `sheet` as the self parameter (standard VisiData convention)

This distinction makes the conceptual difference clear in code.

## Meta Rules

- Update CLAUDE.md whenever major context is learned.
- When the user says "learn to X", add a rule to ensure X happens automatically next time.
- When checking files for style consistency, always check for and remove unnecessary imports.

## Documentation and Communication

- Use round approximations for code metrics to avoid staleness:
  - "~1200 lines" instead of "1,199 lines"
- Keep documentation token-efficient - prefer overviews to comprehensive details
- See STYLE.md for coding conventions
- See DESIGN.md for architecture overview
- See CONTRIBUTING.md for development workflow

## Refactoring Pattern

When extracting functionality from drawing.py into a separate module, include all of:
- Functions being extracted
- Functions that only those functions call directly
- `@Drawing.api` / `@Sheet.api` decorated methods
- Command registrations (`Drawing.addCommand()`, etc.) that use those functions
- Sheet initialization (`Drawing.init()`, etc.) for variables only those functions use
- Menu items (`vd.addMenuItems()`) for those commands
- Keep all related functionality together in the same file

After extraction, **always check the source file (drawing.py) for imports that are now unused** and remove them.

