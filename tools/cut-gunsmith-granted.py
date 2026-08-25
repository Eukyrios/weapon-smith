"""Find the slots a fitted part opens, and where the gunsmith draws them.

Source: seven screen recordings of the RM277's gunsmith, each with one part
fitted -- a tactical riser, a micro sight riser on top of it, two rear grips,
two barrels and a sniper scope. Between them they cover every slot the bare
rifle does not have. Produces the extra icons in smith/slot/ and the `layouts`
block of data/gunsmith-rm277.json.

Three things have to come out of each frame, and each is read a different way.

WHICH SLOT.  The game prints a chip's name directly above it and clips the name
to the chip's width when it is too long, so a Riser Optic reads "ser Optic" and
a Rear Grip Mount reads "ip Mount". A tail is still unambiguous across the
twenty-odd names, so the label is the identity. Matching the icon art instead
does not work here: the chip holding a fitted part shows the part, not the slot.

WHERE IT IS.  The label gives a seed and the same ring score the base layout
used snaps it to the exact pixel. Chips whose label the reader cannot make out
are followed by their artwork inside a window of where they sat before, and the
handful neither method pins down are seeded by hand in CLIPS below -- hand-
placed to the right object, machine-placed to the right pixel, as the base pass
was.

WHERE ITS LINE GOES.  Walk out from the chip in every direction and ask which
way a hairline actually leaves it. Scoring candidate anchors against candidate
chips instead picks whichever pairing happens to cross a bright part of the
weapon; following the line asks the only question that matters. A chip that
already had an anchor in the base layout keeps it, because the weapon does not
move between recordings and the anchor is a point on the weapon.

What comes out is one whole layout per configuration rather than a list of
extra chips. The game reflows the entire fan when the count changes -- fitting
a barrel combo moves the left arm by up to 155px -- so a chip pasted onto the
base positions would land on its neighbour.

The frames must be settled ones. The chips slide into place over about a
second, and a frame caught mid-animation gives positions that are real but
transient; what this file is for is where they come to rest.
"""
import difflib
import json
import pathlib

import numpy as np
import pytesseract
from PIL import Image
from scipy import ndimage
from skimage.feature import match_template

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data/gunsmith-rm277.json'
ICONS = ROOT / 'smith/slot'
FRAMES = pathlib.Path('clips')       # settled frames, one per clip
BASE_FRAME = 'base/f006.png'         # the bare rifle, from cut-gunsmith.py

S = 73                               # chip side, in the 2032x1080 frame
DY = 16                              # label top to chip top, measured on base

NAMES = {
    'optics': 'Optic', 'offset-optics': 'Offset Optic',
    'riser-optics': 'Riser Optic', 'red-dot-optics': 'Red Dot Optic',
    'tactical-device': 'Tactical Device', 'kill-flash': 'Killflash',
    'upper-rail': 'Upper Rail', 'barrel': 'Barrel', 'muzzle': 'Muzzle',
    'foregrip': 'Foregrip', 'rail-bipod': 'Rail Bipod',
    'left-rail': 'Left Rail', 'right-rail': 'Right Rail',
    'left-patch': 'Left Patch', 'right-patch': 'Right Patch',
    'mag': 'Mag', 'mag-mount': 'Mag Mount', 'rear-grip': 'Rear Grip',
    'rear-grip-patch': 'Rear Grip Patch', 'rear-grip-mount': 'Rear Grip Mount',
    'cheek-pad': 'Cheek Pad', 'stock-pad': 'Stock Pad',
}

