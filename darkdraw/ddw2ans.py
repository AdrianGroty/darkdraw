#!/usr/bin/env python3
"""Convert DarkDraw format (.ddw) to ANSI art files (.ans)."""

import sys
import json
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

from .ans2ddw import (
    VGA_PALETTE, COLOR_256_PALETTE,
    rgb_to_256color, vga_to_256color,
    SauceRecord,
)

ESC = '\x1b'
CSI = f'{ESC}['
SUB = '\x1a'

# ── Color parsing ─────────────────────────────────────────────────────────────

@dataclass
class ParsedColor:
    fg: int = 7          # xterm-256 or ANSI 0-15
    bg: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    dim: bool = False

def parse_color_string(color: str) -> ParsedColor:
    """Parse a DDW color string like '7 on 0 bold italic' into attributes."""
    pc = ParsedColor()
    if not color:
        return pc

    parts = color.split()
    i = 0
    while i < len(parts):
        p = parts[i]
        if p == 'on':
            if i + 1 < len(parts):
                try:
                    pc.bg = int(parts[i + 1])
                    i += 2
                    continue
                except ValueError:
                    pass
        elif p == 'bold':
            pc.bold = True
        elif p == 'italic':
            pc.italic = True
        elif p == 'underline':
            pc.underline = True
        elif p == 'blink':
            pc.blink = True
        elif p == 'reverse':
            pc.reverse = True
        elif p == 'dim':
            pc.dim = True
        else:
            try:
                pc.fg = int(p)
            except ValueError:
                pass
        i += 1
    return pc

# ── 256→ANSI fallback ─────────────────────────────────────────────────────────

def xterm256_to_ansi16(color: int) -> int:
    """Map an xterm-256 color index to the nearest ANSI 0-15 index."""
    if color < 16:
        return color
    if color > 255:
        return 7

    r, g, b = COLOR_256_PALETTE[color]

    best, best_dist = 0, float('inf')
    for i, (pr, pg, pb) in enumerate(VGA_PALETTE):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_dist:
            best_dist = d
            best = i
    return best

def ansi16_to_sgr_fg(c: int) -> int:
    """ANSI 0-15 → SGR foreground code."""
    return (c - 8 + 90) if c >= 8 else (c + 30)

def ansi16_to_sgr_bg(c: int) -> int:
    """ANSI 0-15 → SGR background code."""
    return (c - 8 + 100) if c >= 8 else (c + 40)

def index_to_rgb(color: int) -> Tuple[int, int, int]:
    """xterm-256 index → (r, g, b) via the appropriate palette."""
    if color < 16:
        return VGA_PALETTE[color]
    if color > 255:
        return VGA_PALETTE[7]
    return COLOR_256_PALETTE[color]

# ── SGR building ──────────────────────────────────────────────────────────────

def build_sgr(pc: ParsedColor, prev: Optional[ParsedColor],
              use_256color: bool, icecolors: bool,
              use_truecolor: bool = False) -> str:
    """Return a CSI…m string (possibly empty) to transition from prev to pc."""
    params: List[int] = []

    need_reset = prev is None
    if need_reset:
        params.append(0)
        prev = ParsedColor()

    # ── attributes ───────────────────────────────────────────────────────────
    def toggle(cur, prv, on_code, off_code):
        if cur and not prv:
            params.append(on_code)
        elif not cur and prv:
            params.append(off_code)

    toggle(pc.bold,      prev.bold,      1, 22)
    toggle(pc.dim,       prev.dim,       2, 22)
    toggle(pc.italic,    prev.italic,    3, 23)
    toggle(pc.underline, prev.underline, 4, 24)
    toggle(pc.blink,     prev.blink,     5, 25)
    toggle(pc.reverse,   prev.reverse,   7, 27)

    # ── foreground ───────────────────────────────────────────────────────────
    if pc.fg != prev.fg:
        if use_truecolor:
            r, g, b = index_to_rgb(pc.fg)
            params += [38, 2, r, g, b]
        elif use_256color:
            params += [38, 5, pc.fg]
        else:
            params.append(ansi16_to_sgr_fg(xterm256_to_ansi16(pc.fg)))

    # ── background ───────────────────────────────────────────────────────────
    if pc.bg != prev.bg:
        if use_truecolor:
            r, g, b = index_to_rgb(pc.bg)
            params += [48, 2, r, g, b]
        elif use_256color:
            params += [48, 5, pc.bg]
        else:
            bg16 = xterm256_to_ansi16(pc.bg)
            if bg16 >= 8 and not icecolors:
                if not pc.blink:
                    params.append(5)
                bg16 -= 8
            params.append(ansi16_to_sgr_bg(bg16))

    if not params:
        return ''
    return f"{CSI}{';'.join(str(p) for p in params)}m"

