#!/usr/bin/env python3
"""Everything a weapon's gunsmith frame has to give: chips, art, anchors.

    python tools/cut-gunsmith-frame.py data/cut-specs/ar-57.json

Reads one frame of a gunsmith screen recording and writes three things, all in
that frame's coordinates so they cannot drift apart: where each slot chip sits,
where the leader line from each chip meets the weapon, and the weapon itself
cut out as RGBA. The art lands in smith/<weapon>.png; the coordinates are
merged into data/gunsmith-<weapon>.json, leaving everything else in that file
-- the stat block, the granted slots, the layouts, the dev-mode edits --
exactly as it was.

WHAT A SPEC HOLDS

    weapon  the id, as in weapons.json: "ar-57"
    frame   path to the still, anywhere on disk
    chip    the side of a slot chip in frame pixels
    box     [x0, y0, x1, y1], the region the weapon can be in. Not the whole
            frame: the game's own furniture -- the tab bar, the loadout strip,
            the firing-range card -- is as different from the ground as the
            rifle is, and this is what says which difference is the weapon.
    seeds   [slot, label, x, y] per chip, and optionally "pinned" as a fifth
            element for a chip whose border is too faint to snap to.
    erase   optional [x0, y0, x1, y1] rectangles of the frame that are NOT the
            weapon whatever the measurements say -- a shadow the gun throws on
            the lit floor with its own leader line running through it, which no
            test tells from a smooth panel of the gun. Hand-placed, like the
            seeds, and for the same reason.

Nothing else. The two bands of bare ground the background is first guessed
from are derived from `box`, and so is the gradient between them.

SEEDS ARE PLACED BY HAND ON PURPOSE

A ring detector finds the chips and also finds a hundred other square-ish
things on a busy screen, and telling them apart automatically costs more than
the answer is worth for a layout that is traced once per weapon. So each chip
is seeded by hand to within a few tens of pixels and then snapped to the exact
local maximum of the same ring score -- hand-placed to the right object,
machine-placed to the right pixel. Same bargain as tools/cut-gunsmith.py,
which did the RM277 before this existed.

CUTTING THE WEAPON OFF THE GROUND

Four things went wrong on the way to this, in rising order of subtlety, and
each of them is a comment further down beside the line that answers it. Read
them before changing a number.

 1. Erosion eats the rifle. A 3x3 opening sheds speckle and, with it, every
    part thinner than three pixels -- on the AR-57 that was the rod carrying
    the folding stock's buttplate, which then floated free with a gap of
    nothing behind it, and a long sliver of the top rail.

 2. Colour tests drawn too tight. Separating the game's cyan floor glow from
    cool grey metal on a plain blue-minus-red difference fails: the coldest
    metal on the gun measures the same as the glow's own fringe.

 3. A background that only varies with height. The game washes horizontal
    light bars across the floor. A vertical-gradient model says the floor
    behind the pistol grip is nearly black; the grip is nearly black; the grip
    vanishes out of the middle of its own silhouette. No threshold could have
    fixed that, because the measurement being thresholded was wrong.

 4. The mask used to hide the weapon from that reading. If it misses the gun's
    darkest faces, the model samples the grip and concludes the floor behind a
    pistol grip looks like a pistol grip -- the same hole by a different road.

CHECK THE RESULT ON ORANGE

The script writes <weapon>-on-orange.png beside the art for exactly this. The
site's ground is nearly black and so is most of a rifle, so a hole in the cut
is invisible where it will actually be seen and obvious against something
loud. A notch bitten out of the AR-57's buttplate survived three passes of
looking at it on the page and was plain the first time it was composited on
orange. Look at both: orange finds the defects, the dark ground decides which
of them matter.

LEARNED MATTING IS NOT A SHORTCUT HERE

Measured on this frame, for anyone tempted: rembg's u2net loses the whole
stock; isnet-general-use finds the whole rifle but keeps every leader line and
the slot chips and washes the alpha out to semi-transparent; birefnet-general
is 973MB and dies in an 8GB container at this resolution. They are saliency
models -- good at what the subject is, poor at which pixel exactly, which is
the entire job for a crisp asset. The useful hybrid, if a weapon ever defeats
the geometry below, is IS-Net's mask opened to shed the lines and taken as the
BOUND on this subtraction, in place of `near`.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parent.parent

if len(sys.argv) != 2:
    raise SystemExit(__doc__.strip().split('\n\n')[1].strip())
spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))

WID = spec['weapon']
S = spec['chip']
X0, Y0, X1, Y1 = spec['box']
a = np.asarray(Image.open(spec['frame']).convert('RGB')).astype(np.float32)
H, W, _ = a.shape
g = a.mean(axis=2)


# ---- chips ---------------------------------------------------------------
def chip_score(x, y):
    """How much brighter a box's border is than its middle."""
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
    # stands.
    if best[0] < 1:
        return (chip_score(sx, sy), sx, sy)
    return best


