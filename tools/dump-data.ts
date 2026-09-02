/**
 * Dump src/data/*.ts to data/*.json for the page generator.
 *
 * The generator is Python and the data is TypeScript, so something has to cross
 * the gap. Doing it here rather than hand-maintaining JSON means the two can
 * never disagree: `npm run gen` re-dumps before it builds, so a rename in
 * attach-rules.ts shows up as a changed page rather than a stale one.
 */
import { writeFileSync } from 'node:fs'
import { ATTACHMENTS } from '../src/data/attachments'
import {
  ATTACH_RULES, PENDING_RULES, SLOT_TYPES, WEAPON_FITS,
} from '../src/data/attach-rules'
import { CARD_FACTS } from '../src/data/card-facts'
import { UNCATALOGUED } from '../src/data/uncatalogued'
import { WEAPON_STAT_ROWS } from '../src/data/weapon-stats'

const put = (name: string, v: unknown) =>
  writeFileSync(`data/${name}.json`, JSON.stringify(v))

// Both rule maps, flattened. The generator does not care which of them a rule
// came from — that distinction is about whether the catalogue carries the item,
// which it can now ask UNCATALOGUED directly.
const rules: Record<string, unknown> = { ...ATTACH_RULES }
for (const [k, v] of Object.entries(PENDING_RULES)) {
  rules[k] = {
    grants: v.grants,
    conflictSlots: (v as { conflictSlots?: string[] }).conflictSlots,
  }
}

put('attachments', ATTACHMENTS)
// Keyed by weapon now, not one flat slot map. The generator asks for a named
// gun's lists and gets nothing for a gun nobody has read, which is the answer
// it should get — the flat map handed the RM277's lists to whoever asked.
put('fits', WEAPON_FITS)
put('rules', { rules, slots: SLOT_TYPES })
put('card-facts', CARD_FACTS)
// The items the catalogue does not carry, so the generator can resolve an id
// in a slot list whether the 414 hold it or not.
put('uncatalogued', UNCATALOGUED)
// The rows of the game's stat panel. Shared: every weapon has these eleven,
// and only the numbers in them are its own.
put('weapon-stats', WEAPON_STAT_ROWS)
console.log('dumped data/{attachments,fits,rules,card-facts,uncatalogued,weapon-stats}.json')
