#!/usr/bin/env python3
"""Build the Weapon Smith site into the repo root.

Generated rather than hand-edited: the catalogue is hundreds of pages of the
same few shapes, and keeping them in step by hand is exactly the kind of drift
the data file was written to avoid. Resolving every id through the dumped data
also means a renamed item shows up as a crash here, not as stale text on a page.
"""

import sys

if sys.version_info < (3, 7):  # noqa: UP036
    raise SystemExit(
        f'needs Python 3.7 or newer, found {sys.version.split()[0]}.\n'
        'Nothing here is fancy — the version is checked up front so a missing '
        'string method does not surface as an AttributeError twenty frames in.')

import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

FITS = json.loads((ROOT / 'data/fits.json').read_text(encoding='utf-8'))
ATTACH = json.loads((ROOT / 'data/attachments.json').read_text(encoding='utf-8'))

# One catalogue name carries stray bidi and zero-width marks — invisible in the
# source, but they survive into the page and come back as mojibake the moment
# anyone copies the text out of it. Strip them once, here, rather than teach
# every consumer to cope.
INVISIBLE = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x061C, 0x2066, 0x2067, 0x2068,
     0x2069, 0xFEFF], None)


def clean(name):
    return name.translate(INVISIBLE).strip()


for _a in ATTACH:
    _a['name'] = clean(_a['name'])
NAMES = {a['id']: a['name'] for a in ATTACH}
_R = json.loads((ROOT / 'data/rules.json').read_text(encoding='utf-8'))
RULES, SLOT_TYPES = _R['rules'], _R['slots']
# Rarity and weight, read off the game's own inventory cards. The catalogue
# carries neither, so for the items it does not carry at all this is the only
# thing either page has to say about them beyond a name.
CARD_FACTS = json.loads((ROOT / 'data/card-facts.json').read_text(encoding='utf-8'))
SLOT_LABEL = {s['id']: s['label'] for s in SLOT_TYPES}
BY_ID = {a['id']: a for a in ATTACH}
BY_NAME = {a['name']: a for a in ATTACH}


def slug(name):
    """A url-safe id for an item the catalogue has no entry for."""
    out = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return out


def item_id(name):
    """The catalogue page id for an item, catalogued or merely named."""
    a = BY_NAME.get(name)
    return a['id'] if a else slug(name)


# Weapons, rounds and attachments share one flat folder, so their filenames are
# prefixed. Subfolders would read better in a URL and cost a third level of
# ../../.. in every link; this is the boring option that cannot break.
def has_art(folder, iid):
    """Is a picture actually committed for this item?

    Asked of the filesystem rather than of the data, because the 24 items the
    game catalogue does not carry have art anyway — cut out of screenshots and
    committed here. `hasArt` in the data cannot know about those.
    """
    return (ROOT / folder / (iid + '.png')).is_file()


def thumb(folder, iid, show=True):
    """A 40px card thumbnail.

    A span with a background image rather than an <img>: a missing file then
    simply leaves the empty box, where a broken <img> draws the browser's own
    torn-page glyph. With 539 of these on one page and a picture mirror that is
    always a little behind the transcripts, the failure mode is the thing worth
    designing for. Browsers defer offscreen background images, so this stays
    lazy without the intrinsic-size trap that makes loading="lazy" never fire.
    """
    if not show:
        return '<span class="thumb" aria-hidden="true"></span>'
    return (f'<span class="thumb" aria-hidden="true" '
            f'style="background-image:url(../{folder}/{iid}.png)"></span>')


def anchor(kind, value):
    """A stable id for one of the catalogue's grouping headings."""
    return f'{kind}-{slug(value)}'


def gun_file(wid):
    return f'gun-{wid}.html'


def ammo_file(aid):
    return f'ammo-{aid}.html'


def nm(i):
    if i not in NAMES:
        raise KeyError(f'unknown attachment id: {i}')
    return NAMES[i]


def stats_for(iid):
    """An item's stat lines, from whichever source has them.

    The catalogue first, card-facts.ts second. The second source is not only for
    items the catalogue lacks entirely: nineteen of the 414 are carried with an
    empty stat block, so being in the catalogue is not the same as having been
    measured, and those get filled from a card reading like anything else.
    """
    return (BY_ID.get(iid, {}).get('stats')
            or (CARD_FACTS.get(iid) or {}).get('stats')
            or {})


def is_gap(iid):
    """Is this item still short of the one thing its page is for?

    One question, asked in one place. It used to be "absent from the 414", which
    was a proxy for this and a poor one in both directions: an uncatalogued item
    can have had its stats read straight off the game, and a catalogued one can
    be carried with an empty stat block and nothing to say. Everything that
    marks a gap — the tag on a heading, the red row on a slot table, the thin
    card in the catalogue — asks here, so they cannot disagree about what counts
    as done.
    """
    return not stats_for(iid)


# Rows that are named in a transcript but absent from the catalogue, keyed by
# the slot they belong to, with the index they occupy in the dictated order.
MISSING = {
    'optics': [(0, 'White Phosphor Thermal Scope'), (1, 'Advanced Thermal Fusion Holographic Sight'),
               (2, 'VMX Frameless Sight'), (3, '1P-33 2/4x Scope'), (4, 'UHX Holographic Sight'),
               (5, 'Prism Universal 2x Optic'), (7, 'M157 Fire Control System'),
               (9, '1P-29 Russian 3x Sight'), (14, 'MEO Micro Sight Riser')],
    'riser-optics': [(0, 'Advanced Thermal Fusion Holographic Sight'), (1, 'VMX Frameless Sight'),
                     (2, 'UHX Holographic Sight'), (3, 'MEO Micro Sight Riser')],
    'red-dot-optics': [(0, 'VMX Frameless Sight')],
    'muzzle': [(0, 'RM277 Breaker Suppressor'), (1, 'Cobweb Titanium Muzzle Brake')],
    'foregrip': [(0, 'Resonant MK III Grip'), (1, 'EC Universal Front Hand Stop')],
    'barrel': [(0, 'RM277 Heavy Integral Barrel'), (1, 'RM277 Whale Shark Barrel Combo')],
    'left-rail': [(0, 'OLIGHT Warrior 3S Tactical Flashlight'), (1, 'OLIGHT Odin S Tactical Flashlight'),
                  (11, 'DD Python Handguard Panel')],
    'right-rail': [(0, 'OLIGHT Warrior 3S Tactical Flashlight'), (1, 'OLIGHT Odin S Tactical Flashlight'),
                   (11, 'DD Python Handguard Panel')],
    'left-patch': [(2, 'DD Python Handguard Panel')],
    'right-patch': [(2, 'DD Python Handguard Panel')],
    'upper-rail': [(0, 'OLIGHT Warrior 3S Tactical Flashlight'), (8, 'DD Python Handguard Panel')],
    'cheek-pad': [(0, 'RM277 Cheek Pad')],
    'stock-pad': [(0, 'RM277 Pad')],
    'rear-grip': [(0, 'AR Modular Rear Grip'), (4, 'AR MOE Rear Grip')],
    'rear-grip-patch': [(0, 'AR Light Grip Piece'), (1, 'AR Heavy Grip Piece')],
}

