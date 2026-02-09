#!/usr/bin/env python3
"""Convert ANSI art files (.ans) to DarkDraw format (.ddw)."""

import sys
import json
from dataclasses import dataclass, field
from typing import List, Optional

# Control characters
LF = 10
CR = 13
TAB = 9
SUB = 26
ESC = 27

# State machine states
STATE_TEXT = 0
STATE_SEQUENCE = 1
STATE_END = 2

ANSI_SEQUENCE_MAX_LENGTH = 32

# 256-color palette (xterm colors)
# Colors 0-15: standard ANSI colors
# Colors 16-231: 6x6x6 RGB cube
# Colors 232-255: grayscale ramp
def _build_256_color_palette():
    """Build the standard xterm 256-color palette."""
    palette = []
    
    # 0-15: Standard ANSI colors
    ansi_colors = [
        (0, 0, 0),       # 0: black
        (128, 0, 0),     # 1: red
        (0, 128, 0),     # 2: green
        (128, 128, 0),   # 3: yellow
        (0, 0, 128),     # 4: blue
        (128, 0, 128),   # 5: magenta
        (0, 128, 128),   # 6: cyan
        (192, 192, 192), # 7: white
        (128, 128, 128), # 8: bright black
        (255, 0, 0),     # 9: bright red
        (0, 255, 0),     # 10: bright green
        (255, 255, 0),   # 11: bright yellow
        (0, 0, 255),     # 12: bright blue
        (255, 0, 255),   # 13: bright magenta
        (0, 255, 255),   # 14: bright cyan
        (255, 255, 255), # 15: bright white
    ]
    palette.extend(ansi_colors)
    
    # 16-231: 6x6x6 RGB cube
    for r in range(6):
        for g in range(6):
            for b in range(6):
                palette.append((
                    0 if r == 0 else 55 + r * 40,
                    0 if g == 0 else 55 + g * 40,
                    0 if b == 0 else 55 + b * 40
                ))
    
    # 232-255: grayscale ramp
    for i in range(24):
        gray = 8 + i * 10
        palette.append((gray, gray, gray))
    
    return palette

COLOR_256_PALETTE = _build_256_color_palette()


# CP437 (DOS) to Unicode mapping for characters 128-255
# Characters 0-127 are identical to ASCII
CP437_TO_UNICODE = [
    0x00C7, 0x00FC, 0x00E9, 0x00E2, 0x00E4, 0x00E0, 0x00E5, 0x00E7,  # 128-135
    0x00EA, 0x00EB, 0x00E8, 0x00EF, 0x00EE, 0x00EC, 0x00C4, 0x00C5,  # 136-143
    0x00C9, 0x00E6, 0x00C6, 0x00F4, 0x00F6, 0x00F2, 0x00FB, 0x00F9,  # 144-151
    0x00FF, 0x00D6, 0x00DC, 0x00A2, 0x00A3, 0x00A5, 0x20A7, 0x0192,  # 152-159
    0x00E1, 0x00ED, 0x00F3, 0x00FA, 0x00F1, 0x00D1, 0x00AA, 0x00BA,  # 160-167
    0x00BF, 0x2310, 0x00AC, 0x00BD, 0x00BC, 0x00A1, 0x00AB, 0x00BB,  # 168-175
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,  # 176-183
    0x2555, 0x2563, 0x2551, 0x2557, 0x255D, 0x255C, 0x255B, 0x2510,  # 184-191
    0x2514, 0x2534, 0x252C, 0x251C, 0x2500, 0x253C, 0x255E, 0x255F,  # 192-199
    0x255A, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256C, 0x2567,  # 200-207
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256B,  # 208-215
    0x256A, 0x2518, 0x250C, 0x2588, 0x2584, 0x258C, 0x2590, 0x2580,  # 216-223
    0x03B1, 0x00DF, 0x0393, 0x03C0, 0x03A3, 0x03C3, 0x00B5, 0x03C4,  # 224-231
    0x03A6, 0x0398, 0x03A9, 0x03B4, 0x221E, 0x03C6, 0x03B5, 0x2229,  # 232-239
    0x2261, 0x00B1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00F7, 0x2248,  # 240-247
    0x00B0, 0x2219, 0x00B7, 0x221A, 0x207F, 0x00B2, 0x25A0, 0x00A0,  # 248-255
]