chips = []
for seed in spec['seeds']:
    sid, label, sx, sy = seed[:4]
    if len(seed) > 4:
        # Pinned: measured off its edge profile instead. Given the run of it
        # the detector walks fourteen pixels to a brighter nothing nearby.
        v, x, y = chip_score(sx, sy), sx, sy
    else:
        v, x, y = snap(sx, sy)
    chips.append({'slot': sid, 'label': label, 'x': int(x), 'y': int(y)})
    print(f'{sid:15} ({x:4},{y:4})  score {v:5.1f}  moved {x-sx:+3},{y-sy:+3}')

# ---- the weapon ----------------------------------------------------------
# Where the gun can be at all, and never inside a chip. The chips are boxes of
# the same dark grey as the rifle, and a mask sensitive enough to keep a
# two-pixel rod is sensitive enough to keep them.
where = np.zeros((H, W), bool)
where[Y0:Y1, X0:X1] = True
for c in chips:
    where[max(0, c['y'] - 22):c['y'] + S + 5,
          max(0, c['x'] - 5):c['x'] + S + 5] = False

# (2) The ambient glow the game washes under the grip is cyan; the rifle is a
# cool grey that is also, mildly, bluer than it is red. A plain difference
# cannot tell them apart -- the coldest metal runs 20 on blue minus red and the
# glow's own fringe passes through 20 on its way out -- and drawing the line at
# 20 cut the top of the AR-57's buffer tube out of its own silhouette. A ratio
# can: the glow is half again as blue as it is red wherever it is bright enough
# to matter, and no part of a weapon is. The brightness floor keeps the test
# off near-black pixels, where a ratio means nothing.
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
# pixels; a grip is ten thousand. The cap is the difference.
glow = ndimage.binary_closing(glow, np.ones((15, 15)))
_h, _n = ndimage.label(~glow)
_edge = set(np.unique(np.concatenate([_h[0], _h[-1], _h[:, 0], _h[:, -1]])))
_z = ndimage.sum(~glow, _h, range(1, _n + 1))
glow |= np.isin(_h, [i + 1 for i, v in enumerate(_z)
                     if v < 3000 and (i + 1) not in _edge])
neutral = ~glow

# ---- the ground ----------------------------------------------------------
# First guess: a vertical gradient between two bands of bare ground, one just
# above the weapon's box and one just below it. Derived from the box rather
# than written down again, because they are the same fact: the box is where
# the weapon is, so its edges are where the ground can be read. Note how tight
# the top band is -- rows further up look like empty sky and are not, since
# the optic chips sit in them.
TOP, BOT = (Y0 - 6, Y0 + 16), (Y1 - 20, Y1 + 40)
top, bot = np.median(a[TOP[0]:TOP[1]], axis=0), np.median(a[BOT[0]:BOT[1]], axis=0)
y_top, y_bot = sum(TOP) / 2, sum(BOT) / 2
t = np.clip((np.arange(H, dtype=np.float32) - y_top) / (y_bot - y_top), 0, 1)
bg = top[None] * (1 - t[:, None, None]) + bot[None] * t[:, None, None]

