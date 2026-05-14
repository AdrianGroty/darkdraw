import itertools
import math
from copy import copy

from visidata import vd, CharBox, dispwidth
from visidata.bezier import bezier

from darkdraw import Drawing


# Drawing primitives: lines, curves, stamps, split/join text


@Drawing.api
def draw_line(self, objlist, x0, y0, x1, y1):
    'Draw line using Bresenham algorithm.'
    dx = abs(x1-x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy

    objit = itertools.cycle(objlist)

    while True:
        row = next(objit)
        self.paste_chars([row], CharBox(None, x0, y0, 1, 1))

        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * error
        if e2 >= dy:
            if x0 == x1: break
            error += dy
            x0 += sx
        if e2 <= dx:
            if y0 == y1: break
            error += dx
            y0 += sy


@Drawing.api
def set_linedraw_mode(sheet):
    'Toggle line drawing mode.'
    if sheet.mode != 'linedraw':
        sheet.mode = 'linedraw'
        sheet.linepoints = []
    else:
        sheet.mode = ''
        sheet.linepoints = []


@Drawing.api
def next_point(sheet, x2, y2):
    'Add next point for line or bezier curve drawing.'
    if sheet.linepoints:
        objs = vd.getClipboardRows()
        if not objs:
            r = sheet.newRow()
            r.text = '.'
            objs = [r]
        if len(sheet.linepoints) == 1 or sheet.linepoints[-1] == (x2, y2):
            sheet.draw_line(objs, *sheet.linepoints[0], x2, y2)
        else:
            xy1, xy3 = sheet.linepoints
            objit = itertools.cycle(objs)
            # reverse engineered bezier equation to draw with a point *on* the curve
            ctrlX = 2 * x2 - 0.5 * (xy1[0] + xy3[0])
            ctrlY = 2 * y2 - 0.5 * (xy1[1] + xy3[1])
            for x, y in bezier(*xy1, ctrlX, ctrlY, *xy3):
                sheet.paste_chars([next(objit)], CharBox(None, int(x), int(y), 1, 1))

        sheet.linepoints = [sheet.linepoints[-1]]


@Drawing.api
def click(sheet, x, y):
    'Handle mouse click for line drawing or cursor positioning.'
    if sheet.mode == 'linedraw':
        sheet.linepoints.append((x, y))

    sheet.cursorBox = CharBox(None, x, y, 1, 1)


@Drawing.api
def release(sheet, x, y):
    'Handle mouse release for line drawing or cursor box selection.'
    if sheet.mode == 'linedraw':
        sheet.next_point(x, y)
    else:
        sheet.cursorBox.x2 = x + 2
        sheet.cursorBox.y2 = y + 2
        sheet.cursorBox.normalize()


@Drawing.api
def split_rows(sheet, rows):
    'Split text strings into individual character objects.'
    vd.addUndo(setattr, sheet.source, 'rows', copy(sheet.source.rows))

    for row in rows:
        i = sheet.source.rows.index(row)
        newrows = []
        dx = 0
        for ch in row.text:
            newr = copy(row)
            newr.text = ch
            newr.x += dx
            dx += dispwidth(ch)
            newrows.append(newr)

        sheet.source.rows[i:i+1] = newrows


@Drawing.api
def join_rows(dwg, rows):
    'Join multiple character objects into single text object.'
    vd.addUndo(setattr, rows[0], 'text', rows[0].text)
    rows[0].text = ''.join(r.text for r in rows)
    dwg.source.deleteBy(lambda r, rows=rows[1:]: r in rows)


@Drawing.api
def stamp_circle(sheet, box):
    'Stamp circle shape using clipboard characters.'
    xr = (box.w-1)/2
    yr = (box.h-1)/2
    x = (2*box.x1 + box.w)/2
    y = (2*box.y1 + box.h)/2

    coords = set()
    for theta in range(0, 361):
        theta = math.radians(theta)
        coords.add((int(x+(xr*math.cos(theta))), int(y+(yr*math.sin(theta)))))

    itchars = itertools.cycle([(r.text, r.color) for r in vd.memory.cliprows or []] or [('*', '')])
    for coord in coords:
        ch, color = next(itchars)
        sheet.place_text(ch, CharBox(x1=coord[0], y1=coord[1]), go_forward=False)


# Sheet initialization
Drawing.init('mode', str)
Drawing.init('linepoints', list)


# Commands
Drawing.addCommand('w', 'line-drawing-mode', 'set_linedraw_mode()', 'toggle line drawing mode')
Drawing.addCommand('.', 'next-point', 'next_point(cursorBox.x1, cursorBox.y1)', 'add next point for line or bezier curve')
Drawing.addCommand('BUTTON1_PRESSED', 'click-cursor', 'click(mouseX, mouseY)', 'start cursor box with left mouse button press')
Drawing.addCommand('BUTTON1_RELEASED', 'end-cursor', 'release(mouseX, mouseY)', 'end cursor box with left mouse button release')

Drawing.addCommand('/', 'split-cursor', 'split_rows(list(itercursor()))', 'split strings at cursor into multiple objects, one object per character')
Drawing.addCommand('g/', 'split-selected', 'split_rows(source.selectedRows)', 'split selected strings into multiple objects, one object per character')
Drawing.addCommand('&', 'join-selected', 'join_rows(source.selectedRows)', 'join selected objects into one text object')

Drawing.addCommand('', 'stamp-circle', 'sheet.stamp_circle(cursorBox)', 'stamp circle using clipboard characters')
