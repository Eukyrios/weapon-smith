"""Everything the AR-57's gunsmith frame has to give: chips, art, anchors.

Run against the clean recording -- bare weapon, no charm -- which is what the
second take of "gun basic" is. The first take had a barrel and a rear grip on
it for part of its length and a dragon hanging off the receiver, and both had
to be worked around; none of that is needed here.

The chips are seeded by hand to within a few tens of pixels and then snapped to
the exact local maximum of a ring score: hand-placed to the right object,
machine-placed to the right pixel. Same trick as tools/cut-gunsmith.py, which
did the RM277.

CUTTING THE RIFLE OFF THE GROUND

The first pass at this thresholded the difference from a modelled background
and opened the result with a 3x3, which is a fine way to shed speckle and a
reliable way to lose every part of a rifle thinner than three pixels. It lost
two: the rod that carries the folding stock's buttplate, which then floated
free with a gap of nothing behind it, and a long sliver of the top rail. It
also drew the line between "cyan glow" and "cool grey metal" at the wrong
place, and took the top of the buffer tube out of its own silhouette.

What replaces it measures the same thing and decides differently. The ground is
modelled per column, corrected by what the floor actually looks like just above
and below the rifle in that column, so the game's ambient glow does not read as
a cloud of not-background hanging off the pistol grip. And the decision uses
two thresholds rather than an erosion: one high enough that anything over it is
certainly the gun, one low enough that nothing of the gun falls under it, with
the low mask kept only where it joins the high one. A two-pixel rod then
survives on the strength of what it bridges, while the leader lines the game
draws across the frame are dropped for joining nothing.
"""
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

FRAME = 'base2.png'
S = 70                                   # chip side, measured on the first take
a = np.asarray(Image.open(FRAME).convert('RGB')).astype(np.float32)
H, W, _ = a.shape
g = a.mean(axis=2)

# ---- chips ---------------------------------------------------------------
def chip_score(x, y):
    if x < 0 or y < 0 or y + S >= H or x + S >= W:
        return -1e9
    b = (g[y:y+2, x:x+S].mean() + g[y+S-2:y+S, x:x+S].mean()
         + g[y:y+S, x:x+2].mean() + g[y:y+S, x+S-2:x+S].mean()) / 4
    return float(b - g[y+6:y+S-6, x+6:x+S-6].mean())

def snap(sx, sy, span=14):
    best = (-1e9, sx, sy)
    for y in range(sy - span, sy + span):
        for x in range(sx - span, sx + span):
            v = chip_score(x, y)
            if v > best[0]:
                best = (v, x, y)
    # A chip drawn over the darkest part of the ground has almost no border to
    # find, and the search wanders off to whatever it can see. Below this the
    # detector has not found anything worth trusting, so the hand-placed seed
    # stands -- which is how the base pass handled the same problem.
    if best[0] < 1:
        return (chip_score(sx, sy), sx, sy)
    return best

SEEDS = [
    ('optics',        'Optic',        1215, 238),
    ('offset-optics', 'Offset Optic', 1325, 258),
    ('right-patch',   'Right Patch',   620, 242),
    ('left-patch',    'Left Patch',    515, 260),
    ('barrel',        'Barrel',        413, 292),
    ('right-rail',    'Right Rail',    316, 337),
    ('foregrip',      'Foregrip',      226, 392),
    ('left-rail',     'Left Rail',     161, 470),
    ('muzzle',        'Muzzle',        168, 588),
    ('rail-bipod',    'Rail Bipod',    240, 665),
    # measured off its edge profile: the border is too faint to snap to
    ('stock-kit',     'Stock Kit',    1699, 455, 'pinned'),
    ('stock',         'Stock',        1707, 572),
    ('rear-grip',     'Rear Grip',    1527, 727),
]
chips = []
for seed in SEEDS:
    sid, label, sx, sy = seed[:4]
    if len(seed) > 4:
        # Drawn over the darkest part of the ground with almost no border to
        # find. Measured off its edge profile instead and left alone: the
        # detector, given the run of it, walks fourteen pixels to a brighter
        # nothing nearby.
        v, x, y = chip_score(sx, sy), sx, sy
    else:
        v, x, y = snap(sx, sy)
    chips.append({'slot': sid, 'label': label, 'x': int(x), 'y': int(y),
                  'score': round(v, 1)})
    print(f'{sid:15} ({x:4},{y:4})  score {v:5.1f}  moved {x-sx:+3},{y-sy:+3}')