# (3) What the ground behind the weapon looks like, read ALONG THE ROWS.
#
# The gradient is most of the answer and not all of it: the game washes a bank
# of cyan light bars across the floor, and those run horizontally, straight
# behind the pistol grip. Reading along the row is the fix because that is the
# direction the bars run -- whatever is behind the grip continues to its left
# and to its right, where it can be seen. Every column the weapon occupies is
# dropped and what is left of each row is stretched across the gap. Where the
# weapon spans most of a row -- the barrel and receiver -- the stretch is long,
# and there the ground really is just the gradient, so a straight line between
# the two ends of it is the right answer anyway.
#
# (4) And what to leave out of that reading. NOT a strict threshold: that
# misses the darkest faces of the weapon, and a background model that samples
# the pistol grip concludes the floor behind a pistol grip looks like a pistol
# grip. Anything differing at all from the first guess is dropped, EXCEPT the
# glow -- the light bars are ground, and carrying them behind the gun is the
# whole point of reading this way.
hide = (np.abs(a - bg).sum(axis=2) > 20) & ~glow
hide = ndimage.binary_dilation(hide, np.ones((3, 3)), iterations=6)
_l, _n = ndimage.label(hide)
_z = ndimage.sum(hide, _l, range(1, _n + 1))
hide = np.isin(_l, [i + 1 for i, v in enumerate(_z) if v > 200])
for c in chips:                       # the chips are not ground either
    hide[max(0, c['y'] - 24):c['y'] + S + 6,
         max(0, c['x'] - 8):c['x'] + S + 8] = True
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
# (1) Two thresholds rather than an erosion. One high enough that anything over
# it is certainly the gun, one low enough that nothing of the gun falls under
# it, and the low mask kept only where it joins the high one -- so a two-pixel
# rod survives on the strength of what it bridges.
strong = (d > 26) & where & neutral
weak = (d > 9) & where & neutral
# The leader lines clear the low threshold everywhere, so they are refused by
# thickness instead. A line two pixels wide fills ten of the twenty-five cells
# in a 5x5; a rod three wide fills fifteen. That is the whole difference
# between the game's lines and the thinnest thing on a rifle, and it is enough.
weak &= ndimage.uniform_filter(weak.astype(np.float32), 5) * 25 >= 12

lab, n = ndimage.label(weak)
m = np.isin(lab, list(set(np.unique(lab[strong])) - {0}))
# And near the weapon. A strict pass over the corrected background is a poor
# silhouette and an excellent bound: it says where the gun IS, so a run of
# leader line that happens to touch the barrel does not trail forty pixels of
# hairline off the front sight, and what the ground still contributes -- the
# shadow a grip throws on the lit floor -- is far enough away to be dropped.
# Every substantial piece of it, not just the largest, so a buttplate across a
# gap bounds itself.
#
# Forty pixels of slack, not sixteen. A buttplate is a dark, low-contrast slab
# the strict pass barely registers, and a tight bound cut a stepped notch out
# of its lower corner.
strict = (np.abs(a - bg2).sum(axis=2) > 45) & where & neutral
strict = ndimage.binary_closing(strict, np.ones((7, 7)))
_l, _n = ndimage.label(strict)
_z = ndimage.sum(strict, _l, range(1, _n + 1))
strict = np.isin(_l, [i + 1 for i, v in enumerate(_z) if v > 800])
m &= ndimage.binary_dilation(ndimage.binary_fill_holes(strict),
                             np.ones((3, 3)), iterations=40)
