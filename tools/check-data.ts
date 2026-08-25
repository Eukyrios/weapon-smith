/**
 * The consistency checks the data file exposes, run as one command.
 *
 * These exist because the lists are transcribed by ear, weeks apart, and the
 * catalogue moves independently. Each check answers a question no reviewer can
 * hold in their head: does every rule point at an item that exists, does every
 * slot key name a real slot, do the optic pools still nest.
 */
import { readFileSync } from 'node:fs'
import {
  ATTACH_RULES, PENDING_RULES,
  danglingRuleIds, ladderViolations, unknownSlotKeys,
  unknownConflictSlots, panelSubsetViolations,
} from '../src/data/attach-rules'
import { unanchoredCardFacts } from '../src/data/card-facts'

/**
 * Does each recorded gunsmith layout still say what the rules say?
 *
 * The layouts are read off screen recordings and the rules are typed from the
 * game's own cards, so the two are independent accounts of the same fact: what
 * a part opens and what it takes over. They agreed when the layouts were cut.
 * If a rule is edited later and this goes quiet, the editor would draw a chip
 * for a slot the rules no longer grant.
 */
function layoutsAgainstRules(): string[] {
  const path = new URL('../data/gunsmith-rm277.json', import.meta.url)
  const d = JSON.parse(readFileSync(path, 'utf8')) as {
    layouts?: { by: string[]; when: string[]; blocks: string[]
                chips: Record<string, unknown> }[]
  }
  // Both books of rules: half these parts are named in a transcript and absent
  // from the catalogue, so they live in PENDING_RULES.
  const all = { ...ATTACH_RULES, ...PENDING_RULES } as Record<string, {
    grants?: string[]; conflictSlots?: string[] }>
  const say = (xs: Iterable<string>) => [...xs].sort().join(',')
  const out: string[] = []
  for (const l of d.layouts ?? []) {
    // A clip can have more than one part on -- the micro sight riser goes in a
    // slot the tactical riser opened -- so the rules to compare against are the
    // union of what everything fitted in that clip does.
    const grants = new Set<string>(), blocks = new Set<string>()
    let known = true
    for (const id of l.by) {
      const r = all[id]
      if (!r) { out.push(`${id}: no rule`); known = false; continue }
      for (const s of r.grants ?? []) grants.add(s)
      for (const s of r.conflictSlots ?? []) blocks.add(s)
    }
    if (!known) continue
    for (const s of blocks) grants.delete(s)
    const who = l.by.join(' + ')
    if (say(grants) !== say(l.when))
      out.push(`${who}: rules open ${say(grants)}, layout shows ${say(l.when)}`)
    if (say(blocks) !== say(l.blocks))
      out.push(`${who}: rules take ${say(blocks)}, layout shows ${say(l.blocks)}`)
    for (const slot of l.when)
      if (!(slot in l.chips)) out.push(`${who}: no chip for ${slot}`)
    for (const slot of l.blocks)
      if (slot in l.chips) out.push(`${who}: chip still drawn for ${slot}`)
  }
  return out
}

const checks: [string, string[]][] = [
  ['rules pointing at missing items', danglingRuleIds()],
  ['optic pools that do not nest', ladderViolations()],
  ['unknown slot keys', unknownSlotKeys()],
  ['conflicts naming a missing slot', unknownConflictSlots()],
  ['patch entries the rail refuses', panelSubsetViolations()],
  ['card facts anchored to nothing', unanchoredCardFacts()],
  ['layouts disagreeing with the rules', layoutsAgainstRules()],
]

let bad = 0
for (const [what, found] of checks) {
  console.log(`${found.length ? 'FAIL' : 'ok  '}  ${what}`, found.length ? found : '')
  bad += found.length
}
process.exit(bad ? 1 : 0)
