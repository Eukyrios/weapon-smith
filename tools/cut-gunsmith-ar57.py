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

Three things went wrong with the first pass at this, and they pull in different
directions.

It ATE THE RIFLE: a 3x3 opening shed speckle and, with it, the rod carrying the
folding stock's buttplate -- which then floated free with a gap of nothing
behind it -- and a long sliver of the top rail. So the decision is made with
two thresholds instead of an erosion now. One high enough that anything over it
is certainly the gun, one low enough that nothing of the gun falls under it,
and the low mask kept only where it joins the high one. A two-pixel rod
survives on the strength of what it bridges; the leader lines the game draws
across the frame are dropped for joining nothing.

It CUT THE BUFFER TUBE out of its own silhouette, because the test separating
the game's cyan floor glow from the rifle was a plain blue-minus-red difference
drawn at 20, and the coldest metal on this gun measures 20. A ratio separates
them properly, and the glow's washed-out white middles are recovered by sealing
each blob inside its own cyan outline.

And it LOST THE PISTOL GRIP into the floor. That one is the deepest. The
background was modelled as a single vertical gradient, but the game washes a
bank of cyan light bars across the floor and those run horizontally, straight
behind the grip. A model that only varies with height says the floor there is
nearly black; the grip is nearly black; so the grip stopped differing from the
background and vanished out of the middle of its own silhouette. No threshold
could have fixed that, because the measurement being thresholded was wrong.

The ground is therefore read ALONG THE ROWS, which is the direction the light
bars run: drop every column the rifle occupies and stretch what is left of each
row across the gap. Whatever is behind the grip continues to its left and its
right, where it can be seen. The one trap is what counts as "the rifle" for
that purpose -- a mask that misses the grip's dark face lets the model sample
the grip and conclude the floor behind a pistol grip looks like a pistol grip,
which is the same hole by a different road -- so anything differing at all from
the first guess is dropped, except the glow, which is ground and has to stay.
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
# the ring and fill it, and the middle comes with it.
#
# Only small holes, though. There are blobs behind the pistol grip as well as
# beside it, and closing the ring around THOSE encloses the grip -- fill that
# and the glow mask swallows the front half of it, which is what took a bite
# out of the grip's leading edge. A blob's washed-out middle is a thousand
# pixels; the grip is ten thousand. The cap is the difference.
glow = ndimage.binary_closing(glow, np.ones((15, 15)))
_h, _n = ndimage.label(~glow)
_edge = set(np.unique(np.concatenate([_h[0], _h[-1], _h[:, 0], _h[:, -1]])))
_sz = ndimage.sum(~glow, _h, range(1, _n + 1))
glow |= np.isin(_h, [i + 1 for i, z in enumerate(_sz)
                     if z < 3000 and (i + 1) not in _edge])
neutral = ~glow

# ---- the ground ----------------------------------------------------------
# First guess, from two bands that hold nothing but ground and read above and
# below the whole rifle. Rows 250-330 look like empty sky and are not: the
# Optic and Offset Optic chips sit in them.
top, bot = np.median(a[334:356], axis=0), np.median(a[810:870], axis=0)
t = np.clip((np.arange(H, dtype=np.float32) - 345) / 495, 0, 1)[:, None, None]
bg = top[None] * (1 - t) + bot[None] * t

# What the ground behind the rifle looks like, read along the rows.
#
# The vertical gradient is most of the answer and not all of it: the game
# washes a bank of cyan light bars across the floor, and those run
# horizontally, straight behind the pistol grip. A model that only varies with
# height says the floor there is nearly black. The grip is nearly black. So the
# grip stopped differing from the background and disappeared out of the middle
# of its own silhouette -- a hole no threshold could have fixed, because the
# measurement being thresholded was wrong.
#
# Reading along the row fixes it, because that is the direction the light bars
# run: whatever is behind the grip continues to its left and to its right,
# where it can be seen. Every column of the rifle is dropped, and what is left
# of each row is stretched across the gap. Where the rifle spans most of a row
# -- the barrel and receiver -- the stretch is long, and there the ground
# really is just the gradient, so a straight line between the two ends of it is
# the right answer anyway.
# What to leave out of the reading. Not the strict guess -- that misses the
# darkest parts of the rifle, and a background model that samples the pistol
# grip concludes the floor behind the grip looks like a pistol grip, which is
# the same hole by a different road. Anything that differs at all from the
# first guess is dropped, EXCEPT the glow: the light bars are ground, and the
# whole point of reading along the row is to carry them behind the gun.
hide = (np.abs(a - bg).sum(axis=2) > 20) & ~glow
hide = ndimage.binary_dilation(hide, np.ones((3, 3)), iterations=6)
_l, _n = ndimage.label(hide)
_z = ndimage.sum(hide, _l, range(1, _n + 1))
hide = np.isin(_l, [i + 1 for i, v in enumerate(_z) if v > 200])
for c in chips:                       # the chips are not ground either
    hide[max(0, c['y'] - 24):c['y'] + S + 6, max(0, c['x'] - 8):c['x'] + S + 8] = True
resid, corr = a - bg, np.zeros_like(a)
xs_all = np.arange(W, dtype=np.float32)
for y in range(H):
    ok = np.where(~hide[y])[0]
    if len(ok) < 2:
        continue
    for ch in range(3):
        corr[y, :, ch] = np.interp(xs_all, ok.astype(np.float32), resid[y, ok, ch])
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
# And near the rifle. A strict pass over the corrected background is a poor
# silhouette and an excellent bound: it says where the rifle IS to within a
# dozen pixels, so a run of leader line that happens to touch the barrel does
# not trail forty pixels of hairline off the front sight, and what the ground
# still contributes -- the shadow the grip throws on the lit floor -- is far
# enough away to be dropped. Every substantial piece of it, not just the
# largest, so the buttplate across its gap bounds itself.
strict = (np.abs(a - bg2).sum(axis=2) > 45) & where & neutral
strict = ndimage.binary_closing(strict, np.ones((7, 7)))
slab, sn = ndimage.label(strict)
ssz = ndimage.sum(strict, slab, range(1, sn + 1))
strict = np.isin(slab, [i + 1 for i, sz in enumerate(ssz) if sz > 800])
near = ndimage.binary_dilation(ndimage.binary_fill_holes(strict),
                               np.ones((3, 3)), iterations=16)
m &= near
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
# The two colour trims above work pixel by pixel and can punch a pinhole in the
# middle of the rifle -- one screw head bright enough and cool enough at once.
# A hole a few dozen pixels across, entirely surrounded by gun, is a mistake by
# construction: nothing that small is background.
solid = alpha > 0.02
gaps = ndimage.binary_fill_holes(solid) & ~solid
_l, _n = ndimage.label(gaps)
_z = ndimage.sum(gaps, _l, range(1, _n + 1))
alpha[np.isin(_l, [i + 1 for i, v in enumerate(_z) if v < 80])] = 1.0

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