# Sealing the silhouette, but NOT WHERE THE HOLE IS REALLY A HOLE. A rifle
# drawn side-on encloses real background -- magazine, receiver and pistol grip
# make a ring around the trigger guard -- and filling every hole puts a slab of
# floor inside it, visible on orange as a stair-edged wedge and on the site as
# a block behind the trigger. The holes this is FOR are the speckle the
# two-threshold pass leaves inside metal.
#
# THIS USED TO BE A SIZE CAP: fill anything under 4,000px. Size was never the
# question, only a proxy for it, and the MK47 walked straight through -- its
# trigger guard is a thousand pixels, so it was filled, and the site drew a
# block behind its trigger exactly as the MCX LT once did.
#
# The question is whether what shows through the hole is the ground. bg2 models
# the ground and is interpolated across the weapon, so it predicts a see-through
# hole well and metal badly, and the three weapons separate with room to spare:
#
#     see-through   1.3  1.4  1.5  1.9      (up to 6,519px)
#     speckle       3.0 .. 8.4              (up to 963px)
#     metal        29.7                     (the AR-57's, 1,418px)
#
# A measurement, where there was a number chosen to make one weapon come out
# right.
_filled = ndimage.binary_fill_holes(ndimage.binary_closing(m, np.ones((5, 5))))
m = ndimage.binary_closing(m, np.ones((5, 5)))
_h, _n = ndimage.label(_filled & ~m)
_dev = ndimage.mean(np.abs(a - bg2).sum(axis=2), _h, range(1, _n + 1))
m = m | np.isin(_h, [i + 1 for i, v in enumerate(_dev) if v > 2.5])
# AND A SLAB THAT LOOKS EXACTLY LIKE THE FLOOR IS THE FLOOR, even when it is
# joined to the weapon. The bound above keeps anything within forty pixels of
# the silhouette, which is what stops a buttplate being trimmed off across a
# gap -- and it also kept the shadow the MK47's magazine throws on the lit
# floor, a wedge of ground with the mag's own leader line running through it,
# hanging off the bottom of the magazine.
#
# Same measurement as the holes, one step stricter, and only on lumps: a patch
# of mask that agrees with the background model to within 8 and runs to more
# than 150px is not a soft edge, it is ground. A real fringe -- the top of a
# buffer tube fading out over three pixels -- is neither that flat nor that
# big. Checked on all three weapons: it takes the wedge and nothing else.
# AND WHAT IS LEFT, SOMEBODY POINTS AT. The MK47's magazine throws a shadow on
# the lit floor and the mag's own leader line runs through it, so a wedge of
# ground hangs off the magazine, inside the forty-pixel bound that keeps a
# buttplate attached. Three measurements were tried on it and none separates it
# from the weapon: it agrees with the background model no better than the dark
# parts of the receiver do, and its local texture (3.96) is ROUGHER than the
# buttstock's flat panel (1.81), because the leader line crosses it. A rule
# tuned to take it takes pieces of every rifle with it -- that was tested, and
# it ate a stripe of the MK47's receiver and two chunks of its stock.
#
# So it is named in the spec, the same bargain the seeds make: hand-placed to
# the right object, machine-placed to the right pixel. A rectangle written down
# in a file is a claim somebody can check against the picture; a threshold
# chosen until one weapon came out right is not.
for x0, y0, x1, y1 in spec.get('erase', []):
    m[y0:y1, x0:x1] = False

_l, _n = ndimage.label(m)
_z = ndimage.sum(m, _l, range(1, _n + 1))
m = np.isin(_l, [i + 1 for i, v in enumerate(_z) if v > 400])

# ---- the edge ------------------------------------------------------------
# A hard yes-or-no at the silhouette leaves the soft edges ragged: the top of a
# buffer tube is a thin highlight fading into the ground over three or four
# pixels, and a threshold through the middle of a fade bites lumps out of it.
# Inside stays solid -- including every hole just filled, which is the point of
# forcing it rather than letting the measurement speak there -- and the outline
# gets the measurement as a ramp, which is what those pixels were to begin with.
inside = ndimage.binary_erosion(m, np.ones((3, 3)), iterations=2)
alpha = np.where(inside, 1.0, np.clip((d - 6) / 20.0, 0, 1))
alpha *= ndimage.binary_dilation(m, np.ones((3, 3)), iterations=2)
# The glow's outermost fringe rides the edge of the grip where the sealed blob
# stops. Same ratio, drawn tighter, applied last: nothing on a weapon is a
# third again as blue as it is red at this brightness.
alpha[(a[:, :, 2] > 1.3 * a[:, :, 0] + 8) & (a.mean(axis=2) > 55)] = 0
# Where a blob's hot middle runs out past the sealed outline it washes to
# near-white, which no colour test can tell from metal. Nothing on a weapon
# within six pixels of the glow is bright -- the grip's rear edge is the only
# thing down there and it is nearly black -- so brightness is the test that
# works in that one neighbourhood.
alpha[ndimage.binary_dilation(glow, np.ones((3, 3)), iterations=6)
      & (a.mean(axis=2) > 72)] = 0
