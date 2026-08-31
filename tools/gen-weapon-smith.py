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

import hashlib, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Every page sits at the root, so nothing has to climb out of a folder to reach
# an asset or another page. One name rather than a hundred literals of '../',
# so a move back down a level stays one line rather than a hunt.
UP = ''
# Where "back" goes. UP is a prefix for reaching a sibling of the index; on its
# own it is the empty string, and an empty href is not the index — it is the
# page you are already on. The back link on every one of 594 pages was a
# reload, which looks like a link that does nothing rather than a broken one,
# and reads as the site being stuck.
HOME = UP or './'

# What the last run wrote, so this one can take away what it no longer writes
# without reaching for anything it did not put there. See the end of the run.
MANIFEST = ROOT / 'data/generated-pages.txt'

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
# The items somebody sat down with the game and read. A card prints every line
# the part moves, so for these an unlisted stat is unchanged rather than
# unread — which is the opposite of what an empty column means everywhere else,
# and the only reason the distinction is worth keeping.
#
# The test is the presence of the key, not a value in it: an item read and
# found to move nothing is `stats: {}`, and that is a finding, not a blank.
# `read: true` says the same for an item whose catalogue stat block was already
# right, where restating it would only duplicate a number to record a look.
CLEARED = {iid for iid, f in CARD_FACTS.items()
           if 'stats' in f or f.get('read')}
# Stats where a smaller number is the better one. Only gunshot range so far,
# and it only started mattering when the first suppressor reading landed: until
# then nothing on record moved it, so it was not a dimension anybody sorted on.
LOWER_IS_BETTER = {'Gunshot heard'}
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
            f'style="background-image:url({UP}{folder}/{iid}.png)"></span>')


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
    """An item's stat lines, from both sources, the read one winning.

    The card-facts reading is laid over the catalogue's rather than chosen
    instead of it. The two sources do not carry the same columns: the import has
    control and handling for nearly everything and muzzle velocity, gunshot
    range and fire rate for nothing at all, while the game's own card prints all
    of them. A suppressor is the case that forces this — the catalogue knows it
    costs handling, and only the card knows it is the thing that makes the shot
    quieter, which is the entire reason anyone fits one.

    Either-or lost that. It also had a quieter fault: it read as a fallback for
    items the catalogue lacks, which was true only because nothing had been read
    for an item the catalogue already covered. Where both speak, the card is the
    better witness — somebody looked at it — so it goes on top, key by key.
    """
    return {**BY_ID.get(iid, {}).get('stats', {}),
            **(CARD_FACTS.get(iid) or {}).get('stats', {})}


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
    return iid not in CLEARED and not stats_for(iid)


# The two halves of a card, and the two different silences about them.
#
# The catalogue import carries these five columns and no others. So a blank in
# one of them means the item's stat block was never filled in, while a blank in
# damage or fire rate means only that this source has never carried such a
# thing for anybody — a different fact, needing a different word, and until now
# both were told the same way.
CORE_STATS = {'Range', 'Control', 'Handling', 'Stability', 'Accuracy'}


def needs_info(iid):
    """Are this item's base stats unread? The #missing-info tag.

    Range, control, handling, stability, accuracy — the five the catalogue is
    supposed to carry. Missing here means somebody has to go and read them.
    """
    return iid not in CLEARED and not (set(stats_for(iid)) & CORE_STATS)


def needs_extra(iid):
    """Are this item's further stats unread? The #not-tracked tag.

    Damage, armour penetration, fire rate, muzzle velocity, gunshot range. No
    import has ever carried these for anything; they come off the game's own
    card or not at all, so the only thing that answers this is somebody having
    sat down and read one. That is what CLEARED records.

    Which makes this the larger of the two gaps by a long way, and the honest
    number: nearly every item in the catalogue has a full set of base stats and
    nothing at all below them.
    """
    return iid not in CLEARED