# ---- the weapon ---------------------------------------------------------
# Where the gun can be at all: the middle of the frame, and never inside a
# chip. The chips are boxes of the same dark grey as the rifle, and a mask
# sensitive enough to keep a two-pixel rod is sensitive enough to keep them.
Y0, Y1, X0, X1 = 340, 830, 430, 1690
where = np.zeros((H, W), bool)
where[Y0:Y1, X0:X1] = True
for c in chips:
    where[max(0, c['y'] - 22):c['y'] + S + 5, max(0, c['x'] - 5):c['x'] + S + 5] = False

# The ambient glow the game washes under the grip is cyan; the rifle is a cool
# grey that is also, mildly, bluer than it is red. A plain difference cannot
# tell them apart -- the coldest metal on the gun runs 20 on blue minus red and
# the glow's own fringe passes through 20 on its way out -- and drawing the line
# at 20 cut the top of the buffer tube out of its own silhouette. A ratio can:
# the glow is half again as blue as it is red wherever it is bright enough to
# matter, and no part of the rifle is. The brightness floor keeps the test off
# near-black pixels, where a ratio means nothing.
glow = (a[:, :, 2] > 1.5 * a[:, :, 0] + 10) & (a.mean(axis=2) > 40)
# Each blob of the glow has a white-hot middle where the colour washes out and
# the ratio says nothing. The ratio does catch the cyan fringe all the way
# round it, so the blob is recovered as the inside of its own outline: close
# the ring, fill it, and the middle comes with it.
glow = ndimage.binary_fill_holes(
    ndimage.binary_closing(glow, np.ones((15, 15))))
neutral = ~glow

# ---- the ground ----------------------------------------------------------
# First guess, from two bands that hold nothing but ground and read above and
# below the whole rifle. Rows 250-330 look like empty sky and are not: the
# Optic and Offset Optic chips sit in them.
top, bot = np.median(a[334:356], axis=0), np.median(a[810:870], axis=0)
t = np.clip((np.arange(H, dtype=np.float32) - 345) / 495, 0, 1)[:, None, None]
bg = top[None] * (1 - t) + bot[None] * t

# A rifle-shaped guess, only good enough to say which rows of a column are
# ground. Deliberately strict: it may miss half the thin work and still bound
# the silhouette correctly.
rough = (np.abs(a - bg).sum(axis=2) > 45) & where & neutral
rough = ndimage.binary_closing(rough, np.ones((11, 11)))
lab, n = ndimage.label(rough)
if n:
    sizes = ndimage.sum(rough, lab, range(1, n + 1))
    rough = lab == (int(np.argmax(sizes)) + 1)
rough = ndimage.binary_fill_holes(rough)

# What the ground in each column actually looks like just clear of the rifle,
# as a correction on the first guess. PAD keeps the sample off the silhouette's
# own soft edge; SPAN is how much ground to average.
PAD, SPAN = 10, 26
resid = a - bg
corr = np.zeros_like(a)
cols = np.where(rough.any(axis=0))[0]
lo = np.full(W, -1); hi = np.full(W, -1)
for x in cols:
    ys = np.where(rough[:, x])[0]
    lo[x], hi[x] = ys.min(), ys.max()

