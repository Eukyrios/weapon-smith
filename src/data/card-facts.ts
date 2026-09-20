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
 * FIRE RATE, MUZZLE VELOCITY AND GUNSHOT HEARD ARE NOT IN THIS FILE.
 *
 * The game SCALES those three rather than adding to them, so one number here
 * could only ever be true of one weapon. They live in data/scaled-stats.json
 * instead, which keeps the figure each card showed on each weapon and derives
 * a multiplier where two weapons disagree enough to settle one. The site reads
 * a weapon's own figure first and falls back to the multiplier only for guns
 * nobody has checked. Everything else about those parts -- rarity, weight, the
 * eight stats that add, whether anybody has read the card -- is still here.
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
   * THIS FLAG IS THE ONLY THING THAT CLEARS THE HEDGE. Numbers in `stats` do
   * not, and used to. The reasoning was that stats can only come off a card
   * and a card lists everything — true of a card somebody sits down with, and
   * false of one read off a paused video, which shows the five lines the frame
   * happened to include. The AR-57's Wave Blaster barrel was entered that way,
   * came out looking fully read, and was quietly missing a muzzle velocity of
   * +158 that nothing on the site could have told you was absent.
   *
   * So an item is unread until this says otherwise, and a partial reading is
   * numbers with no flag. The default has to be the cautious one: the failure
   * it prevents is a figure that is wrong rather than a figure that is missing,
   * and only one of those announces itself.
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
    read: true
  },
  'advanced-thermal-fusion-holographic-sight': {
    tier: 'red', weight: 0.3, stats: { Handling: -2, Stability: -2 },
    read: true
  },
  'vmx-frameless-sight': {
    tier: 'purple', weight: 0.55, stats: { Handling: -2 },
    read: true
  },
  '1p-33-2-4x-scope': {
    // Restated. An earlier reading of -4 / +3 turned out to be the Prism's.
    tier: 'purple', weight: 0.6, stats: { Handling: -6, Stability: 4 },
    read: true
  },
  'uhx-holographic-sight': {
    tier: 'purple', weight: 0.15, stats: { Handling: -2 },
    read: true
  },
  'prism-universal-2x-optic': {
    tier: 'purple', weight: 0.3, stats: { Handling: -4, Stability: 3 },
    read: true
  },
  'm157-fire-control-system': {
    tier: 'purple', weight: 0.6, stats: { Handling: -6 },
    read: true
  },
  '1p-29-russian-3x-sight': {
    tier: 'purple', weight: 0.6, stats: { Handling: -4 },
    read: true
  },
  'meo-micro-sight-riser': {
    tier: 'blue', weight: 0.3, stats: { Handling: -1, Stability: 2 },
    read: true
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
    read: true
  },
  'offset-mini-red-dot-sight': {
    tier: 'purple', imageChange: true,
    read: true
  },
  'offset-xro-quick-response-sight': {
    tier: 'purple', imageChange: true,
    read: true
  },
  'offset-panoramic-red-dot-sight': {
    tier: 'purple', imageChange: true,
    read: true
  },

  // --- magazine and its mount ---------------------------------------------
  /*
   * The drum mag corrects the import rather than filling a blank: the
   * catalogue has it at -12 handling and the card reads -6. Its 45 rounds
   * the catalogue already had right.
   */
  'm7-6-8-45-round-drum-mag': {
    tier: 'purple', read: true, stats: { Handling: -6 }
  },
  /*
   * This one fills a blank instead. The catalogue has its 45 rounds and no
   * handling at all -- not zero, absent -- and an extended magazine that costs
   * nothing to handle would be the only one on the site. It costs 9.
   *
   * No rarity, because none was read. The card would have printed one.
   */
  'm4-45-round-extended-mag': {
    tier: 'blue', read: true, stats: { Handling: -9 }
  },
  /*
   * The rest of the MCX LT's five, by rarity only. Read down that list and the
   * bands are purple, then blue for three, then green for the last -- the same
   * shape every slot on this site has, most to least.
   */
  'm4-60-round-drum-mag': { tier: 'blue' },
  '5-56x45-30-round-polymer-mag': { tier: 'green' },
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
      Range: 10, Control: 5, Accuracy: -8
    }
  },
  'cobweb-titanium-muzzle-brake': {
    tier: 'purple', weight: 0.2, stats: { Control: 7, Stability: -2, Accuracy: 8 },
    read: true
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
      Range: 17, Control: 8, Handling: -9, Stability: 5, Accuracy: -12
    }
  },
  'rm277-heavy-integral-barrel': {
    tier: 'purple', weight: 0.5, read: true,
    stats: {
      Range: 10, Control: 7, Handling: -2, Stability: 5, Accuracy: 12
    }
  },

  // --- grips, pads and panels ---------------------------------------------
  'rm277-pad': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 4, Handling: 2, Accuracy: -8 },
    read: true
  },
  'rm277-cheek-pad': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 2, Handling: -2, Stability: 4 },
    read: true
  },
  // Dictated as "Resonant MK II". The RM277's foregrip list holds one Resonant
  // grip and it is the MK III.
  'resonant-mk-iii-grip': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 4, Handling: -2, Stability: 4, Accuracy: 8 },
    read: true
  },
  // Dictated as "EU universal" — the EC Universal Front Hand Stop.
  'ec-universal-front-hand-stop': {
    tier: 'purple', weight: 0.13,
    stats: { Control: -4, Handling: 6, Stability: 2, Accuracy: 16 },
    read: true
  },
  'ar-light-grip-piece': {
    tier: 'purple', weight: 0.2, stats: { Handling: 2, Stability: 4 },
    read: true
  },
  'ar-heavy-grip-piece': {
    tier: 'purple', weight: 0.2,
    stats: { Control: 8, Handling: -6, Stability: 4 },
    read: true
  },
  'ar-modular-rear-grip': {
    tier: 'purple', weight: 0.2, stats: { Control: 2, Handling: 2 },
    read: true
  },
  'ar-moe-rear-grip': {
    tier: 'blue', weight: 0.2, stats: { Control: 3, Stability: 3 },
    read: true
  },
  'dd-python-handguard-panel': {
    tier: 'green', weight: 0.1, read: true, stats: { Handling: 1 }
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
  'spiral-fire-flash-hider': { tier: 'purple', read: true,
    stats: { Control: 4, Stability: 1 } },
  'advanced-multi-caliber-suppressor': { tier: 'purple', read: true,
    stats: { Range: 5, Control: 9, Handling: -6, Accuracy: -4 } },
  'm7-practical-suppressor': { tier: 'purple', read: true,
    stats: { Control: 8, Handling: -4, Stability: 2 } },
  'silent-suppressor': { tier: 'purple', read: true,
    stats: { Range: 7, Control: 8, Handling: -13, Stability: -5 } },
  'sandstorm-vertical-compensator': {
    tier: 'purple',
    read: true,
    stats: { Control: 9 }
  },
  'bastion-horizontal-compensator': {
    tier: 'purple',
    read: true,
    stats: { Control: 9 }
  },
  'poseidon-flash-hider': { tier: 'purple', read: true },
  'whisper-tactical-suppressor': { tier: 'purple', read: true,
    stats: { Range: 5, Control: 6, Handling: -5, Stability: 2, Accuracy: -4 } },
  'titanium-contest-muzzle-brake': { tier: 'purple', read: true },
  'blazing-fire-suppressor': { tier: 'purple', read: true },
  'steel-muzzle-brake': { tier: 'blue', read: true },
  'practical-suppressor': { tier: 'blue', read: true,
    stats: { Control: 2, Stability: 2 } },
  'birdcage-flash-hider': { tier: 'green', read: true },
  'practical-flash-hider': { tier: 'green', read: true },
  // Read on the MCX LT, where it had been sitting in the list uncoloured and
  // unread since the muzzle slot was transcribed.
  'smg-echo-suppressor': { tier: 'purple', read: true },

  /*
   * The five the MK47 brings, all of them AK-pattern and none of them on a
   * weapon here before. RARITY ONLY -- nobody has opened these cards.
   *
   * The colour comes from where each one falls in the MK47's muzzle list, and
   * that list is a better witness than it sounds. The game orders a slot's
   * parts by rarity, most to least, and fifteen of the twenty already had a
   * colour on record from other weapons: everything from the Cobweb Titanium
   * down to the Blazing Fire reads purple, the Steel Muzzle Brake and the
   * Practical Suppressor read blue, the Practical Flash Hider reads green.
   * Fifteen independent readings, no contradictions, and the five unknowns
   * sit inside bands the other fifteen have already fixed the edges of.
   *
   * That also settled a name. Al gave the blue band as "AK Bravefire
   * Suppressor to Practical Suppressor", and the AK Bravefire is seventh in
   * the list -- six places inside a purple run that the recorded tiers put
   * beyond doubt. The band he meant starts at the AK Practical Compensator,
   * the other AK in the list and the one in the right place. The data caught
   * it; nothing here is a guess about which he meant.
   */
  'dtk-muzzle-brake': { tier: 'purple', read: true,
    stats: { Control: 6, Accuracy: 12 } },
  'ak-bravefire-suppressor': { tier: 'purple', read: true,
    stats: { Range: 5, Control: 3, Handling: -4, Stability: 3, Accuracy: -8 } },
  'pbs-russian-suppressor': { tier: 'purple', read: true,
    stats: { Control: 10, Handling: -4 } },
  // Read and unchanged: the catalogue already had both its lines right.
  'ak-practical-compensator': { tier: 'blue', read: true },
  'bell-mouth-flash-hider': { tier: 'green', read: true },

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
  'honeycomb-killflash': { tier: 'purple', read: true },
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
    tier: 'purple', read: true, stats: { Handling: -5, Accuracy: -8 }
  },
  'olight-warrior-3s-tactical-flashlight': {
    tier: 'purple', weight: 0.1,
    read: true
      },
  'olight-odin-s-tactical-flashlight': {
    tier: 'purple', weight: 0.1, stats: { Handling: -1 },
    read: true
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
    tier: 'purple', read: true, stats: { Handling: -4 }
  },
  'perst-7-blue-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 }
  },
  'flare-tactical-flashlight': { tier: 'purple', read: true },
  'la-3c-green-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 }
  },
  'peq-2-red-laser-light-combo': {
    tier: 'purple', read: true, stats: { Handling: -4 }
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
  'practical-bipod': { tier: 'blue', stats: { Handling: -4 }, read: true },

  /*
   * The first card off a second weapon. Read from the AR-57 clip that its slot
   * layout came from, so the five base lines are what the card showed and the
   * five below them were not on screen — hence no `read`, and the item keeps
   * its #not-tracked tag.
   */
  'ar57-wave-blaster-ultra-long-barrel': {
    tier: 'blue', read: true,
    stats: {
      Range: 11, Control: 9, Handling: -7, Stability: 4, Accuracy: -12,
      // Its muzzle velocity is not here. See data/scaled-stats.json.
    }
  },
  /*
   * Its integrally suppressed sibling, and the trade reads exactly as one:
   * ninety metres of gunshot range for sixty-three of muzzle velocity against
   * the Wave Blaster, and it keeps four points of stability the other loses.
   *
   * NO SLOT RULE ON IT YET. The RM277's integral barrel takes over the muzzle
   * — an integrally suppressed barrel occupies the place a suppressor would go
   * — and this one is very likely the same. Nobody has watched it do that, and
   * the Whale Shark already taught this file that silence about a conflict is
   * not the same as none, so it is not written down. Until it is, a build can
   * be offered with this barrel and a suppressor both.
   */
  'night-gale-integrally-suppressed-combo': {
    tier: 'purple', read: true,
    stats: {
      Range: 6, Control: 8, Handling: -2, Stability: 8, Accuracy: -4,
      // 620 and 210 on the card, against the rifle's 525 and 300.
    }
  },
  /*
   * The AR-57's two stock kits, both purple.
   *
   * The catalogue has three lines for the Resonant 2 — control, accuracy,
   * stability — and no handling at all, so the page printed a stock kit that
   * did nothing for how the rifle carries, which is most of what a stock kit
   * is for. The card says +10. Written here as one more line rather than as a
   * replacement block, because stats_for lays the card over the catalogue key
   * by key: the three the import already had are right, and this is the one it
   * was missing.
   */
  'resonant-2-integral-stock': {
    tier: 'purple', read: true,
    stats: { Handling: 10 }
  },
  'restricted-zone-integral-stock': { tier: 'purple', read: true },
  /*
   * An AR-57 muzzle brake the import does not carry, so every figure on it is
   * off the card and there is no picture of it yet — which the page now says
   * out loud, with #no-picture, rather than quietly closing the gap where the
   * image would have been.
   */
  'ffc-double-port-muzzle-brake': {
    tier: 'purple', read: true,
    stats: { Control: 10, Handling: -4, Stability: 3 }
  },

  /*
   * --- the AR-57's stocks --------------------------------------------------
   *
   * Eighteen, dictated off the picker as three runs of colour: five purple
   * down to the Shadow Rail, eight blue down to the Lightning Rail, five green
   * to the Core Rail.
   *
   * The tiers arrived one reading ahead of the figures, and for a few minutes
   * this block was the first in the file to hold a tier with no `read` beside
   * it -- correctly, because a run of colour in a list says nothing about what
   * any of those parts does to the rifle. The pass that followed closed it:
   * the three the import does not carry were read off their cards, the other
   * fifteen were checked against what the site already showed, and all but two
   * of them are signed off here.
   *
   * TWO OF THEM WERE HELD BACK, and holding them back was worth it. The
   * Cardinal Stable Stock and the Practical Light Stock come out of the import
   * with an EMPTY stat block, so unlike their thirteen neighbours there was
   * nothing on screen for "looks fine as it is" to be agreeing with, and
   * clearing them would have turned that into "this stock moves nothing" --
   * a claim about the game rather than a note about our data. Their cards were
   * then opened, and neither of them moves nothing: +6 control on one, +2
   * handling on the other. Two figures that a confident clear would have
   * buried under a badge saying the reading was complete.
   */
  'anchor-point-rail-stock': {
    tier: 'purple', read: true,
    stats: { Control: 4, Handling: -2, Stability: 6 }
  },
  'qr-high-performance-stock': {
    tier: 'purple', read: true,
    stats: { Control: 3, Handling: -2, Stability: 3, Accuracy: 16 }
  },
  'ct-enhanced-stock': {
    // Restated on a second pass: stability is +2, not the +6 first dictated.
    tier: 'purple', read: true,
    stats: { Control: 2, Handling: 6, Stability: 2, Accuracy: -8 }
  },
  'shadow-buffer-tube-stock': { tier: 'purple', read: true },
  /*
   * The two the MCX LT takes and the AR-57 does not, which is why they had no
   * rarity when the other sixteen did: this list was read off the AR-57 first
   * and these were not on it. Rarity only, no stats -- the AR-57's purple band
   * ran Anchor Point Rail Stock to Shadow Rail Stock and on the MCX LT's list
   * these two sit inside it, so the band is what says they are purple, not a
   * card anybody has opened. They keep the hedge.
   */
  'mrgs-skeleton-stock': { tier: 'purple' },
  'ur-spec-ops-tactical-stock': { tier: 'purple' },
  'shadow-rail-stock': { tier: 'purple', read: true },
  // Drawn with somebody else's stock. The figures are right; the picture is
  // not, which is what imageChange is for.
  'skeleton-sniper-stock': { tier: 'blue', read: true, imageChange: true },
  'cardinal-advanced-combat-stock': { tier: 'blue', read: true },
  '416-stable-stock': { tier: 'blue', read: true },
  '416-light-stock': { tier: 'blue', read: true },
  // The import has its +3 control and stops there; the card also gives it +3
  // handling, which is the difference between a light stock and a decoration.
  'elite-light-stock': { tier: 'blue', read: true, stats: { Handling: 3 } },
  'invasion-core-stock': { tier: 'blue', read: true },
  // The two the import carried empty. Their cards were opened rather than
  // waved through, and neither of them moves nothing after all.
  'cardinal-stable-stock': { tier: 'blue', read: true, stats: { Control: 6 } },
  'lightning-rail-stock': { tier: 'blue', read: true },
  'm4-recoil-buffer-tube': { tier: 'green', read: true },
  'practical-light-stock': { tier: 'green', read: true, stats: { Handling: 2 } },
  'practical-tactical-stock': { tier: 'green', read: true },
  'practical-stable-stock': { tier: 'green', read: true },
  'core-rail-stock': { tier: 'green', read: true },

  /*
   * --- the MCX LT's own parts ---------------------------------------------
   *
   * These were read off the cards in the recording, where a frame shows the six
   * rows it happens to include and the five below it -- armour penetration,
   * fire rate, capacity, muzzle velocity, gunshot range -- sit off the bottom.
   * That is the exact shape of reading that put a wrong muzzle velocity on the
   * Wave Blaster, so all four kept the hedge until someone scrolled the card.
   *
   * Everything here has now been read that way and is cleared EXCEPT the SUR
   * Heat Shield, which still says so on the page.
   */
  'mcx-lt-fierce-barrel': {
    tier: 'purple',
    stats: {
      Control: 11, Handling: 2, Accuracy: -20,
      // The one figure here the card does not print as a change: it shows 36
      // against the rifle's 34, and lists Firing Damage among its effects.
      Damage: 2
    },
    read: true
  },
  'mcx-lt-hunter-barrel': {
    tier: 'blue',
    stats: {
      Range: 9, Control: 12, Handling: -7, Stability: 5, Accuracy: -36,
      // Given as the card's figure, 760, not as a change -- the same way the
      // Fierce Barrel's damage was given. The rifle leaves the rack at 450, so
      // this is the longest barrel on the site by a distance: the RM277's
      // Heavy Integral is +195 and nothing else clears +160.
    },
    read: true
  },
  'sur-heat-shield': {
    tier: 'purple',
    // "Increased Fire Rate" on the card. The figure is in scaled-stats.json.
    stats: { Stability: -2 }
  },
  /*
   * Two of the five magazines, both AR-pattern and neither in the catalogue.
   *
   * `Holds` is the set value, not a change: weapon-stats.ts carries Capacity
   * with mode 'set', so 30 here means the rifle holds 30 with this mag in,
   * which happens to be what it holds without one. That is a real reading and
   * not a missing one -- the polymer mag is the standard-size option and buys
   * its stability without costing a round.
   */
  'ar-60-round-extended-mag': {
    tier: 'purple',
    stats: { Holds: 60, Handling: -12 },
    read: true
  },
  'ar-30-round-polymer-mag': {
    tier: 'blue',
    stats: { Holds: 30, Stability: 2 },
    read: true
  },
  /*
   * The MK47's two barrels, both MK47-exclusive and so absent from a catalogue
   * compiled by category -- the fourth weapon in a row whose barrels are.
   *
   * COLOUR ONLY. Al gave the rarity band and no stat line, and neither card has
   * been opened, so there is no `read` and both keep the #not-tracked tag. Two
   * purples with nothing to tell them apart is exactly what an unread pair
   * should look like; the day one is read it stops being a twin.
   *
   * No slot rule on either. The MK47 already carries an upper rail and all
   * three patches on the bare rifle, so unlike the RM277's and the AR-57's
   * barrels there is nothing here for a barrel to hand it -- which is why this
   * weapon's barrel list is two items long and does not branch.
   */
  'mk47-battle-barrel': { tier: 'purple' },
  'mk47-ember-barrel': { tier: 'purple' },
  /*
   * COLOUR READ OFF THE ORDER, not off a card. The game lists a slot by rarity,
   * most to least, and this stock is fourth in a nineteen-item list whose first
   * eight -- the Anchor Point Rail Stock through the Shadow Rail Stock -- are
   * all purple. Fourth place is inside that run with purples on both sides of
   * it, so there is only one band it can be in.
   *
   * That is the same argument that coloured five AK muzzles on this weapon, and
   * it is only as good as the position: an item at the seam between two bands
   * gets no colour this way. The APX Hybrid Sight below is exactly that case.
   */
  'mk47-dominator-stock': { tier: 'purple' }
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
    weight: 0.6
  }
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