def needs_art(iid):
    """Is this item drawn with somebody else's picture? The #image-change tag.

    The odd one out in here: not a gap in what the record says but in what it
    shows. It earns a tag for the same reason the other two do — it is a debt
    somebody pays by going and looking at the game, and a list of those is
    worth being able to pull up.
    """
    return bool((CARD_FACTS.get(iid) or {}).get('imageChange'))


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
    'barrel': [(0, 'RM277 Whale Shark Barrel Combo'), (1, 'RM277 Heavy Integral Barrel')],
    # No Warrior 3S: dictated onto this list and not on it. Dropping it moves
    # the Python up one, because these indices are positions in the list as it
    # is being built, not in the finished one.
    'left-rail': [(0, 'OLIGHT Odin S Tactical Flashlight'),
                  (10, 'DD Python Handguard Panel')],
    # The Odin S is on this rail after all, above the Baldr as it is on the
    # left. The Warrior 3S is here and not on the left, so the two lists still
    # differ -- in the other direction from how they used to.
    'right-rail': [(0, 'OLIGHT Warrior 3S Tactical Flashlight'),
                   (1, 'OLIGHT Odin S Tactical Flashlight'),
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
    ('kill-flash', 'Killflash', 'Opened by any of five magnified optics: the Insight 3/7 Sniper Scope, M157 Fire Control System, LPVO Scope, 3/7 Adjustable Scope and Recon 1.5/5 Adjustable Scope. One option.'),
    ('tactical-device', 'Tactical device', 'Opened by the Multi-Purpose Tactical Riser. These four also fit all three rails.'),
    ('muzzle', 'Muzzle', 'Fourteen of the catalogue&rsquo;s 37 muzzles &mdash; shotgun, pistol and AK devices are excluded.'),
    ('barrel', 'Barrel', 'Both are RM277-exclusive and absent from the catalogue. Each opens an upper rail; the integral barrel also occupies the muzzle.'),
    ('foregrip', 'Foregrip', 'Every foregrip in the catalogue fits, so this slot is not filtered.'),
    ('left-rail', 'Left rail', 'Nine lights and lasers plus the five handguard panels.'),
    ('right-rail', 'Right rail', 'The left rail&rsquo;s list less the OLIGHT Odin S, which fits the left side only.'),
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

# Deliberate departures from the derived lists, recorded by the editor's dev
# mode and written into the weapon's own file.
#
# A delta rather than a frozen copy of the lists. The whole point of deriving
# them is that a rule added tomorrow reaches every weapon at once, and a copy
# would quietly stop doing that. What is in here is a claim that the derivation
# is wrong for this weapon in this one place — which is a thing worth seeing on
# its own in a diff, rather than buried in four hundred unchanged rows.
EDITS = json.loads(
    (ROOT / 'data/gunsmith-rm277.json').read_text(encoding='utf-8')
).get('edits') or {}
_SLOT_EDITS = EDITS.get('slots') or {}
_FIT_EDITS = EDITS.get('fits') or {}

SECTIONS = [s for s in SECTIONS if s[0] not in set(_SLOT_EDITS.get('remove', []))]
for _sid in _SLOT_EDITS.get('add', []):
    if _sid not in {s[0] for s in SECTIONS}:
        SECTIONS.append((_sid, SLOT_LABEL.get(_sid, _sid), ''))


def rows_for(slot):
    """Dictated order: resolved ids with the missing names spliced back in,
    then whatever the dev mode says this weapon does or does not take."""
    out = [nm(i) for i in FITS.get(slot, [])]
    for idx, name in MISSING.get(slot, []):
        out.insert(idx, name)
    e = _FIT_EDITS.get(slot) or {}
    if e:
        drop = set(e.get('remove', []))
        out = [n for n in out if item_id(n) not in drop]
        for iid in e.get('add', []):
            name = NAMES.get(iid) or iid
            if name not in out:
                out.append(name)
    return [(name, needs_info(item_id(name)), needs_extra(item_id(name)))
            for name in out]


def is_finished(wid):
    """Has this weapon been read to the end?

    Not the same question as DOCUMENTED, which only says somebody has started:
    a gun can have every slot listed and still owe a stat line on half of them.
    Finished means every row of every slot is answered — no base stats missing,
    nothing below them unread.

    SECTIONS is the RM277's slot list, so this is only honest for the weapon
    those sections belong to. When a second gunsmith is traced this has to take
    the weapon's own sections, and the assert below is what will say so.
    """
    if wid not in DOCUMENTED:
        return False
    if DOCUMENTED != {'rm277'}:
        raise SystemExit('is_finished: SECTIONS is one weapon\'s; make it take '
                         'the weapon before documenting a second')
    return all(not missing and not unread
               for slot, _, _ in SECTIONS
               for _n, missing, unread in rows_for(slot))


def table(slot, prefix=UP):
    body = ''
    for name, missing, unread in rows_for(slot):
        tag = (' <span class="tag">#missing-info</span>' if missing else '')
        tag += (' <span class="tag tag--soft">#not-tracked</span>'
                if unread else '')
        tag += (' <span class="tag tag--soft">#image-change</span>'
                if needs_art(item_id(name)) else '')
        cls = ' class="is-gap"' if missing else ''
        adds = ADDS.get(name, '')
        blocks = BLOCKS.get(name, '')
        a = f'<td class="slotcell">{adds}</td>' if adds else '<td class="none">&mdash;</td>'
        b = f'<td class="cut">{blocks}</td>' if blocks else '<td class="none">&mdash;</td>'
        href = prefix + item_id(name) + '.html'
        body += (f'          <tr{cls} data-item="{item_id(name)}">'
                 f'<td><a href="{href}">{name}</a>{tag}</td>'
                 f'{a}{b}</tr>\n')
    return ('    <div class="tablewrap">\n      <table>\n        <thead>\n'
            '          <tr><th>Attachment</th><th>Opens</th><th>Occupies</th></tr>\n'
            '        </thead>\n        <tbody>\n' + body +
            '        </tbody>\n      </table>\n    </div>\n')


def section(n, slot, title, lede, prefix=UP):
    total = len(rows_for(slot))
    head = (f'  <section id="slot-{slot}">\n    <h2><span class="n">{n}</span>'
            f'{title} <span class="count">{total}</span></h2>\n')
    if lede:
        head += f'    <p class="lede">{lede}</p>\n'
    return head + table(slot, prefix) + '  </section>\n\n'


def weapon_sections(prefix=UP):
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
    for name, _m, _x in rows_for(slot):
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
    """The slot tree. A child is a slot that only exists once `via` is fitted.

    Rooted in the slots THIS weapon has, not in every slot type the game knows
    about. SLOT_TYPES is the vocabulary shared by every gun in the catalogue, so
    walking it drew a handguard, a stock and a functional slot on a rifle that
    has none of the three — each with a dash where the count should be, which is
    the tell nobody reads as a bug because a dash looks like an answer.
    """
    mine = {slot for slot, _, _ in SECTIONS}
    tree = [(SLOT_TITLE.get(t['id'], t['label']), t['id'],
             subtree(t['id'], {t['id']}))
            for t in SLOT_TYPES if t['kind'] == 'base' and t['id'] in mine]

    parts, state = [], {'y': TOP}

    drawn = set()

    def walk(label, slot, kids, depth, via=None, names=()):
        drawn.add(slot)
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

    # Every slot the weapon has, and nothing else. The tree is derived, so it
    # cannot go stale — but it can go wrong in the other direction, by drawing
    # from the wrong list or by losing a granted slot whose only opener was
    # removed, and neither shows up as anything but a picture that looks fine.
    if drawn != mine:
        raise SystemExit(
            f'tree: draws {sorted(drawn - mine)}, misses {sorted(mine - drawn)}')

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


# The four slots with no catalogued member of their own: the RM277's two
# barrels, both pads and the rear grip patch. Every other slot has catalogued
# items in it, and those are better evidence than anything typed here — so the
# category of an uncatalogued item is read off its slot-mates below and only
# falls back to this list where there are none. Note the panels: the game files
# a handguard panel under Functional, not Handguard, which is exactly the sort
# of thing a hand-written map gets wrong.
SLOT_CAT_FALLBACK = {'barrel': 'barrel', 'cheek-pad': 'stock',
                     'stock-pad': 'stock', 'rear-grip-patch': 'rear grip'}


def slot_category(slot):
    """What an item in this slot is, judged by the catalogued items beside it.

    A slot whose members disagree stops the build rather than picking one: it
    would mean the slot draws on two categories, and then filing an
    uncatalogued row by its slot is the wrong idea rather than a wrong answer.
    """
    cats = {BY_ID[i]['cat'] for i in FITS.get(slot, []) if i in BY_ID}
    if len(cats) > 1:
        raise SystemExit(f'{slot}: catalogued members span {sorted(cats)}')
    return cats.pop() if cats else SLOT_CAT_FALLBACK[slot]


def catalogue_items():
    """Every item: the 414 from the catalogue, plus everything a transcript
    named that the catalogue does not carry. The second group is why this page
    exists — an item with no stats is still an item that fits somewhere.

    The uncatalogued ones get a category too, so they file under Optic or
    Muzzle with everything else rather than into a bin of their own. What they
    are and what we still owe them are two different facts; the second is a
    search tag now, not a category.
    """
    items = {a['id']: dict(a, known=True) for a in ATTACH}
    for slot, misses in MISSING.items():
        cat = slot_category(slot)
        for _, name in misses:
            sid = BY_NAME[name]['id'] if name in BY_NAME else slug(name)
            if sid not in items:
                items[sid] = {'id': sid, 'name': name, 'cat': cat, 'price': None,
                              'stats': {}, 'traits': [], 'known': False}
            elif not items[sid]['known'] and items[sid]['cat'] != cat:
                raise SystemExit(f'{name}: {items[sid]["cat"]} here, {cat} in {slot}')
    return items


def fits_index():
    """slot id -> the item ids it accepts, including the missing ones."""
    out = {}
    for slot, _, _ in SECTIONS:
        ids = []
        for name, _m, _x in rows_for(slot):
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
    elif item['id'] in CLEARED:
        # Read, and it moves nothing. That is a finding, and it has to read as
        # one: the sentence below it would otherwise say nobody has looked, at
        # the one item somebody has looked at hardest.
        stats = ('    <p class="lede">Nothing. This one was read off the game '
                 'and changes no stat on the weapon &mdash; not an empty record, '
                 'an empty answer.</p>\n')
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
        img = (f'      <img class="shot" src="{UP}att/{item["id"]}.png" alt="" '
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

    tag = (' <span class="tag">#missing-info</span>'
           if needs_info(item['id']) else '')
    tag += (' <span class="tag tag--soft">#not-tracked</span>'
            if needs_extra(item['id']) else '')
    tag += (' <span class="tag tag--soft">#image-change</span>'
            if needs_art(item['id']) else '')
    kind = CAT_LABEL.get(item['cat'], item['cat']) if item['cat'] else ''
    # The description says what this page can answer. An item whose stats are
    # not read yet says that instead of implying numbers it does not have.
    desc = f"{item['name']} &mdash; "
    desc += f'{kind.lower()} attachment ' if kind else 'attachment '
    desc += 'for Delta Force: Operations. '
    desc += ('Every stat line it changes. ' if stat_lines
             else 'Its stat lines are not read off the game yet. ')
    n = len(accepted_in)
    if n:
        slots = 'one weapon slot' if n == 1 else f'{n} weapon slots'
        desc += f'Fits {slots}.'
    return shell(f"{item['name']} &middot; Weapon Smith",
                 'Catalogue', item['name'] + tag,
                 kind if kind else 'Named in a slot list.',
                 body, NAV.format(up=HOME, back='Weapon Smith'), UP + 'smith.css',
                 desc=desc, path=f"{item['id']}.html",
                 crumb=item['name'])


def gun_page(w):
    """One weapon: what it is, and every slot on it.

    No ammunition table. The Caliber row above is a link to the catalogue group
    holding every round of that caliber, which is the same list with a page of
    its own, so printing it here as well was two places to read the same thing.
    """
    # Both facts are also how the catalogue groups things, so both are a way in
    # rather than a dead end: the class lands on every weapon of that class, the
    # caliber on every round that fits.
    facts = [('Class', f'<a href="{UP}index.html#{anchor("class", w["cls"])}">'
                       f'{w["cls"]}</a>')]
    if w.get('caliber'):
        facts.append(('Caliber',
                      f'<a href="{UP}index.html#{anchor("caliber", w["caliber"])}">'
                      f'{w["caliber"]}</a>'))
    # The standfirst carries them. It already said the class; now it says the
    # class and the caliber, and both are the way into the catalogue. A table
    # drew a bordered box around four words and repeated what was directly
    # above it.
    sub = ' &middot; '.join(v for _k, v in facts)

    smith = ''
    if w['id'] in GUNSMITHS:
        smith = gunsmith_body()
        # The stage shows the weapon at full size; a thumbnail above it as well
        # would be the same picture twice.
        img = ''
    else:
        img = (f'      <img class="shot" src="{UP}gear/{w["id"]}.png" alt="" '
               'width="280" height="140" onerror="this.remove()">\n')

    # Folded away again. It was opened out when the tables were the whole page;
    # now the editor above answers most of what they answer and is what anyone
    # arrives for. Opened, they read exactly as before — same rows_for(), same
    # order — and the chips link straight into them.
    if w['id'] in DOCUMENTED:
        slots = (f'''  <details class="deploy" id="tables">
    <summary>Attachment slots<span class="hint">{len(SECTIONS)} slots &middot; every attachment listed</span></summary>
    <div class="deploy__body">
{weapon_sections('')}    </div>
  </details>
''')
    else:
        slots = ('  <section>\n    <h2>Attachment slots</h2>\n'
                 '    <p class="lede">Not transcribed yet. Slot lists are done '
                 'one weapon at a time.</p>\n  </section>\n')

    head = ('' if not img else
            f'  <section>\n    <div class="itemgrid">\n{img}    </div>\n  </section>\n')

    body = f"""{head}
{smith}
{slots}"""
    cal = f" chambered in {w['caliber']}" if w.get('caliber') else ''
    if w['id'] in DOCUMENTED:
        desc = (f"{w['name']} &mdash; {w['cls'].lower()}{cal} in Delta Force: "
                f'Operations. All {len(SECTIONS)} attachment slots and every '
                'attachment that fits each one.')
    else:
        desc = (f"{w['name']} &mdash; {w['cls'].lower()}{cal} in Delta Force: "
                'Operations. Its slot list is not transcribed yet; the '
                'catalogue holds the attachments it will draw from.')
    return shell(f"{w['name']} &middot; Weapon Smith", 'Catalogue', w['name'],
                 sub, body, NAV.format(up=HOME, back='Weapon Smith'),
                 UP + 'smith.css',
                 desc=desc, path=gun_file(w['id']),
                 crumb=w['name'])


def ammo_page(a, guns):
    facts = [('Caliber', a['caliber'])]
    if a['pen'] is not None:
        facts.append(('Penetration', f"{a['pen']} of 7"))
    if a['price'] is not None:
        facts.append(('Price', format(a['price'], ',')))
    rows = ''.join(f'          <tr><td>{k}</td><td class="v">{v}</td></tr>\n'
                   for k, v in facts)

    img = (f'      <img class="shot" src="{UP}ammo/{a["id"]}.png" alt="" '
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
    pen = f", penetration {a['pen']} of 7" if a['pen'] is not None else ''
    desc = (f"{a['name']} &mdash; {a['caliber']} round for Delta Force: "
            f'Operations{pen}. ')
    n = len(guns)
    desc += (f"The {'one weapon' if n == 1 else str(n) + ' weapons'} that "
             f"chamber{'s' if n == 1 else ''} it." if guns
             else 'No weapon in the catalogue chambers it yet.')
    return shell(f"{a['name']} &middot; Weapon Smith", 'Catalogue', a['name'],
                 a['caliber'], body, NAV.format(up=HOME, back='Weapon Smith'),
                 UP + 'smith.css',
                 desc=desc, path=ammo_file(a['id']),
                 crumb=a['name'])


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
    def tile(href, name, pic, gap=False, tags=(), done=False):
        """One item: its picture, with its name laid over the bottom of it.

        `tags` are what the search box's #words match on. They are not printed:
        a tile is 96px wide and the tag is a property of the record rather than
        of the thing, so it lives in the markup and surfaces when asked for.

        `done` is the exception, and it is printed. A finished gun is the one
        thing about this catalogue a reader wants to see at a glance rather
        than have to ask for, because for now it is the difference between a
        page that answers questions and a page that lists names.
        """
        cls = 'tile tile--gap' if gap else 'tile'
        bg = (f' style="background-image:url({art}{pic})"' if pic else '')
        tg = f' data-tags="{" ".join(tags)}"' if tags else ''
        mark = ('<span class="tile__done" title="Read to the end">&#10003;</span>'
                if done else '')
        return (f'      <a class="{cls}" href="{pages}{href}"{tg}>'
                f'<span class="tile__art"{bg}></span>{mark}'
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

    def tag_link(tag, label, n):
        """A status is not a group any more, so its link runs the search.

        Written as the tag itself rather than as prose, because the point is
        that the reader can then type it: the link and the thing you type into
        the box are the same six characters.
        """
        return (f'          <a class="navlink navlink--tag" href="#{tag}" '
                f'data-tag="{tag}" title="{label}">'
                f'<code>#{tag}</code><em>{n}</em></a>\n')

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
                 f'gear/{w["id"]}.png' if has_art('gear', w['id']) else None,
                 tags=('complete',) if is_finished(w['id']) else (),
                 done=is_finished(w['id']))
            for w in rows), len(rows))
        links += nav_link(gid, cls, len(rows))
    n_done = sum(1 for w in WEAPONS if is_finished(w['id']))
    if n_done:
        links += '          <span class="navdiv">By tag</span>\n'
        links += tag_link('complete', 'Every slot listed and every attachment '
                                      'read', n_done)
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
    # Nine categories and nine only. What we still owe an item — its stats not
    # read yet, or its whole record coming off the game's cards rather than the
    # catalogue — used to sit here as two more entries, which read as eleven
    # categories and hid two dozen items from the category they belong to. It
    # is a tag now: every item files under Optic or Muzzle with the rest, and
    # #missing-info in the search box gathers the other axis.
    by_cat = {}
    for i in items.values():
        by_cat.setdefault(i['cat'], []).append(i)

    def item_tags(i):
        """The facts that are about the record rather than about the part.

        Two of them, because they are two different debts. #missing-info is the
        rare one and the urgent one: the five base stats were never filled in.
        #not-tracked is the common one, and it is common because no import has
        ever carried damage or fire rate for anything — it comes off the game's
        own cards, one item at a time, and most of the catalogue is still
        waiting. Filed together would make the rare one invisible.
        """
        out = []
        if needs_info(i['id']):
            out.append('missing-info')
        if needs_extra(i['id']):
            out.append('not-tracked')
        if needs_art(i['id']):
            out.append('image-change')
        return tuple(out)

    def att_tile(i):
        return tile(f'{i["id"]}.html', i['name'],
                    f'att/{i["id"]}.png'
                    if (i['known'] or has_art('att', i['id'])) else None,
                    gap=needs_info(i['id']), tags=item_tags(i))

    links = ''
    for cat in ['muzzle', 'barrel', 'handguard', 'foregrip', 'rear grip',
                'stock', 'mag', 'optic', 'functional']:
        if cat not in by_cat:
            continue
        gid = anchor('cat', cat)
        rows = sorted(by_cat[cat], key=lambda x: x['name'])
        group(gid, CAT_LABEL[cat], ''.join(att_tile(i) for i in rows), len(rows))
        links += nav_link(gid, CAT_LABEL[cat], len(rows))

    n_gap = sum(1 for i in items.values() if needs_info(i['id']))
    n_extra = sum(1 for i in items.values() if needs_extra(i['id']))
    links += '          <span class="navdiv">By tag</span>\n'
    links += tag_link('missing-info', 'Base stats not read yet', n_gap)
    links += tag_link('not-tracked', 'Damage, penetration, fire rate, muzzle '
                                     'velocity and gunshot range not read yet',
                      n_extra)
    n_art = sum(1 for i in items.values() if needs_art(i['id']))
    if n_art:
        links += tag_link('image-change', 'Drawn with the wrong picture', n_art)
    nav_group('Attachments', len(items), links)

    body = [f"""  <div class="browse">
    <aside class="browse__nav">
      <input class="filter" type="search"
             placeholder="Search everything, or #missing-info&hellip;"
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
    let current = groups[0].id;
    function show(id) {
      let found = false;
      if (groups.some((g) => g.id === id)) current = id;
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
    //
    // A word beginning with # is a tag rather than a name. Tags and words
    // combine, and every tag has to match, so "#missing-info rm277" is the
    // RM277 parts still short of their stats. Tags are the only way to ask a
    // question about the record rather than about the part, which is why they
    // are not just another group in the sidebar.
    function search(v) {
      const tags = [], words = [];
      for (const tok of v.split(/\\s+/)) {
        if (!tok) continue;
        if (tok[0] === '#') { if (tok.length > 1) tags.push(tok.slice(1)); }
        else words.push(tok);
      }
      const text = words.join(' ');
      let hits = 0;
      for (const g of groups) {
        let shown = 0;
        for (const t of g.querySelectorAll('.tile')) {
          const has = (t.dataset.tags || '').split(' ');
          const hit = tags.every((x) => has.includes(x))
                   && (!text || t.textContent.toLowerCase().includes(text));
          t.hidden = !hit;
          if (hit) shown++;
        }
        g.hidden = shown === 0;
        hits += shown;
      }
      for (const a of links) {
        a.classList.toggle('is-on',
          tags.length === 1 && !text && a.dataset.tag === tags[0]);
      }
      empty.hidden = hits > 0;
    }

    q.addEventListener('input', () => {
      const v = q.value.trim().toLowerCase();
      if (v) { search(v); return; }
      // Emptying the box means "stop filtering". The tag is still in the
      // address bar at that point, and re-reading it here typed itself back
      // in the moment the last character went: the box could not be cleared.
      // Clearing the hash first is what makes the delete key work.
      if (TAGS.includes(decodeURIComponent(location.hash.slice(1)))) {
        history.replaceState(null, '', location.pathname + location.search);
      }
      show(current);
    });

    // #optic is a group and #missing-info is a tag, and both arrive the same
    // way — as a hash somebody pasted or a sidebar link they clicked. One
    // router decides which it is, so a tag link is as linkable as a group.
    const TAGS = [...document.querySelectorAll('[data-tag]')]
                   .map((a) => a.dataset.tag);
    function route() {
      const h = decodeURIComponent(location.hash.slice(1));
      if (TAGS.includes(h)) {
        q.value = '#' + h;
        for (const g of groups) g.hidden = false;
        const on = document.querySelector(`[data-tag="${h}"]`);
        if (on) on.closest('details').open = true;
        search('#' + h);
        return;
      }
      q.value = '';
      if (!show(h)) show(groups[0].id);
    }

    for (const a of links) {
      if (!a.dataset.tag) a.addEventListener('click', () => { q.value = ''; });
    }
    addEventListener('hashchange', route);
    route();
  </script>
""")

    return ''.join(body)
GUNSMITH = ROOT / 'data/gunsmith-rm277.json'


# The search, as a worker. It runs off the main thread because it takes a few
# seconds, and a frozen page during those seconds reads as a broken one — and
# because the point of the exercise is to watch it work.
#
# The whole trick is prune(). Carrying every part-way build would mean carrying
# billions; carrying only the ones nothing else beats means carrying a few
# thousand. That is allowed because two part-way builds in the same state — the
# same slots still open, the same slots still taken — have exactly the same
# futures available to them, so if one already beats the other on every stat it
# will still beat it whatever gets added next. The loser can go now instead of
# at the end, and the answer is the same one.
FORGE_CTRL = '''
    // ---- smithing ---------------------------------------------------------
    // The search runs in a worker built from a string, so there is no second
    // file to serve and nothing is fetched. It does not start until asked: a
    // reader who came for the slot lists should not pay for a search they did
    // not run.
    const forge = {
      go: document.getElementById('forge-go'),
      goLabel: document.querySelector('#forge-go span'),
      work: document.getElementById('forge-work'),
      fill: document.getElementById('forge-fill'),
      say: document.getElementById('forge-say'),
      tick: document.getElementById('forge-tick'),
      out: document.getElementById('forge-out'),
      shut: document.getElementById('forge-close'),
      sort: document.getElementById('forge-sort'),
      mins: document.getElementById('forge-mins'),
      tally: document.getElementById('forge-tally'),
      list: document.getElementById('forge-list'),
      pager: document.getElementById('forge-pager'),
      none: document.getElementById('forge-none'),
      reset: document.getElementById('forge-reset'),
      find: document.getElementById('forge-find'),
      type: document.getElementById('forge-type'),
      sug: document.getElementById('forge-sug'),
      chips: document.getElementById('forge-chips'),
      fold: document.getElementById('forge-fold'),
      count: document.getElementById('forge-count'),
    };
    // Only the stats something on record actually moves. The rest are not
    // unchanged, they are unread, and a slider on a column of zeroes would say
    // the opposite.
    const FKEYS = WEAPON.filter((s) => s.tracked && s.mode !== 'set')
                        .map((s) => s.key);
    const FBASE = {}, SIGN = {}, LOWER = {};
    for (const k of FKEYS) {
      const w = WEAPON.find((s) => s.key === k);
      FBASE[k] = w.base;
      // The worker compares builds on the rule that more is better, in every
      // dimension, which is what makes it a plain dominance test. Rather than
      // teach it about the one stat that runs the other way, that stat's
      // numbers are flipped on the way in and flipped back on the way out. The
      // search never learns there was an exception; the reader never sees one.
      LOWER[k] = !!w.lower;
      SIGN[k] = w.lower ? -1 : 1;
    }
    const PER = 4;

    // "Overall" is a sort, not a stat: it has no column of its own and no
    // floor. It sits first because it is the question most people arrive with
    // -- not "which gun has the most range" but "which of these is the best
    // gun" -- and the frontier alone cannot answer it. Every build on the
    // frontier is the best at something, so the frontier has no top; a ranking
    // needs somebody to say what counts, and this says all eight stats count
    // the same.
    const OVERALL = 'Overall';
    let found = [], shortlist = [], sortBy = OVERALL, page = 0;
    let span = {};
    let picked = null, floors = {}, sliders = {};

    // The worker talks faster than anyone can read. Its messages are queued and
    // shown one at a time, each for long enough to be read; when the search
    // finishes ahead of the queue the queue is cut short rather than made to
    // hold the results back.
    let sayQ = [], sayT = null, sayGap = 240;

    // ---- the part of the screen that is always moving ---------------------
    // A search that takes four seconds and reports twenty-two times looks
    // stalled for most of them: one slot can take longer than the rest put
    // together, and a bar that only moves when a message arrives sits still
    // through exactly the stretch a reader starts to doubt it. So the bar eases
    // toward a point just short of the next milestone rather than jumping to
    // the last one, and a counter under it climbs toward the real number of
    // arrangements looked at. Neither is a lie about progress: the bar never
    // passes a milestone it has not reached, and the counter never passes the
    // count the worker has actually reported.
    let barAt = 0, barTo = 0, tickAt = 0, tickTo = 0, t0 = 0, spinning = false;

    function frame() {
      if (!spinning) return;
      barAt += (barTo - barAt) * 0.055;
      forge.fill.style.width = (barAt * 100).toFixed(2) + '%';
      tickAt += (tickTo - tickAt) * 0.12;
      const secs = ((performance.now() - t0) / 1000).toFixed(1);
      forge.tick.textContent = tickAt < 1 ? secs + 's'
        : Math.round(tickAt).toLocaleString() + ' arrangements weighed \u00b7 '
          + secs + 's';
      requestAnimationFrame(frame);
    }

    function spin(on) {
      spinning = on;
      if (on) {
        barAt = barTo = tickAt = tickTo = 0;
        t0 = performance.now();
        requestAnimationFrame(frame);
      }
    }

    function pump() {
      if (!sayQ.length) { sayT = null; return; }
      forge.say.textContent = sayQ.shift();
      forge.say.classList.remove('is-new');
      void forge.say.offsetWidth;
      forge.say.classList.add('is-new');
      sayT = setTimeout(pump, sayGap);
    }

    function note(text) {
      sayQ.push(text);
      if (sayT === null) pump();
    }

    function drained(fn) {
      const tick = () => (sayQ.length ? setTimeout(tick, 60) : setTimeout(fn, 420));
      tick();
    }

    // One panel at a time. Three of them want the same stage -- the weapon's
    // build, a slot's attachments, and this -- and two open at once is two
    // things claiming to be what you are looking at.
    function openPanel() {
      shut();
      showWeapon(false);
      forge.work.hidden = true;
      forge.out.hidden = false;
      forge.go.classList.add('is-on');
      requestAnimationFrame(() => forge.out.classList.add('is-open'));
    }

    function shutPanel() {
      forge.go.classList.remove('is-on');
      forge.out.classList.remove('is-open');
      setTimeout(() => { forge.out.hidden = true; }, 240);
    }

    forge.shut.addEventListener('click', shutPanel);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !forge.out.hidden
          && !forge.find.value) shutPanel();
    });
    // Anywhere off the panel puts it away -- a chip, the weapon, the empty
    // stage. Three exceptions: the button is the panel's own switch and would
    // otherwise close what it had just been pressed to open, and the two
    // controls along the foot of the stage act on the stage rather than
    // instead of it -- going full screen with the builds up is going full
    // screen to read them.
    document.addEventListener('click', (e) => {
      if (forge.out.hidden) return;
      if (e.target.closest('.fside, #forge-go, .expand, #equip')) return;
      shutPanel();
    });

    const value = (b, k) =>
      FBASE[k] + b.v[FKEYS.indexOf(k)] * SIGN[k];

    function fitBuild(list) {
      for (const slot of Object.keys(fitted)) unfit(slot);
      relayout();
      for (const [slot, iid] of list) fit(slot, iid);
      paintWeapon();
      relayout();
    }

    function card(b) {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'fbuild' + (b === picked ? ' is-on' : '');
      let html = '<span class="fbuild__s">';
      for (const k of FKEYS) {
        const d = b.v[FKEYS.indexOf(k)];
        const cls = (d > 0 ? 'up' : d < 0 ? 'down' : '')
                  + (k === sortBy ? ' key' : '');
        html += '<i><b class="' + cls + '">' + value(b, k) + '</b>'
             + k.slice(0, 4).toLowerCase() + '</i>';
      }
      el.innerHTML = html + '</span><span class="fbuild__n">'
        + b.fit.length + ' parts</span>';
      el.addEventListener('click', () => {
        picked = b;
        for (const o of forge.list.children) o.classList.remove('is-on');
        el.classList.add('is-on');
        fitBuild(b.fit);
        document.querySelector('.gunsmith').scrollIntoView(
          {behavior: 'smooth', block: 'start'});
      });
      return el;
    }

    // Pages rather than a growing list: seven thousand rows appended to a
    // page is a page nobody can scroll, and a page number is a place you can
    // come back to.
    function pager(pages) {
      forge.pager.innerHTML = '';
      if (pages < 2) return;
      const go = (n, text, on, dead) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'fpage' + (on ? ' is-on' : '');
        b.textContent = text;
        if (dead) b.disabled = true;
        else b.addEventListener('click', () => { page = n; paintList(); });
        forge.pager.appendChild(b);
      };
      const gap = () => {
        const s = document.createElement('span');
        s.className = 'fgap';
        s.textContent = '\\u2026';
        forge.pager.appendChild(s);
      };
      go(page - 1, '\\u2039', false, page === 0);
      const near = [0, pages - 1, page, page - 1, page + 1]
        .filter((n) => n >= 0 && n < pages);
      let last = -1;
      for (const n of [...new Set(near)].sort((a, b) => a - b)) {
        if (n > last + 1) gap();
        go(n, String(n + 1), n === page);
        last = n;
      }
      go(page + 1, '\\u203a', false, page === pages - 1);
    }

    function paintList() {
      const i = FKEYS.indexOf(sortBy);
      shortlist = found.filter((b) =>
        FKEYS.every((k) => LOWER[k] ? value(b, k) <= floors[k]
                                    : value(b, k) >= floors[k])
        && must.every((id) => b.has.has(id)));
      shortlist.sort((a, b) => sortBy === OVERALL
        ? b.score - a.score : b.v[i] - a.v[i]);
      const pages = Math.ceil(shortlist.length / PER);
      page = Math.min(page, Math.max(0, pages - 1));
      forge.list.innerHTML = '';
      for (const b of shortlist.slice(page * PER, page * PER + PER))
        forge.list.appendChild(card(b));
      forge.none.hidden = shortlist.length > 0;
      if (!shortlist.length) {
        // Two different reasons for an empty list, and the difference matters:
        // a floor set too high is yours to lower, a part in none of the builds
        // is a fact about the part.
        const dead = must.filter((id) => !usage[id]).map((id) => NAMEOF[id]);
        forge.none.textContent = dead.length
          ? 'Every build wearing ' + dead.join(' and ')
            + ' is beaten by one that is not, so none of them are here.'
          : must.length
            ? 'Nothing with those parts is that good at everything at once.'
            : 'Nothing is that good at everything at once. Pull a slider back down.';
      }
      forge.tally.textContent = shortlist.length === found.length
        ? shortlist.length.toLocaleString() + ' builds'
        : shortlist.length.toLocaleString() + ' of '
          + found.length.toLocaleString();
      pager(pages);
      // What each slider could still be moved to without emptying the list.
      for (const k of FKEYS) {
        const others = found.filter((b) => FKEYS.every(
          (o) => o === k || (LOWER[o] ? value(b, o) <= floors[o]
                                      : value(b, o) >= floors[o])));
        const vals = others.map((b) => value(b, k));
        const best = !vals.length ? null
          : LOWER[k] ? Math.min(...vals) : Math.max(...vals);
        const past = best !== null
          && (LOWER[k] ? best > floors[k] : best < floors[k]);
        sliders[k].note.textContent = best === null ? 'nothing left'
          : past ? 'too far \\u2014 best here is ' + best
          : (LOWER[k] ? 'down to ' : 'up to ') + best;
        sliders[k].note.classList.toggle('is-over', !!past);
      }
    }

    function buildSliders() {
      forge.mins.innerHTML = '';
      sliders = {};
      for (const k of FKEYS) {
        const vals = found.map((b) => value(b, k));
        const lo = Math.min(...vals), hi = Math.max(...vals);
        // The handle starts where it rules nothing out: the bottom of the range
        // for a stat you want a lot of, the top of it for the one you want
        // little of.
        const open = LOWER[k] ? hi : lo;
        floors[k] = open;
        const row = document.createElement('label');
        row.className = 'fmin';
        row.innerHTML = '<span class="fmin__k">' + k + '</span>'
          + '<b class="fmin__v"></b>'
          + '<input type="range" min="' + lo + '" max="' + hi + '" value="' + open + '">'
          + '<em class="fmin__n"></em>';
        const input = row.querySelector('input');
        const out = row.querySelector('.fmin__v');
        out.textContent = open;
        input.addEventListener('input', () => {
          floors[k] = +input.value;
          out.textContent = input.value;
          page = 0;
          paintList();
        });
        forge.mins.appendChild(row);
        sliders[k] = {input, out, note: row.querySelector('.fmin__n')};
      }
    }

    // Each stat stretched onto nought-to-one across the builds that were found,
    // then added up. Stretching is the whole of it: raw, muzzle velocity moves
    // in nearly two hundreds and handling in tens, so a plain sum would be a
    // muzzle velocity ranking wearing a different name. On this scale a build
    // that is best-in-set at everything scores eight and one that is worst at
    // everything scores nought.
    function score(b) {
      let t = 0;
      for (let i = 0; i < FKEYS.length; i++) {
        const sp = span[FKEYS[i]];
        if (sp.hi > sp.lo) t += (b.v[i] - sp.lo) / (sp.hi - sp.lo);
      }
      return t;
    }

    function measure() {
      span = {};
      for (let i = 0; i < FKEYS.length; i++) {
        let lo = Infinity, hi = -Infinity;
        for (const b of found) {
          if (b.v[i] < lo) lo = b.v[i];
          if (b.v[i] > hi) hi = b.v[i];
        }
        span[FKEYS[i]] = {lo, hi};
      }
      for (const b of found) b.score = score(b);
    }

    function buildTabs() {
      forge.sort.innerHTML = '';
      for (const k of [OVERALL, ...FKEYS]) {
        const b = document.createElement('button');
        b.type = 'button';
        b.role = 'tab';
        b.className = 'ftab' + (k === sortBy ? ' is-on' : '');
        b.setAttribute('aria-selected', String(k === sortBy));
        b.textContent = k;
        b.addEventListener('click', () => {
          sortBy = k;
          for (const o of forge.sort.children) {
            o.classList.toggle('is-on', o === b);
            o.setAttribute('aria-selected', String(o === b));
          }
          page = 0;
          paintList();
        });
        forge.sort.appendChild(b);
      }
    }

    forge.reset.addEventListener('click', () => {
      must = [];
      chips();
      for (const k of FKEYS) {
        const s = sliders[k];
        const open = LOWER[k] ? s.input.max : s.input.min;
        s.input.value = open;
        floors[k] = +open;
        s.out.textContent = open;
      }
      page = 0;
      paintList();
    });

    forge.go.addEventListener('click', () => {
      // Nothing about the answer changes between runs, so once it has been
      // worked out the button is the panel's switch rather than a second
      // search: press it to bring the builds back, press it again to put
      // them away.
      if (found.length) return forge.out.hidden ? openPanel() : shutPanel();

      forge.go.disabled = true;
      forge.go.classList.add('is-busy');
      forge.goLabel.textContent = 'Smithing\\u2026';
      forge.work.hidden = false;
      forge.out.hidden = true;
      forge.out.classList.remove('is-open');
      forge.fill.style.width = '0%';
      forge.tick.textContent = '';
      spin(true);
      sayQ = [];
      clearTimeout(sayT);
      sayT = null;
      sayGap = 320;
      forge.say.textContent = '';

      // Everything the search needs, read off the page rather than shipped a
      // second time: the slot lists are already in the panel, and the rules and
      // stat lines are already here for the build panel.
      const pool = {};
      for (const l of lists)
        pool[l.id.slice(3)] = [...l.querySelectorAll('.pcard')]
                                .map((c) => c.dataset.item);
      const delta = {};
      for (const [iid, st] of Object.entries(DELTA))
        delta[iid] = FKEYS.map((k) => {
          const w = WEAPON.find((s) => s.key === k);
          return (st[w.from || k] || 0) * SIGN[k];
        });

      const w = new Worker(URL.createObjectURL(
        new Blob([FORGE_SRC], {type: 'text/javascript'})));
      const t0 = performance.now();
      w.onerror = (e) => {
        spin(false);
        sayQ = [];
        forge.say.textContent = 'The search stopped: ' + e.message;
        forge.go.disabled = false;
        forge.go.classList.remove('is-busy');
        forge.goLabel.textContent = 'Try again';
      };
      w.onmessage = ({data}) => {
        if (data.say) return note(data.say);
        if (data.total !== undefined)
          return note(data.total.toLocaleString() + ' builds to get through');
        if (data.step) {
          // Just short of the next one, so the ease has somewhere to go.
          barTo = Math.min(1, (data.step + 0.85) / data.of);
          if (data.raw) tickTo += data.raw;
          const what = data.slot.replace(/-/g, ' ');
          return note(data.idle
            ? 'Skipping ' + what + ' \\u2014 nothing on record moves a stat'
            : 'Fitting ' + what + ' \\u2014 ' + data.raw.toLocaleString()
              + ' tried, ' + data.kept.toLocaleString() + ' still worth keeping');
        }
        if (data.done) {
          found = data.done;
          w.terminate();
          // The queue is behind by now. Keep the last couple of lines so the
          // panel does not appear mid-sentence, and run them out quickly.
          if (sayQ.length > 2) sayQ = sayQ.slice(-2);
          sayGap = 110;
          note(found.length.toLocaleString() + ' builds nothing else beats, in '
            + ((performance.now() - t0) / 1000).toFixed(1) + 's');
          barTo = 1;
          forge.goLabel.textContent = 'Builds';
          forge.go.disabled = false;
          forge.go.classList.remove('is-busy');
          picked = null;
          page = 0;
          must = [];
          measure();
          countUses();
          chips();
          buildTabs();
          buildSliders();
          paintList();
          drained(() => { spin(false); openPanel(); });
        }
      };
      w.postMessage({pool, delta, opens: OPENS,
                     base: [...BASE_SLOTS], keys: FKEYS});
    });


    // ---- required parts ---------------------------------------------------
    // A floor says how good the gun has to be. This says what has to be on it,
    // which is the other half of the question: the optimiser does not know you
    // already own a particular scope, or that you will not run a build without
    // a suppressor.
    //
    // A part can be asked for and turn out to be in none of the builds worth
    // keeping. That is worth saying rather than leaving as an empty list: it
    // means every build wearing it is beaten by one that is not, which is a
    // fact about the part.
    const NAMEOF = {};
    for (const c of document.querySelectorAll('.pcard')) {
      const n = c.querySelector('.pcard__n');
      if (n) NAMEOF[c.dataset.item] = n.textContent.trim();
    }
    // Which lists a part turns up in, so the type box can narrow the search to
    // one kind of part. A part can be in more than one list -- the micro sight
    // riser is an optic and a mount for one -- so this is a list, not a value.
    const SLOTOF = {}, TYPES = [];
    for (const l of lists) {
      const sid = l.id.slice(3);
      const label = (SLOTS.find((s) => s.id === sid) || {}).label || sid;
      if (!TYPES.includes(label)) TYPES.push(label);
      for (const c of l.querySelectorAll('.pcard')) {
        const iid = c.dataset.item;
        SLOTOF[iid] = SLOTOF[iid] || [];
        if (!SLOTOF[iid].includes(label)) SLOTOF[iid].push(label);
      }
    }
    for (const t of TYPES.slice().sort((a, b) => a.localeCompare(b))) {
      const o = document.createElement('option');
      o.value = t;
      o.textContent = t;
      forge.type.appendChild(o);
    }

    let must = [], usage = {}, folded = false;

    function countUses() {
      usage = {};
      for (const b of found) {
        b.has = new Set(b.fit.map((f) => f[1]));
        for (const id of b.has) usage[id] = (usage[id] || 0) + 1;
      }
    }

    function chips() {
      forge.chips.innerHTML = '';
      for (const id of must) {
        const el = document.createElement('span');
        el.className = 'fchip' + (usage[id] ? '' : ' is-empty');
        el.innerHTML = '<b></b><em></em>';
        el.querySelector('b').textContent = NAMEOF[id] || id;
        el.querySelector('em').textContent = usage[id]
          ? usage[id].toLocaleString() : 'in none of them';
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'fchip__x';
        x.textContent = '\\u00d7';
        x.addEventListener('click', () => {
          must = must.filter((m) => m !== id);
          chips();
          page = 0;
          paintList();
        });
        el.appendChild(x);
        forge.chips.appendChild(el);
      }
      forge.count.textContent = must.length
        ? must.length + (must.length === 1 ? ' part' : ' parts') : 'none';
      forge.chips.hidden = folded || !must.length;
    }

    forge.fold.addEventListener('click', () => {
      folded = !folded;
      forge.fold.setAttribute('aria-expanded', String(!folded));
      forge.chips.hidden = folded || !must.length;
    });

    function suggest() {
      const q = forge.find.value.trim().toLowerCase();
      const kind = forge.type.value;
      forge.sug.innerHTML = '';
      // With neither a name nor a type there is nothing to narrow: the whole
      // catalogue is not a suggestion.
      if (!q && !kind) { forge.sug.hidden = true; return; }
      const hits = Object.keys(NAMEOF)
        .filter((id) => !must.includes(id)
                     && (!kind || (SLOTOF[id] || []).includes(kind))
                     && NAMEOF[id].toLowerCase().includes(q))
        .sort((a, b) => (usage[b] || 0) - (usage[a] || 0)
                     || NAMEOF[a].localeCompare(NAMEOF[b]))
        .slice(0, 8);
      for (const id of hits) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'fsug__i' + (usage[id] ? '' : ' is-empty');
        b.innerHTML = '<span></span><em></em>';
        b.querySelector('span').textContent = NAMEOF[id];
        b.querySelector('em').textContent = usage[id]
          ? 'in ' + usage[id].toLocaleString() : 'in none';
        b.addEventListener('click', () => {
          must.push(id);
          forge.find.value = '';
          forge.sug.hidden = true;
          folded = false;
          forge.fold.setAttribute('aria-expanded', 'true');
          chips();
          page = 0;
          paintList();
        });
        forge.sug.appendChild(b);
      }
      forge.sug.hidden = !hits.length;
    }

    forge.find.addEventListener('input', suggest);
    forge.find.addEventListener('focus', suggest);
    forge.type.addEventListener('change', suggest);
    forge.find.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const first = forge.sug.querySelector('.fsug__i');
        if (first) first.click();
      }
      if (e.key === 'Escape') { forge.find.value = ''; forge.sug.hidden = true; }
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.freq__bar')) forge.sug.hidden = true;
    });
'''

FORGE_JS = r"""
// Which slots exist depends on what is fitted, so a slot has to be visited
// after anything that can open or shut it. Sorted here rather than written
// down: the rules already say who opens what.
function order(pool, opens, base) {
  const slots = Object.keys(pool);
  const slotOf = {};
  for (const s of slots)
    for (const i of pool[s]) (slotOf[i] = slotOf[i] || []).push(s);
  const after = {};
  for (const s of slots) after[s] = new Set();
  for (const [iid, r] of Object.entries(opens))
    for (const home of slotOf[iid] || [])
      for (const t of (r.grants || []).concat(r.blocks || []))
        if (after[t]) after[t].add(home);
  // One at a time, and the moment a slot places, place everything it just
  // unlocked. Taking them in waves instead -- every base slot, then every
  // granted one -- leaves the state split all the way to the end, and the set
  // being carried grows fourteen times bigger before it collapses.
  const out = [], done = new Set();
  const ready = (s) => !done.has(s)
    && [...after[s]].every((d) => done.has(d) || d === s);
  const place = (s) => {
    out.push(s);
    done.add(s);
    for (const t of slots) if (ready(t) && after[t].size) place(t);
  };
  // And take the slots that open or shut something before the ones that do
  // not. Every branch in the state is resolved early that way, so the merge
  // fires early and the big slots -- the foregrip and the rails, where the
  // options are -- are worked through once instead of once per branch.
  const opener = new Set();
  for (const [iid, r] of Object.entries(opens))
    if ((r.grants || []).length || (r.blocks || []).length)
      for (const home of slotOf[iid] || []) opener.add(home);
  const first = slots.filter((s) => opener.has(s));
  for (const s of first) if (ready(s)) place(s);
  for (const s of slots) if (ready(s)) place(s);
  for (const s of slots) if (!done.has(s)) place(s);   // cycles cannot hang it
  return out;
}

const has = (set, slot) => set.includes('|' + slot + '|');

function step(open_, blocked, iid, opens) {
  const r = opens[iid] || {};
  let o = open_, b = blocked;
  for (const g of r.grants || []) if (!has(o, g)) o += g + '|';
  for (const x of r.blocks || []) if (!has(b, x)) b += x + '|';
  return [o, b];
}

// How many builds there are, which is not the same as how many are worth
// looking at. Counted exactly, by remembering the count per state rather than
// by visiting anything.
function census(ORDER, pool, opens, base) {
  const memo = new Map();
  function go(k, open_, blocked) {
    if (k === ORDER.length) return 1;
    const key = k + open_ + ' ' + blocked;
    const hit = memo.get(key);
    if (hit !== undefined) return hit;
    const slot = ORDER[k];
    let n = go(k + 1, open_, blocked);
    if ((base.has(slot) || has(open_, slot)) && !has(blocked, slot))
      for (const iid of pool[slot]) {
        const [o, b] = step(open_, blocked, iid, opens);
        n += go(k + 1, o, b);
      }
    memo.set(key, n);
    return n;
  }
  return go(0, '|', '|');
}

// Keep the rows nothing else beats. Sorting by the total first means the
// strong rows are tested against almost nothing and the weak ones die against
// the first thing they meet, which is what keeps this quick in practice.
function prune(rows, D) {
  rows.sort((a, b) => b.sum - a.sum);
  const keep = [];
  outer:
  for (const r of rows) {
    for (const k of keep) {
      let beats = true;
      for (let d = 0; d < D; d++) if (k.v[d] < r.v[d]) { beats = false; break; }
      if (beats) continue outer;        // equal counts as beaten: no repeats
    }
    keep.push(r);
  }
  return keep;
}

onmessage = ({data}) => {
  const {pool, delta, opens, base, keys} = data;
  const D = keys.length;
  const BASE = new Set(base);
  const ORDER = order(pool, opens, BASE);
  const cares = new Set();
  for (const r of Object.values(opens))
    for (const s of (r.grants || []).concat(r.blocks || [])) cares.add(s);

  postMessage({say: 'Counting what there is to look through'});
  postMessage({total: census(ORDER, pool, opens, BASE)});

  // A slot where nothing on record moves anything, and which opens and shuts
  // nothing either, cannot change the answer -- so it is said out loud and
  // stepped over. Said out loud because a slot with no numbers against it is a
  // gap in the reading, not a slot that does nothing.
  const idle = (slot) => pool[slot].every((i) =>
    !opens[i] && (delta[i] || []).every((x) => !x));

  let cur = new Map([['| |', [{v: new Int16Array(D), sum: 0, fit: []}]]]);
  for (let k = 0; k < ORDER.length; k++) {
    const slot = ORDER[k];
    if (idle(slot)) {
      postMessage({step: k + 1, of: ORDER.length, slot, idle: true});
      continue;
    }
    const next = new Map();
    let raw = 0;
    for (const [st, rows] of cur) {
      const [open_, blocked] = st.split(' ');
      const live = (BASE.has(slot) || has(open_, slot)) && !has(blocked, slot);
      for (const iid of [null].concat(live ? pool[slot] : [])) {
        const [o, b] = iid ? step(open_, blocked, iid, opens) : [open_, blocked];
        const key = o + ' ' + b;
        let bucket = next.get(key);
        if (!bucket) next.set(key, bucket = []);
        const dv = iid ? delta[iid] : null;
        for (const row of rows) {
          raw++;
          if (!dv) { bucket.push(row); continue; }
          const v = new Int16Array(row.v);
          let sum = row.sum;
          for (let d = 0; d < D; d++) { v[d] += dv[d]; sum += dv[d]; }
          bucket.push({v, sum, fit: row.fit.concat([[slot, iid]])});
        }
      }
    }
    // Once nothing left can be opened or taken away, the states are the same
    // story told twice and can be merged into one.
    let merged = next;
    if (!ORDER.slice(k + 1).some((s) => cares.has(s))) {
      // Concatenated, not spread: pushing thirty thousand arguments at once
      // is thirty thousand stack slots, and the browser says so.
      let all = [];
      for (const rows of next.values()) all = all.concat(rows);
      merged = new Map([['| |', all]]);
    }
    let kept = 0;
    for (const [key, rows] of merged) {
      const cut = prune(rows, D);
      merged.set(key, cut);
      kept += cut.length;
    }
    cur = merged;
    postMessage({step: k + 1, of: ORDER.length, slot, raw, kept});
  }

  let all = [];
  for (const rows of cur.values()) all = all.concat(rows);
  postMessage({done: prune(all, D).map((r) => ({v: [...r.v], fit: r.fit}))});
};
"""



def stat_bar(name, delta):
    """One stat line: the change, and a bar the size of it.

    The game prints the resulting value with the change beside it — "42 (-8)".
    We only hold the change, never the weapon's base figures, so only the change
    is shown. Inventing the total to complete the picture would be inventing
    numbers, and the bar carries the same comparison honestly.
    """
    cls = 'up' if delta > 0 else 'down'
    w = min(100, abs(delta) * 100 / 20)      # 20 is the widest change on record
    return (f'            <div class="sr">'
            f'<span class="sr__n">{name}</span>'
            f'<span class="sr__v {cls}">{"+" if delta > 0 else "&minus;"}'
            f'{abs(delta)}</span>'
            f'<span class="sr__bar"><i class="{cls}" style="width:{w:.0f}%"></i>'
            f'</span></div>\n')


def slot_tile(sid):
    """A slot as the game draws it in "Adds Slots": named box with its icon."""
    icon = (f' style="background-image:url({UP}smith/slot/{sid}.png)"'
            if (ROOT / 'smith' / 'slot' / f'{sid}.png').is_file() else '')
    return (f'<span class="stile"{icon}>'
            f'<em>{SLOT_LABEL.get(sid, sid)}</em></span>')


def pick_detail(name, slot):
    """The right-hand card: what fitting this thing does.

    The id carries the slot as well as the item because the same attachment is
    in as many as five of these lists — a handguard panel fits both rails, both
    patches and the upper rail — and an id repeated five times in one document
    is not an id. It looked like it worked: the page hides all but one detail,
    and the panel it filled was the first one in the document, which for an item
    in a single list is also the visible one. For the twenty-three items in more
    than one, four times out of five the numbers were written into a pane nobody
    could see and the visible one stayed blank under its "If fitted" heading.
    """
    iid = item_id(name)
    item = BY_ID.get(iid)
    rule = RULES.get(iid, {})
    card = CARD_FACTS.get(iid) or {}

    tier = card.get('tier')
    dot = f'<span class="tier {tier}"></span>' if tier else ''
    head = (f'          <h4>{dot}<a href="{iid}.html">{name}</a></h4>\n')

    # No price. It is a market snapshot rather than a property of the thing,
    # it drifts, and it is not what this screen is for — the item's own page
    # still carries it.
    rows = ''

    # No effects list. The catalogue's trait strings are clipped on import —
    # "High Optical" for "High Optical Zoom", "Moderate Glint" for "Moderate
    # Glint on ADS" — so the section printed half-sentences and read as though
    # the data were complete.
    fx = ''

    adds = ''
    if rule.get('grants'):
        adds += ('          <p class="dlabel">Adds Slots</p>\n'
                 '          <div class="stiles">'
                 + ''.join(slot_tile(s) for s in rule['grants']) + '</div>\n')
    if rule.get('conflictSlots'):
        adds += ('          <p class="dlabel">Occupies</p>\n'
                 '          <div class="stiles">'
                 + ''.join(slot_tile(s) for s in rule['conflictSlots'])
                 + '</div>\n')

    # No stat block here. What a change is worth depends on what is already
    # fitted, so the numbers are computed in the page against the live build
    # rather than baked in against nothing.
    return (f'        <div class="detail" id="d-{slot}-{iid}" hidden>\n'
            + head + rows + fx + adds
            + '          <p class="dlabel">If fitted</p>\n'
            + '          <div class="delta"></div>\n'
            + '        </div>\n')


def slot_panel(slot, label):
    """One slot: every attachment that fits it, and what the chosen one does.

    Laid out as the game lays it out — a column of cards, then a panel of
    detail for whichever is selected — because that is the thing being
    reproduced. The rows come from the same rows_for() the weapon page's tables
    use, so the two cannot disagree about what fits.
    """
    cards, details = '', ''
    for i, (name, missing, unread) in enumerate(rows_for(slot)):
        iid = item_id(name)
        tier = (CARD_FACTS.get(iid) or {}).get('tier') or 'none'
        art = (f' style="background-image:url({UP}att/{iid}.png)"'
               if has_art('att', iid) or iid in BY_ID else '')
        cards += (f'          <button class="pcard{" is-on" if i == 0 else ""}" '
                  f'data-item="{iid}" type="button">'
                  f'<span class="pcard__n tier-{tier}">{name}</span>'
                  f'<span class="pcard__art"{art}></span></button>\n')
        details += pick_detail(name, slot)

    n = len(rows_for(slot))
    return (f'      <div class="slotlist" id="sl-{slot}" hidden>\n'
            f'        <div class="picks">\n'
            f'          <p class="picks__h">{label} <span class="count">{n}</span></p>\n'
            f'{cards}        </div>\n'
            f'        <div class="dpane">\n{details}        </div>\n'
            '      </div>\n')


def gunsmith_body():
    """The editor: the weapon, its slots around it, a leader line to each.

    Returns a body fragment, not a page. It is the top half of the weapon's own
    catalogue entry now — reaching it used to mean clicking the picture through
    to a second URL, which put the interesting half of a weapon page somewhere
    nobody would guess at.

    Rebuilt from the game's own screen rather than invented, because the point
    of it is recognition — someone who has used the gunsmith should see the
    same picture. The artwork and the coordinates are cut from screen
    recordings by tools/cut-gunsmith.py and tools/cut-gunsmith-granted.py; this
    only lays them out.

    Everything is positioned in the coordinates of the frame the art came from
    and scaled as one unit, so the chips, the weapon and the lines cannot drift
    apart at any window size. A slot with no anchor recorded yet simply gets no
    line, which is why the page was useful before all of them were placed.
    """
    d = json.loads(GUNSMITH.read_text(encoding='utf-8'))
    fw, fh = d['frame']['w'], d['frame']['h']
    g, C = d['gun'], d['chip']
    pc = lambda v, tot: f'{v / tot * 100:.4f}%'

    # The base fifteen, and every chip a fitted part opens. A granted chip is
    # in the page from the start and simply hidden, because the alternative --
    # building it on equip -- means its picture, its count and its whole
    # attachment list arrive late, and the list is the expensive half.
    base = {s['slot']: s for s in d['slots']}
    extra = {}
    for lay in d.get('layouts', []):
        for slot, c in lay['chips'].items():
            if slot not in base and slot not in extra:
                extra[slot] = dict(c, slot=slot)
    order = list(base.values()) + [extra[k] for k in sorted(extra)]

    chips, lines, panels = [], [], []
    for s in order:
        granted = s['slot'] in extra
        cx, cy = s['x'] + C / 2, s['y'] + C / 2
        label = SLOT_TITLE.get(s['slot'], s['label'])
        n = len(rows_for(s['slot'])) if s['slot'] in dict(
            (k, 1) for k, _, _ in SECTIONS) else 0
        chips.append(
            f'      <a class="chip3{" is-granted" if granted else ""}" '
            f'style="left:{pc(s["x"], fw)};'
            f'top:{pc(s["y"], fh)};width:{pc(C, fw)};height:{pc(C, fh)}" '
            f'href="#slot-{s["slot"]}" '
            f'data-slot="{s["slot"]}" title="{s["label"]}"'
            f'{" hidden" if granted else ""}>'
            f'<span class="chip3__label">{s["label"]}</span>'
            f'<span class="chip3__art" style="background-image:'
            f'url({UP}smith/slot/{s["slot"]}.png)"></span>'
            + (f'<em>{n}</em>' if n else '') + '</a>\n')
        panels.append(slot_panel(s['slot'], label))
        if s.get('ax') is not None:
            lines.append(f'      <line data-slot="{s["slot"]}" '
                         f'x1="{cx}" y1="{cy}" '
                         f'x2="{s["ax"]}" y2="{s["ay"]}"'
                         + (' hidden' if granted else '') + '></line>\n')

    prov = (' <em class="prov">derived, unconfirmed</em>'
            if d['weapon'].get('derived') else '')
    # Every stat line the page might need to add up, by item, so the arithmetic
    # happens against the build the reader has assembled rather than against a
    # blank rifle.
    deltas = {}
    for s in order:
        for name, _m, _x in rows_for(s['slot']):
            iid = item_id(name)
            st = stats_for(iid)
            if st:
                deltas[iid] = st
    # Which stats anything we hold can actually move. A row nobody modifies is
    # shown as untracked rather than as unchanged: a suppressor plainly alters
    # how far the shot carries, and printing "500 m, no change" would be a
    # claim about the game rather than a note about our data.
    seen = {k for st in deltas.values() for k in st}
    for st in d['weapon']['stats']:
        st['tracked'] = (st.get('from') or st['key']) in seen
        # Which way is better. Every other stat rewards a bigger number; the
        # distance your shot carries to somebody else's ears rewards a smaller
        # one, and nothing downstream can work that out for itself.
        st['lower'] = st['key'] in LOWER_IS_BETTER

    # What each fittable part opens and what it takes over. Only the parts that
    # can go on this rifle, and only the ones that do either, so the page ships
    # the rules it can act on rather than all of them.
    opens = {}
    for s in order:
        for name, _m, _x in rows_for(s['slot']):
            iid = item_id(name)
            r = RULES.get(iid) or {}
            if r.get('grants') or r.get('conflictSlots'):
                opens[iid] = {'grants': r.get('grants', []),
                              'blocks': r.get('conflictSlots', [])}

    # Every arrangement of chips we have watched the game draw. The first is the
    # bare rifle; the rest each come from a clip with one part fitted. They are
    # whole pictures rather than lists of additions because the game reflows the
    # fan when the count changes — a barrel combo moves the left arm by up to
    # 155px — and a chip pasted onto the base positions would land on its
    # neighbour.
    def xy(c):
        return {'x': c['x'], 'y': c['y'], 'ax': c.get('ax'), 'ay': c.get('ay')}

    lays = [{'when': [], 'blocks': [],
             'chips': {s['slot']: xy(s) for s in d['slots']}}]
    for lay in d.get('layouts', []):
        lays.append({'when': lay['when'], 'blocks': lay['blocks'],
                     'chips': {k: xy(c) for k, c in lay['chips'].items()}})
    body = f"""  <div class="gunsmith" style="--ar:{fw / fh:.4f}">
  <div class="stage" style="aspect-ratio:{fw}/{fh}">
    <div class="wname">
      <button class="wname__b" id="wtab" aria-expanded="false">
        <span>{d['weapon']['name']}</span>
        <svg viewBox="0 0 16 16" aria-hidden="true" width="15" height="15">
          <rect x="1" y="2.5" width="14" height="2"></rect>
          <rect x="1" y="7" width="14" height="2"></rect>
          <rect x="1" y="11.5" width="14" height="2"></rect>
        </svg>
      </button>
      <div class="wpanel" id="wpanel" hidden>
        <p class="dlabel">Current build{prov}</p>
        <div class="wstats"></div>
      </div>
    </div>
    <button class="smith" id="forge-go" type="button">
      <svg viewBox="0 0 64 64" width="17" height="17" aria-hidden="true">
        <g fill="#95a8b4">
          <path d="M13 34h36v6H13l-6-3z"></path>
          <path d="M24 46h14l7 7H17z"></path>
        </g>
        <path class="h" d="M31 33l7 2 9-9-2-7-7 2z" fill="#0ff796"></path>
        <path class="h" d="M33 30l5-5-16-16-5 5z" fill="#0a8f57"></path>
      </svg>
      <span>Smith</span>
    </button>
    <img class="stage__gun" src="{UP}smith/rm277.png" alt="RM277"
         style="left:{pc(g['x'], fw)};top:{pc(g['y'], fh)};
                width:{pc(g['w'], fw)};height:{pc(g['h'], fh)}">
    <svg class="stage__wires" viewBox="0 0 {fw} {fh}" preserveAspectRatio="none"
         aria-hidden="true">
{''.join(lines)}    </svg>
{''.join(chips)}    <div class="pins" hidden></div>

    <div class="fwork" id="forge-work" hidden>
      <div class="fwork__box">
        <div class="fwork__art">
          <svg class="fring" viewBox="0 0 100 100" aria-hidden="true">
            <circle class="fring__t" cx="50" cy="50" r="45"></circle>
            <circle class="fring__s" cx="50" cy="50" r="45"></circle>
          </svg>
          <svg class="fanvil" viewBox="0 0 64 64" role="img" aria-label="Smithing">
            <g class="fanvil__a">
              <g fill="#95a8b4">
                <path d="M13 34h36v6H13l-6-3z"></path>
                <path d="M24 46h14l7 7H17z"></path>
                <rect x="15" y="52.4" width="34" height="3.6" rx="1.4"></rect>
              </g>
              <path d="M19 40h24l-5 6H24z" fill="#5e7381"></path>
            </g>
            <g class="fanvil__h">
              <path d="M33 30l5-5-16-16-5 5z" fill="#0a8f57"></path>
              <path d="M31 33l7 2 9-9-2-7-7 2z" fill="#0ff796"></path>
            </g>
            <g class="fanvil__k" stroke="#0ff796" stroke-width="2"
               stroke-linecap="round" fill="none">
              <path d="M41 31l7-3"></path>
              <path d="M40 35l6 3"></path>
              <path d="M40 27l3-6"></path>
            </g>
          </svg>
        </div>
        <div class="fwork__bar"><i id="forge-fill"></i></div>
        <p class="fwork__say" id="forge-say"></p>
        <p class="fwork__tick" id="forge-tick"></p>
      </div>
    </div>

    <aside class="fside" id="forge-out" hidden aria-label="Smithing">
      <header class="fside__top">
        <h2>Smithing</h2>
        <p class="fside__n" id="forge-tally"></p>
        <button class="fside__x" id="forge-close" type="button"
                aria-label="Close">&times;</button>
      </header>
      <p class="fside__lede">Each of these is the best there is at something and
      beaten by nothing at everything. Click one to fit it.</p>

      <div class="freq">
        <div class="freq__bar">
          <select id="forge-type" aria-label="Attachment type">
            <option value="">Any type</option>
          </select>
          <div class="fsearch">
            <input type="search" id="forge-find" autocomplete="off"
                   placeholder="Name a part it must have&hellip;">
            <div class="fsug" id="forge-sug" hidden></div>
          </div>
        </div>
        <button class="freq__t" id="forge-fold" type="button" aria-expanded="true">
          <span>Required</span><em id="forge-count">none</em>
        </button>
        <div class="fchips" id="forge-chips" hidden></div>
      </div>

      <div class="ftabs" id="forge-sort" role="tablist"></div>
      <div class="forge__list" id="forge-list"></div>
      <p class="fside__none" id="forge-none" hidden></p>
      <div class="forge__pager" id="forge-pager"></div>

      <div class="fmins">
        <p class="dlabel">Nothing below
          <button class="freset" id="forge-reset" type="button">reset</button></p>
        <div class="forge__mins" id="forge-mins"></div>
      </div>
    </aside>

    <aside class="panel" id="panel" hidden>
{''.join(panels)}      <button class="panel__x" id="close" aria-label="Close">&times;</button>
    </aside>
    <button class="equip" id="equip" hidden></button>
    <button class="expand" id="expand" hidden aria-label="Full screen">
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path d="M1 6V1h5M15 10v5h-5M10 1h5v5M6 15H1v-5"></path>
      </svg>
    </button>
  </div>
  </div>


  <script>
    const WEAPON = {json.dumps(d['weapon']['stats'])};
    const SPECS = {json.dumps(d['weapon'].get('specs', []))};
    const READ = new Set({json.dumps(sorted(CLEARED))});
    const DELTA = {json.dumps(deltas)};
    const OPENS = {json.dumps(opens)};
    const LAYOUTS = {json.dumps(lays)};
    const FW = {fw}, FH = {fh}, CHIP = {C};
    const SLOTS = {json.dumps([{'id': s['id'], 'label': SLOT_LABEL.get(s['id'], s['id'])} for s in SLOT_TYPES])};
    const FORGE_SRC = {json.dumps(FORGE_JS)};

    // The hash carries two things: which slot to open, and whether the editor
    // is in dev mode. Written as #right-patch#dev because that is one string to
    // paste and one to delete.
    const HASH = location.hash.slice(1).split('#');
    const DEV = HASH.includes('dev');
    const TAIL = DEV ? '#dev' : '';

    // Each chip is a real link to the slot's table on the weapon page, and stays
    // one. This only intercepts the click to show the same list here instead,
    // so the page still works with the script off and a middle-click still
    // opens the long version in a tab.
    const wrap = document.querySelector('.gunsmith');
    const panel = document.getElementById('panel');
    const lists = [...panel.querySelectorAll('.slotlist')];

    const stage = document.querySelector('.stage');
    const equipBtn = document.getElementById('equip');

    // What is fitted, by slot. A page-lifetime scratch state: the point is to
    // see what a build does, not to save one, and nothing here is written down.
    const fitted = {{}};
    let cur = {{slot: null, item: null}};

    function chipFor(slot) {{
      return document.querySelector('.chip3[data-slot="' + slot + '"]');
    }}

    // ---- which slots exist right now ------------------------------------
    // Half the rifle's slots are not on the rifle. A riser opens two, a rear
    // grip opens a third, and either barrel opens an upper rail while taking
    // the muzzle or the bipod away with it. So the set of chips is a function
    // of what is fitted, and it is recomputed rather than toggled.
    const BASE_SLOTS = new Set(Object.keys(LAYOUTS[0].chips));
    // Slots dev mode has been told this weapon does not have. Held here rather
    // than in the layouts, because it is an opinion about the weapon and the
    // layouts are a record of the game.
    const DROPPED = new Set();

    // What each layout changed about the base picture: its new chips, and the
    // neighbours the game pushed aside to make room. Composing two layouts
    // means composing these rather than the whole pictures -- the whole picture
    // also carries every chip the clip did not touch, and laying one over
    // another would undo the first one's reflow. The 20px floor is the drift
    // between one recording session and the next, which is not a move.
    const DIFFS = LAYOUTS.map((l) => {{
      const d = {{}};
      for (const [slot, p] of Object.entries(l.chips)) {{
        const b = LAYOUTS[0].chips[slot];
        if (!b || Math.abs(p.x - b.x) > 20 || Math.abs(p.y - b.y) > 20)
          d[slot] = p;
      }}
      return d;
    }});

    function openSlots() {{
      const grants = new Set(), blocks = new Set();
      for (const iid of Object.values(fitted)) {{
        const r = OPENS[iid];
        if (!r) continue;
        for (const s of r.grants) grants.add(s);
        for (const s of r.blocks) blocks.add(s);
      }}
      for (const s of blocks) grants.delete(s);
      return {{grants, blocks}};
    }}

    const sameSet = (set, list) =>
      set.size === list.length && list.every((x) => set.has(x));

    function unfit(slot) {{
      delete fitted[slot];
      const chip = chipFor(slot);
      if (chip) {{
        chip.classList.remove('has-item');
        chip.querySelector('.chip3__art').style.backgroundImage =
          'url({UP}smith/slot/' + slot + '.png)';
      }}
      for (const b of document.querySelectorAll('#sl-' + slot + ' .pcard'))
        b.classList.remove('is-fitted');
    }}

    function separate(chips) {{
      // Push overlapping chips apart, along whichever axis they overlap least,
      // until none touch. A handful of passes is plenty for twenty boxes, and
      // the alternative -- two chips stacked -- reads as a broken page rather
      // than as an arrangement we have not filmed.
      const keys = Object.keys(chips);
      const pos = {{}};
      for (const k of keys) pos[k] = {{x: chips[k].x, y: chips[k].y}};
      const GAP = CHIP + 8;
      for (let pass = 0; pass < 40; pass++) {{
        let touched = false;
        for (let i = 0; i < keys.length; i++) {{
          for (let j = i + 1; j < keys.length; j++) {{
            const a = pos[keys[i]], b = pos[keys[j]];
            const ox = GAP - Math.abs(a.x - b.x);
            const oy = GAP - Math.abs(a.y - b.y);
            if (ox <= 0 || oy <= 0) continue;
            touched = true;
            if (ox < oy) {{
              const s = (a.x < b.x ? -1 : 1) * ox / 2;
              a.x += s; b.x -= s;
            }} else {{
              const s = (a.y < b.y ? -1 : 1) * oy / 2;
              a.y += s; b.y -= s;
            }}
          }}
        }}
        if (!touched) break;
      }}
      const out = {{}};
      for (const k of keys)
        out[k] = Object.assign({{}}, chips[k],
          {{x: Math.round(pos[k].x), y: Math.round(pos[k].y)}});
      return out;
    }}

    function relayout() {{
      // Taking the riser off takes its two slots with it, and whatever was in
      // them. A few passes because that can cascade -- a part in a granted slot
      // could itself have granted another.
      for (let pass = 0; pass < 4; pass++) {{
        const {{grants, blocks}} = openSlots();
        let changed = false;
        for (const slot of Object.keys(fitted)) {{
          const open = BASE_SLOTS.has(slot) ? !blocks.has(slot) : grants.has(slot);
          if (!open) {{ unfit(slot); changed = true; }}
        }}
        if (!changed) break;
      }}

      const {{grants, blocks}} = openSlots();
      // The arrangement we have watched for exactly this configuration, if we
      // have one. Otherwise the base picture with each opened chip placed where
      // the clip that opened it had it: about where the game would put it,
      // without pretending we watched this combination.
      const exact = LAYOUTS.find(
        (l) => sameSet(grants, l.when) && sameSet(blocks, l.blocks));
      let chips = Object.assign({{}}, LAYOUTS[0].chips);
      if (exact) {{
        chips = Object.assign({{}}, exact.chips);
      }} else {{
        // No footage of this combination, so compose the ones it contains.
        // Whole layouts, not just their new chips: dropping a riser optic onto
        // the base positions would land it on top of the optic, because the
        // clip that opened it also shows the optic sliding out of the way.
        LAYOUTS.forEach((l, i) => {{
          if (!l.when.length && !l.blocks.length) return;
          if (l.when.every((s) => grants.has(s))
              && l.blocks.every((s) => blocks.has(s)))
            Object.assign(chips, DIFFS[i]);
        }});
        // A slot can be open without any single layout covering it: the 3/7
        // Adjustable Scope opens a kill flash and a red dot at once, and the
        // clips have those two apart. An open slot always gets a chip, from
        // wherever it was last seen; separate() sorts out where it lands.
        for (const slot of grants) {{
          if (chips[slot]) continue;
          const src = LAYOUTS.find((l) => l.chips[slot]);
          if (src) chips[slot] = src.chips[slot];
        }}
      }}
      for (const slot of blocks) delete chips[slot];
      for (const slot of Object.keys(chips))
        if (!BASE_SLOTS.has(slot) && !grants.has(slot)) delete chips[slot];
      for (const slot of DROPPED) delete chips[slot];
      // Two clips can each move the same neighbour a different way, and a
      // composed picture can land one chip on another. Only composed ones: a
      // layout we actually watched is left at the pixel it was measured at.
      if (!exact) chips = separate(chips);

      for (const c of document.querySelectorAll('.chip3')) {{
        const slot = c.dataset.slot;
        const p = chips[slot];
        const line = document.querySelector(
          '.stage__wires line[data-slot="' + slot + '"]');
        c.hidden = !p;
        // The attribute, not an inline display. This used to set style.display
        // because [hidden] on an SVG element did nothing; the sheet now carries
        // one [hidden] display-none-important rule for the whole page, and an
        // inline display of '' cannot argue with an !important one -- so every
        // granted slot's line stayed invisible however good its anchor was.
        if (line) line.toggleAttribute('hidden', !(p && p.ax != null));
        if (!p) continue;
        c.style.left = (p.x / FW * 100).toFixed(4) + '%';
        c.style.top = (p.y / FH * 100).toFixed(4) + '%';
        if (line && p.ax != null) {{
          line.setAttribute('x1', p.x + CHIP / 2);
          line.setAttribute('y1', p.y + CHIP / 2);
          line.setAttribute('x2', p.ax);
          line.setAttribute('y2', p.ay);
        }}
      }}
      // A slot that has just closed cannot stay the one on screen.
      if (cur.slot && !chips[cur.slot]) shut();
      if (DEV) pins(chips);
    }}

    // One dot per visible chip, on the end of its line. Rebuilt with the
    // layout rather than toggled, because which chips exist is the thing that
    // changes.
    function pins(chips) {{
      const box = document.querySelector('.pins');
      box.hidden = false;
      box.innerHTML = '';
      for (const [slot, p] of Object.entries(chips)) {{
        const ax = p.ax == null ? p.x + CHIP / 2 : p.ax;
        const ay = p.ay == null ? p.y + CHIP / 2 : p.ay;
        const el = document.createElement('button');
        el.className = 'pin' + (p.ax == null ? ' is-loose' : '');
        el.dataset.slot = slot;
        el.style.left = (ax / FW * 100).toFixed(4) + '%';
        el.style.top = (ay / FH * 100).toFixed(4) + '%';
        el.title = slot + ' — ' + ax + ', ' + ay;
        box.appendChild(el);
      }}
    }}

    // ---- the arithmetic -----------------------------------------------
    // Everything below works from `fitted`, so the numbers always describe the
    // build on screen. A candidate is judged against the build WITHOUT whatever
    // currently occupies its slot, because fitting it would replace that.
    // Catalogue stat key -> the weapon row it lands on, and how it combines.
    // The five the catalogue is supposed to carry. Everything else on a stat
    // row comes off a game card or not at all.
    // Capacity is not one of these and is not hedged either: it is a set value
    // read straight off the magazine, not a modifier anybody has to measure.
    const CORE = new Set(['Range', 'Control', 'Handling', 'Stability', 'Accuracy']);
    const MAP = {{}};
    for (const s of WEAPON) MAP[s.from || s.key] = s;

    function apply(out, iid) {{
      for (const [k, v] of Object.entries(DELTA[iid] || {{}})) {{
        const s = MAP[k];
        if (s && s.mode === 'set') out[s.key] = v;      // "Holds 45" is 45, not +45
        else if (s) out[s.key] = (out[s.key] ?? 0) + v;
        else out[k] = (out[k] ?? 0) + v;                // a stat with no row of its own
      }}
    }}

    function totals(skipSlot, add) {{
      const out = {{}};
      for (const s of WEAPON) out[s.key] = s.base;
      for (const [slot, iid] of Object.entries(fitted)) {{
        if (slot === skipSlot) continue;
        apply(out, iid);
      }}
      if (add) apply(out, add);
      return out;
    }}

    const unit = (k) => (WEAPON.find((s) => s.key === k) || {{}}).unit || '';
    const cap = (k) => (WEAPON.find((s) => s.key === k) || {{}}).max || 100;

    function paintWeapon() {{
      const now = totals(null, null);
      let html = '';
      for (const s of WEAPON) {{
        const v = now[s.key];
        const d = v - s.base;
        const pctBase = Math.max(0, Math.min(100, Math.min(v, s.base) / s.max * 100));
        const pctD = Math.max(0, Math.min(100, Math.abs(d) / s.max * 100));
        // Better, not bigger -- the quieter gunshot is the good one.
        const cls = (s.lower ? d < 0 : d > 0) ? 'up' : 'down';
        const pctStock = Math.max(0, Math.min(100, s.base / s.max * 100));
        html += '<div class="sr"><span class="sr__n">' + s.key + '</span>'
             + '<span class="sr__v' + (d ? ' ' + cls : '') + '">' + v + (s.unit || '')
             + (d ? ' <i class="' + cls + '">' + (d > 0 ? '+' : '&minus;')
                    + Math.abs(d) + '</i>' : '')
             + '</span><span class="sr__bar">'
             + '<i class="base" style="width:' + pctBase.toFixed(1) + '%"></i>'
             + (d ? '<i class="' + cls + '" style="width:' + pctD.toFixed(1) + '%"></i>' : '')
             + '<i class="stock" style="left:' + pctStock.toFixed(1) + '%"></i>'
             + '</span></div>';
      }}
      for (const s of SPECS) {{
        if (s.text !== undefined) {{
          html += '<div class="kv"><span>' + s.key + '</span><b>' + s.text + '</b></div>';
          continue;
        }}
        const pct = Math.max(0, Math.min(100, s.n / s.max * 100));
        html += '<div class="sr"><span class="sr__n">' + s.key + '</span>'
             + '<span class="sr__v">' + s.n + (s.unit || '') + '</span>'
             + '<span class="sr__bar"><i class="base" style="width:'
             + pct.toFixed(1) + '%"></i></span></div>';
      }}
      document.querySelector('.wstats').innerHTML = html;
    }}

    function paintDelta(slot, iid) {{
      // Against the build as it stands, not against the build with this slot
      // emptied. Swapping one optic for another should read as the two or three
      // points it actually moves, not as the whole of the new optic's effect.
      const before = totals(null, null);
      const after = totals(slot, iid);
      // Five of these stats are marked "not tracked" because nothing we hold
      // moves them, which is a fact about the data rather than about the gun.
      // It stops being true of a part somebody has read off the game's own
      // card: that card lists everything the part moves, so a line it does not
      // mention is a line that does not move. Saying "not tracked" there would
      // be hedging a thing we actually know.
      // Per item, and only on the five a card would answer. Whether some other
      // attachment somewhere moves fire rate is not the question here; whether
      // anybody has read THIS card is. The base stats have their own tag and
      // are not hedged twice.
      const unread = !READ.has(iid);
      let html = '';
      for (const s of WEAPON) {{
        const b = before[s.key], a = after[s.key];
        // Every stat, every time. Listing only what moves makes a short list
        // look like a complete one, and hides that the others were considered.
        const pctBase = Math.max(0, Math.min(100, Math.min(a, b) / s.max * 100));
        const pctD = Math.max(0, Math.min(100, Math.abs(a - b) / s.max * 100));
        // Green for better, not for bigger. Everywhere else those are the same
        // thing; on gunshot range the quieter number is the good one.
        const cls = (s.lower ? a < b : a > b) ? 'up' : 'down';
        const same = a === b;
        // Where the rifle sits with nothing on it. The two numbers on this row
        // are the build's and the change this part would make to it, and
        // neither says how far the build has already travelled from stock.
        const pctStock = Math.max(0, Math.min(100, s.base / s.max * 100));
        html += '<div class="sr' + (same ? ' is-flat' : '') + '">'
             + '<span class="sr__n">' + s.key
             + (unread && !CORE.has(s.key) && s.mode !== 'set'
                  ? ' <i class="untracked">not tracked</i>' : '') + '</span>'
             // The total takes the colour too. Left plain it reads as the
             // number the gun already has, with the change beside it as a
             // suggestion, when it is the number the gun would have.
             + '<span class="sr__v' + (same ? '' : ' ' + cls) + '">'
             + a + (s.unit || '')
             + (same ? '' : ' <i class="' + cls + '">(' + (a > b ? '+' : '&minus;')
                            + Math.abs(a - b) + ')</i>')
             + '</span><span class="sr__bar">'
             + '<i class="base" style="width:' + pctBase.toFixed(1) + '%"></i>'
             + (same ? '' : '<i class="' + cls + '" style="width:'
                            + pctD.toFixed(1) + '%"></i>')
             + '<i class="stock" style="left:' + pctStock.toFixed(1) + '%"></i>'
             + '</span></div>';
      }}
      // Stat lines the weapon panel has no base for — magazine capacity and the
      // like — still matter, so they are listed as the plain change they are.
      for (const [k, v] of Object.entries(DELTA[iid] || {{}})) {{
        if (MAP[k]) continue;
        html += '<div class="sr"><span class="sr__n">' + k + '</span>'
             + '<span class="sr__v ' + (v > 0 ? 'up' : 'down') + '">'
             + (v > 0 ? '+' : '&minus;') + Math.abs(v) + '</span></div>';
      }}

      const box = document.querySelector('#d-' + slot + '-' + iid + ' .delta');
      if (box) box.innerHTML = html;
    }}

    function paintEquip() {{
      if (!cur.item) {{ equipBtn.hidden = true; return; }}
      const on = fitted[cur.slot] === cur.item;
      equipBtn.hidden = false;
      equipBtn.textContent = on ? 'Unequip' : 'Equip';
      equipBtn.classList.toggle('is-fitted', on);
    }}

    // One card selected at a time, and one detail block shown for it.
    function pick(list, iid) {{
      for (const b of list.querySelectorAll('.pcard'))
        b.classList.toggle('is-on', b.dataset.item === iid);
      for (const d of list.querySelectorAll('.detail'))
        d.hidden = d.id !== 'd-' + list.id.slice(3) + '-' + iid;
      cur = {{slot: list.id.slice(3), item: iid}};
      paintDelta(cur.slot, iid);
      paintEquip();
    }}

    // One thing per slot: fitting a second replaces the first.
    function fit(slot, iid) {{
      const chip = chipFor(slot);
      fitted[slot] = iid;
      if (chip) {{
        chip.classList.add('has-item');
        chip.querySelector('.chip3__art').style.backgroundImage =
          'url({UP}att/' + iid + '.png)';
      }}
      for (const b of document.querySelectorAll('#sl-' + slot + ' .pcard'))
        b.classList.toggle('is-fitted', iid === b.dataset.item);
      relayout();
    }}

    equipBtn.addEventListener('click', () => {{
      if (!cur.item) return;
      if (fitted[cur.slot] === cur.item) unfit(cur.slot);
      else fit(cur.slot, cur.item);
      relayout();
      paintDelta(cur.slot, cur.item);
      paintWeapon();
      paintEquip();
    }});

    function showSlot(slot) {{
      showWeapon(false);
      let found = null;
      for (const l of lists) {{
        l.hidden = l.id !== 'sl-' + slot;
        if (!l.hidden) found = l;
      }}
      for (const c of document.querySelectorAll('.chip3'))
        c.classList.toggle('is-on', c.dataset.slot === slot);
      panel.hidden = !found;
      wrap.classList.toggle('is-open', !!found);
      stage.classList.toggle('is-focused', !!found);
      if (found) {{
        const first = found.querySelector('.pcard');
        if (first) pick(found, first.dataset.item);
        found.querySelector('.picks').scrollTop = 0;
        history.replaceState(null, '', '#' + slot + TAIL);
      }}
    }}

    function shut() {{
      panel.hidden = true;
      wrap.classList.remove('is-open');
      stage.classList.remove('is-focused');
      cur = {{slot: null, item: null}};
      equipBtn.hidden = true;
      for (const c of document.querySelectorAll('.chip3')) c.classList.remove('is-on');
      history.replaceState(null, '', location.pathname + (TAIL ? '#dev' : ''));
    }}

    for (const l of lists) {{
      l.addEventListener('click', (e) => {{
        const b = e.target.closest('.pcard');
        if (b) pick(l, b.dataset.item);
      }});
    }}

    // With the tables folded away, following a chip's own href would jump to a
    // heading inside a closed <details> and appear to do nothing. Opening it
    // first is what makes the no-JS fallback and the middle-click both land.
    const tables = document.getElementById('tables');
    if (tables) {{
      for (const a of document.querySelectorAll('a[href^="#slot-"]'))
        a.addEventListener('click', () => {{ tables.open = true; }});
      if (location.hash.startsWith('#slot-')) tables.open = true;
    }}

    for (const c of document.querySelectorAll('.chip3')) {{
      c.addEventListener('click', (e) => {{
        // Modified clicks keep their normal meaning: open the weapon page.
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        if (c.classList.contains('is-on')) shut();
        else showSlot(c.dataset.slot);
      }});
    }}
    // Full screen is offered only where the browser actually supports it —
    // an inert button is worse than no button.
    const expand = document.getElementById('expand');
    if (document.fullscreenEnabled) {{
      expand.hidden = false;
      expand.addEventListener('click', () => {{
        if (document.fullscreenElement) document.exitFullscreen();
        else wrap.requestFullscreen().catch(() => {{}});
      }});
      document.addEventListener('fullscreenchange', () => {{
        const on = document.fullscreenElement === wrap;
        expand.classList.toggle('is-on', on);
        expand.setAttribute('aria-label', on ? 'Exit full screen' : 'Full screen');
      }});
    }}

    const wtab = document.getElementById('wtab');
    const wpanel = document.getElementById('wpanel');
    function showWeapon(on) {{
      wpanel.hidden = !on;
      wtab.setAttribute('aria-expanded', String(on));
    }}
    // One at a time: the build panel opens where the attachment list sits, so
    // showing both means the top one covers the other.
    wtab.addEventListener('click', () => {{
      const opening = wpanel.hidden;
      if (opening) shut();
      showWeapon(opening);
    }});
    paintWeapon();
    relayout();

    document.getElementById('close').addEventListener('click', shut);
    addEventListener('keydown', (e) => {{ if (e.key === 'Escape') shut(); }});

    // Anywhere that is not the panel, a chip or the equip button closes it —
    // including the weapon itself. The chip and equip handlers run first and
    // are excluded here, or a chip click would open and then immediately close.
    document.addEventListener('click', (e) => {{
      // The build panel overlays the stage, so a click anywhere but on it
      // dismisses it — otherwise it sits over the chips and swallows them.
      if (!e.target.closest('.wname')) showWeapon(false);
      if (panel.hidden) return;
      if (e.target.closest('.panel, .chip3, #equip, .pins')) return;
      shut();
    }});
    if (location.hash) showSlot(HASH[0]);
{FORGE_CTRL}

    // Typing #dev onto a page that is already open only changes the hash, and
    // dev mode is decided at load. Reload for it, or the address bar and the
    // page disagree about which one you are looking at.
    addEventListener('hashchange', () => {{
      if (location.hash.slice(1).split('#').includes('dev') !== DEV)
        location.reload();
    }});

    // ---- dev mode ---------------------------------------------------------
    // Put #dev on the end of the hash to turn it on:
    //     gun-rm277.html#right-patch#dev
    // It edits the two things this page cannot derive — where a chip and the
    // end of its line sit, and which attachments a slot takes on this weapon —
    // and prints the file to paste back. Nothing is saved: the page is a view
    // of the repo, not a store, and a tool that wrote silently would be one
    // more place for the data to live.
    //
    // Everything it needs is fetched rather than baked in, so a reader who is
    // not editing carries none of it.
    if (DEV) dev();

    async function dev() {{
      const [doc, cat] = await Promise.all([
        fetch('{UP}data/gunsmith-rm277.json').then((r) => r.json()),
        fetch('{UP}data/attachments.json').then((r) => r.json()),
      ]);
      const named = {{}};
      for (const a of cat) named[a.id] = a.name;
      doc.edits = doc.edits || {{}};
      const ed = doc.edits;
      ed.slots = ed.slots || {{add: [], remove: []}};
      ed.fits = ed.fits || {{}};

      document.body.classList.add('is-dev');
      const bar = document.createElement('div');
      bar.className = 'devbar';
      const tabs = document.createElement('div');
      tabs.className = 'devtabs';
      document.querySelector('.gunsmith').prepend(bar);
      bar.after(tabs);

      // Half the slots are not on the bare rifle, so half of them cannot be
      // dragged until whatever opens them is fitted. These buttons fit it:
      // each one puts on the parts of a recorded arrangement, which is also
      // the only honest way to show one — the layout IS what is fitted, so
      // drawing it any other way would be drawing something the game does not.
      const shown = (iid) => {{
        const n = document.querySelector(
          '.pcard[data-item="' + iid + '"] .pcard__n');
        return n ? n.textContent.trim() : iid.replace(/-/g, ' ');
      }};
      function wear(by) {{
        for (const slot of Object.keys(fitted)) unfit(slot);
        relayout();
        // In order: a part can sit in a slot an earlier one opened. And when
        // it fits in two, the opened one wins — a micro sight riser is in the
        // optic list as well as the riser-optic list, and putting it in the
        // first would replace the riser that made the second exist.
        for (const iid of by) {{
          const open = lists.filter((l) => {{
            const chip = chipFor(l.id.slice(3));
            return chip && !chip.hidden
                && l.querySelector('.pcard[data-item="' + iid + '"]');
          }});
          const list = open.find((l) => !BASE_SLOTS.has(l.id.slice(3))) || open[0];
          if (list) fit(list.id.slice(3), iid);
        }}
        paintWeapon();
        say('');
      }}
      const configs = [{{by: [], name: 'Bare rifle'}}].concat(
        (doc.layouts || []).map((l) => ({{by: l.by, name: l.by.map(shown).join(' + ')}})));
      for (const c of configs) {{
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'devtab';
        btn.textContent = c.name;
        btn.addEventListener('click', () => wear(c.by));
        tabs.appendChild(btn);
      }}

      const out = document.createElement('div');
      out.className = 'devout';
      out.innerHTML = '<p class="dlabel">data/gunsmith-rm277.json</p>'
        + '<textarea class="out" spellcheck="false" rows="10"></textarea>'
        + '<p><button class="btn" type="button">Copy</button>'
        + '<button class="btn btn--ghost" type="button">Undo everything</button></p>';
      document.querySelector('.gunsmith').after(out);
      const text = out.querySelector('textarea');
      const [copyBtn, undoBtn] = out.querySelectorAll('button');
      const clean = JSON.stringify(doc);

      function say(msg) {{
        const {{grants, blocks}} = openSlots();
        const exact = LAYOUTS.find(
          (l) => sameSet(grants, l.when) && sameSet(blocks, l.blocks));
        const i = exact ? LAYOUTS.indexOf(exact) : -1;
        [...tabs.children].forEach((b, n) => b.classList.toggle('is-on', n === i));
        bar.innerHTML = '<b>Dev</b> <span>' + (exact
          ? 'editing the layout for: ' + (exact.when.length
              ? exact.when.join(', ') : 'the bare rifle')
          : 'this combination has no recorded layout, so chips cannot be moved '
            + '&mdash; line ends still can') + '</span>'
          + (msg ? '<em>' + msg + '</em>' : '');
        text.value = JSON.stringify(doc, null, 1);
      }}

      // Where a slot's numbers live in the file. An anchor is a point on the
      // weapon, so it is written everywhere that slot appears; a chip position
      // belongs to one arrangement, so it is written only to the one on screen.
      function homes(slot, anchor) {{
        const {{grants, blocks}} = openSlots();
        const hit = [];
        const base = doc.slots.find((s) => s.slot === slot);
        if (anchor) {{
          if (base) hit.push(base);
          for (const l of doc.layouts || [])
            if (l.chips[slot]) hit.push(l.chips[slot]);
          return hit;
        }}
        const i = LAYOUTS.findIndex(
          (l) => sameSet(grants, l.when) && sameSet(blocks, l.blocks));
        if (i < 0) return [];
        if (i === 0) return base ? [base] : [];
        const c = (doc.layouts[i - 1] || {{}}).chips || {{}};
        return c[slot] ? [c[slot]] : [];
      }}

      let drag = null;
      function frameXY(e) {{
        const r = stage.getBoundingClientRect();
        return [Math.round((e.clientX - r.left) / r.width * FW),
                Math.round((e.clientY - r.top) / r.height * FH)];
      }}

      stage.addEventListener('pointerdown', (e) => {{
        const pin = e.target.closest('.pin');
        const chip = e.target.closest('.chip3');
        if (!pin && !chip) return;
        const slot = (pin || chip).dataset.slot;
        const where = homes(slot, !!pin);
        if (!where.length) {{ say('nothing to write that to'); return; }}
        drag = {{slot, anchor: !!pin, where, moved: false,
                wasOpen: (pin || chip).classList.contains('is-on')}};
        stage.setPointerCapture(e.pointerId);
        e.preventDefault();
      }});
      stage.addEventListener('pointermove', (e) => {{
        if (!drag) return;
        const [x, y] = frameXY(e);
        for (const t of drag.where) {{
          if (drag.anchor) {{ t.ax = x; t.ay = y; }}
          else {{ t.x = x - CHIP / 2 | 0; t.y = y - CHIP / 2 | 0; }}
        }}
        drag.moved = true;
        pushLayouts();
        relayout();
        say(drag.slot + (drag.anchor ? ' line ends at ' : ' chip at ')
            + x + ', ' + y);
      }});
      stage.addEventListener('pointerup', () => {{
        // A drag that never moved was a click, and a click on a chip still
        // opens its list. It has to wait a tick: capturing the pointer on the
        // stage retargets the click there too, and the page's own handler reads
        // that as a click on the background and closes whatever is open.
        if (drag && !drag.moved && !drag.wasOpen) {{
          const slot = drag.slot;
          setTimeout(() => showSlot(slot), 0);
        }}
        drag = null;
      }});

      // The page draws from LAYOUTS; the file is what is edited. Copy across
      // after every change so the two cannot disagree about what is on screen.
      function pushLayouts() {{
        LAYOUTS[0].chips = doc.slots.reduce((a, s) => {{
          a[s.slot] = {{x: s.x, y: s.y, ax: s.ax, ay: s.ay}}; return a;
        }}, {{}});
        (doc.layouts || []).forEach((l, i) => {{
          LAYOUTS[i + 1].chips = Object.fromEntries(
            Object.entries(l.chips).map(([k, c]) =>
              [k, {{x: c.x, y: c.y, ax: c.ax, ay: c.ay}}]));
        }});
      }}

      // ---- the slot tables --------------------------------------------
      // Removing a row is a claim that the derived list is wrong for this
      // weapon, so it is recorded as a departure from that list rather than by
      // freezing a copy of it: add a rule tomorrow and every other weapon still
      // picks it up.
      function delta(slot) {{
        ed.fits[slot] = ed.fits[slot] || {{add: [], remove: []}};
        return ed.fits[slot];
      }}
      const strike = (id, list) => {{
        const i = list.indexOf(id);
        if (i >= 0) list.splice(i, 1);
      }};

      for (const sec of document.querySelectorAll('[id^="slot-"]')) {{
        const slot = sec.id.slice(5);
        const h2 = sec.querySelector('h2');
        const kill = document.createElement('button');
        kill.className = 'devx';
        kill.type = 'button';
        kill.textContent = 'remove slot';
        kill.addEventListener('click', () => {{
          sec.hidden = true;
          DROPPED.add(slot);
          strike(slot, ed.slots.add);
          if (!ed.slots.remove.includes(slot)) ed.slots.remove.push(slot);
          relayout();
          say('removed the ' + slot + ' slot');
        }});
        h2.appendChild(kill);

        for (const tr of sec.querySelectorAll('tbody tr')) {{
          const id = tr.dataset.item;
          const x = document.createElement('button');
          x.className = 'devx';
          x.type = 'button';
          x.textContent = '\\u00d7';
          x.title = 'This does not fit here';
          x.addEventListener('click', () => {{
            tr.hidden = true;
            const d = delta(slot);
            strike(id, d.add);
            if (!d.remove.includes(id)) d.remove.push(id);
            say('dropped ' + id + ' from ' + slot);
          }});
          tr.firstElementChild.appendChild(x);
        }}

        const add = document.createElement('p');
        add.className = 'devadd';
        add.innerHTML = '<select><option value="">Add an attachment&hellip;</option>'
          + cat.slice().sort((a, b) => a.name.localeCompare(b.name))
               .map((a) => '<option value="' + a.id + '">' + a.name + '</option>')
               .join('') + '</select>';
        add.querySelector('select').addEventListener('change', (e) => {{
          const id = e.target.value;
          if (!id) return;
          e.target.value = '';
          const d = delta(slot);
          strike(id, d.remove);
          if (!d.add.includes(id)) d.add.push(id);
          // Built as nodes rather than as a string: the name comes from a
          // data file and this is the one place on the page that would put it
          // straight into markup.
          const tr = document.createElement('tr');
          tr.dataset.item = id;
          const td = document.createElement('td');
          const a = document.createElement('a');
          a.href = id + '.html';
          a.textContent = named[id] || id;
          const flag = document.createElement('em');
          flag.className = 'devnew';
          flag.textContent = 'added';
          td.append(a, ' ', flag);
          tr.append(td);
          for (let i = 0; i < 2; i++) {{
            const c = document.createElement('td');
            c.className = 'none';
            c.textContent = '\u2014';
            tr.append(c);
          }}
          sec.querySelector('tbody').appendChild(tr);
          say('added ' + id + ' to ' + slot);
        }});
        sec.appendChild(add);
      }}

      const newSlot = document.createElement('p');
      newSlot.className = 'devadd devaddslot';
      newSlot.innerHTML = '<select><option value="">Add a slot&hellip;</option>'
        + SLOTS.map((s) => '<option value="' + s.id + '">' + s.label
                           + '</option>').join('') + '</select>';
      newSlot.querySelector('select').addEventListener('change', (e) => {{
        const id = e.target.value;
        if (!id) return;
        e.target.value = '';
        strike(id, ed.slots.remove);
        if (!ed.slots.add.includes(id)) ed.slots.add.push(id);
        DROPPED.delete(id);
        const back = document.querySelector('#slot-' + id);
        if (back) {{
          back.hidden = false;
          relayout();
          say('put the ' + id + ' slot back');
          return;
        }}
        // A slot the page has never drawn needs a chip before it can be
        // dragged, so one is parked in the middle for exactly that.
        if (!doc.slots.some((s) => s.slot === id))
          doc.slots.push({{slot: id, label: id, x: (FW - CHIP) / 2 | 0,
                          y: (FH - CHIP) / 2 | 0, ax: null, ay: null}});
        pushLayouts();
        relayout();
        say('added the ' + id + ' slot — regenerate for its chip and table');
      }});
      (document.getElementById('tables') || document.body).append(newSlot);

      copyBtn.addEventListener('click', () => {{
        text.select();
        if (navigator.clipboard)
          navigator.clipboard.writeText(text.value).catch(() => {{}});
      }});
      undoBtn.addEventListener('click', () => {{ location.reload(); }});

      pushLayouts();
      relayout();
      say('');
      // Losing an hour of dragging to a stray click is the failure this
      // prevents; the browser decides whether to honour it.
      addEventListener('beforeunload', (e) => {{
        if (JSON.stringify(doc) !== clean) e.preventDefault();
      }});
    }}
  </script>
"""
    return body

CSS = """
/* Hidden means hidden. The browser's own rule for [hidden] is the weakest
   there is, so any element given a display of its own quietly ignores it --
   and an invisible element that still takes its space and still swallows
   clicks is a bug that looks like nothing at all. This cost four separate
   fixes before it was worth one line: the panel, the slot lists, the chips,
   and the search suggestions, each found by a click landing on nothing.
   -------------------------------------------------------------------------- */
[hidden] { display: none !important; }

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

  /* Yellow is the caveat colour. The green accent marks what is finished, so
     the standing notice about what is *not* finished must not borrow it. */
  --warn: #f5d90a;
  --warn-line: #a08c05;
  --warn-ink: #17130a;

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
/* The mark sits inside the h1 rather than above it: one lockup, and it takes
   its size from the heading instead of needing its own at every breakpoint.
   Sized in em and nudged onto the baseline, so the h1 stays a line of text —
   making it a flex row would have relaid every other h1 on the site. display
   and margin are spelled out because the diagram rule further down sets every
   svg to block with auto margins, which put the mark on a line of its own. */
.mark {
  display: inline-block; width: 1.3em; height: 1.3em;
  vertical-align: -0.26em; margin: 0 12px 0 0;
}
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

/* Printed as the token you would type, not as a caption: uppercasing it would
   break the one thing it is for. */
.tag {
  font-family: var(--mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.02em;
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
/* A tag link wears the tag, so the sidebar teaches the search box's syntax
   rather than describing it somewhere else. */
.navlink--tag code {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.02em;
  color: var(--text-faint);
}
.navlink--tag:hover code, .navlink--tag.is-on code { color: inherit; }
.navlink:hover, .navlink:focus-visible { background: var(--surface-2); color: var(--text); }
.navlink.is-on { background: rgba(var(--accent-rgb), 0.12); color: var(--accent); }
.navlink.is-on em { color: var(--accent-dim); }

/* The notice sits in the flow, above the page wrapper: a full-width bar that
   the content begins below, so it covers nothing. It is the top of the
   document rather than a fixture of the viewport, so it scrolls away once
   read. */
.banner {
  font-size: 13px; color: var(--warn-ink); background: var(--warn);
  border-bottom: 1px solid var(--warn-line);
  /* Side padding tracks .wrap's own gutter, so the sentence lines up with the
     page content instead of running to the edges of a wide screen. */
  padding: 10px max(18px, calc((100vw - 1240px) / 2 + 18px));
}
.banner strong { color: var(--warn-ink); font-weight: 700; }
/* Inverted out of the yellow rather than set in it: a link the colour of the
   text it sits in is a link nobody sees, and this is the one thing on the
   notice anyone is meant to do. */
.banner__go {
  display: inline-block; margin-left: 10px; padding: 3px 11px;
  font-weight: 700; text-decoration: none; white-space: nowrap;
  color: var(--warn); background: var(--warn-ink); border-radius: 4px;
}
.banner__go:hover, .banner__go:focus-visible { background: #000; }

.tiles { display: grid; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(148px, 1fr)); }
.tile {
  position: relative; display: block; aspect-ratio: 4 / 3; overflow: hidden;
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  text-decoration: none;
}
.tile--gap { border-style: dashed; }
/* The tick on a finished gun. Top right, over the picture and clear of the
   name strip along the bottom, small enough to read as a mark on the tile
   rather than a badge stuck to it. */
.tile__done {
  position: absolute; top: 4px; right: 4px; z-index: 2;
  width: 15px; height: 15px; line-height: 15px; text-align: center;
  font-size: 10px; font-weight: 700; border-radius: 50%;
  color: var(--bg); background: var(--accent);
}
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

@media (max-width: 760px) {
  .browse { grid-template-columns: 1fr; }
  .browse__nav { position: static; }
}

/* --------------------------------------------------------------------------
   The gunsmith stage. Everything inside is positioned as a percentage of the
   frame the artwork was cut from, so the weapon, the chips and the wires scale
   together and cannot drift apart at any width.
   -------------------------------------------------------------------------- */
/* The slot panel, laid out as the game lays it out: the weapon fills the stage
   and the list and its detail sit ON it, down the left. Overlaid rather than
   beside, so opening a slot does not shrink the thing you are looking at. */
.gunsmith { display: block; }
.panel {
  /* Starts below the weapon name rather than under it. */
  position: absolute; inset: 54px auto 10px 10px; display: flex; gap: 8px;
  max-width: calc(100% - 20px); z-index: 3;
}
.slotlist { display: flex; gap: 8px; min-height: 0; }

/* Both columns scroll without showing a bar: they sit ON the weapon, and a
   scrollbar down the middle of the picture is the one piece of chrome the game
   does not have. Keyboard and wheel scrolling are untouched. */
.picks, .dpane { scrollbar-width: none; -ms-overflow-style: none; }
.picks::-webkit-scrollbar, .dpane::-webkit-scrollbar { width: 0; height: 0; }

.panel__x {
  position: absolute; top: 6px; right: 6px; z-index: 5;
  width: 26px; height: 26px; padding: 0; font-size: 17px; line-height: 1;
  cursor: pointer; border-radius: 4px; color: var(--text-dim);
  background: rgba(6, 14, 19, 0.9); border: 1px solid var(--line);
}
.panel__x:hover { color: var(--accent); border-color: var(--accent-dim); }

/* No padding along the top edge: the header is stuck to it, and any padding
   there is a gap the cards scroll up into and show through above the header.
   The header carries that space in its own padding instead. */
.picks {
  width: 208px; flex: 0 0 auto; display: flex; flex-direction: column; gap: 4px;
  overflow-y: auto; padding: 0 8px 8px; border-radius: 6px;
  background: rgba(6, 14, 19, 0.82); border: 1px solid var(--line);
  backdrop-filter: blur(3px);
}
.picks__h {
  position: sticky; top: 0; z-index: 2; margin: 0 -8px 4px; padding: 9px 10px;
  background: var(--bg); font-size: 12px; font-weight: 800;
  color: var(--accent); display: flex; align-items: baseline; gap: 8px;
}
.picks__h .count { margin-left: auto; font-family: var(--mono); font-size: 11px; color: var(--text-faint); }

.pcard {
  position: relative; display: block; width: 100%; padding: 5px 5px 3px;
  text-align: left; cursor: pointer; font: inherit; flex: 0 0 auto;
  background: rgba(14, 26, 33, 0.9); border: 1px solid var(--line); border-radius: 4px;
}
.pcard__n {
  display: inline-block; max-width: 100%; padding: 1px 6px; border-radius: 2px;
  font-size: 11px; line-height: 1.35; color: var(--text);
  background: rgba(255, 255, 255, 0.07);
}
.pcard__art {
  display: block; height: 46px; margin-top: 3px;
  background-repeat: no-repeat; background-position: center; background-size: contain;
}
.pcard:hover { border-color: var(--line-2); }
.pcard.is-on { border-color: var(--text); background: var(--surface-2); }
/* A fitted attachment is marked in the list, so the state is visible without
   opening its card. */
.pcard.is-fitted::after {
  content: "FITTED"; position: absolute; top: 4px; right: 4px;
  font-family: var(--mono); font-size: 8px; letter-spacing: 0.1em;
  color: var(--bg); background: var(--accent); border-radius: 2px; padding: 1px 4px;
}
.pcard__n.tier-green  { background: rgba(42, 202, 150, 0.22); }
.pcard__n.tier-blue   { background: rgba(88, 160, 221, 0.22); }
.pcard__n.tier-purple { background: rgba(155, 114, 221, 0.28); }
.pcard__n.tier-red    { background: rgba(218, 87, 88, 0.26); }

.dpane {
  width: 252px; flex: 0 0 auto; overflow-y: auto; padding: 0 12px 12px; border-radius: 6px;
  background: rgba(6, 14, 19, 0.82); border: 1px solid var(--line);
  backdrop-filter: blur(3px);
}
/* Pinned, and opaque. Padding alone does not help here: in a scrolling box the
   padding scrolls away with everything else, so the title slid up under the
   top edge and was cut in half. Sticking it means the rest passes behind it. */
.detail h4 {
  position: sticky; top: 0; z-index: 2;
  margin: 0 -12px 10px; padding: 12px 30px 8px 12px; font-size: 14px; font-weight: 800;
  background: rgb(7, 15, 20);
}
.detail h4 a { color: var(--text); text-decoration: none; }
.detail h4 a:hover { color: var(--accent); }
.tier {
  display: inline-block; width: 8px; height: 8px; margin-right: 7px;
  transform: rotate(45deg); vertical-align: 1px; border-radius: 1px;
}
.tier.green  { background: rgb(42, 202, 150); }
.tier.blue   { background: rgb(88, 160, 221); }
.tier.purple { background: rgb(155, 114, 221); }
.tier.red    { background: rgb(218, 87, 88); }

.dlabel {
  margin: 14px 0 6px; padding-top: 10px; border-top: 1px solid var(--line);
  font-family: var(--mono); font-size: 9px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase; color: var(--text-faint);
}
/* Scoped to both, not to .detail: the build panel uses the same row. */
.detail .kv, .wstats .kv {
  display: flex; align-items: baseline; font-size: 13px; color: var(--text-dim);
}
.detail .kv b, .wstats .kv b {
  margin-left: auto; font-family: var(--mono); color: var(--text);
}
.fx { font-size: 12px; color: var(--text-dim); padding: 2px 0 2px 12px; position: relative; }
.fx::before {
  content: ""; position: absolute; left: 0; top: 8px;
  width: 5px; height: 5px; background: var(--line-2); border-radius: 1px;
}
.fx.none { color: var(--text-faint); font-style: italic; padding-left: 0; }
.fx.none::before { display: none; }

.stiles { display: flex; flex-wrap: wrap; gap: 6px; }
/* Square, and the art fills it. The icons are 70x70 crops of the game's own
   chips — hatched ground included — so cover with a square box reproduces the
   chip exactly rather than floating a shrunken copy on a different backing. */
.stile {
  position: relative; display: block; width: 62px; aspect-ratio: 1; border-radius: 3px;
  background-color: var(--bg); background-repeat: no-repeat;
  background-position: center; background-size: cover;
  box-shadow: inset 0 0 0 1px var(--line);
}
.stile em {
  position: absolute; top: 0; left: 0; right: 0; padding: 3px 4px 4px;
  font-family: var(--mono); font-size: 8px; font-style: normal; line-height: 1.1;
  color: var(--text-dim);
  background: linear-gradient(to bottom, rgba(6, 14, 19, 0.85), transparent);
}

.sr { display: grid; grid-template-columns: 1fr auto; gap: 0 8px; margin-bottom: 7px; }
.sr__n { font-size: 12px; color: var(--text-dim); }
.sr__v { font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; }
.sr__v.up { color: var(--accent); }
.sr__v.down { color: var(--red); }
.sr__bar { grid-column: 1 / -1; height: 3px; border-radius: 2px; background: var(--surface-2); }
.sr__bar i { display: block; height: 100%; border-radius: 2px; }
.sr__bar i.up { background: var(--accent); }
.sr__bar i.down { background: var(--red); }

/* The weapon's two facts, set as a line of text rather than a table. */
/* The weapon's class and caliber live in the standfirst and are links. */
.sub a {
  color: var(--accent); font-weight: 600; text-decoration: none;
  border-bottom: 1px solid var(--accent-dim);
}
.sub a:hover, .sub a:focus-visible { border-bottom-color: var(--accent); }

/* The slot tables, folded. */
.deploy {
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
}
.deploy > summary {
  cursor: pointer; list-style: none; padding: 12px 16px;
  font-size: 17px; font-weight: 800; letter-spacing: 0.01em; color: var(--accent);
  display: flex; align-items: baseline; gap: 10px;
}
.deploy > summary::-webkit-details-marker { display: none; }
.deploy > summary::before {
  content: "\\25B8"; color: var(--accent-dim); font-size: 13px;
  transition: transform 120ms ease;
}
.deploy[open] > summary::before { transform: rotate(90deg); }
.deploy > summary:hover { background: var(--surface-2); }
.deploy > summary:focus-visible { outline: 2px solid var(--accent-dim); outline-offset: -2px; }
.deploy .hint {
  margin-left: auto; font-family: var(--mono); font-size: 11px; font-weight: 600;
  color: var(--text-faint);
}
.deploy__body {
  display: flex; flex-direction: column; gap: 28px;
  padding: 4px 16px 20px; border-top: 1px solid var(--line);
}
.deploy__body h2 { font-size: 15px; }
@media (prefers-reduced-motion: reduce) {
  .deploy > summary::before { transition: none; }
}

/* Bottom right, in the corner the game keeps its own screen controls in — and
   away from the card column, which fills the bottom left once a slot is open
   and put a card's border above and below the button. */
.expand {
  position: absolute; right: 16px; bottom: 16px; z-index: 3;
  width: 32px; height: 32px; padding: 0; cursor: pointer; border-radius: 4px;
  background: rgba(6, 14, 19, 0.7); border: 1px solid var(--line);
}
.expand svg { fill: none; stroke: var(--text-dim); stroke-width: 1.6; }
.expand:hover { border-color: var(--accent-dim); }
.expand:hover svg, .expand.is-on svg { stroke: var(--accent); }

/* Full screen keeps the stage's own proportions rather than stretching to the
   monitor's. Everything inside is positioned as a percentage of the stage, so
   letting it take a different aspect would skew the weapon and every chip on
   it; the box is sized to the taller or wider limit and centred instead. */
.gunsmith:fullscreen {
  display: grid; place-items: center;
  /* The backdrop wears the stage's own colours, so the strip left over by
     keeping the aspect ratio reads as more room rather than as a border. */
  background:
    radial-gradient(120% 90% at 50% 0%, #10333d 0%, transparent 60%),
    var(--surface);
}
.gunsmith:fullscreen .stage {
  width: min(100vw, calc(100vh * var(--ar)));
  border-radius: 0; border: 0; background: none;
}

/* The weapon name, top left of the stage, and the build panel it opens. */
.wname { position: absolute; top: 10px; left: 10px; z-index: 4; }
.wname__b {
  display: flex; align-items: center; gap: 9px; padding: 6px 11px;
  font: inherit; font-size: 17px; font-weight: 800; letter-spacing: -0.01em;
  cursor: pointer; color: var(--text); border-radius: 5px;
  background: rgba(6, 14, 19, 0.7); border: 1px solid var(--line);
}
.wname__b svg { fill: var(--text-dim); }
.wname__b:hover, .wname__b[aria-expanded="true"] { border-color: var(--accent-dim); }
.wname__b:hover svg, .wname__b[aria-expanded="true"] svg { fill: var(--accent); }
.wpanel {
  width: 258px; margin-top: 6px; padding: 12px; border-radius: 6px;
  background: rgba(6, 14, 19, 0.9); border: 1px solid var(--line);
  backdrop-filter: blur(3px);
}
.wpanel .dlabel { margin-top: 0; padding-top: 0; border-top: 0; }
.prov {
  display: block; margin-top: 3px; font-style: normal; text-transform: none;
  letter-spacing: 0; color: var(--warn);
}

/* A stat bar is white up to the figure the two readings share, then a coloured
   tail for the difference — added to the right, taken off the end. */
.sr__bar { display: flex; position: relative; }
.sr__bar i.base { background: var(--text-dim); }
/* Where the bare rifle sits on this bar. The bar shows what the gun would be
   and the slice this part moves it by, and until now there was nothing to
   measure either against: a build eight attachments deep looked the same as a
   stock one that happened to score the same. Absolute, so it does not take a
   share of the flex row -- it is a mark on the bar, not a part of it. */
.sr__bar i.stock {
  position: absolute; top: -3px; bottom: -3px; width: 2px; margin-left: -1px;
  height: auto; border-radius: 1px; background: var(--text); opacity: 0.6;
}
.sr__v i { font-style: normal; }
.sr__v i.up { color: var(--accent); }
.sr__v i.down { color: var(--red); }
.delta .sr:last-child { margin-bottom: 0; }
/* A stat this attachment leaves alone is still shown, just quietly. */
.sr.is-flat .sr__n, .sr.is-flat .sr__v { color: var(--text-faint); }
/* The commoner of the two debts, so it is drawn quieter: on most items it is
   the only tag there is, and at the same weight as #missing-info it would make
   the rare and urgent one impossible to pick out of a page of them. */
.tag--soft { color: var(--text-faint); border-color: var(--line); }
.sr__n .untracked {
  font-family: var(--mono); font-size: 8px; font-style: normal;
  letter-spacing: 0.08em; text-transform: uppercase; color: var(--warn);
  opacity: 0.75; margin-left: 5px;
}
.wstats .kv { padding: 3px 0; border-top: 1px solid var(--line); }
.wstats .kv:first-of-type { margin-top: 10px; }

/* Bottom right of the stage, where the game puts INSTALL. */
.equip {
  position: absolute; right: 64px; bottom: 16px; z-index: 3;
  font: inherit; font-size: 13px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; padding: 10px 26px; cursor: pointer;
  color: var(--bg); background: var(--accent); border: 0; border-radius: 4px;
}
.equip.is-fitted { color: var(--accent); background: transparent; border: 1px solid var(--accent); }

/* With a slot open the game shows only that slot's marker. */
.chip3.is-on { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-dim); }
.chip3.is-on .chip3__label { color: var(--accent); }
.chip3.has-item { border-color: var(--accent-dim); }
.stage.is-focused .chip3 { opacity: 0.18; }
.stage.is-focused .chip3.is-on { opacity: 1; }
.stage.is-focused .stage__wires { opacity: 0.25; }

@media (max-width: 900px) {
  .panel { position: static; inset: auto; max-width: none; margin-top: 10px; }
  .picks, .dpane { max-height: 52vh; }
  .picks { width: 45%; }
  .dpane { width: 55%; }
  .equip { position: static; display: block; width: 100%; margin-top: 10px; }
}
}

}

.shotlink { position: relative; display: inline-block; text-decoration: none; }
.shotlink__cue {
  display: block; margin-top: 6px; font-family: var(--mono); font-size: 10px;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-faint);
}
.shotlink:hover .shot, .shotlink:focus-visible .shot { border-color: var(--accent-dim); }
.shotlink:hover .shotlink__cue, .shotlink:focus-visible .shotlink__cue { color: var(--accent); }

.stage {
  position: relative; width: 100%; border: 1px solid var(--line);
  border-radius: 8px; overflow: hidden;
  container-type: inline-size;
  background:
    radial-gradient(120% 90% at 50% 0%, #10333d 0%, transparent 60%),
    var(--surface);
}
.stage__gun { position: absolute; object-fit: contain; }
.stage__wires {
  position: absolute; inset: 0; width: 100%; height: 100%;
  /* vector-effect keeps the hairline a hairline once the stage is scaled down;
     without it preserveAspectRatio="none" stretches the stroke too. */
  stroke: var(--line-2); stroke-width: 1; fill: none;
}
.stage__wires line { vector-effect: non-scaling-stroke; }

.chip3 {
  position: absolute; display: block; text-decoration: none;
  border: 1px solid var(--line-2); border-radius: 2px; background: rgba(6,14,19,.35);
  /* The fan reflows when a fitted part opens a slot rather than the new chip
     dropping into a gap, so the neighbours slide. Watching one move is what
     makes it read as the same chip. */
  transition: left 220ms ease, top 220ms ease;
}
@media (prefers-reduced-motion: reduce) {
  .chip3 { transition: none; }
}
.chip3__art {
  display: block; width: 100%; height: 100%;
  background-repeat: no-repeat; background-position: center; background-size: contain;
}
/* Clipped to the chip's width, and clipped at the front, which is why the game
   shows a Riser Optic as "ser Optic". Without it the long names on the optic
   arm -- Tactical Device, Riser Optic, Red Dot Optic, three in a row -- print
   over each other. `direction: rtl` does the front-clipping: the words are
   strong left-to-right so their order is untouched, only which end overflows.
   The full name is on the chip's title for anyone who needs it. */
.chip3__label {
  position: absolute; bottom: 100%; left: 0; margin-bottom: 3px;
  max-width: 100%; overflow: hidden; direction: rtl;
  font-size: 11px; line-height: 1; white-space: nowrap; color: var(--text-dim);
  /* Sized against the stage, not the page, so a label keeps the same share of
     its chip at every width -- the game's does, and a fixed 11px turned
     "Left Rail" into "eft Rail" on a narrow window. */
  font-size: clamp(8px, 0.82cqw, 15px);
}
.chip3 em {
  position: absolute; right: -1px; bottom: -1px; padding: 0 4px;
  font-family: var(--mono); font-size: 10px; font-style: normal;
  color: var(--bg); background: var(--accent-dim); border-radius: 2px 0 0 0;
}
.chip3:hover, .chip3:focus-visible {
  border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent-dim);
}
.chip3:hover .chip3__label, .chip3:focus-visible .chip3__label { color: var(--accent); }

 /* The dots layer sits over the chips, so it has to be transparent to the
   pointer or it swallows every click meant for a chip underneath. */
.pins { position: absolute; inset: 0; pointer-events: none; }
.pin { pointer-events: auto; }
.pin {
  position: absolute; width: 16px; height: 16px; margin: -8px 0 0 -8px;
  padding: 0; border: 2px solid var(--warn); border-radius: 50%;
  background: rgba(245,217,10,.25); cursor: grab; touch-action: none;
}
.pin:active { cursor: grabbing; }

/* --------------------------------------------------------------------------
   Smithing: the button in the corner, the mark that hammers while it thinks,
   and the drawer of builds it opens.
   -------------------------------------------------------------------------- */
/* Top right of the stage, in the corner opposite the weapon's name, so the
   two things you can do to the gun sit on the same line as the gun. */
.smith {
  position: absolute; top: 10px; right: 10px; z-index: 4;
  display: flex; align-items: center; gap: 8px; padding: 7px 12px;
  font: inherit; font-size: 12px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; cursor: pointer; color: var(--text);
  border-radius: 5px; background: rgba(6, 14, 19, 0.7);
  border: 1px solid var(--line);
}
.smith:hover:not(:disabled), .smith:focus-visible {
  border-color: var(--accent-dim); color: var(--accent);
}
.smith:disabled { cursor: default; color: var(--text-faint); }
.smith.is-on { color: var(--accent); border-color: var(--accent); }
.smith svg { display: block; }
.smith:hover:not(:disabled) svg .h { fill: var(--accent); }

/* The working overlay: the site's own mark, hammering, over the stage it is
   working on. There is nothing else to look at while it runs. */
.fwork {
  position: absolute; inset: 0; z-index: 6; display: grid; place-items: center;
  background: rgba(4, 10, 14, 0.72); backdrop-filter: blur(3px);
}
.fwork__box { width: min(340px, 80%); text-align: center; }
.fwork__art { position: relative; width: 118px; height: 118px; margin: 0 auto 20px; }
.fring { position: absolute; inset: 0; width: 100%; height: 100%; }
.fring circle { fill: none; stroke-width: 2.5; }
.fring__t { stroke: var(--line-2); }
.fring__s {
  stroke: var(--accent); stroke-linecap: round; stroke-dasharray: 66 210;
  transform-origin: 50% 50%; animation: fspin 1.15s linear infinite;
}
@keyframes fspin { to { transform: rotate(360deg); } }
.fanvil {
  position: absolute; inset: 19px;
  width: calc(100% - 38px); height: calc(100% - 38px);
}
/* The hammer swings from the far end of its handle, where a hand would hold
   it, so the head travels and the grip stays put. */
.fanvil__h {
  transform-box: view-box; transform-origin: 19.5px 11.5px;
  animation: fstrike 900ms cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.fanvil__a {
  transform-box: view-box; transform-origin: 32px 44px;
  animation: fshake 900ms linear infinite;
}
.fanvil__k {
  transform-box: view-box; transform-origin: 40px 30px; opacity: 0;
  animation: fspark 900ms linear infinite;
}
@keyframes fstrike {
  0% { transform: rotate(2deg); }
  40% { transform: rotate(-34deg); }
  52% { transform: rotate(-37deg); }
  66% { transform: rotate(5deg); }
  74% { transform: rotate(-2deg); }
  100% { transform: rotate(2deg); }
}
@keyframes fshake {
  0%, 62% { transform: translateY(0); }
  68% { transform: translateY(1.4px); }
  82%, 100% { transform: translateY(0); }
}
@keyframes fspark {
  0%, 62% { opacity: 0; transform: scale(0.3); }
  70% { opacity: 0.9; transform: scale(1); }
  92%, 100% { opacity: 0; transform: scale(1.7); }
}
/* Reduced motion means a smaller swing, not a still picture. A loading mark
   that does not move says the page has hung, which is the one thing it must
   not say, so the ring keeps turning and the hammer keeps time -- it just
   stops sweeping across a third of the frame, and the blow lands without the
   sparks or the shake. */
@media (prefers-reduced-motion: reduce) {
  .fanvil__h { animation-name: fnudge; }
  .fanvil__a, .fanvil__k { animation: none; }
}
@keyframes fnudge {
  0% { transform: rotate(1deg); }
  45% { transform: rotate(-7deg); }
  70% { transform: rotate(2deg); }
  100% { transform: rotate(1deg); }
}
.fwork__bar {
  height: 4px; border-radius: 2px; background: var(--surface-2); overflow: hidden;
}
/* No width transition: the width is driven frame by frame from script, easing
   toward a point just short of the next milestone, so the bar is always moving
   even while one slot is taking its time. A transition here would fight that.
   The sheen runs regardless, so the bar says "working" even at a standstill. */
.fwork__bar i {
  display: block; height: 100%; width: 0;
  background: linear-gradient(90deg,
    var(--accent-dim) 0%, var(--accent) 35%, #8ffbd0 50%,
    var(--accent) 65%, var(--accent-dim) 100%);
  background-size: 280% 100%;
  animation: fsheen 1.3s linear infinite;
}
@keyframes fsheen { from { background-position: 140% 0; } to { background-position: -140% 0; } }
/* The line that never stops: a running count of arrangements looked at, easing
   toward the real figure a frame at a time, and the seconds ticking beside it.
   The message above changes once a slot; this changes every frame, which is
   the difference between a screen that is working and one that has hung. */
.fwork__tick {
  margin: 4px 0 0; font-family: var(--mono); font-size: 10px;
  color: var(--text-faint); font-variant-numeric: tabular-nums;
  min-height: 1.4em;
}
@media (prefers-reduced-motion: reduce) {
  .fwork__bar i { animation: none; background: var(--accent); }
}
.fwork__say {
  margin: 12px 0 0; min-height: 3.2em; font-family: var(--mono); font-size: 11px;
  line-height: 1.6; color: var(--text-dim);
}
.fwork__say.is-new { animation: ffade 280ms ease; }
@keyframes ffade { from { opacity: 0; transform: translateY(3px); } }
@media (prefers-reduced-motion: reduce) { .fwork__say.is-new { animation: none; } }

/* The drawer. Fixed to the window rather than the page, so the weapon stays
   where it is and a build can be read against the gun it would make. */
.fside {
  /* The mirror of the attachment column: same inset from the stage, same
     glass, same border. One side of the gun lists the parts, the other lists
     the guns they make, and neither should look like a different program. */
  /* Stops short of the bottom rather than filling the stage: the strip along
     the foot is where the game keeps INSTALL and the screen control, and a
     panel that covers the full screen button is a panel you cannot get out
     from behind. */
  position: absolute; inset: 54px 10px 56px auto; z-index: 8;
  display: flex; flex-direction: column; gap: 9px;
  width: min(400px, 44%); padding: 0 12px 12px;
  overflow-y: auto; overscroll-behavior: contain;
  scrollbar-width: none; -ms-overflow-style: none;
  background: rgba(6, 14, 19, 0.82); backdrop-filter: blur(3px);
  border: 1px solid var(--line); border-radius: 6px;
  /* It comes in on the spot rather than sliding in from off the stage: there
     is no off the stage to slide in from, and clipping the stage to make one
     would cut the weapon name's panel off at the bottom. */
  opacity: 0; transform: translateX(10px);
  transition: opacity 190ms ease, transform 190ms ease;
}
.fside.is-open { opacity: 1; transform: none; }
.fside::-webkit-scrollbar { width: 0; height: 0; }
@media (prefers-reduced-motion: reduce) { .fside { transition: none; } }
/* Pinned to the top of the panel, and opaque, so the count is readable while
   you page through and the title does not slide up under the edge and get cut
   in half. Same reason the slot list's header is pinned, same shape of fix:
   the panel has no padding along the top, and the header carries it. */
.fside__top {
  position: sticky; top: 0; z-index: 3;
  display: flex; flex-direction: row; align-items: baseline; gap: 10px;
  margin: 0 -12px; padding: 9px 12px 7px; background: var(--bg);
}
.fside__top h2 { margin: 0; font-size: 17px; }
.fside__n {
  margin: 0; font-family: var(--mono); font-size: 11px; color: var(--text-faint);
}
.fside__x {
  margin-left: auto; padding: 0 2px; font: inherit; font-size: 22px; line-height: 1;
  cursor: pointer; color: var(--text-faint); background: none; border: 0;
}
.fside__x:hover { color: var(--accent); }
.fside__lede { margin: 0; font-size: 12px; line-height: 1.6; color: var(--text-dim); }
.fside__none { margin: 0; font-size: 12px; line-height: 1.6; color: var(--warn); }

/* Required parts: a type to narrow to, a name to search, and a chip per part
   asked for. The chips fold away, because the answer to "what did I ask for"
   is only wanted now and then and the list of builds is wanted always. */
.freq { display: grid; gap: 8px; }
.freq__bar {
  position: relative; display: grid; gap: 6px;
  grid-template-columns: minmax(0, 8.5rem) minmax(0, 1fr);
}
.freq__bar select, .fsearch input {
  width: 100%; font: inherit; font-size: 12px; padding: 7px 9px;
  color: var(--text); background: rgba(14, 26, 33, 0.9);
  border: 1px solid var(--line); border-radius: 5px;
}
.freq__bar select:focus, .fsearch input:focus {
  outline: none; border-color: var(--accent-dim);
}
.freq__t {
  display: flex; align-items: baseline; gap: 8px; width: 100%; padding: 0;
  font: inherit; font-family: var(--mono); font-size: 10px; letter-spacing: 0.1em;
  text-transform: uppercase; text-align: left; cursor: pointer;
  color: var(--text-faint); background: none; border: 0;
}
.freq__t::before { content: "\\25BE"; font-size: 9px; }
.freq__t[aria-expanded="false"]::before { content: "\\25B8"; }
.freq__t:hover { color: var(--accent); }
.freq__t em { margin-left: auto; font-style: normal; color: var(--text-dim); }
.fsearch { position: relative; }
.fsug {
  position: absolute; z-index: 5; top: calc(100% + 3px); left: 0; right: 0;
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--surface); border: 1px solid var(--line-2);
  border-radius: 5px; box-shadow: 0 8px 22px rgba(0, 0, 0, 0.5);
}
.fsug__i {
  display: flex; align-items: baseline; gap: 10px; padding: 7px 11px;
  font: inherit; font-size: 12px; text-align: left; cursor: pointer;
  color: var(--text); background: none; border: 0;
}
.fsug__i:hover { background: var(--surface-2); }
.fsug__i em {
  margin-left: auto; font-style: normal; font-family: var(--mono);
  font-size: 10px; color: var(--text-faint); white-space: nowrap;
}
.fsug__i.is-empty span, .fsug__i.is-empty em { color: var(--red); }

.fchips { display: flex; flex-wrap: wrap; gap: 5px; }
.fchip {
  display: inline-flex; align-items: baseline; gap: 8px;
  padding: 4px 4px 4px 10px; font-size: 12px; color: var(--text);
  background: var(--surface-2); border: 1px solid var(--line-2);
  border-radius: 4px;
}
.fchip em {
  font-style: normal; font-family: var(--mono); font-size: 10px;
  color: var(--text-faint);
}
.fchip.is-empty { border-color: var(--red); }
.fchip.is-empty em { color: var(--red); }
.fchip__x {
  font: inherit; font-size: 13px; line-height: 1; padding: 1px 5px;
  cursor: pointer; color: var(--text-faint); background: none; border: 0;
}
.fchip__x:hover { color: var(--red); }

/* One tab per stat. The tab is the sort: "show me the best handling" is the
   only question anyone opens this for, so it is the only control on top. */
/* Wrapping, not scrolling. There were five of these when the panel was drawn
   and there are eight now — the suppressor readings turned muzzle velocity,
   gunshot range and fire rate from columns nobody had into stats you can sort
   on — and a row that scrolls hides the ones added last behind an edge nobody
   thinks to drag. Two lines of four is worth more than one line and a secret. */
.ftabs {
  display: flex; flex-wrap: wrap; gap: 0 14px;
  border-bottom: 1px solid var(--line);
}
.ftab {
  flex: 0 0 auto; margin-bottom: -1px; padding: 6px 1px 7px;
  font: inherit; font-size: 11px; font-weight: 700; white-space: nowrap;
  cursor: pointer; color: var(--text-faint); background: none;
  border: 0; border-bottom: 2px solid transparent;
}
.ftab:hover { color: var(--text); }
.ftab.is-on { color: var(--accent); border-bottom-color: var(--accent); }

.forge__list { display: grid; gap: 4px; }
.fbuild {
  display: flex; align-items: center; gap: 12px; width: 100%;
  padding: 6px 11px; font: inherit; text-align: left; cursor: pointer;
  color: var(--text); background: rgba(14, 26, 33, 0.9);
  border: 1px solid var(--line); border-radius: 5px;
}
.fbuild:hover { border-color: var(--line-2); }
.fbuild.is-on { border-color: var(--accent); background: var(--surface-2); }
.fbuild__s { display: flex; gap: 10px; }
/* Each stat as a figure over its name, so a column of builds reads down as
   well as across and the numbers line up under the tab you chose. */
.fbuild__s i {
  display: flex; flex-direction: column; font-style: normal;
  font-family: var(--mono); font-size: 9px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--text-faint);
}
.fbuild__s b { font-size: 14px; font-weight: 700; letter-spacing: 0; color: var(--text); }
.fbuild__s b.up { color: var(--accent); }
.fbuild__s b.down { color: var(--red); }
.fbuild__s b.key { text-decoration: underline; text-underline-offset: 3px; }
.fbuild__n {
  margin-left: auto; font-family: var(--mono); font-size: 10px;
  color: var(--text-faint); white-space: nowrap;
}

.forge__pager { display: flex; flex-wrap: wrap; gap: 4px; }
.fpage {
  min-width: 2rem; padding: 5px 8px; font: inherit; font-size: 12px;
  font-family: var(--mono); cursor: pointer; color: var(--text-dim);
  background: rgba(14, 26, 33, 0.9); border: 1px solid var(--line); border-radius: 4px;
}
.fpage:hover:not(:disabled) { border-color: var(--line-2); color: var(--text); }
.fpage.is-on { color: var(--bg); background: var(--accent); border-color: var(--accent); }
.fpage:disabled { opacity: 0.35; cursor: default; }
.fgap { padding: 5px 2px; color: var(--text-faint); }

/* A floor per stat, below the list because it is the thing you reach for
   second: first look, then rule out. The number left of the slider is where it
   is set; the note under it is how far it could go before the list empties,
   which is the thing you actually want to know while dragging. */
.fmins { margin-top: auto; padding-top: 14px; border-top: 1px solid var(--line); }
.fmins .dlabel { margin-top: 0; padding-top: 0; border-top: 0; }
/* The dev bar's little clear button, but this one is for readers, so it is not
   one of the dev bar's classes -- a page that ships .devx to everyone makes
   "does this page carry any of the workbench" impossible to ask. */
.freset {
  font: inherit; font-size: 10px; margin-left: 8px; padding: 1px 6px;
  cursor: pointer; color: var(--red); background: transparent;
  border: 1px solid currentColor; border-radius: 3px;
}
.freset:hover { color: var(--bg); background: var(--red); }
.forge__mins { display: grid; gap: 4px; }
.fmin {
  display: grid; align-items: center; gap: 0 10px;
  grid-template-columns: 5.6rem 2.2rem minmax(0, 1fr);
  font-size: 12px; color: var(--text-dim);
}
.fmin__v {
  font-family: var(--mono); font-size: 13px; color: var(--text);
  text-align: right; font-variant-numeric: tabular-nums;
}
.fmin__n {
  grid-column: 2 / -1; margin-bottom: 3px; text-align: right;
  font-family: var(--mono); font-size: 10px; font-style: normal;
  color: var(--text-faint);
}
.fmin__n.is-over { color: var(--red); }
.fmin input[type="range"] { width: 100%; accent-color: var(--accent); }

/* On a narrow stage there is no room to sit beside the gun, so it takes the
   whole of it -- which is what closing it is for. */
@media (max-width: 760px) {
  .fside { inset: 54px 10px 56px 10px; width: auto; }
  .freq__bar { grid-template-columns: 1fr; }
}

/* --------------------------------------------------------------------------
   Dev mode: #dev on the end of the hash. None of this is reachable from the
   site, and the script that builds it does not run without the hash, so a
   reader carries the rules and nothing else.
   -------------------------------------------------------------------------- */
.devbar {
  grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 10px;
  align-items: baseline; padding: 7px 11px; border-radius: 5px;
  font-size: 12px; color: var(--bg); background: var(--warn);
}
.devbar b { letter-spacing: 0.08em; text-transform: uppercase; font-size: 10px; }
.devbar em { margin-left: auto; font-style: normal; font-family: var(--mono); }
.devtabs { display: flex; flex-wrap: wrap; gap: 6px; grid-column: 1 / -1; }
.devtab {
  font: inherit; font-size: 12px; padding: 5px 10px; cursor: pointer;
  color: var(--text-dim); background: var(--surface);
  border: 1px solid var(--line); border-radius: 5px;
}
.devtab:hover { border-color: var(--line-2); color: var(--text); }
.devtab.is-on {
  color: var(--bg); background: var(--warn); border-color: var(--warn);
}
.devout { margin-top: 14px; }
.devout .dlabel { margin-top: 0; padding-top: 0; border-top: 0; }
.devout textarea {
  width: 100%; resize: vertical;
  font-family: var(--mono); font-size: 12px; color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  padding: 12px;
}
.devout .btn { margin-right: 8px; }
.devx {
  font: inherit; font-size: 10px; margin-left: 8px; padding: 1px 6px;
  cursor: pointer; color: var(--red); background: transparent;
  border: 1px solid currentColor; border-radius: 3px;
}
.devx:hover { color: var(--bg); background: var(--red); }
.devadd { margin: 8px 0 0; }
.devadd select {
  font: inherit; font-size: 12px; padding: 5px 8px; color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--line); border-radius: 5px;
}
.devnew {
  font-family: var(--mono); font-size: 9px; font-style: normal;
  letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent);
}
/* A dot with no line yet: it sits on its own chip until it is dragged off. */
.pin.is-loose { border-style: dashed; border-color: var(--red); }
body.is-dev .chip3 { cursor: grab; }

.btn {
  font: inherit; font-size: 13px; padding: 7px 14px; cursor: pointer;
  color: var(--bg); background: var(--accent); border: 0; border-radius: 6px;
}
.out {
  font-family: var(--mono); font-size: 12px; color: var(--text-dim);
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  padding: 12px; overflow-x: auto; max-height: 40vh;
}

@media (max-width: 700px) {
  .chip3__label { font-size: 9px; }
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
  .banner { padding: 9px 12px; font-size: 12px; }
}
"""

# The stylesheet's address carries its own fingerprint, so a changed sheet is a
# different URL and no cache anywhere can serve yesterday's.
#
# This is not hypothetical tidiness. Twice now a deployed page has looked
# broken on a machine where the file on the server was perfectly correct, and
# both times the answer was a stylesheet the browser had already decided it
# knew: once the whole page lost its layout, once the smithing button sat in
# the wrong corner while lines pointed at attachment slots that were not
# there. The page and the sheet have to change together or the page is a lie,
# and the only way to promise that is to make them one thing.
CSS_V = hashlib.md5(CSS.encode('utf-8')).hexdigest()[:10]


WEAPONS = json.loads((ROOT / 'data/weapons.json').read_text(encoding='utf-8'))
AMMO = json.loads((ROOT / 'data/ammo.json').read_text(encoding='utf-8'))
WEAPON_NAME = {w['id']: w['name'] for w in WEAPONS}
DOCUMENTED = {'rm277'}
# Weapons whose gunsmith layout has been traced from the game.
GUNSMITHS = {'rm277'}
PAGES = ['gun-rm277.html']   # documented weapons, for the sitemap
SITE = 'https://eukyrios.github.io/weapon-smith/'

# The mark: a hammer over an anvil. Drawn on a 64 grid in three tones — steel
# for the anvil, a darker steel for the waist it stands on, accent green for the
# hammer, because a smith's tools are the thing being lit and the anvil is what
# they land on. Built from filled masses rather than outlines: a stroked drawing
# silts up at tab size, a silhouette survives it. The horn points away from the
# hammer so the two shapes never touch at small sizes. Every edge is a straight
# line or a rounded corner, which is what lets tools/make-og.py redraw the same
# mark with Pillow: one geometry, two renderers, no drift.
_MARK = """  <g fill="#95a8b4">
    <path d="M13 34h36v6H13l-6-3z"/>
    <path d="M24 46h14l7 7H17z"/>
    <rect x="15" y="52.4" width="34" height="3.6" rx="1.4"/>
  </g>
  <path d="M19 40h24l-5 6H24z" fill="#5e7381"/>
  <path d="M33 30l5-5-16-16-5 5z" fill="#0a8f57"/>
  <path d="M31 33l7 2 9-9-2-7-7 2z" fill="#0ff796"/>"""

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" '
           'role="img" aria-label="Weapon Smith">\n'
           '  <rect width="64" height="64" rx="12" fill="#060e13"/>\n'
           + _MARK + '\n</svg>\n')