def band(x, y0, y1):
    """What the ground looks like in this column between these rows.

    The glow is skipped. Under the grip the band below the rifle lands square
    on it, and a background estimate taken there says the floor is four times
    as bright as it is -- which then makes the grip's own shadow, a little
    darker than the floor, look more different from the background than the
    rifle does.
    """
    y0, y1 = max(Y0, y0), min(Y1, y1)
    if y1 <= y0:
        return np.zeros(3, np.float32)
    seg, ok = resid[y0:y1, x], ~glow[y0:y1, x]
    return np.median(seg[ok] if ok.sum() >= 4 else seg, axis=0)


above = np.zeros((W, 3), np.float32); below = np.zeros((W, 3), np.float32)
for x in cols:
    above[x] = band(x, lo[x] - PAD - SPAN, lo[x] - PAD)
    below[x] = band(x, hi[x] + PAD, hi[x] + PAD + SPAN)

yy = np.arange(H, dtype=np.float32)
for x in cols:
    y0, y1 = float(lo[x] - PAD), float(hi[x] + PAD)
    f = np.clip((yy - y0) / max(1.0, y1 - y0), 0, 1)[:, None]
    corr[:, x] = above[x][None] * (1 - f) + below[x][None] * f
bg2 = bg + corr
d = np.abs(a - bg2).sum(axis=2)

# ---- the decision --------------------------------------------------------
strong = (d > 26) & where & neutral
weak = (d > 9) & where & neutral
# A line two pixels wide fills ten of the twenty-five cells in a 5x5; a rod
# three wide fills fifteen. That is the whole difference between the game's
# leader lines and the thinnest thing on the rifle, and it is enough.
weak &= ndimage.uniform_filter(weak.astype(np.float32), 5) * 25 >= 12

lab, n = ndimage.label(weak)
keep = set(np.unique(lab[strong])) - {0}
m = np.isin(lab, list(keep))
# And only near it, so a run of leader line that happens to touch the barrel
# does not trail forty pixels of hairline off the front sight.
# And near the rifle. `rough` is deliberately strict, so it is a poor
# silhouette and an excellent bound: it says where the rifle IS, to within a
# dozen pixels, and everything the ground still contributes -- the shadow the
# grip throws on the lit floor, the hairline of a leader line -- is a hundred
# pixels away from it. Every substantial strict piece, not just the largest,
# so the buttplate across its gap bounds itself.
strict = (np.abs(a - bg2).sum(axis=2) > 45) & where & neutral
strict = ndimage.binary_closing(strict, np.ones((7, 7)))
slab, sn = ndimage.label(strict)
ssz = ndimage.sum(strict, slab, range(1, sn + 1))
strict = np.isin(slab, [i + 1 for i, sz in enumerate(ssz) if sz > 800])
near = ndimage.binary_dilation(ndimage.binary_fill_holes(strict),
                               np.ones((3, 3)), iterations=16)
m &= near
# A column of the picture holds the rifle between two heights and nothing
# above or below them. The grip throws a shadow on the lit floor a few pixels
# under its toe, and a shadow is as different from the ground as the thing
# casting it -- so it is excluded by where it is rather than by what it looks
# like. Columns the strict mask never reached keep everything: that is where
# the thin work lives, and it is already bounded by `near`.
sf = ndimage.binary_fill_holes(strict)
band = np.zeros_like(m)
for x in np.where(sf.any(axis=0))[0]:
    ys_ = np.where(sf[:, x])[0]
    band[max(0, ys_.min() - 8):ys_.max() + 9, x] = True
band[:, ~sf.any(axis=0)] = True
m &= band

m = ndimage.binary_fill_holes(ndimage.binary_closing(m, np.ones((5, 5))))
lab, n = ndimage.label(m)
sizes = ndimage.sum(m, lab, range(1, n + 1))
m = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz > 400])