# ── Row data model ────────────────────────────────────────────────────────────

@dataclass
class DdwChar:
    x: int
    y: int
    text: str
    color: ParsedColor

def load_ddw_rows(source) -> Tuple[List[DdwChar], Optional[SauceRecord]]:
    """Read a .ddw file or file-like object; return (chars, sauce_or_None)."""
    sauce_fields: Dict[str, str] = {}
    chars: List[DdwChar] = []

    if isinstance(source, str):
        import builtins
        f_ctx = builtins.open(source, encoding='utf-8')
    else:
        from contextlib import nullcontext
        f_ctx = nullcontext(source)

    with f_ctx as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            frame = row.get('frame', '')
            text  = row.get('text', '')
            if not text:
                continue

            if frame == 'SAUCE record':
                label = row.get('type', '')
                sauce_fields[label] = text
                continue

            chars.append(DdwChar(
                x=int(row.get('x', 0)),
                y=int(row.get('y', 0)),
                text=text,
                color=parse_color_string(row.get('color', '')),
            ))

    sauce = _rebuild_sauce(sauce_fields) if sauce_fields else None
    return chars, sauce

def _rebuild_sauce(fields: Dict[str, str]) -> SauceRecord:
    s = SauceRecord()
    s.title  = fields.get('Title',  '')
    s.author = fields.get('Author', '')
    s.group  = fields.get('Group',  '')
    s.date   = fields.get('Date',   '') or datetime.date.today().strftime('%Y%m%d')
    dim = fields.get('Dimensions', '')
    if 'x' in dim:
        try:
            w, h = dim.split('x')
            s.t_info1 = int(w)
            s.t_info2 = int(h)
        except ValueError:
            pass
    flags_str = fields.get('Flags', '')
    if flags_str:
        for part in flags_str.split(','):
            part = part.strip()
            if part == 'non-blink':
                s.t_flags |= 0x01
            elif part.startswith('letter-spacing:'):
                try:
                    s.t_flags |= (int(part.split(':')[1]) & 0x3) << 1
                except ValueError:
                    pass
            elif part.startswith('aspect-ratio:'):
                try:
                    s.t_flags |= (int(part.split(':')[1]) & 0x3) << 3
                except ValueError:
                    pass
    s.t_info_s = fields.get('Font', '')
    i = 1
    while f'Comment {i}' in fields:
        s.comments.append(fields[f'Comment {i}'])
        i += 1
    return s

# ── ANSI rendering ────────────────────────────────────────────────────────────

def render_ansi(chars: List[DdwChar], columns: int = 80,
                use_256color: bool = False, icecolors: bool = False,
                use_truecolor: bool = False,
                encoding: str = 'utf-8') -> bytes:
    """Convert DdwChar list to raw ANSI bytes."""
    if not chars:
        return b''

    chars = sorted(chars, key=lambda c: (c.y, c.x))

    out: List[str] = []
    cur_row = 0
    cur_col = 0
    prev_color: Optional[ParsedColor] = None

    out.append(f'{CSI}0m')
    prev_color = ParsedColor()

    for ch in chars:
        target_row, target_col = ch.y, ch.x

        # ── cursor movement ───────────────────────────────────────────────────
        if target_row < cur_row:
            out.append(f'{CSI}{target_row + 1};{target_col + 1}H')
            cur_row, cur_col = target_row, target_col
        elif target_row > cur_row:
            diff = target_row - cur_row
            if diff == 1:
                out.append('\r\n')
            else:
                out.append(f'\r{CSI}{diff}B')
            cur_row = target_row
            cur_col = 0

        if target_col > cur_col:
            diff = target_col - cur_col
            out.append(f'{CSI}{diff}C')
            cur_col = target_col
        elif target_col < cur_col:
            out.append(f'{CSI}{target_row + 1};{target_col + 1}H')
            cur_col = target_col

        # ── color SGR ────────────────────────────────────────────────────────
        sgr = build_sgr(ch.color, prev_color, use_256color, icecolors, use_truecolor)
        if sgr:
            out.append(sgr)
        prev_color = ch.color

        # ── character ────────────────────────────────────────────────────────
        out.append(ch.text)
        cur_col += len(ch.text)

        if cur_col >= columns:
            cur_row += 1
            cur_col = 0

    out.append(f'{CSI}0m')
    return ''.join(out).encode(encoding, errors='replace')