# What a row opens and what it occupies, by display name.
#
# Derived from the rules rather than typed out beside them. The hand-written
# version of this drifted the first time a rule was added without its label —
# the 3/7 Adjustable Scope gained a kill-flash grant and the table went on
# showing an em dash, which is the failure that does not look like one.
_SLOT_ORDER = {s['id']: i for i, s in enumerate(SLOT_TYPES)}


def _rule_name(iid, rule):
    """A rule's display name: from the catalogue, or carried on a pending rule."""
    return NAMES.get(iid) or rule.get('name') or iid


def _labels(slots):
    return ' &middot; '.join(
        SLOT_LABEL.get(x, x)
        for x in sorted(slots, key=lambda x: _SLOT_ORDER.get(x, 99)))


ADDS, BLOCKS = {}, {}
for _iid, _rule in RULES.items():
    _name = _rule_name(_iid, _rule)
    if _rule.get('grants'):
        ADDS[_name] = _labels(_rule['grants'])
    if _rule.get('conflictSlots'):
        BLOCKS[_name] = _labels(_rule['conflictSlots'])

SECTIONS = [
    ('optics', 'Optics', 'The base optic slot. The catalogue&rsquo;s other eleven optics belong to the offset slot or are sniper glass this rifle does not take.'),
    ('riser-optics', 'Riser optics', 'Opened by the Multi-Purpose Tactical Riser.'),
    ('red-dot-optics', 'Red dot optics', 'Opened by either micro sight riser, and by the 3/7 Adjustable Scope&rsquo;s own dot mount. A subset of riser optics.'),
    ('offset-optics', 'Offset optics', 'The offset twins of the five red dots.'),
    ('kill-flash', 'Kill flash', 'Opened by any of five magnified optics: the Insight 3/7 Sniper Scope, M157 Fire Control System, LPVO Scope, 3/7 Adjustable Scope and Recon 1.5/5 Adjustable Scope. One option.'),
    ('tactical-device', 'Tactical device', 'Opened by the Multi-Purpose Tactical Riser. These four also fit all three rails.'),
    ('muzzle', 'Muzzle', 'Fourteen of the catalogue&rsquo;s 37 muzzles &mdash; shotgun, pistol and AK devices are excluded.'),
    ('barrel', 'Barrel', 'Both are RM277-exclusive and absent from the catalogue. Each opens an upper rail; the integral barrel also occupies the muzzle.'),
    ('foregrip', 'Foregrip', 'Every foregrip in the catalogue fits, so this slot is not filtered.'),
    ('left-rail', 'Left rail', 'Nine lights and lasers plus the five handguard panels.'),
    ('right-rail', 'Right rail', 'The same list as the left rail.'),
    ('upper-rail', 'Upper rail', 'A shorter list than the side rails: no OLIGHT Odin S, OLIGHT Baldr Pro R or Practical Weapon Light.'),
    ('left-patch', 'Left patch', 'Handguard panels only.'),
    ('right-patch', 'Right patch', 'The same five panels.'),
    ('mag', 'Magazine', 'The RM277 is chambered in 6.8x51mm. The catalogue also holds an M7 6.8 30-Round Mag, which was not named.'),
    ('mag-mount', 'Magazine mount', ''),
    ('rear-grip', 'Rear grip', 'Two of these open further slots.'),
    ('rear-grip-patch', 'Rear grip patch', 'Opened by the AR Modular Rear Grip. Neither piece is in the catalogue, and nor is the grip that opens the slot.'),
    ('rear-grip-mount', 'Rear grip mount', 'Opened by the AR Heavy Tower Grip.'),
    ('rail-bipod', 'Rail bipod', 'One option.'),
    ('cheek-pad', 'Cheek pad', ''),
    ('stock-pad', 'Stock pad', ''),
]

def rows_for(slot):
    """Dictated order: resolved ids with the missing names spliced back in."""
    out = [nm(i) for i in FITS.get(slot, [])]
    for idx, name in MISSING.get(slot, []):
        out.insert(idx, name)
    return [(name, is_gap(item_id(name))) for name in out]


def table(slot, prefix='catalogue/'):
    body = ''
    for name, missing in rows_for(slot):
        tag = ' <span class="tag">missing info</span>' if missing else ''
        cls = ' class="is-gap"' if missing else ''
        adds = ADDS.get(name, '')
        blocks = BLOCKS.get(name, '')
        a = f'<td class="slotcell">{adds}</td>' if adds else '<td class="none">&mdash;</td>'
        b = f'<td class="cut">{blocks}</td>' if blocks else '<td class="none">&mdash;</td>'
        href = prefix + item_id(name) + '.html'
        body += (f'          <tr{cls}><td><a href="{href}">{name}</a>{tag}</td>'
                 f'{a}{b}</tr>\n')
    return ('    <div class="tablewrap">\n      <table>\n        <thead>\n'
            '          <tr><th>Attachment</th><th>Opens</th><th>Occupies</th></tr>\n'
            '        </thead>\n        <tbody>\n' + body +
            '        </tbody>\n      </table>\n    </div>\n')


def section(n, slot, title, lede, prefix='catalogue/'):
    total = len(rows_for(slot))
    head = f'  <section>\n    <h2><span class="n">{n}</span>{title} <span class="count">{total}</span></h2>\n'
    if lede:
        head += f'    <p class="lede">{lede}</p>\n'
    return head + table(slot, prefix) + '  </section>\n\n'


def weapon_sections(prefix='catalogue/'):
    """Every slot table for the weapon, plus the tree.

    Shared by the standalone weapon page and the panel folded into its
    catalogue entry, so the two can never drift. `prefix` is the only thing
    that differs: links to an item page are relative to wherever this lands.
    """
    out = [section(i, slot, title, lede, prefix)
           for i, (slot, title, lede) in enumerate(SECTIONS, 1)]
    n = len(SECTIONS) + 1
    out.append(f"""  <section>
    <h2><span class="n">{n}</span>The whole tree</h2>
    <figure>
      <div class="canvas">
        {graph()}
      </div>
      <figcaption>Solid boxes are slots the rifle always has. Outlined boxes only
      appear once the named attachment is fitted. Numbers are how many attachments
      the slot accepts.</figcaption>
    </figure>
  </section>
""")
    return '\n'.join(out)


# --------------------------------------------------------------------------
# The node graph. Root is the gun; base slots hang off it; a slot that only
# exists because an attachment opened it hangs off that attachment.
# --------------------------------------------------------------------------

