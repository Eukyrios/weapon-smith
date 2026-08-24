"""Matte a single item render out of a full-screen inspect video frame.

Different problem from the card cutter: the background is a large, smooth,
slowly-varying gradient rather than a flat panel, and the item sits in the
middle of it. So the background is estimated by heavily blurring the frame with
the item's rough location knocked out, which reconstructs the gradient
underneath it, and the matte is the difference.
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

CANVAS = (1024, 512)


def cut(path, top_crop=0.05):
    im = np.array(Image.open(path).convert('RGB')).astype(float)
    h, w, _ = im.shape
    im = im[int(h * top_crop):]          # drop the HUD strip along the top
    h = im.shape[0]

    # Rough item: anything well away from the frame's median colour.
    med = np.median(im.reshape(-1, 3), axis=0)
    rough = np.linalg.norm(im - med, axis=2) > 34
    rough = ndimage.binary_dilation(rough, np.ones((9, 9)))

    # Rebuild the gradient behind it: fill the item's area with the local
    # background before blurring, or the blur smears the item into its own
    # background estimate.
    filled = im.copy()
    for c in range(3):
        ch = filled[..., c]
        ch[rough] = np.nan
        idx = ndimage.distance_transform_edt(np.isnan(ch), return_distances=False,
                                             return_indices=True)
        filled[..., c] = ch[tuple(idx)]
    bg = np.array(Image.fromarray(filled.astype(np.uint8))
                  .filter(ImageFilter.GaussianBlur(25))).astype(float)

    dist = np.linalg.norm(im - bg, axis=2)
    core = dist > 26
    lab, n = ndimage.label(ndimage.binary_opening(core, np.ones((3, 3))),
                           structure=np.ones((3, 3)))
    sizes = ndimage.sum(core, lab, range(1, n + 1))
    keep = lab == (np.argmax(sizes) + 1)
    keep = ndimage.binary_fill_holes(
        ndimage.binary_dilation(keep, np.ones((3, 3)), iterations=3) & (dist > 9))

    alpha = np.clip((dist - 9) / 22, 0, 1) * keep
    alpha = np.array(Image.fromarray((alpha * 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    a = alpha[..., None]
    fg = np.clip(np.where(a > 0.06, (im - (1 - a) * bg) / np.maximum(a, 0.06), im),
                 0, 255)

    ys, xs = np.where(alpha > 0.12)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = Image.fromarray(
        np.dstack([fg, alpha * 255])[y0:y1 + 1, x0:x1 + 1].astype(np.uint8), 'RGBA')

    scale = min((CANVAS[1] - 40) / crop.height, (CANVAS[0] - 40) / crop.width)
    crop = crop.resize((round(crop.width * scale), round(crop.height * scale)),
                       Image.LANCZOS)
    out = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
    out.paste(crop, ((CANVAS[0] - crop.width) // 2,
                     (CANVAS[1] - crop.height) // 2), crop)
    return out