# One entry per clip. `seed` holds the chips the reader cannot place on its own:
# names clipped past recognition, and the three "Optic" chips a riser puts in a
# row, which the label alone cannot tell apart.
CLIPS = [
    dict(key='riser', frame='S_riser.png',
         items=['multi-purpose-tactical-riser'],
         grants=['tactical-device', 'riser-optics'], occupies=[],
         seed={'tactical-device': (739, 239), 'riser-optics': (989, 226),
               'optics': (889, 226)}),
    # The micro sight riser goes in a slot the tactical riser opened, so this
    # clip has both parts on and its layout answers for both.
    dict(key='reddot', frame='S_reddot.png',
         items=['multi-purpose-tactical-riser', 'meo-micro-sight-riser'],
         grants=['tactical-device', 'riser-optics', 'red-dot-optics'],
         occupies=[],
         seed={'tactical-device': (739, 239), 'optics': (868, 226),
               'riser-optics': (976, 226), 'red-dot-optics': (1061, 226)}),
    dict(key='modular', frame='S_modular.png',
         items=['ar-modular-rear-grip'],
         grants=['rear-grip-patch'], occupies=[],
         seed={'rear-grip': (1394, 834), 'rear-grip-patch': (1608, 765)}),
    dict(key='tower', frame='S_tower.png', items=['ar-heavy-tower-grip'],
         grants=['rear-grip-mount'], occupies=[],
         seed={'rear-grip-mount': (1224, 864)}),
    dict(key='integral', frame='S_integral.png',
         items=['rm277-heavy-integral-barrel'],
         grants=['upper-rail'], occupies=['muzzle', 'rail-bipod'],
         seed={'upper-rail': (333, 351)}),
    # The clip is filed under the muzzle brake but fits an Insight 3/7, whose
    # card prints "Adds Slots: Killflash" -- which is the rule, arrived at from
    # the footage rather than from the rules file.
    dict(key='killflash', frame='S_killflash.png',
         items=['insight-3-7-sniper-scope'],
         grants=['kill-flash'], occupies=[],
         seed={'kill-flash': (670, 250), 'left-patch': (347, 342)}),
    dict(key='whale', frame='S_whale.png',
         items=['rm277-whale-shark-barrel-combo'],
         grants=['upper-rail'], occupies=['rail-bipod'],
         seed={'upper-rail': (623, 257), 'offset-optics': (1310, 250),
               'mag': (1703, 714)}),
]

# Which clip to cut each new slot's icon from: one where the slot is empty, so
# the picture is the slot's own rather than whatever is fitted in it.
ICON_FROM = {'tactical-device': 'riser', 'riser-optics': 'riser',
             'red-dot-optics': 'reddot', 'rear-grip-patch': 'modular',
             'rear-grip-mount': 'tower', 'upper-rail': 'integral',
             'kill-flash': 'killflash'}


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


