#!/usr/bin/env python3
"""Where the gunsmith puts every chip once a fitted part opens a new slot.

    python tools/cut-gunsmith-layouts.py data/cut-specs/ar-57-layouts.json

One settled frame per configuration goes in; the `layouts` block of
data/gunsmith-<weapon>.json comes out, plus an icon in smith/slot/ for each
slot the bare weapon does not have. Everything else in that file is left
exactly as it was.

WHY A WHOLE LAYOUT PER CLIP AND NOT A LIST OF EXTRA CHIPS

The game reflows the entire fan when the count changes. Fitting the AR-57's
Wave Blaster barrel slides the left arm out by more than a hundred pixels and
lifts the optic chips forty; pasting the new Upper Rail chip onto the base
positions would land it on its neighbour and leave everything else lying. So
each clip contributes the position of every chip on screen at the time, keyed
by the set of slots that are open, and the page uses the arrangement it has
actually watched whenever the reader assembles a build that matches one.

THREE THINGS TO READ OFF A FRAME, EACH A DIFFERENT WAY

WHICH SLOT.  The game prints a chip's name directly above it and clips the
name to the chip's width, so a Rear Grip Patch reads "p Patch" and a Rear Grip
Mount reads "ip Mount". A tail is still unambiguous across the twenty-odd
names, so the label is the identity. Matching the icon art instead does not
work, because the chip holding a fitted part shows the part, not the slot.

WHERE IT IS.  The label gives a seed and the same ring score the base pass
used snaps it to the exact pixel. Chips whose label the reader cannot make out
are followed by their artwork inside a window of where they sat in the base
layout, and the handful neither method pins down are seeded by hand in the
spec -- hand-placed to the right object, machine-placed to the right pixel.

WHERE ITS LINE GOES.  Walk out from the chip in every direction and ask which
way a hairline actually leaves it. Scoring candidate anchors against candidate
chips instead picks whichever pairing happens to cross a bright part of the
weapon; following the line asks the only question that matters. A chip that
already has an anchor keeps it -- the weapon does not move between recordings,
and an anchor may have been dragged into place by hand in the editor's dev
mode, which a tool that silently undid would make worthless.

WHAT A SPEC HOLDS

    weapon      the id, as in weapons.json
    chip        the side of a chip in frame pixels; label_dy, the gap from the
                top of its name to the top of the box. Both are properties of
                the recording's resolution, not of the weapon.
    frames      directory the frames live in, absolute or repo-relative
    base_frame  a frame of the bare weapon, for the artwork fallback
    labels      on-screen name per slot, for slots the weapon's own file does
                not already name (its `slots` and `granted` blocks do most)
    clips       one entry each: key, frame, items (the ids fitted), grants
                (slots opened), occupies (base slots taken away), seed,
                and optionally unshown -- slots the rules say are open in this
                arrangement but which the frame does not draw a chip for. That
                is a claim about the RECORDING, not about the weapon: occupies
                means the slot is gone, unshown means it is there and this
                picture is short of it. Keep the two apart or the page will
                tell people a slot does not exist because a video missed it.
    icon_from   which clip to cut each new slot's icon from -- one where the
                slot is EMPTY, so the picture is the slot's own rather than
                whatever happens to be fitted in it

THE FRAMES MUST BE SETTLED ONES

The chips slide into place over about a second, and a frame caught mid-flight
gives positions that are real but transient; what this file records is where
they come to rest. Two independent recordings of the same configuration agree
to about a third of a grey level, so a frame that disagrees with its
neighbours by more than that was caught moving.
"""
import difflib
import json
import pathlib
import sys

import numpy as np
import pytesseract
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.feature import match_template

ROOT = pathlib.Path(__file__).resolve().parent.parent

if len(sys.argv) != 2:
    raise SystemExit(__doc__.strip().split('\n\n')[1].strip())
spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))

WID = spec['weapon']
S = spec['chip']
DY = spec.get('label_dy', 16)
FRAMES = pathlib.Path(spec['frames'])
if not FRAMES.is_absolute():
    FRAMES = ROOT / FRAMES
