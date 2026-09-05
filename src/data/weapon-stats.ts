/**
 * The stat panel the game shows for every weapon: which rows, in which order.
 *
 * THE SHAPE IS SHARED. ONLY THE NUMBERS ARE NOT.
 *
 * Eleven rows, the same eleven on every gun, in the order the gunsmith prints
 * them. Damage is out of 100 whichever rifle you are looking at; fire rate is
 * out of 1200; capacity is a set value rather than a modifier, and it arrives
 * under the name "Holds". None of that is a fact about the RM277 — it is what
 * the panel IS — and it lived inside the RM277's own file only because the
 * RM277 was the first weapon traced.
 *
 * What is per weapon is the `base`: the figure that gun starts at. Those stay
 * in data/gunsmith-<id>.json, read off that weapon's own panel.
 *
 * WHY THIS MATTERS BEYOND TIDINESS
 *
 * A weapon whose panel nobody has read had no rows at all, so the detail pane
 * for an attachment on it collapsed from eleven rows with resulting figures to
 * a bare list of the two or three lines that part moves. The same attachment,
 * shown two entirely different ways depending on which gun you were looking at
 * — which reads as the site being broken rather than as a measurement being
 * absent. With the rows here, every weapon has all eleven, always, and a base
 * nobody has read shows as a dash in the one cell it belongs in.
 */
export interface WeaponStatRow {
  key: string;
  /** Full scale for the bar. */
  max: number;
  /** Printed after the number, spacing included. */
  unit?: string;
  /** The attachment-data key this row is fed by, when it differs. */
  from?: string;
  /**
   * How an attachment's number combines with this row.
   *
   *   (none)  adds:      control +8 on a rifle at 44 gives 52.
   *   'set'   replaces:  "Holds 45" is 45, not +45.
   *   'scale' MULTIPLIES, and the number stored is the multiplier itself:
   *           0.7 on a gunshot row, not -150.
   *
   * MULTIPLYING IS PROVEN FOR SOME PARTS AND ASSUMED FOR THE REST, and the
   * difference is worth keeping straight.
   *
   * A part read on ONE weapon tells you nothing about which it is. A delta and
   * a multiplier that agree on that weapon are the same claim there and
   * different claims everywhere else; the reading cannot choose between them
   * and never will. Only a part read on TWO DIFFERENT BASES decides, because
   * only then do the two models predict different things.
   *
   * AND ONLY ITS OWN READINGS COUNT. Two different suppressors both landing on
   * x0.7 says nothing about either of them -- the thing being determined is
   * the multiplier for one attachment, and a coincidence between two of them
   * is not evidence about either. An earlier version of this comment argued
   * exactly that from the Night Gale and the RM277 Breaker, and it was wrong
   * to.
   *
   * Three parts clear that bar today, all on muzzle velocity, and they clear
   * it decisively. The Silent Suppressor shows 806 on the RM277's 650 and 651
   * on the MK47's 525: x1.24 fits both exactly, and the best single flat delta
   * misses by 30. The Advanced Multi-Caliber and the Whisper Tactical are
   * x1.18 the same way, flat missing by 22.
   *
   * NOTHING ELSE IS ESTABLISHED. Seventeen of the twenty-one part-and-stat
   * pairs on file have been read on one base only -- including EVERY gunshot
   * value, because every suppressor read so far sits on a weapon whose gunshot
   * base is 500. For those, the multiplier stored here reproduces the reading
   * it came from and is a guess about every other weapon. It is the right
   * guess to make, since multiplying is the only shape any part has been shown
   * to have and no part has been shown to add, but it is a guess.
   *
   * `python tools/scaled.py table` prints which is which, and the readings
   * that would settle the rest.
   *
   * THE GAME ROUNDS UP, and this was solved rather than guessed. For each
   * rounding rule and each reading there is an exact interval of multipliers
   * that reproduces it; intersecting the intervals for one part across two
   * weapons gives the only multipliers that can be right, and the test is then
   * how many of the twenty-one land on a whole percent -- because a game's
   * numbers do, and twenty-one arbitrary decimals would not.
   *
   *     ceil    19 of 21 whole percent, 1 half percent, 1 neither
   *     round   19 of 21 whole percent, 0 half,          2 neither
   *     floor   14 of 21 whole percent, 0 half,          7 neither
   *
   * Floor is out on its own evidence. Ceil beats round on the SUR Heat Shield,
   * which lands on x1.035 under ceil and on nothing tidy under round. So: ceil.
   *
   * FIRE RATE MIGHT NOT MULTIPLY AT ALL. It has one part read on two bases,
   * the Silent Suppressor, and that part is the one whose readings disagree --
   * so the row is set to scale by analogy with muzzle velocity rather than on
   * its own evidence. What its two readings do say is that flat is worse: a
   * single delta misses them by 11, where x0.87 misses by 1. The SUR Heat
   * Shield, the only other part with a fire-rate figure, has one reading.
   *
   * TWO READINGS DISAGREE WITH IT BY EXACTLY ONE, and both are cases where the
   * exact product is fractional:
   *
   *     Silent Suppressor fire rate   x0.87 of 625 = 543.75, ceil 544, read 543
   *     MCX LT Hunter Barrel velocity x1.69 of 450 = 760.5,  ceil 761, read 760
   *
   * The Silent Suppressor is kept at 0.87 because that is the only whole
   * percent that fits either of its two readings, and it fits the RM277's 479
   * exactly. The Hunter Barrel is kept at 1.688 -- untidy, and deliberately so:
   * it has ONE reading and 1.688 reproduces it, where 1.69 would overrule the
   * only evidence there is with a preference for round numbers. If both cards
   * really do read 543 and 760, the rounding is not plain ceil and this whole
   * comment wants redoing; two cards, and it is settled.
   */
  mode?: 'set' | 'scale';
}

export const WEAPON_STAT_ROWS: WeaponStatRow[] = [
  { key: 'Damage', max: 100 },
  { key: 'Range', max: 100, unit: 'm' },
  { key: 'Control', max: 100 },
  { key: 'Handling', max: 100 },
  { key: 'Stability', max: 100 },
  { key: 'Accuracy', max: 100 },
  { key: 'Armour penetration', max: 100 },
  { key: 'Fire rate', max: 1200, unit: ' rpm', mode: 'scale' },
  { key: 'Capacity', max: 100, from: 'Holds', mode: 'set' },
  { key: 'Muzzle velocity', max: 1200, unit: ' m/s', mode: 'scale' },
  { key: 'Gunshot heard', max: 1000, unit: ' m', mode: 'scale' },
];
