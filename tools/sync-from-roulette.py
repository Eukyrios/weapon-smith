#!/usr/bin/env python3
"""Pull the two things this repo does NOT own from loadout-roulette.

Attachments and slot rules are authored here, in src/data/. Still authored next
door are the weapon roster (it drives the roulette's reels) and the ammunition
table, along with all three picture mirrors that `npm run icons` fills.

So this script copies exactly those two, and nothing else:

    data/weapons.json   names, classes and calibers
    data/ammo.json      the ammunition table
    att/  gear/  ammo/  item, weapon and round pictures

Run it when a weapon is added next door or the picture mirror is refreshed.
Everything else comes from `npm run gen`.
"""
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIBLING = ROOT.parent / 'loadout-roulette'

DATA = ['weapons.json', 'ammo.json']


def main() -> int:
    if not SIBLING.is_dir():
        print(f'not found: {SIBLING}\n'
              'This script needs loadout-roulette beside weapon-smith. The '
              'committed weapons.json and att/ are still usable without it.',
              file=sys.stderr)
        return 1

    # The weapon roster still lives in the sibling's TypeScript, so ask it to
    # dump. Nothing else here depends on that dump succeeding.
    dump = SIBLING / 'tools' / 'dump-smith-data.ts'
    if dump.is_file():
        print('dumping in', SIBLING.name)
        subprocess.run(['npx', 'vite-node', 'tools/dump-smith-data.ts'],
                       cwd=SIBLING, shell=(sys.platform == 'win32'))

    src = SIBLING / 'tools' / '.smith'
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    for name in DATA:
        f = src / name
        if not f.is_file():
            print(f'missing {f}', file=sys.stderr)
            return 1
        shutil.copy2(f, out / name)
    print(f'copied {", ".join(DATA)}')

    # Pictures. Mirrored next door by `npm run icons`; copied rather than
    # hotlinked so this site makes no request to the other one.
    for folder in ('att', 'gear', 'ammo'):
        src_dir = SIBLING / 'public' / folder
        if not src_dir.is_dir():
            print(f'no public/{folder} next door — run `npm run icons` there')
            continue
        out_dir = ROOT / folder
        out_dir.mkdir(exist_ok=True)
        n = 0
        for f in src_dir.glob('*.png'):
            dst = out_dir / f.name
            if not dst.exists() or dst.stat().st_mtime < f.stat().st_mtime:
                shutil.copy2(f, dst)
                n += 1
        print(f'{folder}/: {n} new or changed '
              f'({len(list(out_dir.glob("*.png")))} total)')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