def identify(text):
    """Best slot for a label, scored against the tail of each name."""
    t = norm(text)
    if not t:
        return None, 0.0
    best, score = None, 0.0
    for sid, name in NAMES.items():
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
    rr = ndimage.uniform_filter1d(g, S, axis=1, origin=-(S//2),
                                  mode='constant') * S
    cr = ndimage.uniform_filter1d(g, S, axis=0, origin=-(S//2),
                                  mode='constant') * S
    inner = ndimage.uniform_filter(g, S - 8, mode='constant')
    H, W = g.shape
    Y, X = H - S, W - S
    r = (rr[:Y, :X] + rr[S-1:S-1+Y, :X]
         + cr[:Y, :X] + cr[:Y, S-1:S-1+X]) / (4 * S)
    return r - inner[S//2:S//2+Y, S//2:S//2+X]


def snap(sc, x, y, r=12):
    H, W = sc.shape
    x0, y0 = max(0, min(x - r, W - 1)), max(0, min(y - r, H - 1))
    win = sc[y0:min(H, y + r), x0:min(W, x + r)]
    if win.size == 0:
        return x, y, -1e9
    dy, dx = np.unravel_index(win.argmax(), win.shape)
    return int(x0 + dx), int(y0 + dy), float(win.max())


def by_label(path, sc, cut=0.80, ring_floor=12.0):
    picks = {}
    for text, x, y, w, h in lines(words(path)):
        sid, r = identify(text)
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
        if win.shape[0] < S or win.shape[1] < S:
            continue
        m = match_template(win, t)
        y, x = np.unravel_index(m.argmax(), m.shape)
        if m[y, x] >= floor:
            out[sid] = (int(x0 + x), int(y0 + y))
    return out


# --- following the leader line ---------------------------------------------

def _lit(g, x, y):
    H, W = g.shape
    xi, yi = int(round(x)), int(round(y))
    if not (3 < xi < W - 4 and 3 < yi < H - 4):
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


def trace(g, cx, cy, reach=420):
    """Which way the hairline leaves this chip, and where it stops."""
    best = (0.0, None)
    for deg in np.arange(0, 360, 0.4):
        a = np.radians(deg)
        s = _run(g, cx, cy, a, S*0.62, S*0.62 + 110)
        if s > best[0]:
            best = (s, a)
    score, a = best
    if a is None or score < 0.7:
        return None
    r = S * 0.62
    while r < reach:
        if _run(g, cx, cy, a, r, r + 24) < 0.62:
            break
        r += 12
    return int(round(cx + r*np.cos(a))), int(round(cy + r*np.sin(a)))


# --- putting it together ---------------------------------------------------

def main():
    d = json.loads(DATA.read_text(encoding='utf-8'))
    base_xy = {s['slot']: (s['x'], s['y']) for s in d['slots']}
    base_anchor = {s['slot']: (s.get('ax'), s.get('ay')) for s in d['slots']}
    base_label = {s['slot']: s['label'] for s in d['slots']}

    # What the file already says, keyed the way a layout is keyed. An anchor in
    # here stays: it may have been dragged into place by hand in the editor's
    # dev mode, and a tool that silently undid that on the next run would make
    # every hand correction worthless. Only a slot with no anchor anywhere gets
    # one traced.
    was = {(tuple(l['when']), tuple(l['blocks'])): l['chips']
           for l in d.get('layouts', [])}

    layouts, icons = [], {}
    for c in CLIPS:
        path = str(FRAMES / c['frame'])
        g = np.array(Image.open(path).convert('L')).astype(float)
        sc = ring(g)
        present = [s for s in base_xy if s not in c['occupies']] + c['grants']

        got = by_label(path, sc)
        got.update(by_art(path, str(FRAMES / BASE_FRAME), got,
                          {k: v for k, v in base_xy.items()
                           if k not in c['occupies']}))
        for sid, (sx, sy) in c['seed'].items():        # hand seeds win
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
            elif base_anchor.get(sid, (None,))[0] is not None:
                ax, ay = base_anchor[sid]
            else:
                p = trace(g, x + S//2, y + S//2)
                if p is None:
                    raise SystemExit(f'{c["key"]}/{sid}: no leader line')
                ax, ay = p
                print(f'  traced {c["key"]}/{sid} -> {ax},{ay}')
            chips[sid] = dict(x=x, y=y, ax=ax, ay=ay,
                              label=NAMES.get(sid) or base_label[sid])
        layouts.append(dict(when=sorted(c['grants']),
                            blocks=sorted(c['occupies']),
                            by=c['items'], chips=chips))
        print(f'{c["key"]:<9} {len(chips)} chips, '
              f'{len(c["grants"])} opened, {len(c["occupies"])} taken')

        for sid, key in ICON_FROM.items():
            if key == c['key'] and sid in got:
                icons[sid] = (path, *got[sid])

    d['layouts'] = layouts
    DATA.write_text(json.dumps(d, indent=1), encoding='utf-8')
    print(f'wrote {len(layouts)} layouts')

    for sid, (frame, x, y) in icons.items():
        im = Image.open(frame).convert('RGB').crop(
            (x + 2, y + 2, x + S - 1, y + S - 1))
        im.resize((70, 70), Image.LANCZOS).save(ICONS / f'{sid}.png')
        print('  icon', sid)


if __name__ == '__main__':
    main()
