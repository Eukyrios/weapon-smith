"""Pin down the RM277 gunsmith chips and cut the artwork for the editor page.

Source: the base-slots screen recording, one frame at 2032x1080. Produces the
fifteen slot icons in smith/slot/ and the coordinates the editor lays out from.


The ring detector finds the chips but also finds a hundred other square-ish
things on a busy screen, and telling them apart automatically costs more than
the answer is worth for a single static layout. So each chip is seeded by hand
to within a few tens of pixels and then snapped to the exact local maximum of
the same ring score — hand-placed to the right object, machine-placed to the
right pixel.
"""
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

S = 73
FRAME = 'base/f006.png'

# (slot id, label as the game prints it, rough top-left in the 2032x1080 frame)
SEEDS = [
    ('optics',        'Optic',        972, 220),
    ('offset-optics', 'Offset Optic', 1240, 236),
    ('barrel',        'Barrel',        458, 292),
    ('right-patch',   'Right Patch',   566, 256),
    ('left-patch',    'Left Patch',    354, 341),
    ('right-rail',    'Right Rail',    260, 380),
    ('left-rail',     'Left Rail',     178, 480),
    ('muzzle',        'Muzzle',        168, 592),
    ('foregrip',      'Foregrip',      234, 688),
    ('rail-bipod',    'Rail Bipod',    330, 748),
    ('rear-grip',     'Rear Grip',    1306, 844),
    ('mag-mount',     'Mag Mount',    1536, 788),
    ('mag',           'Mag',          1674, 728),
    ('stock-pad',     'Stock Pad',    1816, 536),
    ('cheek-pad',     'Cheek Pad',    1680, 376),
]

im = Image.open(FRAME).convert('RGB')
g = np.array(im.convert('L')).astype(float)
H, W = g.shape

rr = ndimage.uniform_filter1d(g, S, axis=1, origin=-(S // 2), mode='constant') * S
cr = ndimage.uniform_filter1d(g, S, axis=0, origin=-(S // 2), mode='constant') * S
inner = ndimage.uniform_filter(g, S - 8, mode='constant')
Y, X = H - S, W - S
ring = (rr[:Y, :X] + rr[S - 1:S - 1 + Y, :X]
        + cr[:Y, :X] + cr[:Y, S - 1:S - 1 + X]) / (4 * S)
score = ring - inner[S // 2:S // 2 + Y, S // 2:S // 2 + X]

# Small: the label sits directly above each chip and is itself a bright thing
# on a dark ground, so a wide search happily snaps to the words instead. The
# printed `moved` column is the check that it did not.
R = 20
out = []
for sid, label, sx, sy in SEEDS:
    win = score[sy - R:sy + R, sx - R:sx + R]
    dy, dx = np.unravel_index(win.argmax(), win.shape)
    x, y = sx - R + dx, sy - R + dy
    out.append({'slot': sid, 'label': label, 'x': int(x), 'y': int(y),
                'score': round(float(score[y, x]), 1),
                'moved': int(abs(x - sx) + abs(y - sy))})

print(f'{"slot":<14} {"x":>5} {"y":>5} {"score":>6} {"moved":>6}')
for c in out:
    print(f'{c["slot"]:<14} {c["x"]:5d} {c["y"]:5d} {c["score"]:6.1f} {c["moved"]:6d}')

json.dump(out, open('chips.json', 'w'), indent=1)

sheet = Image.new('RGB', (S * 5 + 60, (S + 20) * 3 + 20), (10, 20, 26))
d = ImageDraw.Draw(sheet)
for i, c in enumerate(out):
    crop = im.crop((c['x'], c['y'], c['x'] + S, c['y'] + S))
    cx, cy = (i % 5) * (S + 12) + 10, (i // 5) * (S + 20) + 10
    sheet.paste(crop, (cx, cy))
    d.text((cx, cy + S + 3), c['label'][:13], fill=(150, 168, 180))
sheet.resize((sheet.width * 2, sheet.height * 2), Image.LANCZOS).save('chipsheet.png')
print('wrote chips.json and chipsheet.png')