ROW, GROW, TOP = 32, 42, 30
COLS = [(180, 190), (420, 215), (676, 215)]   # (x, width) per depth


SLOT_TITLE = dict({s['id']: s['label'] for s in SLOT_TYPES},
                  **{slot: title for slot, title, _ in SECTIONS})

VIA_CHARS = 34          # how much "via ..." fits in a node before it overruns


def grants_from(slot, seen):
    """The slots that open off `slot`, and what opens each.

    Read out of the rules rather than drawn by hand. The hand-drawn version of
    this had to be edited every time a grant was added, and the edit is exactly
    what gets forgotten — the tree would then keep showing a shape the data no
    longer had, which is worse than showing nothing.

    `seen` guards the walk. A slot whose list contains something that opens
    that same slot would otherwise recurse forever, and the data is free to say
    that at any point without anyone noticing until the build hangs.
    """
    out = {}
    for name, _missing in rows_for(slot):
        for g in RULES.get(item_id(name), {}).get('grants') or []:
            if g in seen:
                continue
            out.setdefault(g, []).append(name)
    return out


def via_label(names, parent):
    """Name the openers if they fit, count them if they do not."""
    joined = ', '.join(names)
    if len(joined) <= VIA_CHARS:
        return joined
    noun = SLOT_TITLE.get(parent, parent).lower()
    return f'{len(names)} {noun}' + ('' if noun.endswith('s') else 's')


def subtree(slot, seen):
    kids = []
    for g, names in grants_from(slot, seen).items():
        kids.append((via_label(names, slot), names, SLOT_TITLE.get(g, g), g,
                     subtree(g, seen | {g})))
    return kids


def graph():
    """The slot tree. A child is a slot that only exists once `via` is fitted."""
    tree = [(SLOT_TITLE.get(t['id'], t['label']), t['id'],
             subtree(t['id'], {t['id']}))
            for t in SLOT_TYPES if t['kind'] == 'base']

    parts, state = [], {'y': TOP}

    def walk(label, slot, kids, depth, via=None, names=()):
        x, w = COLS[depth]
        h = GROW if via else 22
        y = state['y']
        parts.append(node(x, y, w, h, label, len(rows_for(slot)), via, names))
        state['y'] = y + (GROW if via else ROW)
        anchor = y + h / 2
        for cvia, cnames, clabel, cslot, ckids in kids:
            cy = walk(clabel, cslot, ckids, depth + 1, cvia, cnames)
            parts.append(elbow(x + w, anchor, COLS[depth + 1][0], cy))
        return anchor

    spine = [walk(l, s, k, 0) for l, s, k in tree]
    bottom = state['y']

    mid = (spine[0] + spine[-1]) / 2
    head = [f'<line class="g-edge" x1="160" y1="{spine[0]}" x2="160" y2="{spine[-1]}"></line>']
    head += [f'<line class="g-edge" x1="160" y1="{a}" x2="{COLS[0][0]}" y2="{a}"></line>' for a in spine]
    head.append(f'<line class="g-edge" x1="140" y1="{mid}" x2="160" y2="{mid}"></line>')
    parts += [f'<rect class="g-root" x="8" y="{mid - 22}" width="132" height="44" rx="3"></rect>',
              f'<text class="g-root-t" x="74" y="{mid + 5}" text-anchor="middle">RM277</text>']

    return ('<svg viewBox="0 0 910 %d" role="img" aria-label="Slot tree for the RM277. '
            'Base slots hang off the gun; slots that only exist once an attachment is '
            'fitted hang off the slot that attachment sits in, to any depth.">\n  %s\n</svg>'
            % (bottom + 10, '\n  '.join(head + parts)))


def node(x, y, w, h, label, count, via=None, names=()):
    cls = 'g-box g-box--grant' if via else 'g-box'
    c = str(count) if count else '&mdash;'
    ty = y + (16 if via else 15)
    out = (f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="2"></rect>'
           f'<text class="g-t" x="{x + 9}" y="{ty}">{label}</text>'
           f'<text class="g-n" x="{x + w - 9}" y="{ty}" text-anchor="end">{c}</text>')
    if via:
        # The visible line is abbreviated once several attachments open the same
        # slot. The title keeps every name, so nothing is only ever a number.
        tip = ('<title>Opened by ' + '; '.join(names) + '</title>') if names else ''
        out += (f'<g>{tip}<text class="g-via" x="{x + 9}" y="{y + 32}">'
                f'via {via}</text></g>')
    return out


def elbow(x1, y1, x2, y2):
    mx = x1 + 12
    return f'<path class="g-edge" d="M {x1} {y1} L {mx} {y1} L {mx} {y2} L {x2} {y2}"></path>'


# --------------------------------------------------------------------------
# The catalogue: one page per item, plus an index of everything.
# --------------------------------------------------------------------------

CAT_LABEL = {'muzzle': 'Muzzle', 'barrel': 'Barrel', 'handguard': 'Handguard',
             'foregrip': 'Foregrip', 'rear grip': 'Rear grip', 'stock': 'Stock',
             'mag': 'Magazine', 'optic': 'Optic', 'functional': 'Functional'}


def catalogue_items():
    """Every item: the 414 from the catalogue, plus everything a transcript
    named that the catalogue does not carry. The second group is why this page
    exists — an item with no stats is still an item that fits somewhere."""
    items = {a['id']: dict(a, known=True) for a in ATTACH}
    for slot, misses in MISSING.items():
        for _, name in misses:
            sid = BY_NAME[name]['id'] if name in BY_NAME else slug(name)
            if sid not in items:
                items[sid] = {'id': sid, 'name': name, 'cat': None, 'price': None,
                              'stats': {}, 'traits': [], 'known': False}
    return items


def fits_index():
    """slot id -> the item ids it accepts, including the missing ones."""
    out = {}
    for slot, _, _ in SECTIONS:
        ids = []
        for name, _missing in rows_for(slot):
            a = BY_NAME.get(name)
            ids.append(a['id'] if a else slug(name))
        out[slot] = ids
    return out


