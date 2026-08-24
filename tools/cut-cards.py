"""Cut item renders out of gunsmith screenshots into 512x256 RGBA art.

THE PROBLEM WITH THRESHOLDING ONE COLOUR

A card looks flat and is not: it carries a vignette that is several levels
brighter across the top than down the right-hand margin. Measure one panel
colour from the margin and every threshold is then wrong somewhere — too tight
at the top, so the highlight mattes in as a grey slab; too loose in the middle,
so a dark grip dissolves.

So the panel is modelled instead of sampled. Both side margins are background
on every card here, so a per-row interpolation between them reconstructs the
vignette closely enough that the item is what is left over.

From there it is a normal matte: a trimap, a soft alpha through the uncertain
band, and colour decontamination so half-covered edge pixels do not keep the
panel's darkness and ring the item in grey.
"""
import re

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

CANVAS = (512, 256)
TARGET_H = 200

LO, HI = 7.0, 26.0      # alpha ramp, in RGB distance from the modelled panel

# Cards where the item is nearly the same value as the panel behind it. The
# matte still runs; the box just says where to look.
BOXES = {
    'ar-modular-rear-grip': (145, 34, 204, 96),
    'ar-light-grip-piece': (146, 34, 203, 94),
    'ar-heavy-grip-piece': (146, 36, 203, 92),
    # Radial vignette on this one: the left margin is lit and the right is not,
    # so interpolating between them models a straight ramp where the card has a
    # curve, and half the panel reads as foreground.
    'rm277-pad': (150, 30, 203, 100),
    # This render starts higher than the others and runs into the band the
    # title chip occupies, so the blanket chip exclusion clips its top off.
    'resonant-mk-iii-grip': (116, 27, 226, 96),
}


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def panel_model(im):
    """Reconstruct the card's own gradient from its left and right margins."""
    h, w, _ = im.shape
    m = max(4, w // 40)
    left = np.median(im[:, 2:2 + m], axis=1)
    right = np.median(im[:, w - 2 - m:w - 2], axis=1)
    # Smooth vertically: a single row of margin is noisy, the vignette is not.
    left = ndimage.uniform_filter1d(left, 9, axis=0, mode='nearest')
    right = ndimage.uniform_filter1d(right, 9, axis=0, mode='nearest')
    t = np.linspace(0, 1, w)[None, :, None]
    return left[:, None, :] * (1 - t) + right[:, None, :] * t


def frame_lines(im):
    """Rows and columns that are the selected card's white frame.

    The frame is the one thing on a card that is both very bright and spans
    almost the whole of a row or column. No render does that — a barrel laid
    across the card is long but nowhere near uniformly bright. Removing it by
    that description is steadier than any threshold on size or shape, both of
    which a long thin item also satisfies.
    """
    lum = im.mean(axis=2)
    bright = lum > 150
    rows = bright.mean(axis=1) > 0.6
    cols = bright.mean(axis=0) > 0.6
    return ndimage.binary_dilation(rows, np.ones(3)), \
        ndimage.binary_dilation(cols, np.ones(3))


def item_mask(dist, h, w, inset, frame=None):
    """Largest island of confidently-not-panel, minus the chip and the frame."""
    core = dist > HI
    if frame is not None:
        core[frame[0], :] = False
        core[:, frame[1]] = False
    core[:int(h * 0.26)] = False
    core[:inset] = core[-inset:] = False
    core[:, :inset] = core[:, -inset:] = False
    core = ndimage.binary_opening(core, np.ones((2, 2)))

    lab, n = ndimage.label(core, structure=np.ones((3, 3)))
    if n == 0:
        return None
    sizes = ndimage.sum(core, lab, range(1, n + 1))
    keep = lab == (np.argmax(sizes) + 1)
    # Pull in the uncertain band that touches the item, and only that band:
    # this is what keeps thin edges and antennae without re-admitting the frame.
    grown = ndimage.binary_dilation(keep, np.ones((3, 3)), iterations=4)
    keep = keep | (grown & (dist > LO))

    # Re-apply the exclusions: growing into the uncertain band is what recovers
    # thin edges, and it is also what reaches back up into the title chip and
    # out to the frame. Cutting them again afterwards, then taking the largest
    # island once more, keeps the edges without the furniture.
    if frame is not None:
        keep[frame[0], :] = False
        keep[:, frame[1]] = False
    keep[:int(h * 0.26)] = False
    keep[:inset] = keep[-inset:] = False
    keep[:, :inset] = keep[:, -inset:] = False
    lab, n = ndimage.label(keep, structure=np.ones((3, 3)))
    if n == 0:
        return None
    sizes = ndimage.sum(keep, lab, range(1, n + 1))
    return ndimage.binary_fill_holes(lab == (np.argmax(sizes) + 1))


def matte(im, box=None):
    h, w, _ = im.shape
    bg = panel_model(im)
    dist = np.linalg.norm(im - bg, axis=2)

    if box:
        fr = frame_lines(im)
        dist[fr[0], :] = 0
        dist[:, fr[1]] = 0
        x0, y0, x1, y1 = box
        region = np.zeros((h, w), bool)
        region[y0:y1, x0:x1] = True
        keep = region & (dist > LO)
        keep = ndimage.binary_closing(keep, np.ones((3, 3)))
        lab, n = ndimage.label(keep, structure=np.ones((3, 3)))
        if n:
            sizes = ndimage.sum(keep, lab, range(1, n + 1))
            big = np.argsort(sizes)[::-1][:2] + 1     # grip pieces come in pairs
            keep = np.isin(lab, big[sizes[big - 1] > sizes.max() * 0.15])
        keep = ndimage.binary_fill_holes(keep)
    else:
        frame = frame_lines(im)
        keep = item_mask(dist, h, w, 5, frame)
        if keep is None:
            return None

    if keep.sum() < 120:
        return None

    alpha = np.clip((dist - LO) / (HI - LO), 0, 1) * keep
    alpha = np.array(Image.fromarray((alpha * 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(0.6))) / 255.0

    # Decontaminate: an edge pixel is part item, part panel. Solving for the
    # item's own colour is what stops every silhouette wearing a dark rim.
    a = alpha[..., None]
    fg = np.where(a > 0.06, (im - (1 - a) * bg) / np.maximum(a, 0.06), im)
    fg = np.clip(fg, 0, 255)

    ys, xs = np.where(alpha > 0.12)
    if len(ys) < 60:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    rgba = np.dstack([fg, alpha * 255])[y0:y1 + 1, x0:x1 + 1]

    crop = Image.fromarray(rgba.astype(np.uint8), 'RGBA')
    scale = TARGET_H / crop.height
    if crop.width * scale > CANVAS[0] - 32:
        scale = (CANVAS[0] - 32) / crop.width
    crop = crop.resize((max(1, round(crop.width * scale)),
                        max(1, round(crop.height * scale))), Image.LANCZOS)
    out = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
    out.paste(crop, ((CANVAS[0] - crop.width) // 2,
                     (CANVAS[1] - crop.height) // 2), crop)
    return out


def cut(card, key=None):
    return matte(np.array(card.convert('RGB')).astype(float), BOXES.get(key))


def cards(path, n):
    im = Image.open(path)
    step = im.height / n
    return [im.crop((0, round(i * step), im.width, round((i + 1) * step)))
            for i in range(n)]
