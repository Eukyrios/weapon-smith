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
READINGS = ROOT / 'data/scaled-readings.json'

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
    return json.loads(READINGS.read_text(encoding='utf-8')) if READINGS.is_file() else {}


def save(d):
    READINGS.write_text(json.dumps(d, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def window(base, shown):
    """Every r with ceil(base * r) == shown, as (low, high]: low exclusive."""
    return ((shown - 1) / base, shown / base)


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
        rs = d.setdefault(item, {}).setdefault(stat, [])
        for r in rs:
            if r['weapon'] == weapon:
                if r['shown'] == int(shown):
                    print('already recorded, unchanged')
                    break
                print(f'{weapon} was {r["shown"]}, now {shown}')
                r['shown'] = int(shown)
                break
        else:
            rs.append({'weapon': weapon, 'shown': int(shown)})
        rs.sort(key=lambda r: r['weapon'])
        save(d)
        print()
        return 0 if report(item, stat, rs, B) else 1

    if cmd == 'solve':
        _, _, item, stat = argv
        rs = (d.get(item) or {}).get(stat)
        if not rs:
            raise SystemExit(f'no readings recorded for {item} :: {stat}')
        return 0 if report(item, stat, rs, B) else 1

    if cmd == 'check':
        facts = json.loads((ROOT / 'data/card-facts.json').read_text(encoding='utf-8'))
        bad = 0
        for item, stats in sorted(d.items()):
            for stat, rs in sorted(stats.items()):
                held = ((facts.get(item) or {}).get('stats') or {}).get(stat)
                m, how, lo, hi, _ = solve(item, stat, rs, B)
                for r in rs:
                    b = B.get(r['weapon'], {}).get(stat)
                    if b is None or held is None:
                        continue
                    got = math.ceil(b * held)
                    if got != r['shown']:
                        bad += 1
                        print(f'MISMATCH {item} :: {stat} :: {r["weapon"]}  '
                              f'card-facts has {held:g}, which shows {got}, '
                              f'but the reading is {r["shown"]}')
                if held is None:
                    bad += 1
                    print(f'MISSING  {item} :: {stat} has readings and no '
                          f'multiplier in card-facts.ts'
                          + (f' (solve says {m:g})' if m else ''))
                elif m is not None and not (lo < held <= hi):
                    bad += 1
                    print(f'LOOSE    {item} :: {stat}  card-facts has {held:g}, '
                          f'outside the window {lo:.6f}..{hi:.6f}')
        n = sum(len(v) for v in d.values())
        print(f'{"FAIL" if bad else "ok"}  {n} scaled stats, '
              f'{sum(len(r) for v in d.values() for r in v.values())} readings, '
              f'{bad} problem(s)')
        return 1 if bad else 0

    raise SystemExit(f'unknown command {cmd!r}; try add, solve or check')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
