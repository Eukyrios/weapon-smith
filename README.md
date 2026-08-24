# Weapon Smith

Every attachment slot on every Delta Force: Operations gun, and what fits in
it — published at <https://eukyrios.github.io/weapon-smith/>.

The point of the project is the next step: with the slot lists and the per-item
stat lines in one place, a loadout can be **searched** rather than assembled by
hand. "The RM277 build with the most accuracy" becomes a query over legal
combinations rather than an afternoon in the gunsmith.

## Layout

    index.html            the weapon list
    catalogue/            one page per weapon, round and attachment,
                          plus an index of all 590
    smith.css             shared stylesheet
    att/                  item pictures, copied from loadout-roulette
    data/*.json           the item data this site is generated from
    tools/                the generator and the sync script

    src/data/*.ts         the attachment data, authored here
    package.json          Vite, for `npm run dev` and the TypeScript

GitHub Pages serves the committed HTML from the repo root, so there is no build
step. Vite is here for the dev server and the TypeScript, not to build the site.

## Working on it

    npm install
    npm run dev      serve the site at localhost:5173
    npm run gen      re-dump src/data to data/*.json, then rebuild every page
    npm run check    run the data's own consistency checks
    npm run typecheck

Everything under `catalogue/`, plus `index.html`, is generated. Edit
`src/data/` or the generator, never the HTML — a hand edit is overwritten on
the next `npm run gen`.

A weapon's slot tables live inside its catalogue page, in a fold-out panel.
There is no separate per-weapon URL: two pages serving the same tables is two
pages to keep in step, and search engines pick one of them at random.

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