# Further out, the bars fade into a dim teal wash across the floor -- too faint
# for any ratio to call it glow, and bright enough that it does not match a
# background read from plain floor further along the row, so it came through as
# blocks of floor stuck to the grip.
#
# Dim and blue is what that wash is, and a weapon's cool greys are all BRIGHT:
# the buffer tube, the top rail, the receiver flats. But a folding stock's
# buttplate is dim and cool too, so the test cannot be let loose on the whole
# frame -- applied everywhere it chews holes in the buttplate. It is fenced to
# within fifty pixels of an actual light bar, which is where a wash from one
# can be. Measured on the AR-57: the blocks stuck to the grip are nought to
# thirteen pixels from a bar, the buttplate ninety-seven at its nearest corner.
bars = (a[:, :, 2] > 1.5 * a[:, :, 0] + 10) & (a.mean(axis=2) > 55)
_l, _n = ndimage.label(ndimage.binary_dilation(bars, np.ones((9, 9))))
_z = ndimage.sum(bars, _l, range(1, _n + 1))
lit = ndimage.binary_dilation(
    np.isin(_l, [i + 1 for i, v in enumerate(_z) if v > 400]),
    np.ones((3, 3)), iterations=25)
alpha[lit & (a[:, :, 2] - a[:, :, 0] >= 12) & (a.mean(axis=2) < 50)] = 0

# The three colour trims above work pixel by pixel and can punch a pinhole in
# the middle of the weapon -- one screw head bright enough and cool enough at
# once. A hole a couple of hundred pixels across, entirely surrounded by gun,
# is a mistake by construction: nothing that small is background, and the teal
# trim in particular nibbles a ragged line down a grip's shaded rear face.
solid = alpha > 0.02
gaps = ndimage.binary_fill_holes(solid) & ~solid
_l, _n = ndimage.label(gaps)
_z = ndimage.sum(gaps, _l, range(1, _n + 1))
alpha[np.isin(_l, [i + 1 for i, v in enumerate(_z) if v < 240])] = 1.0
m = alpha > 0.02

# And a last sweep for crumbs: the soft ramp leaves a scatter of one- and
# two-pixel islands where it clipped something that was never the weapon. A
# weapon is one piece -- buttplate included, since the rod carrying it survives
# now -- so anything not joined to the largest piece goes.
_l, _n = ndimage.label(m)
if _n > 1:
    _z = ndimage.sum(m, _l, range(1, _n + 1))
    m = _l == (int(np.argmax(_z)) + 1)
    alpha *= m

ys, xs = np.where(m)
bx, by = int(xs.min()), int(ys.min())
bw, bh = int(xs.max()) - bx + 1, int(ys.max()) - by + 1
out = np.dstack([a.astype(np.uint8),
                 np.round(alpha * 255).astype(np.uint8)])[by:by+bh, bx:bx+bw]
art = Image.fromarray(out, 'RGBA')
art.save(ROOT / f'smith/{WID}.png')
print(f'\nweapon {int(m.sum()):,}px  box x{bx} y{by} w{bw} h{bh}')

