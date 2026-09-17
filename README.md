# Weapon Smith

Every attachment slot on every Delta Force: Operations gun, and what fits in
it — published at <https://eukyrios.github.io/weapon-smith/>.

The point of the project is the next step: with the slot lists and the per-item
stat lines in one place, a loadout can be **searched** rather than assembled by
hand. "The RM277 build with the most accuracy" becomes a query over legal
combinations rather than an afternoon in the gunsmith.

## Layout

    index.html            the weapon list
    *.html                one page per weapon, round and attachment,
                          593 of them, beside the index
    catalogue/            where those pages used to live; forwards only
    smith.css             shared stylesheet
    att/                  item pictures, copied from loadout-roulette
    data/*.json           the item data this site is generated from
    tools/                the generator and the sync script

    src/data/*.ts         the attachment data, authored here
    package.json          Vite, for `npm run dev` and the TypeScript

The generated files are **not committed**. `.github/workflows/pages.yml` runs
`npm run gen` and uploads the result, so the site is built on every push and the
HTML exists only in the deployed artifact. Vite is here for the dev server and
the TypeScript, not to build the site — the generator is standard-library
Python, which is why CI needs no more than node, python and `npm ci`.

They used to be committed, and that put a second copy of every page on
`raw.githubusercontent.com`. That host serves no robots.txt, so crawlers
indexed the repo's copy and ranked it above the real site on GitHub's domain
authority; a canonical pointing home is only a cross-domain hint and was being
ignored. With nothing generated in git, those URLs 404 instead.

Run `npm run gen` after cloning, or the site is not there to serve.

## Working on it

    npm install
    npm run dev      serve the site at localhost:5173
    npm run gen      re-dump src/data to data/*.json, then rebuild every page
    npm run check    run the data's own consistency checks
    npm run typecheck

Every `.html` in the repo is generated, including `index.html` and everything
in `catalogue/`. Edit `src/data/` or the generator, never the HTML — a hand
edit is overwritten on the next `npm run gen`.

A weapon's slot tables live inside its own page, in a fold-out panel. There is
no separate per-weapon URL: two pages serving the same tables is two pages to
keep in step, and search engines pick one of them at random.

The pages sat under `catalogue/` until August 2026 and now sit beside the
index — `/gun-rm277.html`, not `/catalogue/gun-rm277.html`. The folder said
nothing the page did not, since every page here is a catalogue page. It still
exists, holding one forwarding page per old address: those addresses are in the
sitemap Google has already read and in whatever anyone bookmarked, and a
quarter of a kilobyte each is cheaper than throwing them away.

## Where the data lives

**Attachments and slot rules are authored here**, in `src/data/attachments.ts`
and `src/data/attach-rules.ts`. This repo is their source of truth;
[loadout-roulette](https://github.com/eukyrios/loadout-roulette) keeps a copy,
refreshed with `node tools/sync-attachment-data.mjs` there.

Two things are still authored next door and copied in — the weapon roster,
which drives that app's reels, and the item pictures it mirrors:

    npm run sync

## Checks

`npm run check` runs the assertions the data makes about itself: that no rule
points at an item that does not exist, that every slot key names a real slot,
and that the three optic pools still nest. The lists are transcribed by ear
weeks apart, so these catch what review cannot.

## Adding a weapon

Slot lists are transcribed one weapon at a time into `src/data/attach-rules.ts`.
Once a weapon has lists, add its id to `DOCUMENTED` and `PAGES`, extend
`SECTIONS` and the tree in `tools/gen-weapon-smith.py`, then rebuild.