def item_page(item, accepted_in):
    rule = RULES.get(item['id'], {})
    rows = ''
    # An item the catalogue does not carry can still have had its stat lines
    # read off the game and written into card-facts.ts. Those are the same
    # numbers in the same keys, so they render as the same table.
    stat_lines = stats_for(item['id'])
    if stat_lines:
        for k, v in stat_lines.items():
            sign = '+' if v > 0 else ''
            cls = 'up' if v > 0 else ('down' if v < 0 else '')
            rows += (f'          <tr><td>{k}</td>'
                     f'<td class="num {cls}">{sign}{v}</td></tr>\n')
        stats = ('    <div class="tablewrap">\n      <table>\n'
                 '        <thead><tr><th>Stat</th><th>Change</th></tr></thead>\n'
                 f'        <tbody>\n{rows}        </tbody>\n      </table>\n    </div>\n')
    else:
        stats = ('    <p class="lede">Not read yet. This item was named in a slot list '
                 'but is not in the game catalogue we hold, so its stat lines have to '
                 'be read off the game one at a time.</p>\n')

    facts = []
    if item['cat']:
        facts.append(('Category', CAT_LABEL.get(item['cat'], item['cat'])))
    # Rarity and weight are recorded in card-facts.ts and deliberately not shown:
    # what an attachment page is for is what fitting the thing does to the gun.
    if item['price']:
        facts.append(('Price', f"{item['price']:,}"))
    for g in rule.get('grants') or []:
        facts.append(('Opens', SLOT_LABEL.get(g, g)))
    for c in rule.get('conflictSlots') or []:
        facts.append(('Occupies', SLOT_LABEL.get(c, c)))
    for cid in rule.get('conflicts') or []:
        facts.append(('Conflicts with', BY_ID.get(cid, {}).get('name', cid)))
    fact_rows = ''.join(
        f'          <tr><td>{k}</td><td class="v">{v}</td></tr>\n' for k, v in facts)

    img = ''
    if item['known'] or has_art('att', item['id']):
        # att/ is filled by tools/sync-from-roulette.py; a page must still read
        # correctly on a checkout where the sync has not been run.
        # Every mirrored picture is a 512x256 canvas, so a square frame spent
        # half its height on nothing and showed the art at a fifth of the
        # pixels it has. The frame matches the canvas instead.
        img = (f'      <img class="shot" src="../att/{item["id"]}.png" alt="" '
               'width="280" height="140" onerror="this.remove()">\n')

    slots_html = ''
    if accepted_in:
        slots_html = ('  <section>\n    <h2>Fits</h2>\n    <div class="chips">\n'
                      + '\n'.join(
                          f'      <a class="chip" href="{gun_file(wid)}">'
                          f'{WEAPON_NAME.get(wid, wid)} &middot; {label}</a>'
                          for wid, label in accepted_in)
                      + '\n    </div>\n  </section>\n')

    # With rarity and weight gone from this table, an uncatalogued item with no
    # price and no slot rules has nothing to put in it. An empty bordered box
    # reads as a thing that failed to load, so it is simply not emitted.
    fact_table = (f'      <div class="tablewrap">\n        <table>\n'
                  f'          <tbody>\n{fact_rows}          </tbody>\n'
                  f'        </table>\n      </div>\n') if facts else ''

    body = f"""  <section class="item">
    <div class="itemgrid">
{img}{fact_table}    </div>
  </section>

  <section>
    <h2>Stats</h2>
{stats}  </section>

{slots_html}"""

    tag = ' <span class="tag">missing info</span>' if is_gap(item['id']) else ''
    return shell(f"{item['name']} &middot; Weapon Smith",
                 'Catalogue', item['name'] + tag,
                 CAT_LABEL.get(item['cat'], item['cat']) if item['cat']
                 else 'Named in a slot list.',
                 body, NAV.format(up='../', back='Weapon Smith'), '../smith.css')


def gun_page(w):
    """One weapon: what it is, and every slot on it.

    No ammunition table. The Caliber row above is a link to the catalogue group
    holding every round of that caliber, which is the same list with a page of
    its own, so printing it here as well was two places to read the same thing.
    """
    # Both facts are also how the catalogue groups things, so both are a way in
    # rather than a dead end: the class lands on every weapon of that class, the
    # caliber on every round that fits.
    facts = [('Class', f'<a href="../index.html#{anchor("class", w["cls"])}">'
                       f'{w["cls"]}</a>')]
    if w.get('caliber'):
        facts.append(('Caliber',
                      f'<a href="../index.html#{anchor("caliber", w["caliber"])}">'
                      f'{w["caliber"]}</a>'))
    rows = ''.join(f'          <tr><td>{k}</td><td class="v">{v}</td></tr>\n'
                   for k, v in facts)

    img = (f'      <img class="shot" src="../gear/{w["id"]}.png" alt="" '
           'width="280" height="140" onerror="this.remove()">\n')

    # The slot tables sit open on the page. They were behind a disclosure for a
    # while, which cost a click to reach the thing the page is actually for and
    # kept them out of the browser's find-on-page.
    if w['id'] in DOCUMENTED:
        slots = (f'''  <section class="slots">
    <h2>Attachment slots<span class="hint">{len(SECTIONS)} slots</span></h2>
    <div class="slots__body">
{weapon_sections('')}    </div>
  </section>
''')
    else:
        slots = ('  <section>\n    <h2>Attachment slots</h2>\n'
                 '    <p class="lede">Not transcribed yet. Slot lists are done '
                 'one weapon at a time.</p>\n  </section>\n')

    body = f"""  <section>
    <div class="itemgrid">
{img}      <div class="tablewrap">
        <table>
          <tbody>
{rows}          </tbody>
        </table>
      </div>
    </div>
  </section>

{slots}"""
    return shell(f"{w['name']} &middot; Weapon Smith", 'Catalogue', w['name'],
                 w['cls'], body, NAV.format(up='../', back='Weapon Smith'),
                 '../smith.css')


def ammo_page(a, guns):
    facts = [('Caliber', a['caliber'])]
    if a['pen'] is not None:
        facts.append(('Penetration', f"{a['pen']} of 7"))
    if a['price'] is not None:
        facts.append(('Price', format(a['price'], ',')))
    rows = ''.join(f'          <tr><td>{k}</td><td class="v">{v}</td></tr>\n'
                   for k, v in facts)

    img = (f'      <img class="shot" src="../ammo/{a["id"]}.png" alt="" '
           'width="280" height="140" onerror="this.remove()">\n')

    chambers = ''
    if guns:
        chambers = ('  <section>\n    <h2>Chambered by '
                    f'<span class="count">{len(guns)}</span></h2>\n'
                    '    <div class="chips">\n'
                    + '\n'.join(f'      <a class="chip" href="{gun_file(g["id"])}">'
                                 f'{g["name"]}</a>' for g in guns)
                    + '\n    </div>\n  </section>\n')

    note = ''
    if a['pen'] is None or a['price'] is None:
        note = ('  <section>\n    <p class="lede">Some fields are blank because '
                'no source publishes them for this caliber &mdash; left empty '
                'rather than invented.</p>\n  </section>\n')

    body = f"""  <section>
    <div class="itemgrid">
{img}      <div class="tablewrap">
        <table>
          <tbody>
{rows}          </tbody>
        </table>
      </div>
    </div>
  </section>

{chambers}{note}"""
    return shell(f"{a['name']} &middot; Weapon Smith", 'Catalogue', a['name'],
                 a['caliber'], body, NAV.format(up='../', back='Weapon Smith'),
                 '../smith.css')


