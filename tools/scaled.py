#!/usr/bin/env python3
"""The multiplier behind a scaled stat, solved from every reading of it.

    python tools/scaled.py add silent-suppressor "Fire rate" mk47 543
    python tools/scaled.py solve silent-suppressor "Fire rate"
    python tools/scaled.py check

WHY THIS IS NOT ARITHMETIC YOU CAN DO IN YOUR HEAD

Three stats -- fire rate, muzzle velocity, gunshot heard -- do not add. The
game multiplies the weapon's base and rounds the result UP, so what a card
shows for one part is a different number on every gun, and the thing worth
recording is the multiplier rather than any of the numbers. See
src/data/weapon-stats.ts for the evidence that settles that.

A reading does not give you the multiplier. It gives you a RANGE: if the
game shows 620 on a base of 525, then ceil(525 * r) == 620, so r is somewhere
in (619/525, 620/525] -- a window about a fifth of a percent wide. One reading
never narrows it further than that, and eyeballing a value out of it is how
1.688 and 1.69 become indistinguishable.

Two readings of the same part on two DIFFERENT weapons intersect, and the
window collapses. That is the whole idea here: the readings are kept, every
one of them, and the multiplier is derived from all of them at once and
re-derived whenever another arrives. A part read on one gun has a loose
answer that gets tighter for free the next time it turns up on another.

AN EMPTY INTERSECTION IS A FINDING, NOT AN ERROR TO ROUND AWAY. It means one
of the readings is wrong -- and since the disagreements are always a single
digit, it says exactly which card wants looking at again. The Silent
Suppressor's fire rate is the standing example.
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATS = ROOT / 'data/scaled-stats.json'

# Whole percents first, then halves, then tenths. A game's numbers are round;
# twenty-one arbitrary decimals would not be. Where the window admits a tidy
# value that is the answer, and where it does not the window says so.
LADDER = [('a whole percent', 100), ('a half percent', 200), ('a tenth', 1000)]


def bases():
    """Every traced weapon's base figures. A reading needs one to mean anything."""
    out = {}
    for p in sorted((ROOT / 'data').glob('gunsmith-*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        rows = d.get('weapon', {}).get('stats') or []
        if rows:
            out[d['weapon']['id']] = {r['key']: r['base'] for r in rows}
    return out


def scaled_keys():
    rows = json.loads((ROOT / 'data/weapon-stats.json').read_text(encoding='utf-8'))
    return {r['key'] for r in rows if r.get('mode') == 'scale'}


def load():
    """The whole file. `items` is what everything below works on."""
    return json.loads(STATS.read_text(encoding='utf-8'))


def readings_of(doc):
    """Readings in the shape the solver wants: item, stat -> [{weapon, shown}]."""
    return {i: {k: [{'weapon': w, 'shown': v} for w, v in sorted(e['read'].items())]
                for k, e in st.items()}
            for i, st in doc['items'].items()}


def resolve(doc, B):
    """Rewrite every `basis` and `multiplier` from the readings. Derived data
    does not get to drift from the thing it is derived from."""
    for item, st in doc['items'].items():
        for stat, e in st.items():
            rs = [{'weapon': w, 'shown': v} for w, v in e['read'].items()]
            m, how, lo, hi, _ = solve(item, stat, rs, B)
            nb = len({B[r['weapon']][stat] for r in rs
                      if stat in B.get(r['weapon'], {})})
            e['basis'] = ('contested' if m is None and nb >= 2
                          else 'assumed' if nb < 2 else 'proven')
            e['multiplier'] = None if e['basis'] == 'contested' else m


def save(doc):
    doc['items'] = {i: {k: doc['items'][i][k] for k in sorted(doc['items'][i])}
                    for i in sorted(doc['items'])}
    STATS.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')


def window(base, shown):
    """Every r with ceil(base * r) == shown, as (low, high]: low exclusive."""
    return ((shown - 1) / base, shown / base)


def basis(stat, rs, B):
    """What these readings ESTABLISH about this part, on their own.

    Never across parts. Two suppressors that both come out at x0.7 say nothing
    about either of them: the goal is the multiplier for THIS attachment, and a
    coincidence between two different ones is not evidence about either.

    Everything turns on how many DIFFERENT bases the part has been read on:

      one base    flat and scaled fit identically and always will. A delta and
                  a multiplier that agree on one weapon are the same claim
                  there and different claims everywhere else, and nothing in
                  the readings picks between them. UNDETERMINED, whatever is
                  stored.
      two or more the two models make different predictions and the readings
                  choose. This is the only thing that establishes anything.
    """
    pts = [(B.get(r['weapon'], {}).get(stat), r['shown']) for r in rs]
    pts = [(b, s) for b, s in pts if b is not None]
    nb = len({b for b, _ in pts})
    if nb < 2:
        return 'one base', None, None
    flat = min((max(abs((b + d) - s) for b, s in pts), d)
               for d in sorted({s - b for b, s in pts}))
    lo = max((s - 1) / b for b, s in pts)
    hi = min(s / b for b, s in pts)
    if lo < hi:
        return f'{nb} bases', flat[0], 0
    scal = min((max(abs(math.ceil(b * r) - s) for b, s in pts), r)
               for r in [s / b for b, s in pts])
    return f'{nb} bases', flat[0], scal[0]


def verdict(stat, rs, B):
    """One line saying what is known, in the terms that matter."""
    where, fmiss, smiss = basis(stat, rs, B)
    if where == 'one base':
        return ('ONE BASE ONLY -- flat and scaled fit this identically; '
                'the multiplier below is an assumption, not a finding')
    if smiss == 0:
        return (f'read on {where}: scaled fits exactly, flat is out '
                f'(best flat delta misses by {fmiss})')
    return (f'read on {where}: neither fits exactly -- scaled misses by '
            f'{smiss}, flat by {fmiss}')


def solve(item, stat, rs, B):
    """(multiplier, how it was chosen, low, high, conflicts) from the readings."""
    lo, hi, seen = 0.0, float('inf'), []
    for r in rs:
        b = B.get(r['weapon'], {}).get(stat)
        if b is None:
            seen.append((r, None))
            continue
        w = window(b, r['shown'])
        seen.append((r, w))
        lo, hi = max(lo, w[0]), min(hi, w[1])
    usable = [(r, w) for r, w in seen if w]
    if not usable:
        return None, 'no reading on a weapon whose base is known', lo, hi, []
    if lo >= hi:
        # Which readings cannot hold together, and what a one-off fix would be.
        bad = []
        for r, w in usable:
            others = [x for y, x in usable if y is not r]
            if others and (max(x[0] for x in others) >= w[1]
                           or min(x[1] for x in others) <= w[0]):
                b = B[r['weapon']][stat]
                for d in (1, -1):
                    l2, h2 = window(b, r['shown'] + d)
                    l3 = max([l2] + [x[0] for x in others])
                    h3 = min([h2] + [x[1] for x in others])
                    if l3 < h3:
                        bad.append(f"{r['weapon']} reads {r['shown']}; "
                                   f"{r['shown'] + d} would fit "
                                   f"({l3:.5f}..{h3:.5f})")
        return None, 'readings disagree', lo, hi, bad
    for name, step in LADDER:
        hits = [n / step for n in range(1, 20 * step)
                if lo < n / step <= hi]
        if hits:
            return hits[0], name, lo, hi, []
    return hi, 'nothing tidy in the window, so its top end', lo, hi, []


def report(item, stat, rs, B):
    m, how, lo, hi, bad = solve(item, stat, rs, B)
    reads = ', '.join(f"{r['weapon']} {r['shown']}" for r in rs)
    print(f'{item}  ::  {stat}')
    print(f'  readings   {reads}')
    print(f'  basis      {verdict(stat, rs, B)}')
    if lo < hi:
        print(f'  window     {lo:.6f} .. {hi:.6f}'
              f'   ({(hi - lo) * 100:.3f} percentage points wide)')
    if m is None:
        print(f'  NO MULTIPLIER FITS -- {how}')
        for b in bad:
            print(f'     {b}')
        return False
    print(f'  multiplier {m:g}   ({how})')
    for r in rs:
        b = B.get(r['weapon'], {}).get(stat)
        if b is not None:
            print(f'     {r["weapon"]:8} ceil({b} x {m:g}) = {math.ceil(b * m)}'
                  f'   read {r["shown"]}'
                  f'{"" if math.ceil(b * m) == r["shown"] else "   <-- MISMATCH"}')
    return True


def show(item, stat, e, was_basis, was_mult, was_read, B):
    """What this reading changed, and what the site will do differently.

    The point of the whole arrangement is that a reading can only add truth, so
    the useful thing to print is not the new state but the TRANSITION -- an
    assumption becoming a finding, or a multiplier being withdrawn and every
    weapon falling back to the card it has of its own.
    """
    fits = json.loads((ROOT / 'data/fits.json').read_text(encoding='utf-8'))
    takes = sorted({w for w, b in fits.items()
                    for ids in b.values() if item in ids})
    fmt = lambda m: 'no multiplier' if m is None else f'x{m:g}'
    moved = (was_basis, was_mult) != (e['basis'], e['multiplier'])
    print(f'\n  was        {was_basis}, {fmt(was_mult)}')
    print(f'  now        {e["basis"]}, {fmt(e["multiplier"])}'
          + ('' if moved else '   (unchanged)'))
    if e['basis'] == 'contested' and was_mult is not None:
        print('  ->         THE MULTIPLIER IS WITHDRAWN. Every weapon now uses '
              'the figure its own card showed, and a weapon with no card shows '
              'no change rather than a wrong one.')
    elif e['basis'] == 'proven' and was_basis != 'proven':
        print('  ->         an assumption became a finding: read on a second '
              'base, and the multiplier is now the only one that fits both.')
    print('\n  what the site shows for this part now:')
    for w in takes:
        b = B.get(w, {}).get(stat)
        if b is None:
            continue
        old_v = (was_read.get(w) if w in was_read else
                 (math.ceil(b * was_mult - 1e-9) if was_mult is not None else None))
        if w in e['read']:
            new_v, how = e['read'][w], 'its own card'
        elif e['multiplier'] is not None:
            new_v, how = math.ceil(b * e['multiplier'] - 1e-9), f'x{e["multiplier"]:g}'
        else:
            new_v, how = None, 'no claim'
        a = '--' if new_v is None else str(new_v)
        note = '' if old_v == new_v else (
            f'   (was {"--" if old_v is None else old_v})')
        print(f'     {w:8} {a:>6}   {how}{note}')


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__.strip().split('\n\n')[0])
    cmd, B, SC, d = argv[1], bases(), scaled_keys(), load()

    if cmd == 'add':
        _, _, item, stat, weapon, shown = argv
        if stat not in SC:
            raise SystemExit(f'{stat!r} is not a scaled stat. These are: '
                             + ', '.join(sorted(SC))
                             + '\nA stat that adds needs no multiplier; write it '
                               'straight into card-facts.ts.')
        if weapon not in B:
            raise SystemExit(f'{weapon!r} has no base figures on file, so a shown '
                             'value there says nothing about a multiplier.\n'
                             'Weapons that do: ' + ', '.join(sorted(B)))
        e = d['items'].setdefault(item, {}).setdefault(
            stat, {'read': {}, 'basis': 'assumed', 'multiplier': None})
        was_basis, was_mult = e.get('basis'), e.get('multiplier')
        was_read = dict(e['read'])
        was = e['read'].get(weapon)
        if was == int(shown):
            print('already recorded, unchanged')
        elif was is not None:
            print(f'{weapon} was {was}, now {shown}')
        e['read'][weapon] = int(shown)
        e['read'] = dict(sorted(e['read'].items()))
        resolve(d, B)
        save(d)
        print()
        rs = [{'weapon': w, 'shown': v} for w, v in e['read'].items()]
        ok = report(item, stat, rs, B)
        show(item, stat, e, was_basis, was_mult, was_read, B)
        return 0 if ok else 1

    if cmd == 'solve':
        _, _, item, stat = argv
        rs = (readings_of(d).get(item) or {}).get(stat)
        if not rs:
            raise SystemExit(f'no readings recorded for {item} :: {stat}')
        return 0 if report(item, stat, rs, B) else 1

    if cmd == 'table':
        # Every reading, laid out the way it was gathered: one row per part and
        # stat, one column per weapon. What was READ is printed plain; what the
        # multiplier PREDICTS for a weapon nobody has checked it on is in
        # brackets. The difference matters -- a bracketed figure is this file's
        # own arithmetic and cannot confirm anything, and a second real reading
        # in one of those columns is exactly what tightens the multiplier.
        facts = json.loads((ROOT / 'data/card-facts.json').read_text(encoding='utf-8'))
        att = {a['id']: a['name'] for a in
               json.loads((ROOT / 'data/attachments.json').read_text(encoding='utf-8'))}
        unc = json.loads((ROOT / 'data/uncatalogued.json').read_text(encoding='utf-8'))
        fits = json.loads((ROOT / 'data/fits.json').read_text(encoding='utf-8'))
        name = lambda i: att.get(i) or (unc.get(i) or {}).get('name') or i
        guns = sorted(B)
        rows, nread, npred = [], 0, 0
        for item, stats in sorted(readings_of(d).items(), key=lambda kv: name(kv[0]).lower()):
            takes = {w for w, b in fits.items()
                     for ids in b.values() if item in ids}
            for stat, rs in sorted(stats.items()):
                got = {r['weapon']: r['shown'] for r in rs}
                m = (d['items'][item][stat]).get('multiplier')
                cells = []
                for w in guns:
                    b = B.get(w, {}).get(stat)
                    if w in got:
                        cells.append(str(got[w])); nread += 1
                    elif w not in takes or b is None:
                        cells.append('-')
                    elif m is not None:
                        cells.append(f'({math.ceil(b * m)})'); npred += 1
                    else:
                        cells.append('?')
                where, fm, sm = basis(stat, rs, B)
                mark = ('assumed' if where == 'one base'
                        else 'proven' if sm == 0 else 'CONTESTED')
                rows.append((name(item), stat, f'{m:g}' if m else '?', cells, mark))
        w0 = max(len(r[0]) for r in rows) + 2
        w1 = max(len(r[1]) for r in rows) + 2
        print(f'{"":{w0}}{"":{w1}}{"x":>7}{"basis":>11}'
              + ''.join(f'{g:>9}' for g in guns))
        last = None
        for nm, stat, m, cells, mark in rows:
            b = ''.join(f'{B.get(g, {}).get(stat, "-"):>9}' for g in guns)
            print(f'{nm if nm != last else "":{w0}}{stat:{w1}}{m:>7}{mark:>11}{b}   base')
            print(f'{"":{w0}}{"":{w1}}{"":>7}{"":>11}'
                  + ''.join(f'{c:>9}' for c in cells))
            last = nm
        tally = {}
        for *_, mark in rows:
            tally[mark] = tally.get(mark, 0) + 1
        print(f'\n{nread} read, {npred} predicted (in brackets), '
              f'- where the weapon does not take the part.')
        print('basis: ' + ', '.join(f'{v} {k}' for k, v in sorted(tally.items())))
        print('  proven    read on two or more bases, and scaled fits where flat does not')
        print('  assumed   read on ONE base, where flat and scaled are the same claim')
        print('  CONTESTED read on two bases and nothing fits both')
        return 0

    if cmd == 'check':
        # Two things: that the derived fields still follow from the readings,
        # and that every reading is reproduced by what the site will use for
        # that weapon -- which is the reading itself, so this is really a check
        # that nothing in the file has been hand-edited into disagreeing.
        import copy
        before = copy.deepcopy(d['items'])
        resolve(d, B)
        bad = 0
        for item, st in sorted(d['items'].items()):
            for stat, e in sorted(st.items()):
                was = before[item][stat]
                if (was.get('basis'), was.get('multiplier')) != (e['basis'], e['multiplier']):
                    bad += 1
                    print(f'STALE    {item} :: {stat}  file says '
                          f'{was.get("basis")}/{was.get("multiplier")}, '
                          f'readings say {e["basis"]}/{e["multiplier"]}'
                          f'   -- run `scaled.py solve` or re-add a reading')
                m = e['multiplier']
                if m is None:
                    continue
                for w, shown in e['read'].items():
                    b = B.get(w, {}).get(stat)
                    if b is not None and math.ceil(b * m - 1e-9) != shown:
                        bad += 1
                        print(f'MISMATCH {item} :: {stat} :: {w}  multiplier '
                              f'{m:g} shows {math.ceil(b * m - 1e-9)}, '
                              f'reading is {shown}')
        n = sum(len(v) for v in d['items'].values())
        nr = sum(len(e['read']) for v in d['items'].values() for e in v.values())
        tal = {}
        for v in d['items'].values():
            for e in v.values():
                tal[e['basis']] = tal.get(e['basis'], 0) + 1
        print(f'{"FAIL" if bad else "ok"}  {n} scaled stats, {nr} readings, '
              + ', '.join(f'{v} {k}' for k, v in sorted(tal.items()))
              + f', {bad} problem(s)')
        return 1 if bad else 0

    raise SystemExit(f'unknown command {cmd!r}; try add, solve, table or check')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