# In the page the mark is decoration beside a heading that already says the
# name, so it is hidden from screen readers rather than announced twice. The
# newlines are squeezed out because it goes inline into an h1.
LOGO = ('<svg class="mark" viewBox="0 0 64 64" aria-hidden="true" '
        'focusable="false">' + ' '.join(_MARK.split()) + '</svg>')

OG = SITE + 'og.png'
OG_ALT = ('Weapon Smith &mdash; a Delta Force: Operations weapon, ammunition '
          'and attachment library, and a build maker on top of it')


def attr(text):
    """Text going into an attribute. The descriptions are prose and prose has
    quotation marks in it; everything else here is already entity-escaped."""
    return text.replace('"', '&quot;')


def head(title, desc, path, css_href=None, crumb=''):
    """What a crawler is given, on every one of the 596 pages.

    Copied in shape from the sibling site, which learned it the hard way: the
    canonical and og:url must be absolute and must agree, the description is
    written for the page rather than the site (596 pages sharing one sentence
    is 595 pages telling Google they are duplicates), and the icon and theme
    colour are what make the tab recognisable.

    `path` is the page's address under SITE and doubles as the depth: a page
    inside catalogue/ reaches the icon one level up.
    """
    # Descriptions are assembled from clauses that come and go with the data,
    # so tidy the seams here rather than at every call site.
    desc = ' '.join(desc.split())
    up = '../' if '/' in path else ''
    url = SITE + path
    style = (f'<link rel="stylesheet" href="{css_href}?v={CSS_V}">' if css_href
             else f'<style>{CSS}</style>')
    return '\n'.join([
        '<!doctype html>',
        '<html lang="en">',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<title>{title}</title>',
        f'<meta name="description" content="{attr(desc)}">',
        f'<link rel="canonical" href="{url}">',
        f'<link rel="icon" type="image/svg+xml" href="{up}favicon.svg">',
        '<meta name="color-scheme" content="dark">',
        '<meta name="theme-color" content="#060e13">',
        '',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Weapon Smith">',
        f'<meta property="og:title" content="{attr(title)}">',
        f'<meta property="og:description" content="{attr(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{OG}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{OG_ALT}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{attr(title)}">',
        f'<meta name="twitter:description" content="{attr(desc)}">',
        f'<meta name="twitter:image" content="{OG}">',
        '',
        ld_json(desc, path, crumb),
        style,
    ])