# ---- anchors -------------------------------------------------------------
# Which way each chip's leader line leaves it, then how far along that line the
# weapon is. Swept rather than guessed: the line is the brightest thing in a
# ring around the chip, and it is the only thing out there that is.
# THE LINE IS THE BRIGHTEST *THIN* THING, and thin is the word that matters.
# Sweeping raw brightness above the modelled background sounds like the same
# question and is not: bg is fitted from two bands of bare ground either side
# of the weapon, so it is only honest inside the box, and out where the chips
# live it drifts into a broad smooth ramp. The sweep then follows the ramp. On
# the MK47 that sent fourteen of fifteen chips off toward 210 degrees together
# -- not one of them at its own line, all of them downhill.
#
# A median filter of the neighbourhood subtracted off leaves what a hairline
# is and a gradient is not. Any smooth ramp cancels; a one-pixel line survives
# nearly whole, because a 7x7 median of a field containing a single thin line
# is the field without it.
lift = (a - bg).mean(axis=2)
lift = lift - ndimage.median_filter(lift, 7)

# ANOTHER CHIP'S BOX IS NOT A DIRECTION. A ray that has to cross a neighbour to
# leave is not the way the line goes, and a chip's border is far brighter than
# the hairline, so on a crowded fan two neighbours will happily point at each
# other -- which is what the MK47's Barrel and Upper Rail did, one at 2 degrees
# and the other at 183, dead at one another. Samples landing inside a DIFFERENT
# chip are dropped, and a direction with too few left over is not a direction.
#
# A chip's own box and its own label stay in. The line starts inside the box
# and the first samples along it are still within a label's height of the top;
# masking those cost the MCX LT's magazine pair their anchors, which is how the
# distinction got drawn.
owner = np.full((H, W), -1, np.int16)
for i, c in enumerate(chips):
    owner[c['y']:c['y'] + S, c['x']:c['x'] + S] = i

