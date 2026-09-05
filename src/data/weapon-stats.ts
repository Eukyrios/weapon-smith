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
   * THE LAST OF THOSE IS NOT A PREFERENCE, IT IS WHAT THE GAME DOES. These
   * three were recorded as flat changes for a long time and it worked, because
   * every one of them had been read on a single weapon. Reading the same parts
   * on a second and a third proved it: the Advanced Multi-Caliber Suppressor
   * was written down as +117 muzzle velocity, which is x1.18 of the RM277's
   * 650 -- and on the MK47's 525 the game shows 620, which is x1.18 again, not
   * 525+117. The Night Gale settles the gunshot row on its own, being the only
   * suppressor on a weapon whose gunshot base is not 500: it takes the AR-57's
   * 300 down to 210, which is the same x0.7 the RM277's Breaker applies to 500
   * to reach 350. Two different bases, one multiplier, two unrelated-looking
   * flat numbers.
   *
   * A flat number for these is therefore only true of the gun it was read on,
   * and an attachment belongs to the catalogue rather than to any gun.
   *
   * THE GAME ROUNDS UP. Every one of the twenty-one readings on file is
   * reproduced exactly by ceil(base x multiplier) and by no other rounding:
   * x1.18 of 525 is 619.5 and the game shows 620, x1.3 of 525 is 682.5 and it
   * shows 683, x1.035 of 840 is 869.4 and it shows 870.
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