def catalogue_browser(items, by_caliber, pages='', art=''):
    """The catalogue as a browser: pick a group on the left, see it on the right.

    Returns a body, not a page, because it is the front page now rather than a
    room off it. `pages` and `art` are how far it is from wherever it lands to
    the item pages and the picture mirrors — the same trick `weapon_sections`
    uses, and the reason one function can serve two locations without either
    copy going stale.

    One flat page of every section stacked was 593 tiles of scrolling, and the
    only way to reach the muzzles was to know roughly how far down they were.
    The groups are the same groups; what changed is that one shows at a time.

    Everything is in the page and the switching is display only, so the browser
    still finds any item with ctrl-F once its group is open, the search box
    reaches all three categories at once without a request, and a link straight
    to `#class-assault-rifle` still lands on the right group — which matters,
    because the weapon pages link into here by exactly those ids.
    """
    def tile(href, name, pic, gap=False):
        """One item: its picture, with its name laid over the bottom of it."""
        cls = 'tile tile--gap' if gap else 'tile'
        bg = (f' style="background-image:url({art}{pic})"' if pic else '')
        return (f'      <a class="{cls}" href="{pages}{href}">'
                f'<span class="tile__art"{bg}></span>'
                f'<span class="tile__name">{name}</span></a>\n')

    groups, nav = [], []

    def group(gid, title, body, count):
        groups.append(f'    <section class="group" id="{gid}" hidden>\n'
                      f'      <h2>{title} <span class="count">{count}</span></h2>\n'
                      f'      <div class="tiles">\n{body}      </div>\n'
                      '    </section>\n')

    def nav_group(label, total, links, open_=False):
        nav.append(
            f'      <details class="navgroup"{" open" if open_ else ""}>\n'
            f'        <summary>{label}<span class="count">{total}</span></summary>\n'
            f'        <div class="navgroup__list">\n{links}        </div>\n'
            '      </details>\n')

    def nav_link(gid, label, n):
        return (f'          <a class="navlink" href="#{gid}" data-group="{gid}">'
                f'{label}<em>{n}</em></a>\n')

    # --- weapons, by class ---------------------------------------------------
    by_cls = {}
    for w in WEAPONS:
        by_cls.setdefault(w['cls'], []).append(w)
    links = ''
    for cls in ['Assault Rifle', 'SMG', 'Marksman Rifle', 'Sniper Rifle',
                'Light Machinegun', 'Shotgun', 'Pistol', 'Special']:
        if cls not in by_cls:
            continue
        gid = anchor('class', cls)
        rows = sorted(by_cls[cls], key=lambda x: x['name'])
        group(gid, cls, ''.join(
            tile(gun_file(w['id']), w['name'],
                 f'gear/{w["id"]}.png' if has_art('gear', w['id']) else None)
            for w in rows), len(rows))
        links += nav_link(gid, cls, len(rows))
    nav_group('Weapons', len(WEAPONS), links, open_=True)

    # --- ammunition, by caliber ----------------------------------------------
    links = ''
    for cal in sorted(by_caliber):
        gid = anchor('caliber', cal)
        rows = sorted(by_caliber[cal], key=lambda a: a['name'])
        group(gid, cal, ''.join(
            tile(ammo_file(a['id']), a['name'],
                 f'ammo/{a["id"]}.png'
                 if (a['hasArt'] or has_art('ammo', a['id'])) else None)
            for a in rows), len(rows))
        links += nav_link(gid, cal, len(rows))
    nav_group('Ammunition', len(AMMO), links)

    # --- attachments, by type ------------------------------------------------
    # THE NINE CATEGORIES ARE NOT THE SLOTS.
    #
    # A category says what a part IS — the game files every attachment under
    # exactly these nine and no others. A slot says where one can GO, and the
    # two do not line up: a slot draws on a category or on part of one, several
    # slots share a single category (the stock cat feeds the stock, the cheek
    # pad and the stock pad), and half the slots exist only because something
    # else opened them. SLOT_TYPES is the other list; this is not it.
    #
    # Under the nine sit two more entries that are a third thing again: not what
    # a part is or where it goes, but what we still owe it. They are kept below
    # a divider so the list does not read as eleven categories, and they exist
    # because an item the catalogue never had has no category to be filed under
    # and would otherwise fall off the page.
    by_cat = {}
    for i in items.values():
        if i['known']:
            by_cat.setdefault(i['cat'], []).append(i)

    def att_tile(i):
        return tile(f'{i["id"]}.html', i['name'],
                    f'att/{i["id"]}.png'
                    if (i['known'] or has_art('att', i['id'])) else None,
                    gap=is_gap(i['id']))

    links = ''
    for cat in ['muzzle', 'barrel', 'handguard', 'foregrip', 'rear grip',
                'stock', 'mag', 'optic', 'functional']:
        if cat not in by_cat:
            continue
        gid = anchor('cat', cat)
        rows = sorted(by_cat[cat], key=lambda x: x['name'])
        group(gid, CAT_LABEL[cat], ''.join(att_tile(i) for i in rows), len(rows))
        links += nav_link(gid, CAT_LABEL[cat], len(rows))

    read_off = sorted((i for i in items.values()
                       if not i['known'] and not is_gap(i['id'])),
                      key=lambda x: x['name'])
    homeless = sorted((i for i in items.values()
                       if not i['known'] and is_gap(i['id'])),
                      key=lambda x: x['name'])
    if read_off or homeless:
        links += ('          <span class="navdiv">By status</span>\n')
    if read_off:
        group('status-read-off', 'Read off the game',
              ''.join(att_tile(i) for i in read_off), len(read_off))
        links += nav_link('status-read-off', 'Read off the game', len(read_off))
    if homeless:
        group('status-missing', 'Missing info',
              ''.join(att_tile(i) for i in homeless), len(homeless))
        links += nav_link('status-missing', 'Missing info', len(homeless))
    nav_group('Attachments', len(items), links)

    body = [f"""  <div class="browse">
    <aside class="browse__nav">
      <input class="filter" type="search" placeholder="Search everything&hellip;"
             aria-label="Search every weapon, round and attachment">
      <nav aria-label="Catalogue groups">
{''.join(nav)}      </nav>
    </aside>
    <div class="browse__main">
{''.join(groups)}      <p class="lede" id="noresults" hidden>Nothing matches that.</p>
    </div>
  </div>
"""]

    body.append("""  <script>
    const main = document.querySelector('.browse__main');
    const groups = [...main.querySelectorAll('.group')];
    const links = [...document.querySelectorAll('.navlink')];
    const q = document.querySelector('.filter');
    const empty = document.getElementById('noresults');

    // Picking a group is display only — nothing is fetched, so the back button
    // and a pasted #hash both work with no extra machinery.
    function show(id) {
      let found = false;
      for (const g of groups) { g.hidden = g.id !== id; found ||= g.id === id; }
      for (const a of links) a.classList.toggle('is-on', a.dataset.group === id);
      for (const t of main.querySelectorAll('.tile')) t.hidden = false;
      empty.hidden = true;
      // Open the sidebar section holding the chosen group, so the highlight is
      // not hidden inside a collapsed <details>.
      const on = links.find(a => a.dataset.group === id);
      if (on) on.closest('details').open = true;
      return found;
    }

    // Search reaches every group at once: the point of one box over three.
    function search(v) {
      let hits = 0;
      for (const g of groups) {
        let shown = 0;
        for (const t of g.querySelectorAll('.tile')) {
          const hit = t.textContent.toLowerCase().includes(v);
          t.hidden = !hit;
          if (hit) shown++;
        }
        g.hidden = shown === 0;
        hits += shown;
      }
      for (const a of links) a.classList.remove('is-on');
      empty.hidden = hits > 0;
    }

    q.addEventListener('input', () => {
      const v = q.value.trim().toLowerCase();
      if (v) search(v);
      else show(location.hash.slice(1) || groups[0].id);
    });

    for (const a of links) a.addEventListener('click', () => { q.value = ''; });
    addEventListener('hashchange', () => {
      q.value = '';
      show(location.hash.slice(1) || groups[0].id);
    });
    if (!show(location.hash.slice(1))) show(groups[0].id);
  </script>
""")

    return ''.join(body)
