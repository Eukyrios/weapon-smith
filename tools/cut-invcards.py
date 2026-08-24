"""Cut item renders out of inventory cards into 512x256 RGBA art.

WHY THIS IS NOT A HAND-WRITTEN MATTE

It was one, for a while, and the history is worth keeping because it explains
the shape of the problem. `cut-cards.py`, which still handles the older and
flatter gunsmith list cards, models the panel by interpolating between the two
side margins. The inventory card defeats that: it carries a radial vignette,
dark at both margins and lighter through the middle, so a straight left-to-right
ramp fitted to it reads the whole centre of the panel as foreground and the
cutter hands back the card.

The replacement learnt the panel instead — a per-pixel median across a batch of
cards, with each card's own item masked off so the renders did not bake a ghost
into the middle — and then subtracted it. That worked, and its output is what
the first twenty-three pictures in att/ were cut with. It also never stopped
needing help: a closing radius to bridge dark facets back onto dark items, a
list of boxes describing where the card furniture sits, a floor on island size
to kill speckle, and even then it kept the soft contact shadow under a few of
the renders as a grey smear.

A segmentation model does the whole job and needs none of that. It ignores the
title bar, the star badge, the size grid and the weight without being told they
exist, it takes the shadow off, and it holds an edge better than a distance
threshold does — no dark fringe, so nothing here has to decontaminate. What is
left for this file is framing.

WHAT IT COSTS

    pip install rembg onnxruntime

and, on the first run, a model download of about 180 MB into ~/.u2net. The
pictures in att/ are committed, so this is only needed to cut new ones.
"""
import sys

if sys.version_info < (3, 7):  # noqa: UP036
    raise SystemExit(
        f'needs Python 3.7 or newer, found {sys.version.split()[0]}.')

import numpy as np
from PIL import Image
from scipy import ndimage

try:
    from rembg import new_session, remove
except ImportError:  # pragma: no cover - a missing optional dependency
    raise SystemExit(
        'this needs rembg:  pip install rembg onnxruntime\n'
        'Only for cutting new pictures — the ones in att/ are committed.')

CANVAS = (512, 256)
TARGET_H = 200
MARGIN = 32             # keep the art off the canvas edge

# isnet-general-use over the default u2net: the renders here are hard-surface
# objects with thin mounts and open frames, and it holds those better.
MODEL = 'isnet-general-use'

MIN_ISLAND = 60         # px, below which a detached blob is not part of the item
SOLID = 0.55            # alpha above which a pixel counts towards an island

# An enclosed gap this far off the panel behind it is item, not a see-through
# opening. Measured over every gap the twenty-five cards produce, the one false
# hole reads 10.7 and the genuine openings read 2.4 to 5.7, so the cut sits in
# open space rather than on top of either group.
HOLE_IS_ITEM = 8.0

_session = None


def session():
    global _session
    if _session is None:
        _session = new_session(MODEL)
    return _session


def despeckle(alpha):
    """Drop detached crumbs, keep detached parts.

    The AR grip pieces are genuinely two objects and the mount under a scope
    often reads as a third, so this cannot simply keep the largest island. It
    only removes islands too small to be any part of a render.
    """
    lab, n = ndimage.label(alpha > SOLID * 255, structure=np.ones((3, 3)))
    if n < 2:
        return alpha
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    drop = np.isin(lab, [j + 1 for j in range(n) if sizes[j] < MIN_ISLAND])
    out = alpha.copy()
    out[ndimage.binary_dilation(drop, np.ones((3, 3)))] = 0
    return out


def panel_behind(im, solid):
    """The card panel, reconstructed underneath the whole item.

    Knock the item out — its enclosed gaps included, or a gap is filled from
    its own edge and every gap then looks like panel — flood the hole from its
    nearest surviving neighbours, and blur. What comes back is the vignette the
    item is lying on, which is what a see-through opening should be showing.
    """
    out = im.copy()
    gone = ndimage.binary_dilation(ndimage.binary_fill_holes(solid), np.ones((7, 7)))
    for c in range(3):
        ch = out[..., c]
        ch[gone] = np.nan
        idx = ndimage.distance_transform_edt(
            np.isnan(ch), return_distances=False, return_indices=True)
        out[..., c] = ch[tuple(idx)]
    return ndimage.gaussian_filter(out, (12, 12, 0))


def reclaim_holes(arr, card):
    """Give back the gaps that are item rather than openings.

    Several of these renders are genuinely open — the MEO riser is a frame, the
    Resonant grip is a triangle — so enclosed gaps cannot simply be filled. But
    the model also punches through a dark textured surface now and then, and
    the AR Modular Rear Grip came back with its grip pad missing.

    The two are told apart by what is behind the gap. A real opening shows the
    card's own panel and matches a reconstruction of it closely; a gap that is
    really item does not, whatever it looks like to the eye.
    """
    solid = arr[..., 3] > SOLID * 255
    gaps = ndimage.binary_fill_holes(solid) & ~solid
    if not gaps.any():
        return arr

    im = card.astype(float)
    bg = panel_behind(im, solid)
    lab, n = ndimage.label(gaps)
    sizes = ndimage.sum(gaps, lab, range(1, n + 1))
    for j in range(n):
        if sizes[j] < MIN_ISLAND:
            continue
        m = lab == j + 1
        if np.median(np.linalg.norm(im[m] - bg[m], axis=1)) <= HOLE_IS_ITEM:
            continue                      # sees the panel: a real opening
        arr[..., 3][m] = 255
        arr[..., :3][m] = card[m]         # rembg blanks the colour it hid
    return arr


def cut(path):
    """One card in, one 512x256 RGBA canvas out, or None if nothing was found."""
    card = Image.open(path).convert('RGB')
    cut_out = remove(card, session=session()).convert('RGBA')

    arr = reclaim_holes(np.array(cut_out), np.array(card))
    arr[..., 3] = despeckle(arr[..., 3])
    ys, xs = np.where(arr[..., 3] > 20)
    if len(ys) < 200:
        return None

    crop = Image.fromarray(arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1],
                           'RGBA')
    scale = min(TARGET_H / crop.height, (CANVAS[0] - MARGIN) / crop.width)
    crop = crop.resize((max(1, round(crop.width * scale)),
                        max(1, round(crop.height * scale))), Image.LANCZOS)
    out = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
    out.paste(crop, ((CANVAS[0] - crop.width) // 2,
                     (CANVAS[1] - crop.height) // 2), crop)
    return out


def cut_all(pairs, out_dir):
    """[(card path, item id)] -> out_dir/<id>.png. Returns the ids that failed."""
    import pathlib
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = []
    for path, iid in pairs:
        art = cut(path)
        if art is None:
            failed.append(iid)
            continue
        art.save(out_dir / (iid + '.png'))
    return failed