for n, c in enumerate(chips):
    cx, cy = c['x'] + S / 2, c['y'] + S / 2
    degs = np.arange(0, 360, 0.4)
    vals = np.full(len(degs), -99.0)
    for i, deg in enumerate(degs):
        th = np.radians(deg)
        pts = [(int(round(cy + r*np.sin(th))), int(round(cx + r*np.cos(th))))
               for r in range(S//2 + 8, S//2 + 46)
               if 0 <= cy + r*np.sin(th) < H and 0 <= cx + r*np.cos(th) < W]
        vs = [lift[y, x] for y, x in pts if owner[y, x] in (-1, n)]
        if len(vs) < 0.6 * len(pts):
            continue
        # A HIGH PERCENTILE, NOT THE MEDIAN, because not every leader line is
        # solid. The MK47's are dotted -- roughly half line, half gap -- and
        # the median of a dotted line is the gap, which is the ground, which
        # is nothing. Fourteen of its fifteen chips found no line at all while
        # the line was plainly there in the picture. The median was never
        # measuring "is there a line this way", it was measuring "is there a
        # line this way WITHOUT GAPS", and only one recording had ever been
        # asked. The 70th percentile answers the question that was meant: on a
        # solid line it is the line, on a dotted one it is still the line, and
        # on bare ground it is still bare ground.
        vals[i] = float(np.percentile(vs, 70)) if vs else -99

    # A LINE IS NARROW IN ANGLE. What is left after the background model is not
    # flat: it is interpolated row by row, so what survives streaks sideways,
    # and a ray that runs along a streak scores as well as one that runs along
    # a line. On the MK47 that put thirteen of fifteen chips at 176 degrees --
    # all of them pointing dead left, off the screen, together.
    #
    # The two are easy to tell apart by asking a different question. A leader
    # line occupies a couple of degrees and its neighbours eight degrees away
    # see nothing; a streak is broad, and eight degrees away is still on it. So
    # score a direction by how much it beats its own neighbourhood, not by how
    # bright it is. Brightness alone was never the discriminating measurement.
    off = int(round(8 / 0.4))
    rel = vals - np.maximum(np.roll(vals, off), np.roll(vals, -off))
    i = int(np.argmax(rel))
    best = (float(rel[i]), float(degs[i]))
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
missed = [c['slot'] for c in chips if c['ax'] is None]
if missed:
    raise SystemExit(f'no line found for {missed}: the chip or the cut is wrong, '
                     'not the line -- every chip on a gunsmith screen has one.')

# ---- into the weapon's file ----------------------------------------------
# Merged, never rewritten. Everything else in there was read off the game by
# hand -- the stat block, the granted slots, the layouts, the dev-mode edits --
# and re-running the cutter must not cost any of it.
path = ROOT / f'data/gunsmith-{WID}.json'
# A NEW WEAPON'S NAME COMES FROM THE CATALOGUE, not from its id. Falling back
# on the id put "mk47" in the editor's own tab where every other weapon shows
# its proper name, which is the sort of thing a default hides until the first
# time the default is used.
_named = {w['id']: w['name'] for w in
          json.loads((ROOT / 'data/weapons.json').read_text(encoding='utf-8'))}
doc = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {
    'frame': {'w': W, 'h': H}, 'slots': [],
    'weapon': {'id': WID, 'name': _named.get(WID, WID)}, 'layouts': [],
}
doc['frame'] = {'w': W, 'h': H}
doc['chip'] = S
doc['gun'] = {'src': f'{WID}.png', 'x': bx, 'y': by, 'w': bw, 'h': bh}
was = {s['slot']: s for s in doc.get('slots', [])}
# AN ANCHOR ALREADY IN THE FILE STAYS.
#
# The sweep above finds where a leader line leaves a chip and where it first
# meets the weapon, which is a good guess and not the last word: the game aims
# these at a point on the part, and on a rifle drawn side-on that point is
# often a couple of dozen pixels inside the silhouette rather than on the edge
# the sweep stops at. Five of the AR-57's were dragged into place by hand in
# the editor's dev mode. Overwriting those on the next run would make every
# hand correction worthless, and worse, would do it silently -- the file would
# still look measured. Same rule as tools/cut-gunsmith-layouts.py, which was
# written with it from the start; this one had to learn it.
#
# So a re-cut moves chips and art, and leaves anchors to whoever placed them.
# To retrace one, clear its ax/ay in the JSON first.
doc['slots'] = [
    dict(was.get(c['slot'], {}),
         **({k: v for k, v in c.items() if k not in ('ax', 'ay')}
            if was.get(c['slot'], {}).get('ax') is not None else c))
    for c in chips
]
path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')

# ---- the two pictures to look at -----------------------------------------
# On orange, because the site's ground is nearly black and so is most of a
# rifle: a hole in the cut is invisible where it will be seen and obvious
# against something loud. And the frame with the chips and lines drawn on, to
# check the coordinates against the thing they came from.
checks = ROOT / 'tools/cut-checks'
checks.mkdir(exist_ok=True)
loud = Image.new('RGBA', art.size, (255, 120, 0, 255))
loud.alpha_composite(art)
loud.convert('RGB').save(checks / f'{WID}-on-orange.png')
im = Image.open(spec['frame']).convert('RGB')
dr = ImageDraw.Draw(im)
for c in chips:
    dr.rectangle([c['x'], c['y'], c['x'] + S, c['y'] + S],
                 outline=(255, 60, 60), width=2)
    dr.line([c['x'] + S/2, c['y'] + S/2, c['ax'], c['ay']],
            fill=(0, 255, 120), width=2)
    dr.ellipse([c['ax']-6, c['ay']-6, c['ax']+6, c['ay']+6],
               outline=(255, 230, 0), width=3)
im.resize((im.width * 3 // 4, im.height * 3 // 4)).save(checks / f'{WID}-chips.png')
# Slot pictures, on the same crop convention as the layouts cutter: the chip's
# inside, without its border, resampled to 70.
_want = set(spec.get('icons', []))
if _want:
    _icons = ROOT / 'smith/slot'
    _icons.mkdir(parents=True, exist_ok=True)
    _src = Image.open(spec['frame']).convert('RGB')
    for c in chips:
        if c['slot'] in _want:
            _src.crop((c['x'] + 2, c['y'] + 2, c['x'] + S - 1, c['y'] + S - 1)) \
                .resize((70, 70), Image.LANCZOS).save(_icons / f"{c['slot']}.png")
            print(f"  icon {c['slot']}")

print(f'\nwrote smith/{WID}.png, data/gunsmith-{WID}.json, '
      f'and two checks in tools/cut-checks/')