CSS = """
/* ==========================================================================
   Weapon Smith — same room as Loadout Roulette.
   Ebony ground, Spring Green accent, Alabaster text. Dark only: the sibling
   site made that call deliberately and two halves of one project should not
   disagree about what colour the floor is.
   ========================================================================== */

:root {
  color-scheme: dark;

  --bg: #060e13;
  --surface: #0e1a21;
  --surface-2: #14232c;
  --line: #1f333e;
  --line-2: #2e4756;

  --text: #fafafa;
  --text-dim: #95a8b4;
  --text-faint: #5e7381;

  --accent: #0ff796;
  --accent-dim: #0a8f57;
  --accent-rgb: 15, 247, 150;
  --red: #e04a3a;

  --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  --sans: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background:
    radial-gradient(1200px 700px at 50% -15%, #0e2a33 0%, transparent 62%),
    radial-gradient(900px 520px at 8% 28%, #0a2220 0%, transparent 60%),
    radial-gradient(900px 520px at 95% 18%, #08202a 0%, transparent 58%),
    var(--bg);
  background-attachment: fixed;
  color: var(--text);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.wrap {
  max-width: 1240px;
  margin: 0 auto;
  padding: 26px 18px 60px;
  display: flex;
  flex-direction: column;
  gap: 34px;
}

header { display: flex; flex-direction: column; gap: 8px; }
.eyebrow {
  font-family: var(--mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.22em; text-transform: uppercase; color: var(--text-faint);
}
h1 {
  margin: 0; font-size: 30px; font-weight: 800;
  letter-spacing: -0.02em; text-transform: uppercase; color: var(--text);
}
h1 .tag { text-transform: none; }
.sub { color: var(--text-dim); max-width: 62ch; margin: 0; }

section { display: flex; flex-direction: column; gap: 12px; }
h2 {
  margin: 0; font-size: 17px; font-weight: 800; letter-spacing: 0.01em;
  color: var(--accent); display: flex; align-items: baseline; gap: 10px;
  padding-bottom: 8px; border-bottom: 1px solid var(--line);
}
h2 .n {
  font-family: var(--mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; color: var(--text-faint); min-width: 20px;
}
h2 .count {
  margin-left: auto; font-family: var(--mono); font-size: 11px; font-weight: 600;
  color: var(--text-faint); font-variant-numeric: tabular-nums;
}
p { margin: 0; max-width: 78ch; }
.lede { color: var(--text-dim); font-size: 14px; }
code {
  font-family: var(--mono); font-size: 0.88em;
  background: var(--surface-2); color: var(--text-dim);
  padding: 0.1em 0.36em; border-radius: 3px;
}

.nav { font-family: var(--mono); font-size: 11px; letter-spacing: 0.06em; }
.nav a {
  color: var(--text-faint); text-decoration: none;
  border-bottom: 1px solid transparent;
}
.nav a:hover, .nav a:focus-visible { color: var(--accent); border-color: var(--accent-dim); }

.tablewrap {
  overflow-x: auto; background: var(--surface);
  border: 1px solid var(--line); border-radius: 6px;
}
table { width: 100%; border-collapse: collapse; font-size: 14px; }
thead th {
  text-align: left; font-family: var(--mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--text-faint);
  padding: 10px 14px; border-bottom: 1px solid var(--line); white-space: nowrap;
}
tbody td { padding: 8px 14px; border-bottom: 1px solid var(--line); }
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover td { background: var(--surface-2); }
td a {
  color: var(--text); text-decoration: none;
  border-bottom: 1px solid transparent;
}
td a:hover, td a:focus-visible { color: var(--accent); border-color: var(--accent-dim); }
td.slotcell { color: var(--accent); font-weight: 600; white-space: nowrap; }
td.cut { color: var(--red); font-weight: 600; white-space: nowrap; }
td.none { color: var(--text-faint); }
td.v { color: var(--accent); font-weight: 600; }
/* A link in a value cell keeps the value's colour — `td a` would repaint it as
   body text and it would stop reading as something you can click. */
td.v a { color: inherit; border-bottom: 1px solid var(--accent-dim); }
td.v a:hover, td.v a:focus-visible { border-bottom-color: var(--accent); }
.num { font-family: var(--mono); font-variant-numeric: tabular-nums; color: var(--text-dim); }
.num.up { color: var(--accent); }
.num.down { color: var(--red); }
tr.is-gap td:first-child a { color: var(--red); }

.tag {
  font-family: var(--mono); font-size: 9px; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--red); border: 1px solid currentColor; border-radius: 3px;
  padding: 2px 5px; margin-left: 8px; white-space: nowrap; vertical-align: middle;
}

.grid { display: grid; gap: 6px; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); }
.card {
  display: flex; align-items: center; gap: 10px; padding: 7px 12px; background: var(--surface); border: 1px solid var(--line);
  border-radius: 6px; color: var(--text); text-decoration: none; font-size: 14px;
}
.card > span { flex: 1 1 auto; }
.card:hover, .card:focus-visible {
  border-color: var(--accent-dim); color: var(--accent);
  box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.15);
}
.card--thin { border-style: dashed; color: var(--text-dim); }
.card--thin:hover { color: var(--red); border-color: var(--red); }
.card .thumb {
  flex: 0 0 auto; width: 40px; height: 40px; border-radius: 4px;
  background-color: var(--surface-2); background-repeat: no-repeat;
  background-position: center; background-size: contain;
  box-shadow: inset 0 0 0 1px var(--line);
}
.card em {
  font-family: var(--mono); font-size: 10px; font-style: normal;
  letter-spacing: 0.06em; color: var(--text-faint); white-space: nowrap;
}
.card[hidden], section[hidden] { display: none; }

.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  font-family: var(--mono); font-size: 11px; padding: 5px 10px;
  border: 1px solid var(--line); border-radius: 6px; color: var(--text-dim);
  text-decoration: none;
}
a.chip:hover, a.chip:focus-visible { color: var(--accent); border-color: var(--accent-dim); }

.filter {
  width: 100%; max-width: 22rem; font: inherit; font-size: 14px;
  padding: 8px 12px; color: var(--text); background: var(--surface);
  border: 1px solid var(--line); border-radius: 6px;
}
.filter::placeholder { color: var(--text-faint); }
.filter:focus-visible { outline: none; border-color: var(--accent-dim);
                        box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.25); }

a.big {
  color: var(--accent); font-weight: 600; text-decoration: none;
  border-bottom: 1px solid transparent;
}
a.big:hover, a.big:focus-visible { border-color: var(--accent-dim); }

.cls h3 {
  font-family: var(--mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent-dim);
  margin: 0 0 2px;
}
.cls p { color: var(--text-dim); font-size: 14px; }
.queue { display: flex; flex-direction: column; gap: 14px; }

.itemgrid { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }
.itemgrid .tablewrap { flex: 1 1 20rem; }
.shot {
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  object-fit: contain; padding: 10px;
}

.slots > h2 { border-bottom: 1px solid var(--line); }
.slots .hint {
  margin-left: auto; font-family: var(--mono); font-size: 11px; font-weight: 600;
  color: var(--text-faint);
}
.slots__body { display: flex; flex-direction: column; gap: 28px; }
.slots__body h2 { font-size: 15px; }

/* --------------------------------------------------------------------------
   The catalogue browser: a list of groups on the left, one group on the right.
   -------------------------------------------------------------------------- */
.browse { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 22px; align-items: start; }
.browse__nav { position: sticky; top: 16px; display: flex; flex-direction: column; gap: 10px; }
.browse__main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }

.navgroup { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }
.navgroup > summary {
  cursor: pointer; list-style: none; padding: 9px 12px;
  font-family: var(--mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent);
  display: flex; align-items: center; gap: 8px;
}
.navgroup > summary::-webkit-details-marker { display: none; }
.navgroup > summary::before {
  content: "\\25B8"; color: var(--accent-dim); font-size: 11px;
  transition: transform 120ms ease;
}
.navgroup[open] > summary::before { transform: rotate(90deg); }
.navgroup > summary:hover { background: var(--surface-2); }
.navgroup > summary .count { margin-left: auto; letter-spacing: 0.06em; }
.navgroup__list { display: flex; flex-direction: column; padding: 4px; border-top: 1px solid var(--line); }

.navlink {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 4px;
  color: var(--text-dim); text-decoration: none; font-size: 13px;
}
.navdiv {
  padding: 12px 8px 4px; font-family: var(--mono); font-size: 9px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--text-faint);
}
.navlink em {
  margin-left: auto; font-family: var(--mono); font-size: 10px; font-style: normal;
  color: var(--text-faint); font-variant-numeric: tabular-nums;
}
.navlink:hover, .navlink:focus-visible { background: var(--surface-2); color: var(--text); }
.navlink.is-on { background: rgba(var(--accent-rgb), 0.12); color: var(--accent); }
.navlink.is-on em { color: var(--accent-dim); }

.banner {
  display: block; padding: 10px 14px; border-radius: 6px; font-size: 13px;
  color: var(--text-dim); background: var(--surface);
  border: 1px solid var(--line); border-left: 3px solid var(--accent-dim);
}
.banner strong { color: var(--accent); font-weight: 700; }

.tiles { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); }
.tile {
  position: relative; display: block; aspect-ratio: 4 / 3; overflow: hidden;
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  text-decoration: none;
}
.tile--gap { border-style: dashed; }
.tile__art {
  position: absolute; inset: 0; background-repeat: no-repeat;
  background-position: center 42%; background-size: 88% auto;
}
.tile__name {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 20px 8px 7px;
  font-size: 12px; line-height: 1.25; color: var(--text);
  /* The name sits on top of the picture, so it carries its own backing rather
     than trusting whatever pixels happen to be under it. */
  background: linear-gradient(to top, var(--bg) 38%, rgba(6, 14, 19, 0.72) 68%, transparent);
}
.tile:hover, .tile:focus-visible { border-color: var(--accent-dim); }
.tile:hover .tile__name, .tile:focus-visible .tile__name { color: var(--accent); }
.tile--gap .tile__name { color: var(--red); }
.tile[hidden], .group[hidden] { display: none; }

@media (max-width: 760px) {
  .browse { grid-template-columns: 1fr; }
  .browse__nav { position: static; }
}

figure { margin: 0; display: flex; flex-direction: column; gap: 10px; }
.canvas {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 6px; padding: 18px 14px; overflow-x: auto;
}
svg { display: block; max-width: 100%; height: auto; margin: 0 auto; }
figcaption { font-size: 13px; color: var(--text-dim); max-width: 78ch; }

.g-root { fill: var(--accent); stroke: none; }
.g-root-t { font-family: var(--sans); font-weight: 800; font-size: 15px; fill: var(--bg); }
.g-box { fill: var(--surface-2); stroke: var(--line-2); stroke-width: 1; }
.g-box--grant { fill: none; stroke: var(--accent-dim); stroke-width: 1.5; }
.g-t { font-family: var(--sans); font-size: 12px; fill: var(--text); }
.g-n { font-family: var(--mono); font-size: 11px; fill: var(--text-faint); }
.g-via { font-family: var(--mono); font-size: 10px; fill: var(--text-faint); }
.g-edge { stroke: var(--line-2); stroke-width: 1; fill: none; }

:focus-visible { outline: 2px solid var(--accent-dim); outline-offset: 2px; }

@media (max-width: 34rem) {
  .wrap { padding: 20px 12px 44px; gap: 26px; }
  h1 { font-size: 24px; }
}
"""


