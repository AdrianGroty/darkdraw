import json
import io
from visidata import VisiData, vd

from .ddw2ans import load_ddw_rows, render_ansi, build_sauce_block, build_comment_block

# ── Options (mirrors load_ans.py) ─────────────────────────────────────────────
vd.option('ans_columns',    80,      'width in characters for ANSI files')
vd.option('ans_icecolors',  False,   'enable iCE colors (blinking -> bright backgrounds)')
vd.option('ans_encoding',   'cp437', 'character encoding: cp437/dos, iso8859-1/amiga, or utf-8')
vd.option('ans_vga_colors', False,   'convert SGR color codes to VGA palette when importing .ans files')
# Save-only options
vd.option('ans_256color',   False,   'emit xterm 256-color SGR sequences when saving .ans files')
vd.option('ans_truecolor',  False,   'emit 24-bit RGB SGR sequences (38;2;r;g;b) when saving .ans files')
vd.option('ans_sauce',      True,    'write SAUCE record when saving .ans files')

@VisiData.api
def save_ans(vd, p, vs):
    """Save a DrawingSheet as an ANSI .ans file."""
    rows_jsonl = '\n'.join(json.dumps(r) for r in vs.rows) + '\n'
    chars, sauce = load_ddw_rows(io.StringIO(rows_jsonl))

    cols        = vd.options.ans_columns
    ice         = vd.options.ans_icecolors
    use_256     = vd.options.ans_256color
    use_true    = vd.options.ans_truecolor
    do_sauce    = vd.options.ans_sauce

    enc_input = vd.options.ans_encoding.lower()
    if enc_input == 'dos':
        enc = 'cp437'
    elif enc_input == 'amiga':
        enc = 'iso8859-1'
    else:
        enc = enc_input

    ansi_bytes = render_ansi(chars, columns=cols,
                             use_256color=use_256, icecolors=ice,
                             use_truecolor=use_true, encoding=enc)

    with p.open_bytes(mode='wb') as f:
        f.write(ansi_bytes)
        f.write(bytes([26]))

        if do_sauce and sauce:
            file_size     = len(ansi_bytes) + 1
            comment_block = build_comment_block(sauce.comments)
            sauce_block   = build_sauce_block(
                sauce, file_size,
                columns=sauce.t_info1 or cols,
                rows=sauce.t_info2 or 0,
            )
            f.write(comment_block)
            f.write(sauce_block)
