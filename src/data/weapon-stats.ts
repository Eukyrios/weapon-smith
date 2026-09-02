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
  /** 'set' replaces rather than adds: "Holds 45" is 45, not +45. */
  mode?: 'set';
}

export const WEAPON_STAT_ROWS: WeaponStatRow[] = [
  { key: 'Damage', max: 100 },
  { key: 'Range', max: 100, unit: 'm' },
  { key: 'Control', max: 100 },
  { key: 'Handling', max: 100 },
  { key: 'Stability', max: 100 },
  { key: 'Accuracy', max: 100 },
  { key: 'Armour penetration', max: 100 },
  { key: 'Fire rate', max: 1200, unit: ' rpm' },
  { key: 'Capacity', max: 100, from: 'Holds', mode: 'set' },
  { key: 'Muzzle velocity', max: 1200, unit: ' m/s' },
  { key: 'Gunshot heard', max: 1000, unit: ' m' },
];