def cp437_to_utf8(byte_val: int) -> str:
    """Convert CP437 byte value to UTF-8 character."""
    if byte_val < 128:
        return chr(byte_val)
    else:
        return chr(CP437_TO_UNICODE[byte_val - 128])


def iso8859_1_to_utf8(byte_val: int) -> str:
    """Convert ISO-8859-1 byte value to UTF-8 character."""
    # ISO-8859-1 maps directly to Unicode code points 0-255
    return chr(byte_val)


def rgb_to_256color(rgb: int) -> int:
    """Convert 24-bit RGB to nearest xterm 256 color code."""
    r = (rgb >> 16) & 0xFF
    g = (rgb >> 8) & 0xFF
    b = rgb & 0xFF
    
    best_match = 0
    best_distance = float('inf')
    
    for i, (pr, pg, pb) in enumerate(COLOR_256_PALETTE):
        # Euclidean distance in RGB space
        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if distance < best_distance:
            best_distance = distance
            best_match = i
    
    return best_match


@dataclass
class AnsiChar:
    """Character with position and color attributes."""
    column: int
    row: int
    background: int
    foreground: int
    character: str
    background24: int = 0  # 24-bit RGB background (0xRRGGBB)
    foreground24: int = 0  # 24-bit RGB foreground (0xRRGGBB)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    dim: bool = False
    
    def to_ddw_row(self, frame_id: Optional[str] = None) -> dict:
        """Convert to DarkDraw row format."""
        # Convert colors to 256-color codes
        color_parts = []
        
        if self.foreground24:
            # Convert 24-bit to nearest 256-color
            fg_256 = rgb_to_256color(self.foreground24)
            color_parts.append(str(fg_256))
        else:
            # Use actual ANSI color code (0-15 for standard colors)
            color_parts.append(str(self.foreground))
        
        if self.background24:
            # Convert 24-bit to nearest 256-color
            bg_256 = rgb_to_256color(self.background24)
            color_parts.append(f"on {bg_256}")
        else:
            # Use actual ANSI color code (0-15 for standard colors)
            color_parts.append(f"on {self.background}")
        
        # Add text attributes
        if self.bold:
            color_parts.append("bold")
        if self.italic:
            color_parts.append("italic")
        if self.underline:
            color_parts.append("underline")
        if self.blink:
            color_parts.append("blink")
        if self.reverse:
            color_parts.append("reverse")
        if self.dim:
            color_parts.append("dim")
        
        return {
            "type": "",
            "x": self.column,
            "y": self.row,
            "text": self.character,
            "color": " ".join(color_parts) if color_parts else "",
            "tags": [],
            "group": "",
            "frame": frame_id or "",
            "id": "",
            "rows": []
        }


