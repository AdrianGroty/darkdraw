#!/usr/bin/env python3
"""Convert ANSI escape code text to DarkDraw (.ddw) format."""

import json
import re
import sys
from typing import List, Tuple


def rgb_to_256(r: int, g: int, b: int) -> int:
    """
    Convert RGB values (0-255) to closest xterm 256-color palette index.
    
    The 256-color palette consists of:
    - 0-15: Standard colors (same as 16-color)
    - 16-231: 6x6x6 color cube (216 colors)
    - 232-255: Grayscale ramp (24 shades)
    """
    # Check if it's grayscale (all components equal or very close)
    if abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
        # Use grayscale ramp (232-255)
        # Map 0-255 to 0-23 (24 grayscale levels)
        gray = (r + g + b) // 3
        if gray < 8:
            return 16  # Black
        elif gray > 247:
            return 231  # White
        else:
            return 232 + ((gray - 8) * 24 // 240)
    
    # Use 6x6x6 color cube (indices 16-231)
    # Each component (R,G,B) is mapped to 0-5
    # Formula: 16 + 36*r + 6*g + b
    r_cube = (r * 6) // 256
    g_cube = (g * 6) // 256
    b_cube = (b * 6) // 256
    
    return 16 + 36 * r_cube + 6 * g_cube + b_cube


def parse_ansi(text: str, wrap_at_80: bool = False) -> List[Tuple[int, int, str, str]]:
    """
    Parse ANSI escape codes and return list of (x, y, char, color).
    
    Args:
        text: Input text with ANSI codes
        wrap_at_80: If True, wrap lines at 80 columns
    
    Returns:
        List of tuples: (x_position, y_position, character, color_string)
    """
    # Store all character elements with their positions and colors
    elements = []
    
    # Track current position in 2D grid (column, row)
    x, y = 0, 0
    
    # Track the current color state as we parse
    current_fg_color = ""
    current_bg_color = ""
    current_bold = False
    
    # Map standard ANSI foreground color codes (30-37 normal, 90-97 bright) to simple color numbers
    # These correspond to the 16-color palette: black(0), red(1), green(2), etc.
    ansi_to_color = {
        30: "0", 31: "1", 32: "2", 33: "3",  # Normal colors: black, red, green, yellow
        34: "4", 35: "5", 36: "6", 37: "7",  # blue, magenta, cyan, white
        90: "8", 91: "9", 92: "10", 93: "11",  # Bright colors: bright black, red, green, yellow
        94: "12", 95: "13", 96: "14", 97: "15",  # bright blue, magenta, cyan, white
    }
    
    # Regex to match various ANSI escape sequences
    # ESC [ <numbers> m (SGR color codes), ESC [ <numbers> t (PabloDraw RGB codes),
    # ESC [ <numbers> A/B/C/D (cursor movement), etc.
    ansi_escape = re.compile(r'\x1b\[([0-9;]*)([A-Za-z])')
    
    # Find all ANSI escape sequences with their terminators
    # This approach handles the text and escape sequences separately
    last_pos = 0
    for match in ansi_escape.finditer(text):
        # Add text before the escape sequence
        text_before = text[last_pos:match.start()]
        for char in text_before:
            if char == '\n':  # Newline moves to next row
                y += 1
                x = 0
            elif char == '\r':  # Carriage return moves back to start of line
                x = 0
            else:  # Regular character - store it with current position and color
                # Check if wrapping is needed
                if wrap_at_80 and x >= 80:
                    y += 1
                    x = 0
                # Combine the color components into a single string
                color_components = []
                if current_fg_color:
                    color_components.append(current_fg_color)
                if current_bg_color:
                    color_components.append("on")
                    color_components.append(current_bg_color)
                if current_bold:
                    color_components.append("bold")
                combined_color = " ".join(color_components)
                elements.append((x, y, char, combined_color))
                x += 1  # Move to next column

        # Process the escape sequence based on its type (terminator character)
        codes_str, terminator = match.groups()

        # Parse semicolon-separated codes (e.g., "31;1" -> [31, 1])
        codes = [int(c) for c in codes_str.split(';') if c]

        if terminator == 'm':  # SGR (Select Graphic Rendition) - color and formatting codes
            # Process each code to update current color state
            # Some codes require multiple values (like 256-color mode), so use an index
            idx = 0
            while idx < len(codes):
                code = codes[idx]

                if code == 0:  # Code 0 = reset all attributes
                    current_fg_color = ""
                    current_bg_color = ""
                    current_bold = False
                    idx += 1
                elif code == 1:  # Code 1 = bold
                    current_bold = True
                    idx += 1
                elif code == 22:  # Code 22 = normal intensity (not bold)
                    current_bold = False
                    idx += 1
                elif code == 38:  # Extended foreground color
                    # Check if this is 256-color mode (38;5;N) or RGB mode (38;2;R;G;B)
                    if idx + 1 < len(codes):
                        if codes[idx + 1] == 5 and idx + 2 < len(codes):
                            # 256-color mode: ESC[38;5;Nm where N is 0-255
                            color_num = codes[idx + 2]
                            current_fg_color = str(color_num)
                            idx += 3  # Skip past 38, 5, and the color number
                        elif codes[idx + 1] == 2 and idx + 4 < len(codes):
                            # RGB mode: ESC[38;2;R;G;Bm
                            # DarkDraw doesn't have native RGB, so convert to approximate 256-color
                            r, g, b = codes[idx + 2], codes[idx + 3], codes[idx + 4]
                            # Use simplified RGB to 256-color conversion
                            color_num = rgb_to_256(r, g, b)
                            current_fg_color = str(color_num)
                            idx += 5  # Skip past 38, 2, R, G, B
                        else:
                            idx += 1
                    else:
                        idx += 1
                elif code == 48:  # Extended background color
                    # Same as foreground but for background
                    if idx + 1 < len(codes):
                        if codes[idx + 1] == 5 and idx + 2 < len(codes):
                            # 256-color mode: ESC[48;5;Nm
                            color_num = codes[idx + 2]
                            current_bg_color = str(color_num)
                            idx += 3
                        elif codes[idx + 1] == 2 and idx + 4 < len(codes):
                            # RGB mode: ESC[48;2;R;G;Bm
                            r, g, b = codes[idx + 2], codes[idx + 3], codes[idx + 4]
                            color_num = rgb_to_256(r, g, b)
                            current_bg_color = str(color_num)
                            idx += 5
                        else:
                            idx += 1
                    else:
                        idx += 1
                elif code in ansi_to_color:  # Standard foreground color code
                    current_fg_color = ansi_to_color[code]
                    idx += 1
                elif 40 <= code <= 47:  # Background colors (normal)
                    # Convert to background color string (bg0-bg7)
                    bg = str(code - 40)
                    current_bg_color = str(bg)
                    idx += 1
                elif 100 <= code <= 107:  # Background colors (bright)
                    # Convert to bright background color string (bg8-bg15)
                    bg = str(code - 100 + 8)
                    current_bg_color = str(bg)
                    idx += 1
                else:
                    # Unknown code - skip it
                    idx += 1
        elif terminator == 't' and len(codes) >= 4 and codes[0] in [0, 1]:  # PabloDraw RGB codes
            # Handle PabloDraw RGB codes: \x1b[(0|1);R;G;Bt
            # codes[0] is 0 for background or 1 for foreground
            # codes[1], codes[2], codes[3] are R, G, B values
            r, g, b = codes[1], codes[2], codes[3]
            color_num = rgb_to_256(r, g, b)

            if codes[0] == 0:  # Background
                current_bg_color = str(color_num)
            elif codes[0] == 1:  # Foreground
                current_fg_color = str(color_num)
        elif terminator in 'ABCDEFGHf':  # Cursor movement commands
            # Handle various cursor movement commands
            if terminator == 'A':  # Cursor Up (CUU)
                n = codes[0] if codes else 1
                y = max(0, y - n)
            elif terminator == 'B':  # Cursor Down (CUD)
                n = codes[0] if codes else 1
                y += n
            elif terminator == 'C':  # Cursor Forward (CUF)
                n = codes[0] if codes else 1
                x += n
            elif terminator == 'D':  # Cursor Backward (CUB)
                n = codes[0] if codes else 1
                x = max(0, x - n)
            elif terminator in 'Hf':  # Cursor Position (CUP) - move to row/column
                if len(codes) >= 2:
                    y = codes[0] - 1 if codes[0] > 0 else 0  # Convert to 0-indexed
                    x = codes[1] - 1 if codes[1] > 0 else 0  # Convert to 0-indexed
                elif len(codes) == 1:
                    y = codes[0] - 1 if codes[0] > 0 else 0  # Just row specified
                else:
                    y, x = 0, 0  # Default to home position

        # Move position past the entire escape sequence (we don't add escape chars to output)
        last_pos = match.end()

    # Add any remaining text after the last escape sequence
    remaining_text = text[last_pos:]
    for char in remaining_text:
        if char == '\n':  # Newline moves to next row
            y += 1
            x = 0
        elif char == '\r':  # Carriage return moves back to start of line
            x = 0
        else:  # Regular character - store it with current position and color
            # Check if wrapping is needed
            if wrap_at_80 and x >= 80:
                y += 1
                x = 0
            # Combine the color components into a single string
            color_components = []
            if current_fg_color:
                color_components.append(current_fg_color)
            if current_bg_color:
                color_components.append("on")
                color_components.append(current_bg_color)
            if current_bold:
                color_components.append("bold")
            combined_color = " ".join(color_components)
            elements.append((x, y, char, combined_color))
            x += 1  # Move to next column
    
    return elements


def create_ddw_elements(parsed: List[Tuple[int, int, str, str]]) -> List[dict]:
    """Convert parsed ANSI elements to DarkDraw format, one object per character."""
    # Transform each (x, y, char, color) tuple into a DarkDraw element dictionary
    # Each dictionary represents one character at a specific position with a color
    elements = []
    for x, y, char, color in parsed:
        # Format the color string to match expected format: "fg on bg bold"
        formatted_color = format_color_string(color)
        elements.append({
            "x": x,           # Horizontal position (column number)
            "y": y,           # Vertical position (row number)
            "text": char,     # The actual character to display
            "color": formatted_color,   # Formatted color string
            "tags": [],       # Empty list - used by DarkDraw for grouping/organizing
            "group": ""       # Empty string - used by DarkDraw for hierarchical grouping
        })
    return elements


def format_color_string(color_str: str) -> str:
    """Format the color string to match expected format: 'fg on bg bold'."""
    if not color_str.strip():
        return ""

    parts = color_str.split()
    fg_color = ""
    bg_color = ""
    has_bold = False

    for part in parts:
        if part == "bold":
            has_bold = True
        elif "on" in part:
            # This is a "color on bg_color" format
            sub_parts = part.split(" on ")
            if len(sub_parts) == 2:
                fg_color = sub_parts[0] if sub_parts[0] != "on" else fg_color
                bg_color = sub_parts[1]
            elif part.startswith("on "):
                bg_color = part[3:]  # Remove "on " prefix
        elif part.isdigit():
            # Assume first number is foreground, second might be background
            if not fg_color:
                fg_color = part
            elif not bg_color:
                bg_color = part  # If there's already a fg, treat as bg
        elif part.startswith("on"):
            # Handle "onN" format
            bg_color = part[2:]  # Remove "on" prefix

    # Build the formatted string
    result_parts = []
    if fg_color:
        result_parts.append(fg_color)
    if bg_color:
        result_parts.append("on")
        result_parts.append(bg_color)
    if has_bold:
        result_parts.append("bold")

    return " ".join(result_parts)


def convert_to_ddw(input_text: str) -> str:
    """Convert ANSI text to DarkDraw JSONL format."""
    # Determine if input contains explicit newlines
    # Remove ANSI codes before checking for newlines
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    text_without_ansi = ansi_escape.sub('', input_text)
    has_newlines = '\n' in text_without_ansi
    
    # Step 1: Parse the ANSI escape codes into structured data
    # Enable wrapping if no explicit newlines found
    parsed = parse_ansi(input_text, wrap_at_80=not has_newlines)
    
    # Step 2: Convert parsed data into DarkDraw element dictionaries
    elements = create_ddw_elements(parsed)
    
    # Step 3: Serialize to JSONL format (JSON Lines - one JSON object per line)
    # DarkDraw uses JSONL where each line is a complete JSON object
    # separators=(',', ':') creates compact JSON without extra spaces
    return '\n'.join(json.dumps(elem, separators=(',', ':')) for elem in elements)


def main():
    if len(sys.argv) > 1:
        # Read as bytes, decode from CP437 to UTF-8
        with open(sys.argv[1], 'rb') as f:
            input_text = f.read().decode('cp437')
        
        output_file = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1] + '.ddw'
    else:
        # Read stdin as bytes, decode from CP437
        input_text = sys.stdin.buffer.read().decode('cp437')
        output_file = None
    
    ddw_output = convert_to_ddw(input_text)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(ddw_output)
        print(f"Converted to {output_file}")
    else:
        print(ddw_output)


if __name__ == '__main__':
    main()