# ---- the edge -------------------------------------------------------------
# A hard yes-or-no at the silhouette leaves the soft edges ragged: the top of
# the buffer tube is a thin highlight fading into the ground over three or four
# pixels, and a threshold through the middle of a fade bites lumps out of it.
# Inside stays solid -- including every hole just filled, which is the point of
# forcing it rather than letting the measurement speak there -- and the outline
# gets the measurement as a ramp, which is what the pixels were to begin with.
inside = ndimage.binary_erosion(m, np.ones((3, 3)), iterations=2)
alpha = np.clip((d - 6) / 20.0, 0, 1)
alpha = np.where(inside, 1.0, alpha)
alpha *= ndimage.binary_dilation(m, np.ones((3, 3)), iterations=2)
# The glow's outermost fringe, a few pixels of it, rides the edge of the grip
# where the sealed blob stops. Same ratio, drawn tighter, applied last: nothing
# on the rifle is a third again as blue as it is red at this brightness, and
# the coolest metal on it -- the top of the buffer tube -- is not close.
alpha[(a[:, :, 2] > 1.3 * a[:, :, 0] + 8) & (a.mean(axis=2) > 55)] = 0
# And where a blob's hot middle runs out past the sealed outline it washes to
# near-white, which no colour test can tell from metal. Nothing on the rifle
# within six pixels of the glow is bright -- the grip's rear edge is the only
# thing down there and it is nearly black -- so brightness is the test that
# works in that one neighbourhood.
alpha[ndimage.binary_dilation(glow, np.ones((3, 3)), iterations=6)
      & (a.mean(axis=2) > 72)] = 0
m = alpha > 0.02

ys, xs = np.where(m)
bx, by = int(xs.min()), int(ys.min())
bw, bh = int(xs.max()) - bx + 1, int(ys.max()) - by + 1
out = np.dstack([a.astype(np.uint8),
                 np.round(alpha * 255).astype(np.uint8)])[by:by+bh, bx:bx+bw]
Image.fromarray(out, 'RGBA').save('ar-57.png')
print(f'\ngun {int(m.sum()):,}px  box x{bx} y{by} w{bw} h{bh}')

# ---- anchors -------------------------------------------------------------
lift = (a - (top[None] * (1 - t) + bot[None] * t)).mean(axis=2)
for c in chips:
    cx, cy = c['x'] + S / 2, c['y'] + S / 2
    best = (-1e9, 0.0)
    for deg in np.arange(0, 360, 0.4):
        th = np.radians(deg)
        vs = [lift[int(round(cy + r*np.sin(th))), int(round(cx + r*np.cos(th)))]
              for r in range(S//2 + 8, S//2 + 46)
              if 0 <= cy + r*np.sin(th) < H and 0 <= cx + r*np.cos(th) < W]
        v = float(np.median(vs)) if vs else -99
        if v > best[0]:
            best = (v, deg)
    th = np.radians(best[1])
    c['ax'] = c['ay'] = None
    for r in range(S // 2 + 4, 1600):
        x, y = cx + r * np.cos(th), cy + r * np.sin(th)
        if not (0 <= x < W and 0 <= y < H):
            break
        if m[int(y), int(x)]:
            c['ax'], c['ay'] = int(round(x)), int(round(y))
            break
    print(f"{c['slot']:15} line {best[0]:5.1f} at {best[1]:6.1f}deg -> "
          f"{'(%4d,%4d)' % (c['ax'], c['ay']) if c['ax'] else 'NO HIT'}")

json.dump({'chips': chips, 'gun': {'x': bx, 'y': by, 'w': bw, 'h': bh}},
          open('extract.json', 'w'), indent=1)
im = Image.open(FRAME).convert('RGB'); d = ImageDraw.Draw(im)
for c in chips:
    d.rectangle([c['x'], c['y'], c['x']+S, c['y']+S], outline=(255, 60, 60), width=2)
    if c['ax']:
        d.line([c['x']+S/2, c['y']+S/2, c['ax'], c['ay']], fill=(0, 255, 120), width=2)
        d.ellipse([c['ax']-6, c['ay']-6, c['ax']+6, c['ay']+6], outline=(255, 230, 0), width=3)
im.resize((1440, 810)).save('check2.png')
p = Image.new('RGB', (bw, bh), (150, 40, 90))
gi = Image.fromarray(out, 'RGBA'); p.paste(gi, (0, 0), gi); p.save('ar-57-check.png')