class AnsiParser:
    """Parse ANSI escape sequences and build character buffer."""
    
    def __init__(self, columns: int = 80, icecolors: bool = False, encoding: str = 'cp437'):
        self.columns = columns
        self.icecolors = icecolors
        self.encoding = encoding  # 'cp437' or 'iso8859-1'
        
        # Color state
        self.background = 0
        self.foreground = 7
        self.background24 = 0  # 24-bit RGB background
        self.foreground24 = 0  # 24-bit RGB foreground
        
        # Text attributes
        self.bold = False
        self.blink = False
        self.invert = False
        self.italic = False
        self.underline = False
        self.dim = False
        
        # Cursor position
        self.column = 0
        self.row = 0
        self.saved_row = 0
        self.saved_column = 0
        
        # Output buffer
        self.chars: List[AnsiChar] = []
        self.column_max = 0
        self.row_max = 0
        
    def parse(self, data: bytes) -> List[AnsiChar]:
        """Parse ANSI data and return character list."""
        state = STATE_TEXT
        i = 0
        length = len(data)
        
        while i < length:
            cursor = data[i]
            
            # Handle column wrapping
            if self.column == self.columns:
                self.row += 1
                self.column = 0
            
            if state == STATE_TEXT:
                if cursor == LF:
                    self.row += 1
                    self.column = 0
                elif cursor == CR:
                    pass
                elif cursor == TAB:
                    self.column += 8
                elif cursor == SUB:
                    state = STATE_END
                elif cursor == ESC:
                    # Check for CSI sequence (ESC [)
                    if i + 1 < length and data[i + 1] == 91:  # '['
                        state = STATE_SEQUENCE
                        i += 1
                else:
                    # Record character (convert to UTF-8 based on encoding)
                    if self.encoding == 'utf-8':
                        # For UTF-8, we need to decode multi-byte sequences
                        char_bytes = bytearray([cursor])
                        # Determine how many bytes this UTF-8 character needs
                        if cursor < 0x80:
                            # Single byte (ASCII)
                            pass
                        elif cursor & 0xE0 == 0xC0:
                            # 2-byte sequence
                            if i + 1 < length:
                                i += 1
                                char_bytes.append(data[i])
                        elif cursor & 0xF0 == 0xE0:
                            # 3-byte sequence
                            for _ in range(2):
                                if i + 1 < length:
                                    i += 1
                                    char_bytes.append(data[i])
                        elif cursor & 0xF8 == 0xF0:
                            # 4-byte sequence
                            for _ in range(3):
                                if i + 1 < length:
                                    i += 1
                                    char_bytes.append(data[i])
                        try:
                            self._add_char(char_bytes.decode('utf-8'))
                        except UnicodeDecodeError:
                            self._add_char('?')
                    elif self.encoding == 'iso8859-1':
                        self._add_char(iso8859_1_to_utf8(cursor))
                    else:
                        self._add_char(cp437_to_utf8(cursor))
                    
            elif state == STATE_SEQUENCE:
                # Parse escape sequence
                seq_len = self._parse_sequence(data[i:])
                i += seq_len
                state = STATE_TEXT
                
            elif state == STATE_END:
                break
                
            i += 1
        
        return self.chars
    
    def _add_char(self, char: str):
        """Add character to buffer with current attributes."""
        # Track max dimensions
        if self.column > self.column_max:
            self.column_max = self.column
        if self.row > self.row_max:
            self.row_max = self.row
        
        # Apply invert/reverse
        if self.invert:
            bg = self.foreground % 8
            fg = self.background + (self.foreground & 8)
            bg24 = 0
            fg24 = 0
        else:
            bg = self.background
            fg = self.foreground
            bg24 = self.background24
            fg24 = self.foreground24
        
        self.chars.append(AnsiChar(
            column=self.column,
            row=self.row,
            background=bg,
            foreground=fg,
            background24=bg24,
            foreground24=fg24,
            character=char,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            blink=self.blink,
            reverse=self.invert,
            dim=self.dim
        ))
        
        self.column += 1
    
    def _parse_sequence(self, data: bytes) -> int:
        """Parse CSI sequence and return length consumed."""
        max_len = min(len(data), ANSI_SEQUENCE_MAX_LENGTH)
        
        for seq_len in range(max_len):
            seq_char = chr(data[seq_len]) if seq_len < len(data) else ''
            
            # Cursor position (H or f)
            if seq_char in ('H', 'f'):
                self._handle_cursor_position(data[:seq_len])
                return seq_len
            
            # Cursor up (A)
            if seq_char == 'A':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.row = max(0, self.row - n)
                return seq_len
            
            # Cursor down (B)
            if seq_char == 'B':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.row += n
                return seq_len
            
            # Cursor forward (C)
            if seq_char == 'C':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.column = min(self.columns, self.column + n)
                return seq_len
            
            # Cursor backward (D)
            if seq_char == 'D':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.column = max(0, self.column - n)
                return seq_len
            
            # Save cursor (s)
            if seq_char == 's':
                self.saved_row = self.row
                self.saved_column = self.column
                return seq_len
            
            # Restore cursor (u)
            if seq_char == 'u':
                self.row = self.saved_row
                self.column = self.saved_column
                return seq_len
            
            # Erase display (J)
            if seq_char == 'J':
                n = self._parse_numeric(data[:seq_len], default=0)
                if n == 2:
                    self.column = 0
                    self.row = 0
                    self.column_max = 0
                    self.row_max = 0
                    self.chars.clear()
                return seq_len
            
            # Set graphics mode (m)
            if seq_char == 'm':
                self._handle_sgr(data[:seq_len])
                return seq_len
            
            # PabloDraw 24-bit color (t)
            if seq_char == 't':
                self._handle_pablodraw_color(data[:seq_len])
                return seq_len
            
            # Skip other sequences
            if 64 <= ord(seq_char) <= 126:
                return seq_len
        
        return 0
    
    def _handle_cursor_position(self, seq: bytes):
        """Handle cursor position escape sequence."""
        seq_str = seq.decode('ascii', errors='ignore')
        
        if seq_str.startswith(';'):
            # ";column" format
            parts = seq_str[1:].split(';')
            row = 1
            col = int(parts[0]) if parts and parts[0] else 1
        else:
            # "row;column" format
            parts = seq_str.split(';')
            row = int(parts[0]) if parts and parts[0] else 1
            col = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        
        self.row = max(0, row - 1)
        self.column = max(0, col - 1)
    
    def _handle_sgr(self, seq: bytes):
        """Handle SGR (Select Graphic Rendition) sequence."""
        seq_str = seq.decode('ascii', errors='ignore')
        params = [p.strip() for p in seq_str.split(';') if p.strip()]
        
        if not params:
            params = ['0']
        
        i = 0
        while i < len(params):
            try:
                val = int(params[i])
            except ValueError:
                i += 1
                continue
            
            # Reset all attributes
            if val == 0:
                self.background = 0
                self.background24 = 0
                self.foreground = 7
                self.foreground24 = 0
                self.bold = False
                self.blink = False
                self.invert = False
                self.italic = False
                self.underline = False
                self.dim = False
            
            # Bold/bright
            elif val == 1:
                self.bold = True
                self.foreground = (self.foreground % 8) + 8
                self.foreground24 = 0  # Clear 24-bit when using bold
            
            # Dim
            elif val == 2:
                self.dim = True
            
            # Italic
            elif val == 3:
                self.italic = True
            
            # Underline
            elif val == 4:
                self.underline = True
            
            # Blink

            elif val == 5:
                if self.icecolors:
                    self.background = (self.background % 8) + 8
                    self.blink = False
                else:
                    self.blink = True

            
            # Invert/reverse
            elif val == 7:
                self.invert = True
            
            # Not bold
            elif val == 22:
                self.bold = False
                self.dim = False
                if self.foreground >= 8:
                    self.foreground -= 8
            
            # Not italic
            elif val == 23:
                self.italic = False
            
            # Not underlined
            elif val == 24:
                self.underline = False
            
            # Not blinking
            elif val == 25:
                self.blink = False
                if self.icecolors and self.background >= 8:
                    self.background -= 8
            
            # Not inverted
            elif val == 27:
                self.invert = False
            
            # Foreground color (30-37)
            elif 30 <= val <= 37:
                self.foreground = val - 30
                self.foreground24 = 0
                if self.bold:
                    self.foreground += 8
            
            # Extended foreground color (38)
            elif val == 38:
                if i + 2 < len(params):
                    mode = int(params[i + 1])
                    if mode == 5:  # 256-color mode
                        self.foreground = int(params[i + 2]) & 0xFF
                        self.foreground24 = 0
                        i += 2
                    elif mode == 2 and i + 4 < len(params):  # 24-bit RGB mode
                        r = int(params[i + 2]) & 0xFF
                        g = int(params[i + 3]) & 0xFF
                        b = int(params[i + 4]) & 0xFF
                        self.foreground24 = (r << 16) | (g << 8) | b
                        i += 4
            
            # Background color (40-47)
            elif 40 <= val <= 47:
                self.background = val - 40
                self.background24 = 0
                if self.blink and self.icecolors:
                    self.background += 8
            
            # Extended background color (48)
            elif val == 48:
                if i + 2 < len(params):
                    mode = int(params[i + 1])
                    if mode == 5:  # 256-color mode
                        self.background = int(params[i + 2]) & 0xFF
                        self.background24 = 0
                        i += 2
                    elif mode == 2 and i + 4 < len(params):  # 24-bit RGB mode
                        r = int(params[i + 2]) & 0xFF
                        g = int(params[i + 3]) & 0xFF
                        b = int(params[i + 4]) & 0xFF
                        self.background24 = (r << 16) | (g << 8) | b
                        i += 4
            
            # Bright foreground colors (90-97)
            elif 90 <= val <= 97:
                self.foreground = val - 90 + 8
                self.foreground24 = 0
            
            # Bright background colors (100-107)
            elif 100 <= val <= 107:
                self.background = val - 100 + 8
                self.background24 = 0
            
            i += 1
    
    def _handle_pablodraw_color(self, seq: bytes):
        """Handle PabloDraw 24-bit ANSI color sequences (CSI...t)."""
        seq_str = seq.decode('ascii', errors='ignore')
        params = [p.strip() for p in seq_str.split(';') if p.strip()]
        
        if not params:
            return
        
        try:
            # First param: 0=background, 1=foreground
            color_type = int(params[0])
            
            # Next 3 params: R, G, B values (0-255)
            r = int(params[1]) & 0xFF if len(params) > 1 else 0
            g = int(params[2]) & 0xFF if len(params) > 2 else 0
            b = int(params[3]) & 0xFF if len(params) > 3 else 0
            
            # Combine into 24-bit RGB value
            rgb = (r << 16) | (g << 8) | b
            
            if color_type == 0:
                self.background24 = rgb
            elif color_type == 1:
                self.foreground24 = rgb
        except (ValueError, IndexError):
            pass
    
    def _parse_numeric(self, seq: bytes, default: int = 0) -> int:
        """Parse numeric value from sequence."""
        seq_str = seq.decode('ascii', errors='ignore').strip()
        if not seq_str:
            return default
        try:
            return int(seq_str)
        except ValueError:
            return default


