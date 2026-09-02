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
import { UNCATALOGUED } from './uncatalogued';

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
  /**
   * Somebody has looked at this item's card and the stat lines we hold are the
   * whole of it — whether they came from here or from the catalogue import.
   *
   * The point is what it licenses the site to say. Five stats are marked "not
   * tracked" wherever they appear, because nothing in the imported data moves
   * damage or fire rate and printing "550 rpm, no change" would be a claim
   * about the game rather than a note about our data. A card does not have
   * that gap: it lists everything the part moves, so on a part somebody has
   * read, a line the card does not mention is a line that does not move, and
   * the hedge comes off.
   *
   * Setting `stats` here implies this and does not need it. The flag exists
   * for the other case — an item whose catalogue stat block was already right,
   * where restating it below would be duplicating a number in order to record
   * that somebody looked at it.
   */
  read?: true;
  /**
   * This item is showing the wrong picture and wants a new one.
   *
   * Not a card fact at all, but it lives here because it is the same shape of
   * thing as the rest of this file: a note about what the record still owes,
   * kept per item, surfaced as a tag you can search for. The offset sights are
   * the whole of it so far — each is drawn with its straight cousin's art, so
   * the one feature that distinguishes them is the one thing the picture does
   * not show.
   */
  imageChange?: true;
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

  // --- optics: the whole slot, cleared ------------------------------------
  /*
   * Twenty-two scopes and sights, reviewed in one pass. None of them needed
   * a stat line changed — the import already had the handling and stability
   * they cost, and it had them right — so what is recorded here is only the
   * looking, which is the whole point of the flag: it is the difference
   * between a number nobody has checked and one somebody has.
   *
   * No tier on these. Rarity was not part of the pass, and a colour is a
   * reading like any other; guessing it from price would be inventing a
   * measurement to fill a column.
   */
  'insight-3-7-sniper-scope': { tier: 'purple', read: true },
  'viewpoint-3x-scope': { tier: 'purple', read: true },
  'lpvo-scope': { tier: 'purple', read: true },
  '3-7-adjustable-scope': { tier: 'purple', read: true },
  'recon-1-5-5-adjustable-scope': { tier: 'purple', read: true },
  'hamr-combined-scope': { tier: 'purple', read: true },
  'multi-purpose-tactical-riser': { tier: 'blue', read: true },
  'micro-sight-riser': { tier: 'blue', read: true },
  'acog-precision-6x-scope': { tier: 'blue', read: true },
  'osight-red-dot': { tier: 'blue', read: true },
  'cobra-accuracy-sight': { tier: 'blue', read: true },
  'combat-red-dot-sight': { tier: 'blue', read: true },
  'mini-red-dot-sight': { tier: 'blue', read: true },
  'okp-7-reflex-sight': { tier: 'blue', read: true },
  'xcog-assault-3-5x-scope': { tier: 'blue', read: true },
  'xro-quick-response-sight': { tier: 'blue', read: true },
  'panoramic-red-dot-sight': { tier: 'blue', read: true },
  'ap5000-reflex-sight': { tier: 'green', read: true },
  'holographic-sight-type-ii': { tier: 'green', read: true },
  'reflex-sight': { tier: 'green', read: true },
  'russian-accuracy-2x-scope': { tier: 'green', read: true },
  'holographic-sight': { tier: 'green', read: true },

  // --- offset optics ------------------------------------------------------
  /*
   * All five purple, and all five flagged for a new picture: they are
   * showing the straight sight's art rather than the offset mount's, which
   * is the one thing about them worth looking at.
   */
  'offset-osight-red-dot': { tier: 'purple', imageChange: true, read: true },
  'offset-combat-red-dot-sight': {
    tier: 'purple', imageChange: true,
    read: true,
  },
  'offset-mini-red-dot-sight': {
    tier: 'purple', imageChange: true,
    read: true,
  },
  'offset-xro-quick-response-sight': {
    tier: 'purple', imageChange: true,
    read: true,
  },
  'offset-panoramic-red-dot-sight': {
    tier: 'purple', imageChange: true,
    read: true,
  },

  // --- magazine and its mount ---------------------------------------------
  /*
   * The drum mag corrects the import rather than filling a blank: the
   * catalogue has it at -12 handling and the card reads -6. Its 45 rounds
   * the catalogue already had right.
   */
  'm7-6-8-45-round-drum-mag': {
    tier: 'purple', read: true, stats: { Handling: -6 },
  },
  'grizzly-full-p-mag-assist-sand': { tier: 'green', read: true },
  'grizzly-full-p-mag-assist-green': { tier: 'green', read: true },
  'grizzly-full-p-mag-assist-black': { tier: 'green', read: true },

  // --- rear grips ---------------------------------------------------------
  'ar-heavy-tower-grip': { tier: 'purple', read: true },
  'invasion-rear-grip': { tier: 'purple', read: true },
  'phantom-rear-grip': { tier: 'purple', read: true },
  'marksman-d-2-rear-grip': { tier: 'blue', read: true },
  'hurricane-d-1-rear-grip': { tier: 'blue', read: true },
  'm7-stable-rear-grip': { tier: 'green', read: true },
  '416-practical-rear-grip': { tier: 'green', read: true },

  // --- muzzle and barrel --------------------------------------------------
  'rm277-breaker-suppressor': {
    tier: 'purple', weight: 0.15, read: true,
    stats: {
      Range: 10, Control: 5, Accuracy: -8,
      'Muzzle velocity': 117, 'Gunshot heard': -150,
    },
  },
  'cobweb-titanium-muzzle-brake': {
    tier: 'purple', weight: 0.2, stats: { Control: 7, Stability: -2, Accuracy: 8 },
  },
  /*
   * Both barrels re-read for muzzle velocity, which nothing carried until the
   * suppressors made it a column worth having: 845 m/s and 767 against the bare
   * rifle's 650, so +195 and +117. A barrel being the biggest single thing that
   * happens to muzzle velocity is what you would expect, and worth having on
   * record now that the stat is one the optimiser can sort on.
   */
  'rm277-whale-shark-barrel-combo': {
    tier: 'purple', weight: 0.4, read: true,
    stats: {
      Range: 17, Control: 8, Handling: -9, Stability: 5, Accuracy: -12,
      'Muzzle velocity': 195,
    },
  },
  'rm277-heavy-integral-barrel': {
    tier: 'purple', weight: 0.5, read: true,
    stats: {
      Range: 10, Control: 7, Handling: -2, Stability: 5, Accuracy: 12,
      'Muzzle velocity': 117,
    },
  },

  // --- grips, pads and panels ---------------------------------------------
  'rm277-pad': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 4, Handling: 2, Accuracy: -8 },
  },
  'rm277-cheek-pad': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 2, Handling: -2, Stability: 4 },
  },
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
    tier: 'green', weight: 0.1, read: true, stats: { Handling: 1 },
  },

  // --- muzzles --------------------------------------------------------------
   /*
    * Six suppressors carry stat lines as well as a tier, and they are the first
    * items on the site to move muzzle velocity, gunshot range or fire rate --
    * the columns the catalogue import has for nothing at all. Which is why a
    * card reading is laid over the import rather than used instead of it: the
    * import knows a suppressor costs handling, and only the card knows it is
    * the thing that makes the shot quieter.
    *
    * Dictated as the figures the gun's own panel shows with the part fitted,
    * against the bare RM277 -- fire rate 550, muzzle velocity 650, gunshot 500 --
    * and written down here as the modifiers that produce them. The M7's 650 m/s
    * is the base exactly, so it has no muzzle velocity line: read, and found to
    * move nothing.
    */
   /*
    * Rarity for the whole slot, dictated as three runs the way the foregrips
    * were: purple down to the Blazing Fire, blue down to the Practical
    * Suppressor, green to the end. Two items answer to "practical
    * suppressor" — the M7 sits third from the top — and the runs settle it:
    * the boundary has to fall after the Blazing Fire, so it is the plain one
    * at twelve.
    *
    * The prices agree, and agree with the foregrips: purple 19,633 and up,
    * blue 9,166 to 14,442, green under 5,000, each boundary a cliff. Two
    * slots read on different days landing on the same three bands is worth
    * more than either reading on its own.
    *
    * Stats are not touched here. The rarity was read; nobody said the stat
    * lines were checked, and a tier is not a licence to drop the hedge on
    * five stats this reading never looked at.
    */
  'spiral-fire-flash-hider': { tier: 'purple', read: true },
  'advanced-multi-caliber-suppressor': { tier: 'purple', read: true,
    stats: { 'Muzzle velocity': 117, 'Gunshot heard': -250 } },
  'm7-practical-suppressor': { tier: 'purple', read: true, stats: { 'Gunshot heard': -250 } },
  'silent-suppressor': { tier: 'purple', read: true,
    stats: { 'Fire rate': -71, 'Muzzle velocity': 156, 'Gunshot heard': -250 } },
  'sandstorm-vertical-compensator': {
    tier: 'purple',
    read: true,
    stats: { Control: 9 },
  },
  'bastion-horizontal-compensator': {
    tier: 'purple',
    read: true,
    stats: { Control: 9 },
  },
  'poseidon-flash-hider': { tier: 'purple', read: true },
  'whisper-tactical-suppressor': { tier: 'purple', read: true,
    stats: { 'Muzzle velocity': 117, 'Gunshot heard': -150 } },
  'titanium-contest-muzzle-brake': { tier: 'purple', read: true },
  'blazing-fire-suppressor': { tier: 'purple', read: true },
  'steel-muzzle-brake': { tier: 'blue', read: true },
  'practical-suppressor': { tier: 'blue', read: true, stats: { 'Gunshot heard': -150 } },
  'birdcage-flash-hider': { tier: 'green', read: true },
  'practical-flash-hider': { tier: 'green', read: true },

  // --- foregrips ----------------------------------------------------------
  /*
   * The whole slot, read in one pass: 21 grips, every one of them cleared,
   * so an unlisted stat on any of these is unchanged rather than unread.
   *
   * Rarity was dictated as three runs down the list rather than item by
   * item — purple through the Phase Combat, blue through the VFG Knight,
   * green to the end. The prices agree and say where the runs break: the
   * three bands do not overlap and each boundary is a cliff, 48,141 to
   * 9,391 and 8,244 to 3,472. That is what settles the named items as the
   * last of their run rather than the first of the next; nothing else in
   * the phrasing does.
   *
   * Three of these carry an empty stat block in the catalogue — the CR
   * Prism Hand Stop, the K1 Elite Bevel and the RK-0. Cleared, that stops
   * meaning unread and starts meaning they move nothing.
   */
  'dawn-angled-flashlight-grip': { tier: 'purple', read: true },
  'daybreak-vertical-flashlight-grip': { tier: 'purple', read: true },
  'cr-prism-hand-stop': { tier: 'purple', read: true }, // no modifiers
  'resonant-mkii-foregrip': { tier: 'purple', read: true },
  'collapsible-bipod-grip': { tier: 'purple', read: true },
  'k1-elite-bevel-foregrip': { tier: 'purple', read: true }, // no modifiers
  'x25u-angled-combat-grip': { tier: 'purple', read: true },
  'resonant-ergonomic-grip': { tier: 'purple', read: true },
  'phantom-vertical-foregrip': { tier: 'purple', read: true },
  'tactical-vertical-foregrip': { tier: 'purple', read: true },
  'secret-order-bevel-foregrip': { tier: 'purple', read: true },
  'rk-0-foregrip': { tier: 'purple', read: true }, // no modifiers
  'tactical-angled-foregrip': { tier: 'purple', read: true },
  'angled-hand-stop': { tier: 'purple', read: true },
  'competition-hand-stop': { tier: 'purple', read: true },
  'phase-combat-foregrip': { tier: 'purple', read: true },
  'folding-grip': { tier: 'blue', read: true },
  'vfg-knight-foregrip': { tier: 'blue', read: true },
  'zfsg-tactical-grip': { tier: 'green', read: true },
  'mini-hand-stop': { tier: 'green', read: true },
  'practical-vertical-foregrip': { tier: 'green', read: true },


  // --- read on the RM277, with nothing of their own to add ----------------
  /*
   * The last of the rifle's own lists to be gone through. None of these
   * needed a number changed, so all that is recorded is the looking — which
   * is the whole of what `read` is for.
   */
  'honeycomb-killflash': { read: true },
  'balanced-grip-base': { read: true },
  'stable-grip-base': { read: true },

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
    tier: 'purple', read: true, stats: { Handling: -5, Accuracy: -8 },
  },
  'olight-warrior-3s-tactical-flashlight': {
    tier: 'purple', weight: 0.1,
    read: true,
    stats: {},
  },
  'olight-odin-s-tactical-flashlight': {
    tier: 'purple', weight: 0.1, stats: { Handling: -1 },
  },
  /*
   * The rest of the rail, read in one pass, and rarity dictated as runs the way
   * the foregrips and muzzles were: purple down to the PEQ-2, the Practical
   * Weapon Light on its own in blue, the five panels green.
   *
   * Most of these only confirm what the import already said — the Flare's -1
   * handling, the Python's +1 — and confirmation is worth writing down, because
   * it is the difference between a number nobody has checked and one somebody
   * has. The four laser-light combos are new: the import carried no stat block
   * for any of them.
   */
  'dbal-x2-purple-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 },
  },
  'perst-7-blue-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 },
  },
  'flare-tactical-flashlight': { tier: 'purple', read: true },
  'la-3c-green-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 },
  },
  'peq-2-red-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 },
  },
  'practical-weapon-light': { tier: 'blue', read: true },
  'modular-handguard-panel': { tier: 'green', read: true },
  'hornet-handguard': { tier: 'green', read: true },
  'kc-hound-handguard': { tier: 'green', read: true },
  'ranger-handguard': { tier: 'green', read: true },
  /*
   * The rail bipod, and the only member of its slot. Another of the nineteen
   * the catalogue carries with an empty stat block, read off the game: one
   * line, and the rest of the card genuinely unchanged rather than unread.
   * That distinction is the whole point of this file — an item with no entry
   * here has not been read, and this one now has.
   */
  'practical-bipod': { tier: 'blue', stats: { Handling: -4 } },

  /*
   * The first card off a second weapon. Read from the AR-57 clip that its slot
   * layout came from, so the five base lines are what the card showed and the
   * five below them were not on screen — hence no `read`, and the item keeps
   * its #not-tracked tag.
   */
  'ar57-wave-blaster-ultra-long-barrel': {
    tier: 'blue',
    stats: {
      Range: 11, Control: 9, Handling: -7, Stability: 4, Accuracy: -12,
    },
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

/**
 * Card facts whose id matches no item anywhere.
 *
 * These ids are typed out by hand from a screenshot, and most of them name an
 * item the catalogue does not carry, so nothing else in the build would notice
 * a misspelling — the fact would simply never appear on any page and the page
 * would look exactly as it did before. This is what notices.
 *
 * One set to check against now, rather than three. It used to slug every name
 * in UNRESOLVED_NAMES and union that with the keys of PENDING_RULES, which was
 * a way of asking "does anything, anywhere, claim this item exists" — the
 * question UNCATALOGUED answers on its own.
 */
export function unanchoredCardFacts(): string[] {
  return Object.keys(CARD_FACTS).filter(
    (id) => !ATTACH_BY_ID[id] && !UNCATALOGUED[id],
  );
}