def ld_json(desc, path, crumb):
    """Structured data: what kind of thing this page is, not what words are on
    it. The front page is the site; every other page is a leaf under it, and
    saying so as a breadcrumb is what puts the trail under the result instead
    of a bare URL. A page with no crumb name gets no block rather than a
    half-filled one."""
    if not path:
        data = {
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            'name': 'Weapon Smith',
            'url': SITE,
            'description': desc,
            'inLanguage': 'en',
            'image': OG,
        }
    elif crumb:
        data = {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1,
                 'name': 'Weapon Smith', 'item': SITE},
                {'@type': 'ListItem', 'position': 2,
                 'name': crumb, 'item': SITE + path},
            ],
        }
    else:
        return ''
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False)
            + '</script>')

NAV = ('  <nav class="nav">\n'
       '    <a href="{up}">&larr; {back}</a>\n'
       '  </nav>\n')


def banner(path=''):
    """The standing notice, on every page.

    Written from DOCUMENTED and WEAPONS rather than typed out, because the one
    thing a notice like this must never do is keep saying "one weapon" after the
    second one lands. When the count changes the sentence changes with it, and
    when every weapon is covered the notice stops printing itself.

    It ends with a way to the weapons it is talking about. A notice that names
    the one finished gun and then leaves the reader to go and find it is doing
    half a job, and the pages that most need this notice -- the 65 that carry
    no attachment list -- are exactly the ones furthest from the gun that does.
    `path` is the page the notice is on, so it does not offer a page a link to
    itself.
    """
    total = len(WEAPONS)
    fin = sorted(w for w in DOCUMENTED if is_finished(w))
    started = sorted(DOCUMENTED - set(fin))
    if len(fin) >= total:
        return ''
    named = ', '.join(WEAPON_NAME.get(w, w) for w in fin)
    one = len(fin) == 1

    # Written from the counts, because the one thing a notice like this must
    # never do is go on saying "one weapon" after the second one lands, or keep
    # calling a gun finished while it still owes a stat line. Both facts are
    # computed: DOCUMENTED says who has a list, is_finished says who has been
    # read to the end, and the sentence changes shape when either does.
    if fin:
        head = (f'{"The " + named + " is" if one else named + " are"} done '
                f'&mdash; every slot listed and every attachment read &mdash; '
                f'{"and it is" if one else "and they are"} '
                f'{"the only one" if one else f"{len(fin)}"} of {total} so far. '
                'A tick on a weapon in the list means the same has been done '
                'for it.')
    else:
        head = f'None of the {total} weapons is finished yet.'
    part = ''
    if started:
        s_named = ', '.join(WEAPON_NAME.get(w, w) for w in started)
        part = (f' {s_named} {"has" if len(started) == 1 else "have"} a list '
                'and is still being read.' if len(started) == 1 else
                f' {s_named} have lists and are still being read.')
    return (
        '<aside class="banner">\n'
        f'    <strong>Early days.</strong> This site is being written as the '
        f'game is read. {head}{part} I enter this by hand, one attachment at a '
        'time, so the first few guns will take a while. It gets faster as it '
        'goes: most of what a new gun takes is already catalogued, so there '
        'are fewer attachments left to add each time. Every other weapon page '
        'carries what the catalogue knows and says so.'
        + ''.join(f'\n    <a class="banner__go" href="{UP}{gun_file(w)}">'
                  f'See the {WEAPON_NAME.get(w, w)} &rarr;</a>'
                  for w in sorted(DOCUMENTED) if gun_file(w) != path)
        + '\n</aside>\n')


