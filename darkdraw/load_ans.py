import json
import io
from visidata import VisiData, Path, vd
from . import DrawingSheet
from .ans2ddw import AnsiParser

# Define global options
vd.option('ans_columns', 80, 'width in characters for ANSI files')
vd.option('ans_icecolors', False, 'enable iCE colors (blinking -> bright backgrounds)')
vd.option('ans_encoding', 'cp437', 'character encoding: cp437/dos, iso8859-1/amiga, or utf-8')

@VisiData.api
def open_ans(vd, p):
    # 1. Read raw bytes from source
    data = p.read_bytes()

    # 2. Pull current global options
    enc_input = vd.options.ans_encoding.lower()
    cols = vd.options.ans_columns
    ice = vd.options.ans_icecolors

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
        encoding=enc
    )
    
    # 5. Parse the data into AnsiChar objects
    chars = parser.parse(data)

    # 6. Convert to rows using the AnsiChar transformation logic
    rows = [char.to_ddw_row() for char in chars]

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