WEAPONS = json.loads((ROOT / 'data/weapons.json').read_text(encoding='utf-8'))
AMMO = json.loads((ROOT / 'data/ammo.json').read_text(encoding='utf-8'))
WEAPON_NAME = {w['id']: w['name'] for w in WEAPONS}
DOCUMENTED = {'rm277'}
PAGES = ['catalogue/gun-rm277.html']   # documented weapons, for the sitemap
SITE = 'https://eukyrios.github.io/weapon-smith/'

NAV = ('  <nav class="nav">\n'
       '    <a href="{up}">&larr; {back}</a>\n'
       '  </nav>\n')


def banner():
    """The standing notice, on every page.

    Written from DOCUMENTED and WEAPONS rather than typed out, because the one
    thing a notice like this must never do is keep saying "one weapon" after the
    second one lands. When the count changes the sentence changes with it, and
    when every weapon is covered the notice stops printing itself.
    """
    done, total = len(DOCUMENTED), len(WEAPONS)
    if done >= total:
        return ''
    named = ', '.join(sorted(WEAPON_NAME.get(w, w) for w in DOCUMENTED))
    one = done == 1
    return (
        '  <aside class="banner">\n'
        '    <strong>Early days.</strong> This site is being written as the game '
        f'is read, and {"one" if one else done} of {total} weapons '
        f'{"has an attachment list" if one else "have attachment lists"} so far '
        f'&mdash; {"the " if one else ""}{named}. Every other weapon page carries '
        'what the catalogue knows and says so; slot lists are transcribed one gun '
        'at a time.\n  </aside>\n')