# ── SAUCE serialisation ───────────────────────────────────────────────────────

def build_sauce_block(sauce: SauceRecord, file_size: int,
                      columns: int, rows: int) -> bytes:
    """Serialise a SauceRecord to 128 bytes (comments prepended separately)."""
    def pad(s: str, n: int) -> bytes:
        return s.encode('cp437', errors='replace')[:n].ljust(n, b'\x00')

    if not sauce.date:
        sauce.date = datetime.date.today().strftime('%Y%m%d')
    if not sauce.t_info1:
        sauce.t_info1 = columns
    if not sauce.t_info2:
        sauce.t_info2 = rows

    block = bytearray()
    block += b'SAUCE'
    block += b'00'
    block += pad(sauce.title,  35)
    block += pad(sauce.author, 20)
    block += pad(sauce.group,  20)
    block += pad(sauce.date,    8)
    block += file_size.to_bytes(4, 'little')
    block += bytes([1])                         # DataType: Character
    block += bytes([1])                         # FileType: ANSi
    block += sauce.t_info1.to_bytes(2, 'little')
    block += sauce.t_info2.to_bytes(2, 'little')
    block += (0).to_bytes(2, 'little')          # TInfo3
    block += (0).to_bytes(2, 'little')          # TInfo4
    block += bytes([len(sauce.comments)])
    block += bytes([sauce.t_flags])
    block += pad(sauce.t_info_s, 22)
    assert len(block) == 128
    return bytes(block)

def build_comment_block(comments: List[str]) -> bytes:
    if not comments:
        return b''
    block = bytearray(b'COMNT')
    for c in comments:
        block += c.encode('cp437', errors='replace')[:64].ljust(64, b'\x00')
    return bytes(block)

# ── Public API ────────────────────────────────────────────────────────────────

def ddw_to_ans(input_path: str, output_path: str, columns: int = 80,
               icecolors: bool = False, use_256color: bool = False,
               use_truecolor: bool = False, write_sauce: bool = True,
               encoding: str = 'utf-8'):
    """Convert a .ddw file to an .ans file."""
    chars, sauce = load_ddw_rows(input_path)

    ansi_bytes = render_ansi(chars, columns=columns,
                             use_256color=use_256color, icecolors=icecolors,
                             use_truecolor=use_truecolor, encoding=encoding)

    with open(output_path, 'wb') as f:
        f.write(ansi_bytes)
        f.write(bytes([26]))

        if write_sauce and sauce:
            file_size = len(ansi_bytes) + 1
            comment_block = build_comment_block(sauce.comments)
            sauce_block = build_sauce_block(
                sauce, file_size,
                columns=sauce.t_info1 or columns,
                rows=sauce.t_info2 or 0,
            )
            f.write(comment_block)
            f.write(sauce_block)


def main():
    if len(sys.argv) < 3:
        print("Usage: ddw2ans.py <input.ddw> <output.ans> [columns] [options]")
        print("  columns: width in characters (default: 80)")
        print()
        print("Options:")
        print("  --icecolors   enable iCE colors (bright backgrounds instead of blink)")
        print("  --256color    emit xterm 256-color SGR sequences (38;5;n / 48;5;n)")
        print("  --truecolor   emit 24-bit RGB SGR sequences (38;2;r;g;b / 48;2;r;g;b)")
        print("  --no-sauce    omit SAUCE record even if present in source")
        sys.exit(1)

    input_path   = sys.argv[1]
    output_path  = sys.argv[2]
    columns      = 80
    icecolors    = '--icecolors'  in sys.argv
    use_256color = '--256color'   in sys.argv
    use_truecolor = '--truecolor' in sys.argv
    write_sauce  = '--no-sauce'  not in sys.argv
    encoding = 'utf-8'
    if '--amiga' in sys.argv:
        encoding = 'iso8859-1'
    elif '--pc' in sys.argv or '--cp437' in sys.argv:
        encoding = 'cp437'

    if len(sys.argv) > 3:
        try:
            columns = int(sys.argv[3])
        except ValueError:
            pass

    ddw_to_ans(input_path, output_path, columns=columns,
               icecolors=icecolors, use_256color=use_256color,
               use_truecolor=use_truecolor, write_sauce=write_sauce,
               encoding=encoding)


if __name__ == '__main__':
    main()
