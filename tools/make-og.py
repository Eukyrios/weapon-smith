#!/usr/bin/env python3
"""Draw og.png, the 1200x630 card every link preview of this site shows.

WHY THIS IS A SCRIPT AND NOT A FILE SOMEONE MADE ONCE

The card states the size of the catalogue — "66 weapons, 89 rounds, 438
attachments" — and that is data, not decoration. Drawn by hand it is correct on
the day it is exported and silently wrong every day after, in the one place
nobody looks: a preview rendered on somebody else's website. Generated from the
same JSON the pages are built from, it cannot say a number the site does not.

The mark comes from the same SVG the favicon does, rasterised rather than
redrawn, so there is one anvil in this repo and not two that drift apart.

    python tools/make-og.py

Needs Pillow and cairosvg. The committed og.png means nobody has to run it to
build the site — only to change what it says.
"""
import sys

if sys.version_info < (3, 7):  # noqa: UP036
    raise SystemExit(
        f'needs Python 3.7 or newer, found {sys.version.split()[0]}.')

import io
import json
import pathlib
import re

try:
    import cairosvg
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    raise SystemExit('this needs Pillow and cairosvg:  pip install pillow cairosvg')

ROOT = pathlib.Path(__file__).resolve().parent.parent

W, H = 1200, 630
BG = (6, 14, 19)
TEXT = (250, 250, 250)
DIM = (149, 168, 180)
FAINT = (94, 115, 129)
ACCENT = (15, 247, 150)

PAD = 88
RULE = 8            # the accent bar along the bottom

FONTS = {
    'title': ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 96),
    'lede': ('/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf', 38),
    'mono': ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 24),
}

STRAPLINE = ('A library of every gun, round and attachment '
             '— and a build maker on top of it.')


def font(kind):
    path, size = FONTS[kind]
    if not pathlib.Path(path).is_file():
        raise SystemExit(f'missing font: {path}')
    return ImageFont.truetype(path, size)


def counts():
    """The three numbers, from the data the site itself is built from.

    The attachment figure is the catalogue plus the items a slot list names
    that the catalogue does not carry -- the site gives every one of those a
    page, so the card has to count them or the two disagree in public.

    THIS USED TO READ THE SECOND GROUP BY REGEX out of gen-weapon-smith.py,
    scraping the names out of a MISSING = {...} block. That block was moved
    into data/uncatalogued.json a while ago, and because the regex simply found
    nothing it added nothing and said nothing: the card went on rendering, one
    item short for every uncatalogued part added since. Eleven of them, by the
    time anyone looked at the picture. It is the exact failure this file's own
    header warns about -- wrong in the one place nobody looks -- committed by
    the script written to prevent it.

    So it reads the file, and if a file it needs is missing it stops rather
    than quietly drawing a smaller number.
    """
    def data(n):
        p = ROOT / 'data' / f'{n}.json'
        if not p.is_file():
            raise SystemExit(f'{p.relative_to(ROOT)} is not there; run '
                             '`npm run gen` before drawing the card.')
        return json.loads(p.read_text(encoding='utf-8'))

    weapons, ammo = data('weapons'), data('ammo')
    attach, extra = data('attachments'), data('uncatalogued')
    both = {a['id'] for a in attach} & set(extra)
    if both:
        raise SystemExit('counted twice, catalogued and not: '
                         + ', '.join(sorted(both)))
    return len(weapons), len(ammo), len(attach) + len(extra)


def mark(px):
    """The anvil, rasterised from the favicon so there is only ever one of it."""
    svg = (ROOT / 'favicon.svg').read_text(encoding='utf-8')
    # The favicon sits on its own rounded plate; the card supplies the ground,
    # so drop the plate and keep the mark.
    svg = re.sub(r'<rect[^>]*/>', '', svg, count=1)
    png = cairosvg.svg2png(bytestring=svg.encode('utf-8'),
                           output_width=px, output_height=px)
    return Image.open(io.BytesIO(png)).convert('RGBA')


def wrap(draw, text, fnt, width):
    lines, line = [], ''
    for word in text.split():
        trial = f'{line} {word}'.strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def spaced(draw, xy, text, fnt, fill, tracking):
    """Letter-spaced text. Pillow has no tracking, and the eyebrow and the
    counts row are both set wide enough that faking it is the whole look."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def build():
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)

    # A faint lift towards the top left, the same move the site's own body
    # background makes, so the card looks like it came off the page.
    glow = Image.new('RGB', (W, H), (14, 42, 51))
    grad = Image.new('L', (W, H))
    gd = ImageDraw.Draw(grad)
    for i in range(60):
        gd.ellipse([-500 + i * 6, -700 + i * 8, 1100 - i * 6, 700 - i * 8],
                   fill=int(46 * (1 - i / 60)))
    # Stacked ellipses leave a visible arc where the outermost one ends. Blur
    # the mask, not the image: the text is drawn after this and stays crisp.
    grad = grad.filter(ImageFilter.GaussianBlur(90))
    im = Image.composite(glow, im, grad)
    d = ImageDraw.Draw(im)

    logo = mark(64)
    im.paste(logo, (PAD, 78), logo)
    spaced(d, (PAD + 92, 92), 'DELTA FORCE / OPERATIONS', font('mono'), FAINT, 5.0)

    d.text((PAD - 4, 208), 'WEAPON SMITH', font=font('title'), fill=TEXT)

    y = 370
    lede = font('lede')
    for line in wrap(d, STRAPLINE, lede, W - PAD * 2):
        d.text((PAD, y), line, font=lede, fill=DIM)
        y += 52

    w, a, t = counts()
    x = PAD
    for label in (f'{w} WEAPONS', f'{a} ROUNDS', f'{t} ATTACHMENTS'):
        x = spaced(d, (x, y + 24), label, font('mono'), ACCENT, 2.0) + 44

    d.rectangle([0, H - RULE, W, H], fill=ACCENT)

    out = ROOT / 'og.png'
    im.save(out, optimize=True)
    print(f'wrote {out.name}  {W}x{H}  {out.stat().st_size // 1024} KB'
          f'  ({w} weapons, {a} rounds, {t} attachments)')


if __name__ == '__main__':
    build()
