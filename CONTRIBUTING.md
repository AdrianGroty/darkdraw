# Contributing to DarkDraw

Thank you for your interest in contributing to DarkDraw! This document provides guidelines for development and contributions.

## Getting Started

### Prerequisites
- Python 3.7+
- VisiData >= v3.0
- Git
- A terminal with Unicode and 256-color support

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/devottys/darkdraw.git
   cd darkdraw
   ```

2. **Install in development mode**
   ```bash
   pip3 install -e .
   ```
   This allows you to edit code and see changes immediately without reinstalling.

3. **Launch DarkDraw**
   ```bash
   vd newfile.ddw
   ```
   or open an existing file:
   ```bash
   vd myart.ddw
   ```

### Project Structure

```
- darkdraw/               # Main package (~2200 lines total)
- darkdraw/drawing.py     # Core drawing system (~1200 lines)
- darkdraw/box.py         # Box drawing utilities
- darkdraw/flip.py        # Flip/mirror operations
- darkdraw/save.py        # PNG/GIF export
- darkdraw/ansihtml.py    # HTML export
- samples/                # Example .ddw files for demonstration and testing
```

## Adding a New Command

```python
@Drawing.api
def my_operation(sheet, rows):
    """Docstring describing the operation."""
    for r in rows:
        vd.addUndo(setattr, r, 'property', r.property)
        r.property = new_value
    vd.status('operation complete')

Drawing.addCommand('gx', 'my-operation', 'my_operation(cursorRows)', 'help text')

vd.addMenuItems('''
    DarkDraw > Category > my-operation
''')

- Note the symmetry between `my-operation` command longname and `my_operation` function name.
- If command uses the cursor, always include cursorRows or other `cursor*` in the command string literal.
```

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows STYLE.md conventions
- [ ] Changes are manually tested
- [ ] Commit messages are clear
- [ ] PR description explains what and why (with screenshots if applicable)

## Issue Guidelines

### Reporting Bugs

Include:
- VisiData and DarkDraw version (`vd --version`)
- Operating system and terminal
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if relevant

### Requesting Features

Include:
- Clear description of feature
- Use case and motivation
- Mockups or examples if helpful
- Exact steps for workflow

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).
