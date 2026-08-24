/**
 * The consistency checks the data file exposes, run as one command.
 *
 * These exist because the lists are transcribed by ear, weeks apart, and the
 * catalogue moves independently. Each check answers a question no reviewer can
 * hold in their head: does every rule point at an item that exists, does every
 * slot key name a real slot, do the optic pools still nest.
 */
import {
  danglingRuleIds, ladderViolations, unknownSlotKeys,
  unknownConflictSlots, panelSubsetViolations,
} from '../src/data/attach-rules'
import { unanchoredCardFacts } from '../src/data/card-facts'

const checks: [string, string[]][] = [
  ['rules pointing at missing items', danglingRuleIds()],
  ['optic pools that do not nest', ladderViolations()],
  ['unknown slot keys', unknownSlotKeys()],
  ['conflicts naming a missing slot', unknownConflictSlots()],
  ['patch entries the rail refuses', panelSubsetViolations()],
  ['card facts anchored to nothing', unanchoredCardFacts()],
]

let bad = 0
for (const [what, found] of checks) {
  console.log(`${found.length ? 'FAIL' : 'ok  '}  ${what}`, found.length ? found : '')
  bad += found.length
}
process.exit(bad ? 1 : 0)
