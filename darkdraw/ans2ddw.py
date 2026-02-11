#!/usr/bin/env python3
"""Convert ANSI art files (.ans) to DarkDraw format (.ddw)."""

import sys
import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

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
def _build_256_color_palette():
    """Build the standard xterm 256-color palette."""
    palette = []
    
    # 0-15: Standard ANSI colors
    ansi_colors = [
        (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
        (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
        (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
        (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
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
CP437_TO_UNICODE = [
    0x00C7, 0x00FC, 0x00E9, 0x00E2, 0x00E4, 0x00E0, 0x00E5, 0x00E7,
    0x00EA, 0x00EB, 0x00E8, 0x00EF, 0x00EE, 0x00EC, 0x00C4, 0x00C5,
    0x00C9, 0x00E6, 0x00C6, 0x00F4, 0x00F6, 0x00F2, 0x00FB, 0x00F9,
    0x00FF, 0x00D6, 0x00DC, 0x00A2, 0x00A3, 0x00A5, 0x20A7, 0x0192,
    0x00E1, 0x00ED, 0x00F3, 0x00FA, 0x00F1, 0x00D1, 0x00AA, 0x00BA,
    0x00BF, 0x2310, 0x00AC, 0x00BD, 0x00BC, 0x00A1, 0x00AB, 0x00BB,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255D, 0x255C, 0x255B, 0x2510,
    0x2514, 0x2534, 0x252C, 0x251C, 0x2500, 0x253C, 0x255E, 0x255F,
    0x255A, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256C, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256B,
    0x256A, 0x2518, 0x250C, 0x2588, 0x2584, 0x258C, 0x2590, 0x2580,
    0x03B1, 0x00DF, 0x0393, 0x03C0, 0x03A3, 0x03C3, 0x00B5, 0x03C4,
    0x03A6, 0x0398, 0x03A9, 0x03B4, 0x221E, 0x03C6, 0x03B5, 0x2229,
    0x2261, 0x00B1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00F7, 0x2248,
    0x00B0, 0x2219, 0x00B7, 0x221A, 0x207F, 0x00B2, 0x25A0, 0x00A0,
]

def cp437_to_utf8(byte_val: int) -> str:
    """Convert CP437 byte value to UTF-8 character."""
    if byte_val < 128:
        return chr(byte_val)
    else:
        return chr(CP437_TO_UNICODE[byte_val - 128])

def iso8859_1_to_utf8(byte_val: int) -> str:
    """Convert ISO-8859-1 byte value to UTF-8 character."""
    return chr(byte_val)

def rgb_to_256color(rgb: int) -> int:
    """Convert 24-bit RGB to nearest xterm 256 color code."""
    r = (rgb >> 16) & 0xFF
    g = (rgb >> 8) & 0xFF
    b = rgb & 0xFF
    
    best_match = 0
    best_distance = float('inf')
    
    for i, (pr, pg, pb) in enumerate(COLOR_256_PALETTE):
        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if distance < best_distance:
            best_distance = distance
            best_match = i
    
    return best_match

@dataclass
class SauceRecord:
    """SAUCE metadata record."""
    title: str = ""
    author: str = ""
    group: str = ""
    date: str = ""
    file_size: int = 0
    data_type: int = 0
    file_type: int = 0
    t_info1: int = 0
    t_info2: int = 0
    t_info3: int = 0
    t_info4: int = 0
    comments: List[str] = field(default_factory=list)
    t_flags: int = 0
    t_info_s: str = ""
    
    def to_ddw_rows(self) -> List[dict]:
        """Convert SAUCE record to DarkDraw text rows."""
        rows = []
        y = 0
        
        if self.title:
            rows.append({
                "type": "", "x": 0, "y": y, "text": self.title,
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Title", "rows": []
            })
            y += 1
        
        if self.author:
            rows.append({
                "type": "", "x": 0, "y": y, "text": self.author,
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Author", "rows": []
            })
            y += 1
        
        if self.group:
            rows.append({
                "type": "", "x": 0, "y": y, "text": self.group,
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Group", "rows": []
            })
            y += 1
        
        if self.date:
            rows.append({
                "type": "", "x": 0, "y": y, "text": self.date,
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Date", "rows": []
            })
            y += 1
        
        if self.t_info1 or self.t_info2:
            rows.append({
                "type": "", "x": 0, "y": y, "text": f"{self.t_info1}x{self.t_info2}",
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Dimensions", "rows": []
            })
            y += 1
        
        if self.t_flags:
            flags = []
            if self.t_flags & 0x01:
                flags.append("non-blink")
            if self.t_flags & 0x02:
                flags.append("letter-spacing")
            if self.t_flags & 0x04:
                flags.append("aspect-ratio")
            
            rows.append({
                "type": "", "x": 0, "y": y,
                "text": ", ".join(flags) if flags else str(self.t_flags),
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Flags", "rows": []
            })
            y += 1
        
        if self.t_info_s:
            rows.append({
                "type": "", "x": 0, "y": y, "text": self.t_info_s,
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": "Font", "rows": []
            })
            y += 1
        
        for i, comment in enumerate(self.comments):
            rows.append({
                "type": "", "x": 0, "y": y, "text": comment,
                "color": "", "tags": [], "group": "",
                "frame": "SAUCE record", "id": f"Comment {i+1}", "rows": []
            })
            y += 1
        
        return rows

@dataclass
class AnsiChar:
    """Character with position and color attributes."""
    column: int
    row: int
    background: int
    foreground: int
    character: str
    background24: int = 0
    foreground24: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    dim: bool = False
    
    def to_ddw_row(self, frame_id: Optional[str] = None) -> dict:
        """Convert to DarkDraw row format."""
        color_parts = []
        
        if self.foreground24:
            fg_256 = rgb_to_256color(self.foreground24)
            color_parts.append(str(fg_256))
        else:
            color_parts.append(str(self.foreground))
        
        if self.background24:
            bg_256 = rgb_to_256color(self.background24)
            color_parts.append(f"on {bg_256}")
        else:
            color_parts.append(f"on {self.background}")
        
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
            "type": "", "x": self.column, "y": self.row,
            "text": self.character, "color": " ".join(color_parts) if color_parts else "",
            "tags": [], "group": "", "frame": frame_id or "", "id": "", "rows": []
        }

class AnsiParser:
    """Parse ANSI escape sequences and build character buffer."""
    
    def __init__(self, columns: int = 80, icecolors: bool = False, encoding: str = 'cp437'):
        self.columns = columns
        self.icecolors = icecolors
        self.encoding = encoding
        
        self.background = 0
        self.foreground = 7
        self.background24 = 0
        self.foreground24 = 0
        
        self.bold = False
        self.blink = False
        self.invert = False
        self.italic = False
        self.underline = False
        self.dim = False
        
        self.column = 0
        self.row = 0
        self.saved_row = 0
        self.saved_column = 0
        
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
                    if i + 1 < length and data[i + 1] == 91:
                        state = STATE_SEQUENCE
                        i += 1
                else:
                    if self.encoding == 'utf-8':
                        char_bytes = bytearray([cursor])
                        if cursor < 0x80:
                            pass
                        elif cursor & 0xE0 == 0xC0:
                            if i + 1 < length:
                                i += 1
                                char_bytes.append(data[i])
                        elif cursor & 0xF0 == 0xE0:
                            for _ in range(2):
                                if i + 1 < length:
                                    i += 1
                                    char_bytes.append(data[i])
                        elif cursor & 0xF8 == 0xF0:
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
                seq_len = self._parse_sequence(data[i:])
                i += seq_len
                state = STATE_TEXT
                
            elif state == STATE_END:
                break
                
            i += 1
        
        return self.chars
    
    def _add_char(self, char: str):
        """Add character to buffer with current attributes."""
        if self.column > self.column_max:
            self.column_max = self.column
        if self.row > self.row_max:
            self.row_max = self.row
        
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
            column=self.column, row=self.row, background=bg, foreground=fg,
            background24=bg24, foreground24=fg24, character=char,
            bold=self.bold, italic=self.italic, underline=self.underline,
            blink=self.blink, reverse=self.invert, dim=self.dim
        ))
        
        self.column += 1
    
    def _parse_sequence(self, data: bytes) -> int:
        """Parse CSI sequence and return length consumed."""
        max_len = min(len(data), ANSI_SEQUENCE_MAX_LENGTH)
        
        for seq_len in range(max_len):
            seq_char = chr(data[seq_len]) if seq_len < len(data) else ''
            
            if seq_char in ('H', 'f'):
                self._handle_cursor_position(data[:seq_len])
                return seq_len
            if seq_char == 'A':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.row = max(0, self.row - n)
                return seq_len
            if seq_char == 'B':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.row += n
                return seq_len
            if seq_char == 'C':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.column = min(self.columns, self.column + n)
                return seq_len
            if seq_char == 'D':
                n = self._parse_numeric(data[:seq_len], default=1)
                self.column = max(0, self.column - n)
                return seq_len
            if seq_char == 's':
                self.saved_row = self.row
                self.saved_column = self.column
                return seq_len
            if seq_char == 'u':
                self.row = self.saved_row
                self.column = self.saved_column
                return seq_len
            if seq_char == 'J':
                n = self._parse_numeric(data[:seq_len], default=0)
                if n == 2:
                    self.column = 0
                    self.row = 0
                    self.column_max = 0
                    self.row_max = 0
                    self.chars.clear()
                return seq_len
            if seq_char == 'm':
                self._handle_sgr(data[:seq_len])
                return seq_len
            if seq_char == 't':
                self._handle_pablodraw_color(data[:seq_len])
                return seq_len
            if 64 <= ord(seq_char) <= 126:
                return seq_len
        
        return 0
    
    def _handle_cursor_position(self, seq: bytes):
        """Handle cursor position escape sequence."""
        seq_str = seq.decode('ascii', errors='ignore')
        
        if seq_str.startswith(';'):
            parts = seq_str[1:].split(';')
            row = 1
            col = int(parts[0]) if parts and parts[0] else 1
        else:
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
            elif val == 1:
                self.bold = True
                self.foreground = (self.foreground % 8) + 8
                self.foreground24 = 0
            elif val == 2:
                self.dim = True
            elif val == 3:
                self.italic = True
            elif val == 4:
                self.underline = True
            elif val == 5:
                if self.icecolors:
                    self.background = (self.background % 8) + 8
                    self.blink = False
                else:
                    self.blink = True
            elif val == 7:
                self.invert = True
            elif val == 22:
                self.bold = False
                self.dim = False
                if self.foreground >= 8:
                    self.foreground -= 8
            elif val == 23:
                self.italic = False
            elif val == 24:
                self.underline = False
            elif val == 25:
                self.blink = False
                if self.icecolors and self.background >= 8:
                    self.background -= 8
            elif val == 27:
                self.invert = False
            elif 30 <= val <= 37:
                self.foreground = val - 30
                self.foreground24 = 0
                if self.bold:
                    self.foreground += 8
            elif val == 38:
                if i + 2 < len(params):
                    mode = int(params[i + 1])
                    if mode == 5:
                        self.foreground = int(params[i + 2]) & 0xFF
                        self.foreground24 = 0
                        i += 2
                    elif mode == 2 and i + 4 < len(params):
                        r = int(params[i + 2]) & 0xFF
                        g = int(params[i + 3]) & 0xFF
                        b = int(params[i + 4]) & 0xFF
                        self.foreground24 = (r << 16) | (g << 8) | b
                        i += 4
            elif 40 <= val <= 47:
                self.background = val - 40
                self.background24 = 0
                if self.blink and self.icecolors:
                    self.background += 8
            elif val == 48:
                if i + 2 < len(params):
                    mode = int(params[i + 1])
                    if mode == 5:
                        self.background = int(params[i + 2]) & 0xFF
                        self.background24 = 0
                        i += 2
                    elif mode == 2 and i + 4 < len(params):
                        r = int(params[i + 2]) & 0xFF
                        g = int(params[i + 3]) & 0xFF
                        b = int(params[i + 4]) & 0xFF
                        self.background24 = (r << 16) | (g << 8) | b
                        i += 4
            elif 90 <= val <= 97:
                self.foreground = val - 90 + 8
                self.foreground24 = 0
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
            color_type = int(params[0])
            r = int(params[1]) & 0xFF if len(params) > 1 else 0
            g = int(params[2]) & 0xFF if len(params) > 2 else 0
            b = int(params[3]) & 0xFF if len(params) > 3 else 0
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

def parse_sauce(data: bytes) -> Tuple[bytes, Optional[SauceRecord]]:
    """Parse SAUCE record from file data."""
    if len(data) < 128:
        return data, None
    
    sauce_offset = len(data) - 128
    sauce_block = data[sauce_offset:]
    
    if sauce_block[:5] != b'SAUCE':
        return data, None
    
    sauce = SauceRecord()
    sauce.title = sauce_block[7:42].rstrip(b'\x00').decode('cp437', errors='ignore')
    sauce.author = sauce_block[42:62].rstrip(b'\x00').decode('cp437', errors='ignore')
    sauce.group = sauce_block[62:82].rstrip(b'\x00').decode('cp437', errors='ignore')
    sauce.date = sauce_block[82:90].decode('cp437', errors='ignore')
    sauce.file_size = int.from_bytes(sauce_block[90:94], 'little')
    sauce.data_type = sauce_block[94]
    sauce.file_type = sauce_block[95]
    sauce.t_info1 = int.from_bytes(sauce_block[96:98], 'little')
    sauce.t_info2 = int.from_bytes(sauce_block[98:100], 'little')
    sauce.t_info3 = int.from_bytes(sauce_block[100:102], 'little')
    sauce.t_info4 = int.from_bytes(sauce_block[102:104], 'little')
    num_comments = sauce_block[104]
    sauce.t_flags = sauce_block[105]
    sauce.t_info_s = sauce_block[106:128].rstrip(b'\x00').decode('cp437', errors='ignore')
    
    file_data = data[:sauce_offset]
    
    if num_comments > 0:
        comment_size = num_comments * 64 + 5
        comment_offset = sauce_offset - comment_size
        
        if comment_offset >= 0:
            comment_block = data[comment_offset:sauce_offset]
            
            if comment_block[:5] == b'COMNT':
                for i in range(num_comments):
                    start = 5 + i * 64
                    end = start + 64
                    comment_line = comment_block[start:end].rstrip(b'\x00').decode('cp437', errors='ignore')
                    sauce.comments.append(comment_line)
                
                file_data = data[:comment_offset]
    
    if file_data and file_data[-1] == SUB:
        file_data = file_data[:-1]
    
    return file_data, sauce

def ans_to_ddw(input_path: str, output_path: str, columns: int = 80, 
               icecolors: bool = False, encoding: str = 'cp437'):
    """Convert ANSI file to DarkDraw format."""
    with open(input_path, 'rb') as f:
        data = f.read()
    
    file_data, sauce = parse_sauce(data)

    # Debug output
    if sauce:
        print(f"DEBUG: SAUCE record found")
        print(f"DEBUG: Title: {sauce.title}")
        print(f"DEBUG: Author: {sauce.author}")
        print(f"DEBUG: to_ddw_rows returns {len(sauce.to_ddw_rows())} rows")
    else:
        print("DEBUG: No SAUCE record found")
    
    parser = AnsiParser(columns=columns, icecolors=icecolors, encoding=encoding)
    chars = parser.parse(file_data)
    
    rows = []
    
    if sauce:
        rows.extend(sauce.to_ddw_rows())
    
    rows.extend([char.to_ddw_row(frame_id="ANSI art") for char in chars])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row) + '\n')
    
    print(f"Converted {len(chars)} characters from {input_path} to {output_path}")
    print(f"Dimensions: {parser.column_max + 1} x {parser.row_max + 1}")
    print(f"Encoding: {encoding}")
    if sauce:
        print(f"SAUCE: {sauce.title or '(no title)'} by {sauce.author or '(no author)'}")

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