def ans_to_ddw(input_path: str, output_path: str, columns: int = 80, 
               icecolors: bool = False, encoding: str = 'cp437'):
    """Convert ANSI file to DarkDraw format.
    
    Args:
        input_path: Path to input .ans file
        output_path: Path to output .ddw file
        columns: Width in characters (default: 80)
        icecolors: Enable iCE colors (blinking -> bright backgrounds)
        encoding: Character encoding - 'cp437' (PC/DOS), 'iso8859-1' (Amiga), or 'utf-8' (default: 'cp437')
    """
    # Read ANSI file
    with open(input_path, 'rb') as f:
        data = f.read()
    
    # Parse ANSI
    parser = AnsiParser(columns=columns, icecolors=icecolors, encoding=encoding)
    chars = parser.parse(data)
    
    # Convert to DarkDraw rows
    rows = [char.to_ddw_row() for char in chars]
    
    # Write as JSONL
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row) + '\n')
    
    print(f"Converted {len(rows)} characters from {input_path} to {output_path}")
    print(f"Dimensions: {parser.column_max + 1} x {parser.row_max + 1}")
    print(f"Encoding: {encoding}")


def main():
    if len(sys.argv) < 3:
        print("Usage: ans2ddw.py <input.ans> <output.ddw> [columns] [options]")
        print("  columns: width in characters (default: 80)")
        print()
        print("Options:")
        print("  --icecolors: enable iCE colors (blinking -> bright backgrounds)")
        print("  --amiga: use ISO-8859-1 encoding (Amiga ANSI)")
        print("  --pc: use CP437 encoding (PC/DOS ANSI, default)")
        print("  --utf8: use UTF-8 encoding (modern ANSI)")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    columns = 80
    icecolors = False
    encoding = 'cp437'
    
    if len(sys.argv) > 3:
        try:
            columns = int(sys.argv[3])
        except ValueError:
            pass
    
    if '--icecolors' in sys.argv:
        icecolors = True
    
    if '--amiga' in sys.argv:
        encoding = 'iso8859-1'
    elif '--utf8' in sys.argv:
        encoding = 'utf-8'
    elif '--pc' in sys.argv:
        encoding = 'cp437'
    
    ans_to_ddw(input_path, output_path, columns=columns, icecolors=icecolors, encoding=encoding)


if __name__ == '__main__':
    main()
