/**
 * What an item's own inventory card shows, for items the catalogue does not
 * carry stats for.
 *
 * The 414-item catalogue has prices and stat lines but no rarity and no weight.
 * The game's inventory card has all three, and for the items named in a slot
 * list but absent from the catalogue it is the only source there is. So the
 * cards were captured and read, and what they said is written down here.
 *
 * Only `stats` reaches the site. Rarity and weight were read off the same cards
 * in the same pass and are kept because throwing away a measurement to save a
 * few lines is a bad trade — but an attachment page is about what fitting the
 * thing does to the gun, so that is all it shows.
 *
 * TIER IS A COLOUR, NOT A WORD
 *
 * The card does not print a rarity. It prints a coloured diamond beside the
 * name, and the colour was sampled rather than eyeballed — the four values
 * below came back in tight clusters across twenty-five cards, no reading more
 * than three levels off its group:
 *
 *     red     (218, 87, 88)      3 items
 *     purple  (155, 114, 221)   19 items
 *     blue    (88, 160, 221)     2 items
 *     green   (42, 202, 150)     1 item
 *
 * They are stored as the colour, because the colour is the fact. Every game in
 * this family ramps rarity green < blue < purple < red and these sort that way,
 * but the card never says so and neither does this file.
 *
 * WEIGHT IS READ, NOT MEASURED
 *
 * The kilogram figure is printed on the card and was transcribed by eye. It is
 * the one field here that a sampling script did not check.
 */

import { ATTACH_BY_ID } from './attachments';
import { PENDING_RULES, UNRESOLVED_NAMES } from './attach-rules';

export type CardTier = 'green' | 'blue' | 'purple' | 'red';

export interface CardFacts {
  /**
   * Every field is optional because they come from different readings. The
   * twenty-five captured cards gave a tier and a weight; the stat lines were
   * dictated separately, and cover items no card was captured for. Requiring
   * all three would mean inventing the two that were never read.
   */
  tier?: CardTier;
  /** Kilograms, as printed on the card. */
  weight?: number;
  /**
   * Stat lines, in the catalogue's own keys and sign convention. For items the
   * catalogue does not carry, and for the nineteen it carries with an empty
   * stat block. Read off the game and dictated, not scraped, so an item with no
   * entry here has not been read yet — it does not have none.
   */
  stats?: Record<string, number>;
}