def shell(title, eyebrow, h1, sub, body, nav, css_href=None,
          desc='', path='', crumb=''):
    """`css_href` links a shared stylesheet instead of inlining it. The
    catalogue is 439 pages; inlining 5KB of CSS into each costs 2MB of repo for
    nothing. The two hand-shared pages stay self-contained so they can be
    published or emailed on their own."""
    return '\n'.join([
        head(title, desc, path, css_href, crumb),
        '',
        banner(path),
        '<div class="wrap">',
        '',
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

    The front page carries no back link: there is nothing above it on this
    site, and it is not a page of the sibling site to be returned from.
    """
    # What the site is FOR, then what it holds. The optimiser is written as
    # coming rather than working, because it is: the banner on every page says
    # early days and a description that oversells it would be the one place on
    # the site that lies about the state of it.
    desc = (f'Build Delta Force: Operations loadouts. A library of '
            f'{len(WEAPONS)} weapons, {len(AMMO)} rounds and {len(items)} '
            'attachments, with every slot on a gun, what it accepts and which '
            'attachments open more &mdash; and a build optimiser in progress '
            'that picks the parts maximising the stat you choose.')
    return shell(
        'Weapon Smith &mdash; Delta Force: Operations build maker',
        'Delta Force &middot; Operations', LOGO + 'Weapon Smith', '',
        catalogue_browser(items, by_caliber, pages=UP, art=''), '',
        desc=desc, path='')


def moved(title, to, up, note='This moved up a level.', tab=None):
    """A page that is only an address, pointing at the one that replaced it.

    Three things have to agree or a forward is worse than a 404: the refresh
    sends the reader, the canonical sends the crawler, and noindex says not to
    keep this page in its own right — the canonical alone leaves that to
    Google's judgement, and Google's judgement is that a page which exists is
    a page worth keeping. The link is for anyone whose browser refuses the
    refresh, which is not nobody.
    """
    return ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
            f'<title>{tab or title + " &middot; Weapon Smith"}</title>\n'
            f'<meta http-equiv="refresh" content="0; url={up}{to}">\n'
            f'<link rel="canonical" href="{SITE}{to}">\n'
            '<meta name="robots" content="noindex, follow">\n'
            f'<p>{note} '
            f'<a href="{up}{to}">{title} &rarr;</a></p>\n')


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
    (out / 'smith.css').write_text(CSS, encoding='utf-8')

    # Site furniture. Generated too, so a new weapon page reaches the sitemap
    # without anyone remembering to add it.
    (out / '.nojekyll').write_text('', encoding='utf-8')
    (out / 'favicon.svg').write_text(FAVICON, encoding='utf-8')
    (out / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n\nSitemap: ' + SITE + 'sitemap.xml\n',
        encoding='utf-8')

    # Every page, not a hand-kept list of two. A catalogue is worth nothing to
    # a reader who cannot be shown the page holding the thing they searched
    # for, and a crawler that has to find 595 pages by walking the front page's
    # filter finds them slowly. changefreq and priority are hints Google mostly
    # ignores; they are here to say which pages are the ones being worked on.
    urls = [('', 'weekly', '1.0')]
    urls += [(p, 'weekly', '0.8') for p in PAGES]
    urls += [(gun_file(w['id']), 'monthly', '0.6')
             for w in WEAPONS if gun_file(w['id']) not in PAGES]
    urls += [(ammo_file(a['id']), 'monthly', '0.5') for a in AMMO]
    urls += [(f"{i['id']}.html", 'monthly', '0.5') for i in items.values()]
    (out / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'  <url>\n    <loc>{SITE}{u}</loc>\n'
                  f'    <changefreq>{freq}</changefreq>\n'
                  f'    <priority>{pr}</priority>\n  </url>\n'
                  for u, freq, pr in urls)
        + '</urlset>\n', encoding='utf-8')
    print(f'wrote sitemap.xml with {len(urls)} urls')
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

    TITLES = {f"{i['id']}.html": i['name'] for i in items.values()}
    TITLES.update({gun_file(w['id']): w['name'] for w in WEAPONS})
    TITLES.update({ammo_file(a['id']): a['name'] for a in AMMO})

    # The pages are siblings of the index now: /gun-rm277.html rather than
    # /catalogue/gun-rm277.html. The folder said nothing the page did not —
    # every page on this site is a catalogue page — and it cost a level of
    # nesting in every address and every link out of one.
    written = []
    for i in items.values():
        written.append(f"{i['id']}.html")
        (out / written[-1]).write_text(
            item_page(i, accepted.get(i['id'], [])), encoding='utf-8')
    for w in WEAPONS:
        written.append(gun_file(w['id']))
        (out / written[-1]).write_text(gun_page(w), encoding='utf-8')
    for a in AMMO:
        written.append(ammo_file(a['id']))
        (out / written[-1]).write_text(
            ammo_page(a, guns_by_caliber.get(a['caliber'], [])), encoding='utf-8')
    # The editor moved into the weapon page; this was its address for a while.
    for wid in sorted(GUNSMITHS):
        (out / f'smith-{wid}.html').write_text(
            moved(WEAPON_NAME.get(wid, wid), gun_file(wid), UP,
                  'The gunsmith is part of the weapon page now.'), encoding='utf-8')

    # Every one of those pages answered at /catalogue/ until now, and those
    # addresses are in the sitemap Google has already read, in the links from
    # the sibling site, and in whatever anyone bookmarked. Each becomes a
    # signpost to the page one level up rather than a 404. A forwarding page
    # is a quarter of a kilobyte; throwing away every link that already points
    # into this site costs rather more than 600 of them.
    cat = out / 'catalogue'
    cat.mkdir(exist_ok=True)
    (cat / 'index.html').write_text(
        moved('Weapon Smith', '', '../', 'The catalogue is the front page now.',
              'Catalogue &middot; Weapon Smith'), encoding='utf-8')
    for name in written:
        (cat / name).write_text(moved(TITLES[name], name, '../'), encoding='utf-8')
    for wid in sorted(GUNSMITHS):
        (cat / f'smith-{wid}.html').write_text(
            moved(WEAPON_NAME.get(wid, wid), gun_file(wid), '../'), encoding='utf-8')

    # A renamed item leaves its old page behind, and a stale page is worse than
    # a missing one — it is reachable, wrong, and looks maintained. So the run
    # keeps a list of what it wrote and removes anything the last run wrote
    # that this one did not.
    #
    # A list rather than "delete every .html and write them all again": the
    # root is not this script's to sweep. It holds a Google Search Console
    # verification file, which is an .html this tool did not write and whose
    # disappearance is silent — the console simply stops believing the site is
    # yours. Deleting only what is on the list cannot reach anything this tool
    # did not put there in the first place.
    mine = sorted({'index.html', *written,
                   *(f'smith-{w}.html' for w in GUNSMITHS),
                   'catalogue/index.html',
                   *(f'catalogue/{n}' for n in written),
                   *(f'catalogue/smith-{w}.html' for w in GUNSMITHS)})
    before = set(MANIFEST.read_text(encoding='utf-8').split()) \
        if MANIFEST.exists() else set()
    for gone in sorted(before - set(mine)):
        stale = out / gone
        if stale.exists():
            stale.unlink()
            print(f'removed {gone} — no longer generated')
    MANIFEST.write_text('\n'.join(mine) + '\n', encoding='utf-8')

    print(f'wrote index.html and {len(written)} pages, '
          f'{len(written) + len(GUNSMITHS) + 1} forwards from catalogue/')