DATA = ROOT / f'data/gunsmith-{WID}.json'
ICONS = ROOT / 'smith/slot'


# --- reading the labels ----------------------------------------------------

def words(path):
    """Every word tesseract can find, in frame coordinates.

    The labels are thin light grey on near-black. Stretching that range and
    inverting gives tesseract something it is used to; doubling the size before
    it looks is worth more than any of its own options."""
    im = Image.open(path).convert('L')
    a = np.array(im).astype(float)
    b = np.clip((a - 55) * 5, 0, 255).astype('uint8')
    big = Image.fromarray(255 - b).resize((im.width * 2, im.height * 2),
                                          Image.LANCZOS)
    d = pytesseract.image_to_data(big, output_type=pytesseract.Output.DICT,
                                  config='--psm 11')
    out = []
    for i, t in enumerate(d['text']):
        t = t.strip()
        if t and float(d['conf'][i]) >= 45:
            out.append((t, d['left'][i] // 2, d['top'][i] // 2,
                        d['width'][i] // 2, d['height'][i] // 2))
    return out


def lines(ws):
    """Join words sitting on the same baseline and touching each other."""
    ws = sorted(ws, key=lambda w: (w[2] // 8, w[1]))
    out = []
    for t, x, y, w, h in ws:
        if out:
            pt, px, py, pw, ph = out[-1]
            if abs(y - py) <= 6 and 0 <= x - (px + pw) <= 22:
                out[-1] = (pt + ' ' + t, px, min(py, y), x + w - px, max(ph, h))
                continue
        out.append((t, x, y, w, h))
    return out


def norm(s):
    return ' '.join(''.join(c if c.isalpha() else ' ' for c in s.lower()).split())


def identify(text, names):
    """Best slot for a label, scored against the tail of each name."""
    t = norm(text)
    if not t:
        return None, 0.0
    best, score = None, 0.0
    for sid, name in names.items():
        full = norm(name)
        for k in range(len(full)):
            tail = full[k:].strip()
            if len(tail) < 3:
                continue
            r = difflib.SequenceMatcher(None, t, tail).ratio()
            # A clipped label is a tail of the name, so a long tail matching is
            # better evidence than a short one: "Mount" fits two slots,
            # "Grip Mount" fits one.
            r *= 0.72 + 0.28 * (len(tail) / len(full))
            if r > score:
                best, score = sid, r
    return best, score


# --- finding the boxes -----------------------------------------------------

def ring(g):
    """Border brightness minus interior, for every chip-sized box position."""
    rr = ndimage.uniform_filter1d(g, S, axis=1, origin=-(S // 2),
                                  mode='constant') * S
    cr = ndimage.uniform_filter1d(g, S, axis=0, origin=-(S // 2),
                                  mode='constant') * S
    inner = ndimage.uniform_filter(g, S - 8, mode='constant')
    h, w = g.shape
    Y, X = h - S, w - S
    r = (rr[:Y, :X] + rr[S-1:S-1+Y, :X]
         + cr[:Y, :X] + cr[:Y, S-1:S-1+X]) / (4 * S)
    return r - inner[S//2:S//2+Y, S//2:S//2+X]


def snap(sc, x, y, r=12):
    h, w = sc.shape
    x0, y0 = max(0, min(x - r, w - 1)), max(0, min(y - r, h - 1))
    win = sc[y0:min(h, y + r), x0:min(w, x + r)]
    if win.size == 0:
        return x, y, -1e9
    dy, dx = np.unravel_index(win.argmax(), win.shape)
    return int(x0 + dx), int(y0 + dy), float(win.max())


def by_label(path, sc, names, cut=0.80, ring_floor=12.0):
    picks = {}
    for text, x, y, w, h in lines(words(path)):
        sid, r = identify(text, names)
        if not sid or r < cut:
            continue
        cx, cy, score = snap(sc, x, y + DY)
        if score < ring_floor:            # no box under it: not a chip label
            continue
        if sid not in picks or r > picks[sid][0]:
            picks[sid] = (r, cx, cy)
    return {sid: (x, y) for sid, (r, x, y) in picks.items()}


def by_art(path, base_frame, have, base_xy, r=70, floor=0.72):
    """Chips the label reader missed: follow the artwork instead.

    Only within a window of where the chip was in the base layout, because the
    same crop matches several chips across a whole screen -- a rail icon is a
    rail icon. Inside a window that ambiguity does not arise."""
    g = np.array(Image.open(path).convert('L')).astype(float)
    b = np.array(Image.open(base_frame).convert('L')).astype(float)
    out = {}
    for sid, (bx, by) in base_xy.items():
        if sid in have:
            continue
        t = b[by:by+S, bx:bx+S]
        y0, x0 = max(0, by - r), max(0, bx - r)
        win = g[y0:by+S+r, x0:bx+S+r]
        if win.shape[0] < S or win.shape[1] < S or t.shape != (S, S):
            continue
        m = match_template(win, t)
        y, x = np.unravel_index(m.argmax(), m.shape)
        if m[y, x] >= floor:
            out[sid] = (int(x0 + x), int(y0 + y))
    return out


# --- following the leader line ---------------------------------------------

def _lit(g, x, y):
    h, w = g.shape
    xi, yi = int(round(x)), int(round(y))
    if not (3 < xi < w - 4 and 3 < yi < h - 4):
        return None
    around = min(max(g[yi-3, xi], g[yi+3, xi]), max(g[yi, xi-3], g[yi, xi+3]))
    return g[yi, xi] > around + 2.0


def _run(g, cx, cy, ang, r0, r1):
    ok = tot = 0
    for r in np.arange(r0, r1, 1.0):
        v = _lit(g, cx + r*np.cos(ang), cy + r*np.sin(ang))
        if v is None:
            break
        tot += 1
        ok += v
    return ok / tot if tot else 0.0


# A 14px box with a plus in it: what the game draws where a leader line meets
# the weapon. Synthetic rather than cut from a frame so the tool carries no
# asset, and matched by NORMALISED correlation, which finds it over the bright
# top rail as readily as over the near-black floor. A brightness test does not:
# the same glyph measures 100 above its surroundings on the floor and 10 on lit
# metal, and every threshold that keeps the second keeps half the rifle too.
MARKER = np.zeros((16, 16), float)
MARKER[1, 1:15] = MARKER[14, 1:15] = MARKER[1:15, 1] = MARKER[1:15, 14] = 1.0
MARKER[7:9, 4:12] = MARKER[4:12, 7:9] = 0.8


def markers(g, floor=0.5):
    """Every anchor marker in a frame, as (x, y) centres."""
    m = match_template(g, MARKER, pad_input=True)
    peak = ndimage.maximum_filter(m, 11)
    ys, xs = np.where((m == peak) & (m > floor))
    return np.stack([xs, ys], 1).astype(float)


def trace(g, cx, cy, marks, reach=900):
    """Which way the hairline leaves this chip, and where it stops.

    A line is a direction that scores far above every OTHER direction, not a
    direction that scores above some fixed number. The hairlines vary in
    contrast -- one crossing the lit floor behind the pistol grip reads at 0.9,
    one leaving an optic chip over near-black at 0.69 -- and a flat 0.7 bar
    threw the second away while the sweep had in fact found it cleanly, five
    times clear of the next best angle.

    WHERE IT STOPS IS NOT WHERE IT FADES. The game draws these lines fading
    with distance, so the first place the sweep loses them is nowhere near the
    weapon -- the Rear Grip Patch line reads 1.0 for its first fifty pixels,
    0.0 by two hundred, and actually ends six hundred and fifty out. What ends
    it is the little boxed plus the game draws at the join, so the anchor is
    the first of those on the line and the fade is only the fallback for a
    chip whose marker sits somewhere the matcher cannot see it."""
    degs = np.arange(0, 360, 0.4)
    sc = np.array([_run(g, cx, cy, np.radians(d), S*0.62, S*0.62 + 110)
                   for d in degs])
    score = float(sc.max())
    if score < 0.45 or score < 2 * float(np.percentile(sc, 95)):
        return None
    a = np.radians(float(degs[int(sc.argmax())]))

    u = np.array([np.cos(a), np.sin(a)])
    off = marks - np.array([cx, cy])
    along, across = off @ u, np.abs(off @ np.array([-u[1], u[0]]))
    on = np.where((across < 5) & (along > S * 0.62) & (along < reach))[0]
    if len(on):
        x, y = marks[on[int(np.argmin(along[on]))]]
        return int(round(x)), int(round(y))

    r = S * 0.62
    while r < reach:
        if _run(g, cx, cy, a, r, r + 24) < 0.62:
            break
        r += 12
    return int(round(cx + r*np.cos(a))), int(round(cy + r*np.sin(a)))


# --- where the game has moved the rifle to ---------------------------------

def shift(clip, base, ref, reach=200):
    """How far the weapon itself sits from where the base frame drew it.

    An anchor is a point ON THE WEAPON, and the page draws one picture of the
    weapon at one place whatever is fitted. So an anchor has to be recorded in
    the base frame's coordinates -- and a clip does not always agree with the
    base frame about where the rifle is. Fitting the MCX LT's Fierce Barrel
    makes the rifle longer and the game slides the whole thing 78 pixels right
    and 18 down to fit it on screen. Anchors traced in that clip and written
    down raw would every one of them miss by that much: the Heat Shield's line
    would stop short of the barrel, and the two patches would point at the air
    beside the handguard.

    Measured, not declared, by matching one patch of the weapon that nothing
    fitted in these clips changes -- `anchor_ref` in the spec, which is the
    receiver on every gun so far. A spec with no anchor_ref gets no correction,
    which is right for the RM277 and the AR-57: their guns do not move, and the
    tool that did those clips could not have known that it mattered.
    """
    x0, y0, x1, y1 = ref
    tgt = base[y0:y1, x0:x1]
    best = None
    for dy in range(-reach // 4, reach // 4 + 1, 2):
        for dx in range(-reach, reach + 1, 2):
            v = float(np.abs(clip[y0+dy:y1+dy, x0+dx:x1+dx] - tgt).mean())
            if best is None or v < best[0]:
                best = (v, dx, dy)
    return best[1], best[2], best[0]


# --- putting it together ---------------------------------------------------

def main():
    d = json.loads(DATA.read_text(encoding='utf-8'))
    base_xy = {s['slot']: (s['x'], s['y']) for s in d['slots']}
    base_anchor = {s['slot']: (s.get('ax'), s.get('ay')) for s in d['slots']}
    # What the game calls each slot, taken from the weapon's own file rather
    # than from a table in here: the base slots name themselves, the granted
    # block names the ones a part opens, and the spec covers anything left.
    names = {s['slot']: s['label'] for s in d['slots']}
    names.update({g['slot']: g['label'] for g in d.get('granted', [])})
    names.update(spec.get('labels', {}))

    # An anchor already recorded stays: see the header. Only a slot with no
    # anchor anywhere gets one traced.
    was = {(tuple(l['when']), tuple(l['blocks'])): l['chips']
           for l in d.get('layouts', [])}
    # AND ONE MEASURED IN AN EARLIER CLIP COUNTS AS RECORDED. The anchor is a
    # point on the weapon, so a slot that appears in three arrangements has one
    # anchor between them, not three tries at it -- and three tries is worse
    # than one, because the sweep can fail in a clip where the line is short or
    # crosses something bright. The MCX LT's left patch is the case: traced
    # cleanly onto the handguard from the barrel clip, and, in the clip with
    # the riser as well, off the end of a line the sweep lost, landing in the
    # sky above the rifle. First reading wins; the editor still overrules.
    known = dict(base_anchor)

    ref = spec.get('anchor_ref')
    base_grey = np.array(Image.open(str(FRAMES / spec['base_frame']))
                         .convert('L')).astype(float) if ref else None

    layouts, icons, checks = [], {}, []
    for c in spec['clips']:
        path = str(FRAMES / c['frame'])
        g = np.array(Image.open(path).convert('L')).astype(float)
        sc = ring(g)
        marks = markers(g)
        dx = dy = 0
        if ref is not None:
            dx, dy, resid = shift(g, base_grey, ref)
            if dx or dy:
                print(f'  {c["key"]}: the game moved the rifle '
                      f'{dx:+},{dy:+} here; anchors corrected back '
                      f'(match {resid:.1f})')
        gone = set(c['occupies']) | set(c.get('unshown', ()))
        present = [s for s in base_xy if s not in gone] + [
            s for s in c['grants'] if s not in gone]

        got = by_label(path, sc, names)
        got.update(by_art(path, str(FRAMES / spec['base_frame']), got,
                          {k: v for k, v in base_xy.items()
                           if k not in gone}))
        for sid, (sx, sy) in c.get('seed', {}).items():    # hand seeds win
            x, y, _ = snap(sc, sx, sy, r=8)
            got[sid] = (x, y)
        got = {k: v for k, v in got.items() if k in present}

        missing = [s for s in present if s not in got]
        if missing:
            raise SystemExit(f'{c["key"]}: no chip found for {missing}')

        before = was.get((tuple(sorted(c['grants'])),
                          tuple(sorted(c['occupies'])))) or {}
        chips = {}
        for sid, (x, y) in sorted(got.items(), key=lambda kv: kv[1]):
            kept = before.get(sid) or {}
            if kept.get('ax') is not None:
                ax, ay = kept['ax'], kept['ay']
            elif known.get(sid, (None,))[0] is not None:
                ax, ay = known[sid]
            else:
                p = trace(g, x + S//2, y + S//2, marks)
                if p is None:
                    raise SystemExit(f'{c["key"]}/{sid}: no leader line')
                ax, ay = p[0] - dx, p[1] - dy
                print(f'  traced {c["key"]}/{sid} -> {ax},{ay}'
                      + (f' (from {p[0]},{p[1]} in the clip)' if dx or dy else ''))
            known[sid] = (ax, ay)
            chips[sid] = dict(x=x, y=y, ax=ax, ay=ay, label=names[sid])
        layouts.append(dict(when=sorted(c['grants']),
                            blocks=sorted(c['occupies']),
                            by=c['items'], chips=chips))
        checks.append((c['key'], path, chips))
        print(f'{c["key"]:<16} {len(chips)} chips, '
              f'{len(c["grants"])} opened, {len(c["occupies"])} taken'
              + (f', {len(c["unshown"])} open but not drawn'
                 if c.get('unshown') else ''))

        for sid, key in spec.get('icon_from', {}).items():
            if key == c['key'] and sid in got:
                icons[sid] = (path, *got[sid])

    d['layouts'] = layouts
    DATA.write_text(json.dumps(d, indent=1) + '\n', encoding='utf-8')
    print(f'wrote {len(layouts)} layouts to {DATA.relative_to(ROOT)}')

    ICONS.mkdir(parents=True, exist_ok=True)
    for sid, (frame, x, y) in icons.items():
        im = Image.open(frame).convert('RGB').crop(
            (x + 2, y + 2, x + S - 1, y + S - 1))
        im.resize((70, 70), Image.LANCZOS).save(ICONS / f'{sid}.png')
        print('  icon', sid)

    # One picture per clip with the boxes and the lines drawn on, to check the
    # coordinates against the thing they came from. Same habit as the frame
    # cutter: a number that is wrong by forty pixels reads as a number.
    out = ROOT / 'tools/cut-checks'
    out.mkdir(exist_ok=True)
    for key, path, chips in checks:
        im = Image.open(path).convert('RGB')
        dr = ImageDraw.Draw(im)
        for sid, c in chips.items():
            dr.rectangle([c['x'], c['y'], c['x'] + S, c['y'] + S],
                         outline=(255, 60, 60), width=2)
            dr.line([c['x'] + S/2, c['y'] + S/2, c['ax'], c['ay']],
                    fill=(0, 255, 120), width=2)
            dr.ellipse([c['ax']-6, c['ay']-6, c['ax']+6, c['ay']+6],
                       outline=(255, 230, 0), width=3)
        im.resize((im.width * 3 // 4, im.height * 3 // 4)).save(
            out / f'{WID}-layout-{key}.png')
    print(f'and {len(checks)} checks in tools/cut-checks/')


if __name__ == '__main__':
    main()