export const CARD_FACTS: Record<string, CardFacts> = {
  // --- optics -------------------------------------------------------------
  // Stats below are read in the order the site's own Optics table lists them.
  'white-phosphor-thermal-scope': {
    tier: 'red', weight: 0.6, stats: { Handling: -8, Stability: -2 },
  },
  'advanced-thermal-fusion-holographic-sight': {
    tier: 'red', weight: 0.3, stats: { Handling: -2, Stability: -2 },
  },
  'vmx-frameless-sight': {
    tier: 'purple', weight: 0.55, stats: { Handling: -2 },
  },
  '1p-33-2-4x-scope': {
    // Restated. An earlier reading of -4 / +3 turned out to be the Prism's.
    tier: 'purple', weight: 0.6, stats: { Handling: -6, Stability: 4 },
  },
  'uhx-holographic-sight': {
    tier: 'purple', weight: 0.15, stats: { Handling: -2 },
  },
  'prism-universal-2x-optic': {
    tier: 'purple', weight: 0.3, stats: { Handling: -4, Stability: 3 },
  },
  'm157-fire-control-system': {
    tier: 'purple', weight: 0.6, stats: { Handling: -6 },
  },
  '1p-29-russian-3x-sight': {
    tier: 'purple', weight: 0.6, stats: { Handling: -4 },
  },
  'meo-micro-sight-riser': {
    tier: 'blue', weight: 0.3, stats: { Handling: -1, Stability: 2 },
  },

  // --- muzzle and barrel --------------------------------------------------
  'rm277-breaker-suppressor': {
    tier: 'purple', weight: 0.15, stats: { Range: 10, Control: 5, Accuracy: -8 },
  },
  'cobweb-titanium-muzzle-brake': {
    tier: 'purple', weight: 0.2, stats: { Control: 7, Stability: -2, Accuracy: 8 },
  },
  'rm277-whale-shark-barrel-combo': {
    tier: 'purple', weight: 0.4,
    stats: { Range: 17, Control: 8, Handling: -9, Stability: 5, Accuracy: -12 },
  },
  'rm277-heavy-integral-barrel': {
    tier: 'purple', weight: 0.5,
    stats: { Range: 10, Control: 7, Handling: -2, Stability: 5, Accuracy: 12 },
  },

  // --- grips, pads and panels ---------------------------------------------
  'rm277-pad': { tier: 'purple', weight: 0.2 },
  'rm277-cheek-pad': { tier: 'purple', weight: 0.2 },
  // Dictated as "Resonant MK II". The RM277's foregrip list holds one Resonant
  // grip and it is the MK III.
  'resonant-mk-iii-grip': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 4, Handling: -2, Stability: 4, Accuracy: 8 },
  },
  // Dictated as "EU universal" — the EC Universal Front Hand Stop.
  'ec-universal-front-hand-stop': {
    tier: 'purple', weight: 0.13,
    stats: { Control: -4, Handling: 6, Stability: 2, Accuracy: 16 },
  },
  'ar-light-grip-piece': {
    tier: 'purple', weight: 0.2, stats: { Handling: 2, Stability: 4 },
  },
  'ar-heavy-grip-piece': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 8, Handling: -6, Stability: 4 },
  },
  'ar-modular-rear-grip': {
    tier: 'purple', weight: 0.2, stats: { Control: 2, Handling: 2 },
  },
  'ar-moe-rear-grip': {
    tier: 'blue', weight: 0.2, stats: { Control: 3, Stability: 3 },
  },
  'dd-python-handguard-panel': {
    tier: 'green', weight: 0.1, stats: { Handling: 1 },
  },

  // --- rail devices -------------------------------------------------------
  /*
   * The Baldr is the odd one here: it IS in the 414, so it has a name, a price
   * and a picture, and its stat block is simply empty. Nineteen catalogue
   * entries are like that. Stats read off the game fill those in exactly as
   * they fill in an item the catalogue never had — the site asks for stat
   * lines, not for which file they came out of. No card was captured for it,
   * so stats are all it has here.
   *
   * WHY THE BLANK ONES WILL STAY BLANK UNTIL SOMEONE READS THEM
   *
   * The external data source the catalogue came from was checked directly for
   * this. It carries a weight, a price history and the trait strings for every
   * functional attachment, and no stat modifiers at all — its page for this
   * flashlight has the same three traits our entry has and nothing else. On an
   * optic it does carry them, and its ACOG reads Handling -2, matching ours
   * exactly, which is how we know the two agree and that the gap is the
   * source's rather than the import's.
   *
   * So the nineteen empty stat blocks are not a scraping failure to be retried.
   * Nobody has published them. They come off the game's own cards or not at all.
   */
  'olight-baldr-pro-r-multi-function-flashlight': {
    stats: { Handling: -5, Accuracy: -8 },
  },
  'olight-warrior-3s-tactical-flashlight': { tier: 'purple', weight: 0.1 },
  'olight-odin-s-tactical-flashlight': {
    tier: 'purple', weight: 0.1, stats: { Handling: -1 },
  },
};

/**
 * Seen on a card, and nowhere else.
 *
 * This one turned up in the same batch of captures and belongs to no list we
 * hold. It is not in the 414 — the catalogue's two 8x snipers are the Optical
 * Sniper 8x Scope and the PSO Sniper 8x Scope, and neither is thermal — and no
 * transcript has named it for any slot on the RM277. Its own card cuts the
 * name off at the width of the title bar, so even the name is incomplete.
 *
 * It is parked here rather than guessed into `CATEGORY_FITS`, because putting
 * it in a slot list would assert a fit nobody has observed. Its picture is
 * cut and waiting in att/ for the day the rest of the name arrives.
 */
export const UNPLACED_CARDS: Record<string, CardFacts & { name: string }> = {
  '8x-adv-thermal-vision-sniper-scope': {
    name: '8x Adv. Thermal Vision Sniper S…',
    tier: 'red',
    weight: 0.6,
  },
};

/** The generator's id rule, so a check here agrees with the pages it builds. */
const slug = (name: string) =>
  name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/**
 * Card facts whose id matches no item anywhere.
 *
 * These ids are typed out by hand from a screenshot, and most of them name an
 * item the catalogue does not carry, so nothing else in the build would notice
 * a misspelling — the fact would simply never appear on any page and the page
 * would look exactly as it did before. This is what notices.
 */
export function unanchoredCardFacts(): string[] {
  const known = new Set([
    ...Object.keys(ATTACH_BY_ID),
    ...Object.keys(PENDING_RULES),
  ]);
  for (const bySlot of Object.values(UNRESOLVED_NAMES)) {
    for (const names of Object.values(bySlot)) {
      for (const n of names) known.add(slug(n));
    }
  }
  return Object.keys(CARD_FACTS).filter((id) => !known.has(id));
}