def shell(title, eyebrow, h1, sub, body, nav, css_href=None):
    """`css_href` links a shared stylesheet instead of inlining it. The
    catalogue is 439 pages; inlining 5KB of CSS into each costs 2MB of repo for
    nothing. The two hand-shared pages stay self-contained so they can be
    published or emailed on their own."""
    style = (f'<link rel="stylesheet" href="{css_href}">' if css_href
             else f'<style>{CSS}</style>')
    return '\n'.join([
        f'<title>{title}</title>',
        style,
        '',
        '<div class="wrap">',
        '',
        banner(),
        nav,
        '  <header>',
        f'    <span class="eyebrow">{eyebrow}</span>',
        f'    <h1>{h1}</h1>',
        # An empty standfirst prints nothing rather than an empty paragraph,
        # which would still take its margin and leave an unexplained gap.
        *([f'    <p class="sub">{sub}</p>'] if sub else []),
        '  </header>',
        '',
        body,
        '</div>',
        '',
    ])


def index_page(items, by_caliber):
    """The front door, which is the catalogue.

    There used to be a landing page here whose whole content was a link to the
    catalogue one level down. Nobody wants the page that offers the page: the
    first thing anyone arrives wanting is the list, so the list is what is here,
    and the extra hop is gone.
    """
    return shell(
        'Weapon Smith', 'Delta Force &middot; Operations', 'Weapon Smith', '',
        catalogue_browser(items, by_caliber, pages='catalogue/', art=''),
        NAV.format(up='https://eukyrios.github.io/loadout-roulette/',
                   back='Loadout Roulette'))


def build():
    out = ['<title>RM277 Gunsmith Schema</title>',
           f'<style>{CSS}</style>', '', '<div class="wrap">', '',
           '  <header>',
           '    <span class="eyebrow">Delta Force &middot; Operations</span>',
           '    <h1>RM277 Gunsmith Schema</h1>',
           '    <p class="sub">Which attachments fit each slot on the RM277, and which '
           'attachments open further slots of their own.</p>',
           '  </header>', '']

    for i, (slot, title, lede) in enumerate(SECTIONS, 1):
        out.append(section(i, slot, title, lede))

    n = len(SECTIONS) + 1
    out.append(f'''  <section>
    <h2><span class="n">{n}</span>The whole tree</h2>
    <figure>
      <div class="canvas">
        {graph()}
      </div>
      <figcaption>Solid boxes are slots the rifle always has. Outlined boxes only
      appear once the named attachment is fitted. Numbers are how many attachments
      the slot accepts.</figcaption>
    </figure>
  </section>
''')

    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    out = ROOT
    items = catalogue_items()
    by_caliber = {}
    for a in AMMO:
        by_caliber.setdefault(a['caliber'], []).append(a)

    (out / 'index.html').write_text(
        index_page(items, by_caliber), encoding='utf-8')

    # The weapon page used to live at the root and now folds into its catalogue
    # entry. Remove the old file rather than leave two URLs serving the same
    # tables — this tool wrote it, so this tool cleans it up.
    stale = out / 'rm277.html'
    if stale.exists():
        stale.unlink()
        print('removed stale rm277.html')

    (out / 'smith.css').write_text(CSS, encoding='utf-8')

    # Site furniture. Generated too, so a new weapon page reaches the sitemap
    # without anyone remembering to add it.
    (out / '.nojekyll').write_text('', encoding='utf-8')
    (out / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n\nSitemap: ' + SITE + 'sitemap.xml\n',
        encoding='utf-8')
    urls = [('', '1.0')] + [(w, '0.7') for w in PAGES]
    (out / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'  <url>\n    <loc>{SITE}{u}</loc>\n'
                  f'    <changefreq>weekly</changefreq>\n'
                  f'    <priority>{pr}</priority>\n  </url>\n' for u, pr in urls)
        + '</urlset>\n', encoding='utf-8')
    cat = out / 'catalogue'
    cat.mkdir(exist_ok=True)
    # Wipe before writing: a renamed item leaves its old page behind otherwise,
    # and a stale page is worse than a missing one — it is reachable, wrong,
    # and looks maintained. Everything in here is generated, so nothing is lost.
    for old in cat.glob('*.html'):
        old.unlink()
    fits = fits_index()
    # (weapon id, slot label) per item, so a chip can name both. Today every
    # slot list belongs to the RM277; when a second weapon is transcribed this
    # is where its lists join.
    accepted = {}
    for slot, ids in fits.items():
        label = next(t for s_, t, _ in SECTIONS if s_ == slot)
        for i in ids:
            accepted.setdefault(i, []).append(('rm277', label))
    guns_by_caliber = {}
    for w in WEAPONS:
        if w.get('caliber'):
            guns_by_caliber.setdefault(w['caliber'], []).append(w)

    # /catalogue/ was the catalogue's own address for a while and may be
    # bookmarked or linked. It is a signpost now rather than a 404 — the pages
    # themselves still live in this folder, only the index moved up.
    (cat / 'index.html').write_text(
        '<title>Catalogue &middot; Weapon Smith</title>\n'
        '<meta http-equiv="refresh" content="0; url=../">\n'
        '<link rel="canonical" href="' + SITE + '">\n'
        '<p>The catalogue is the front page now. '
        '<a href="../">Weapon Smith &rarr;</a></p>\n', encoding='utf-8')
    for i in items.values():
        (cat / f"{i['id']}.html").write_text(
            item_page(i, accepted.get(i['id'], [])), encoding='utf-8')
    for w in WEAPONS:
        (cat / gun_file(w['id'])).write_text(
            gun_page(w), encoding='utf-8')
    for a in AMMO:
        (cat / ammo_file(a['id'])).write_text(
            ammo_page(a, guns_by_caliber.get(a['caliber'], [])), encoding='utf-8')

    n = len(items) + len(WEAPONS) + len(AMMO) + 1
    print(f'wrote index.html and {n} catalogue pages')
