import json
import io
from visidata import VisiData, Path, vd
from . import DrawingSheet
from .ans2ddw import AnsiParser

# Define global options
vd.option('ans_columns', 80, 'width in characters for ANSI files')
vd.option('ans_icecolors', False, 'enable iCE colors (blinking -> bright backgrounds)')
vd.option('ans_encoding', 'cp437', 'character encoding: cp437/dos, iso8859-1/amiga, or utf-8')
vd.option('ans_vga_colors', False, 'convert SGR color codes to VGA palette when importing .ans files')

@VisiData.api
def open_ans(vd, p):
    # 1. Read raw bytes from source
    from .ans2ddw import parse_sauce
    
    data = p.read_bytes()
    
    # 1a. Extract SAUCE record if present
    file_data, sauce = parse_sauce(data)

    # 2. Pull current global options
    enc_input = vd.options.ans_encoding.lower()
    cols = vd.options.ans_columns
    ice = vd.options.ans_icecolors
    vga = vd.options.ans_vga_colors

    # 3. Handle aliases for encoding
    # Map 'dos' -> 'cp437' and 'amiga' -> 'iso8859-1' to match AnsiParser logic
    if enc_input == 'dos':
        enc = 'cp437'
    elif enc_input == 'amiga':
        enc = 'iso8859-1'
    else:
        enc = enc_input  # Support 'utf-8', 'cp437', 'iso8859-1' directly

    # 4. Initialize parser with the explicit values
    parser = AnsiParser(
        columns=cols,
        icecolors=ice,
        encoding=enc,
        vga_colors=vga
    )
    
    # 5. Parse the data into AnsiChar objects
    chars = parser.parse(file_data)

    # 6. Convert to rows, including SAUCE if present
    rows = []
    if sauce:
        rows.extend(sauce.sauce_to_rows())
    rows.extend([char.to_ddw_row(vga_colors=vga) for char in chars])

    # 7. Generate JSONL output for DrawingSheet
    ddwoutput = '\n'.join(json.dumps(r) for r in rows) + '\n'

    # 8. Return the DrawingSheet via the virtual path mechanism
    return DrawingSheet(
        p.name,
        source=Path(
            str(p.with_suffix('.ddw')),
            fptext=io.StringIO(ddwoutput)
        )
    ).drawing
