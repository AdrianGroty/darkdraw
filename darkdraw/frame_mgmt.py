from copy import copy as _copy

from visidata import vd, VisiData, ItemColumn

from .drawing import DrawingSheet, Drawing


def _link_id_setter(col, row, val):
    old = getattr(row, 'id', None)
    if not (getattr(row, 'type', '') == 'frame' and old and old != val):
        return
    n = 0
    for r in col.sheet.rows:
        if r is row or getattr(r, 'type', '') or not getattr(r, 'frame', ''): continue
        ids = r.frame.split()
        if old not in ids: continue
        vd.addUndo(setattr, r, 'frame', r.frame)
        r.frame = ' '.join(val if x == old else x for x in ids)
        n += 1
    if n: vd.status(f'link_frame_ids: updated {n} element(s) {old!r} → {val!r}')


for _i, _c in enumerate(DrawingSheet.columns):
    if _c.name == 'id':
        DrawingSheet.columns[_i] = ItemColumn('id', type=str, setter=_link_id_setter)
        break


### DUPLICATE-FRAME ##########################################################
@Drawing.api
def duplicate_frame(sheet, before=False):
    src = sheet.source
    if not src.frames:
        return src.new_between_frame(-1, 0)

    cur = src.frames[sheet.cursorFrameIndex]
    if before:
        adj = src.frames[sheet.cursorFrameIndex-1] if sheet.cursorFrameIndex > 0 else None
        name = (str(adj.id)+'-'+str(cur.id)) if adj else str(int(cur.id)-1)
    else:
        adj = src.frames[sheet.cursorFrameIndex+1] if sheet.cursorFrameIndex+1 < len(src.frames) else None
        name = (str(cur.id)+'-'+str(adj.id)) if adj else str(int(cur.id)+1)

    newf = src.newRow()
    newf.type = 'frame'
    newf.id = name
    newf.duration_ms = cur.duration_ms or 100

    for i, r in enumerate(src.rows):
        if r is cur:
            vd.clearCaches()
            src.addRow(newf, index=i if before else i+1)
            break

    dup_rows = [_copy(r) for r in src.rows if cur.id in (r.frame or '').split()]
    for r in dup_rows:
        r.frame = newf.id
        src.addRow(r)
    return newf

Drawing.addCommand('gz[', 'duplicate-frame-before', 'sheet.duplicate_frame(before=True)', 'insert new frame before current with copy of current frame objects')
Drawing.addCommand('gz]', 'duplicate-frame-after', 'sheet.duplicate_frame(before=False); sheet.cursorFrameIndex += 1', 'insert new frame after current with copy of current frame objects')
##############################################################################

### DELETE ORPHAN-FRAME ELEMENTS ##############################################
@DrawingSheet.api
def delete_orphan_frame_elements(self):
    'Delete elements whose .frame references no existing frame id.'
    valid = {r.id for r in self.rows if r.type == 'frame'}
    orphans = [r for r in self.rows
               if not r.type and r.frame
               and not (set(r.frame.split()) & valid)]
    if not orphans:
        vd.status('no orphan-frame elements')
        return
    oids = set(map(id, orphans))
    self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.status(f'deleted {len(orphans)} orphan-frame element(s)')

DrawingSheet.addCommand(None, 'delete-orphan-frame-elements', 'sheet.delete_orphan_frame_elements()', 'delete elements whose frame field references no existing frame')
Drawing.addCommand(None, 'delete-orphan-frame-elements', 'sheet.source.delete_orphan_frame_elements()', 'delete elements whose frame field references no existing frame')
##############################################################################

### COMBINE DUPLICATES #######################################################
@DrawingSheet.api
def combine_duplicates(self):
    'Merge elements sharing x,y,text,color,tags,group: union their frame ids onto one, delete the rest.'
    groups = {}
    for r in self.rows:
        if r.type: continue
        key = (r.x, r.y, r.text, r.color, frozenset(r.tags or []), r.group)
        groups.setdefault(key, []).append(r)

    to_delete = []
    merged = 0
    for rs in groups.values():
        if len(rs) < 2: continue
        frames = set()
        any_empty = False
        for r in rs:
            if not r.frame:
                any_empty = True
            else:
                frames.update(r.frame.split())
        keeper = rs[0]
        new_frame = '' if any_empty else ' '.join(sorted(frames))
        if keeper.frame != new_frame:
            vd.addUndo(setattr, keeper, 'frame', keeper.frame)
            keeper.frame = new_frame
        to_delete.extend(rs[1:])
        merged += 1

    if not to_delete:
        vd.status('no duplicates')
        return
    oids = set(map(id, to_delete))
    self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.status(f'combined {merged} group(s), removed {len(to_delete)} duplicate(s)')

DrawingSheet.addCommand(None, 'combine-duplicates', 'sheet.combine_duplicates()', 'merge elements with same x,y,text,color,tags,group: union frame ids, delete extras')
Drawing.addCommand(None, 'combine-duplicates', 'sheet.source.combine_duplicates()', 'merge elements with same x,y,text,color,tags,group: union frame ids, delete extras')
##############################################################################

### SELF-CONTAIN FRAMES ######################################################
@DrawingSheet.api
def self_contain_frames(self):
    'Split each element with >1 frame ids into one copy per frame; delete originals. Skips empty/null frame field.'
    to_delete = []
    new_rows = []
    n_split = 0
    for r in list(self.rows):
        if r.type: continue
        if not r.frame: continue
        ids = r.frame.split()
        if len(ids) < 2: continue
        for fid in ids:
            new_r = _copy(r)
            new_r.frame = fid
            self.addRow(new_r)
            new_rows.append(new_r)
        to_delete.append(r)
        n_split += 1
    if not to_delete:
        vd.status('no multi-frame elements')
        return
    new_ids = set(map(id, new_rows))
    vd.addUndo(self.deleteBy, lambda r, ids=new_ids: id(r) in ids)
    oids = set(map(id, to_delete))
    self.deleteBy(lambda r, oids=oids: id(r) in oids)
    vd.status(f'split {n_split} element(s) into {len(new_rows)} copies')

DrawingSheet.addCommand(None, 'self-contain-frames', 'sheet.self_contain_frames()', 'split each multi-frame element into one copy per frame; delete originals')
Drawing.addCommand(None, 'self-contain-frames', 'sheet.source.self_contain_frames()', 'split each multi-frame element into one copy per frame; delete originals')
##############################################################################
