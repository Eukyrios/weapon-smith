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
  ATTACH_RULES, PENDING_RULES, SLOT_TYPES, CATEGORY_FITS,
} from '../src/data/attach-rules'
import { CARD_FACTS } from '../src/data/card-facts'

const put = (name: string, v: unknown) =>
  writeFileSync(`data/${name}.json`, JSON.stringify(v))

const rules: Record<string, unknown> = { ...ATTACH_RULES }
for (const [k, v] of Object.entries(PENDING_RULES)) {
  rules[k] = {
    name: v.name,
    grants: v.grants,
    conflictSlots: (v as { conflictSlots?: string[] }).conflictSlots,
  }
}

put('attachments', ATTACHMENTS)
put('fits', CATEGORY_FITS)
put('rules', { rules, slots: SLOT_TYPES })
put('card-facts', CARD_FACTS)
console.log('dumped data/{attachments,fits,rules,card-facts}.json')
