/**
 * What fitting one attachment does to the rest of the gunsmith.
 *
 * Kept apart from ATTACHMENTS on purpose. That array is 414 entries of stats
 * and prices compiled from one source; this is a different fact about a
 * different, smaller set of items, gathered by hand from voice transcripts.
 * Joining them by id means an item with no rule is simply absent here rather
 * than 414 entries carrying empty fields, and neither file has to be
 * regenerated when the other changes.
 *
 * WHY A FLAT LIST CANNOT HOLD THIS
 *
 * "Adds a slot" makes the gunsmith a tree. A riser occupies the optic slot and
 * opens a new one above it; whatever goes in that new slot does not exist as a
 * choice until the riser is fitted. So the fact lives on the parent — the child
 * is only reachable through it. Model it as a flat list of items each naming
 * their own slot and the relationship disappears, which is why it kept getting
 * lost.
 *
 *   grants     slots this opens up once fitted
 *   conflicts  attachment ids that cannot be fitted alongside this one
 *
 * Both are symmetric in meaning but NOT stored twice: a conflict is written on
 * one side and read from either, via `conflictsWith` below. Writing it on both
 * is how the two halves drift apart.
 *
 * THE THREE RISERS ARE NOT INTERCHANGEABLE
 *
 * This is the part that kept getting flattened. Each riser opens a DIFFERENT
 * slot, so which one you fit decides what you may fit above it:
 *
 *   Micro Sight Riser              -> red-dot optics
 *   MEO Micro Sight Riser          -> red-dot optics
 *   Multi-Purpose Tactical Riser   -> riser optics AND a tactical device
 *
 * Only the MPTR opens the wide riser-optic pool, and that pool contains the two
 * micro risers — so a micro riser stacked on an MPTR still opens red dots. The
 * grant belongs to the attachment, not to how deep it sits: an earlier pass
 * resolved this by stack depth and had to be undone.
 *
 * The three optic pools still nest — optics contains riser optics contains red
 * dots — which is what OPTIC_LADDER records and `ladderViolations` checks. That
 * is a containment fact about the lists, not a rule about stacking.
 */

import { ATTACH_BY_ID } from './attachments';
import { UNCATALOGUED } from './uncatalogued';

/** Every item this file may name: the catalogue's, plus the ones it lacks. */
export const KNOWN_ITEM = (id: string): boolean =>
  Boolean(ATTACH_BY_ID[id]) || Boolean(UNCATALOGUED[id]);

/** A slot that only exists because something else granted it. */
export type GrantedSlot =
  | 'optics'
  | 'riser-optics'
  | 'red-dot-optics'
  | 'offset-optics'
  | 'kill-flash'
  | 'tactical-device'
  | 'upper-rail'
  | 'left-rail'
  | 'right-rail'
  | 'left-patch'
  | 'right-patch'
  | 'rear-grip-patch'
  | 'rear-grip-mount'
  | 'heat-shield'
  | 'cheek-pad'
  | 'stock-pad'
  | 'mag-mount';

export interface AttachRule {
  /** Slots this attachment opens up. */
  grants?: GrantedSlot[];
  /**
   * Slots this attachment conflicts with — base slots included.
   *
   * The slot still exists on the gun; fitting this makes it unusable. An
   * integrally suppressed barrel conflicts with the muzzle because it occupies
   * the same place, not because the gun stopped having a muzzle.
   */
  conflictSlots?: string[];
  /** Attachment ids that cannot be fitted at the same time as this one. */
  conflicts?: string[];
}

/**
 * Keyed by attachment id, as they appear in ATTACHMENTS.
 *
 * An id that is not in here has no special behaviour: it takes its own slot
 * and nothing else changes.
 */
export const ATTACH_RULES: Record<string, AttachRule> = {
  // Both micro risers open a red-dot slot, wherever they are fitted. An earlier
  // pass had this as a riser-optic slot narrowing to red dots one level up; the
  // grant is simply red dots.
  'micro-sight-riser': { grants: ['red-dot-optics'] },
  // "the multi-purpose tactical riser adds a tactical device [slot]", plus
  // "you have ability to put an extra riser on it" — the riser-optic slot,
  // whose list carries the two stackable risers.
  'multi-purpose-tactical-riser': { grants: ['tactical-device', 'riser-optics'] },
  // Five scopes open a kill-flash slot. Four of them are in the catalogue and
  // sit here; the M157 is not, so its identical rule waits in PENDING_RULES.
  'insight-3-7-sniper-scope': { grants: ['kill-flash'] },
  'lpvo-scope': { grants: ['kill-flash'] },
  'recon-1-5-5-adjustable-scope': { grants: ['kill-flash'] },
  // The only one of the five that opens two slots: it carries a dot mount as
  // well, and it takes the same red-dot pool a micro riser opens rather than
  // a list of its own.
  '3-7-adjustable-scope': { grants: ['kill-flash', 'red-dot-optics'] },

  // The first slot grant outside the optic group.
  'ar-heavy-tower-grip': { grants: ['rear-grip-mount'] },
  // MEO Micro Sight Riser -> ['optics'] belongs here too, but the item is not in
  // ATTACHMENTS. Writing the rule now would dangle, so it waits in PENDING_RULES.
};

/**
 * Every slot type the gunsmith can present, in the order they run along the gun.
 *
 * WHY THIS EXISTS SEPARATELY FROM THE CATALOGUE'S CATEGORIES
 *
 * ATTACHMENTS sorts its 414 entries into nine `cat` values — barrel, foregrip,
 * functional, handguard, mag, muzzle, optic, rear grip, stock. Those describe
 * what a part IS. They do not describe where it can go, and they are missing
 * every mount that only exists because something else granted it: the rail
 * positions, the bipod, the riser slots. A bipod is not a ninth category of
 * object, it is a place on the gun. So the slot list is longer than the category
 * list and has to be written down on its own.
 *
 *   base     always present on a weapon that supports it
 *   granted  only appears once a parent attachment opens it (see ATTACH_RULES)
 */
export interface SlotType {
  id: string;
  label: string;
  kind: 'base' | 'granted';
  /** The catalogue `cat` that fills it, when one maps cleanly. */
  cat?: string;
}

export const SLOT_TYPES: SlotType[] = [
  { id: 'muzzle', label: 'Muzzle', kind: 'base', cat: 'muzzle' },
  { id: 'barrel', label: 'Barrel', kind: 'base', cat: 'barrel' },
  { id: 'handguard', label: 'Handguard', kind: 'base', cat: 'handguard' },
  { id: 'foregrip', label: 'Foregrip', kind: 'base', cat: 'foregrip' },

  // The rail family. None of these has a catalogue `cat` of its own, which is
  // the clearest sign that `cat` was never a slot map.
  //
  // `kind` HERE IS THE USUAL CASE, NOT THE RULE. It used to be flatly true:
  // the upper rail had to be opened by an RM277 barrel, and the patches were
  // on the gun. The MCX LT is both of those the other way round -- its upper
  // rail and upper patch are on the bare rifle, and its left and right patches
  // arrive with the Fierce Barrel. Which slots a weapon HAS is answered by
  // that weapon's own traced `slots` in data/gunsmith-<id>.json, and the page
  // reads it from there; this field is a note about the family.
  { id: 'upper-rail', label: 'Upper Rail', kind: 'granted' },
  { id: 'upper-patch', label: 'Upper Patch', kind: 'base' },
  { id: 'left-rail', label: 'Left Rail', kind: 'base' },
  { id: 'right-rail', label: 'Right Rail', kind: 'base' },
  { id: 'left-patch', label: 'Left Patch', kind: 'base' },
  { id: 'right-patch', label: 'Right Patch', kind: 'base' },
  { id: 'rail-bipod', label: 'Rail Bipod', kind: 'base' },
  // Round the barrel rather than on a rail, and opened by one: the MCX LT's
  // Fierce Barrel grants it along with both side patches.
  { id: 'heat-shield', label: 'Heat Shield', kind: 'granted' },

  // The optic ladder — see OPTIC_LADDER, which holds what each one accepts.
  { id: 'optics', label: 'Optics', kind: 'base', cat: 'optic' },
  { id: 'riser-optics', label: 'Riser Optics', kind: 'granted' },
  { id: 'red-dot-optics', label: 'Red Dot Optics', kind: 'granted' },
  // Presented as a standing slot ("the offset optic slot"), the same way the
  // base optic slot was, so recorded as base. If something has to be fitted
  // before it appears, this is a `granted` and the parent is unknown.
  { id: 'offset-optics', label: 'Offset Optics', kind: 'base' },
  // Hangs off magnified glass rather than off the gun: five of the scopes in
  // the base optic list open it, and nothing else does.
  { id: 'kill-flash', label: 'Killflash', kind: 'granted', cat: 'functional' },
  { id: 'tactical-device', label: 'Tactical Device', kind: 'granted' },

  { id: 'mag', label: 'Magazine', kind: 'base', cat: 'mag' },
  { id: 'mag-mount', label: 'Magazine Mount', kind: 'base' },
  { id: 'rear-grip', label: 'Rear Grip', kind: 'base', cat: 'rear grip' },
  { id: 'rear-grip-patch', label: 'Rear Grip Patch', kind: 'granted' },
  // The two grip bases sit under the catalogue's `rear grip` cat but are their
  // own slot — another case of one cat covering several slots.
  { id: 'rear-grip-mount', label: 'Rear Grip Mount', kind: 'granted', cat: 'rear grip' },
  // The AR-57 presents these as two chips, one above the other: a kit that
  // replaces the whole rear assembly, and the stock proper. The RM277 has
  // neither — it is a bullpup — so this pair arrived with the second weapon,
  // which is the first evidence that SLOT_TYPES is a game-wide vocabulary and
  // not one gun's list.
  { id: 'stock-kit', label: 'Stock Kit', kind: 'base', cat: 'stock' },
  { id: 'stock', label: 'Stock', kind: 'base', cat: 'stock' },
  // Both live under the catalogue's `stock` cat but are their own slots.
  { id: 'cheek-pad', label: 'Cheek Pad', kind: 'base', cat: 'stock' },
  { id: 'stock-pad', label: 'Stock Pad', kind: 'base', cat: 'stock' },
  { id: 'functional', label: 'Functional', kind: 'base', cat: 'functional' },
];

/** Slot types by id, for anything that has to join against this list. */
export const SLOT_TYPE_BY_ID: Record<string, SlotType> = Object.fromEntries(
  SLOT_TYPES.map((s) => [s.id, s]),
);

/**
 * A slot named in a transcript that could not be pinned to a SLOT_TYPES entry.
 *
 * Left here verbatim rather than guessed into the list above. A wrong slot id in
 * SLOT_TYPES would quietly attach real compatibility data to a slot that does
 * not exist, and nothing would ever flag it.
 */
export const UNRESOLVED_SLOTS: string[] = [
  // RESOLVED. "left/right path" was left/right PATCH — a real pair of slots,
  // distinct from the rails and taking handguard panels only. Kept as a note
  // rather than deleted, because the same mishearing will recur.
];

/**
 * The risers that can sit on top of another riser.
 *
 * Both appear inside the riser-optic list — being in that list is *what makes*
 * them stackable, so this is a view of it, not a second source of truth. The
 * Multi-Purpose Tactical Riser is deliberately absent: it is not in the
 * riser-optic list, so it mounts in the base optic slot only.
 */
export const STACKABLE_RISERS = ['micro-sight-riser', 'meo-micro-sight-riser'];

/**
 * ONE ARRAY PER CATEGORY. This is the compatibility data.
 *
 * Keyed by the slot-type ids in SLOT_TYPES. Every category gets an entry even
 * when nothing has been transcribed for it yet, so an empty array reads as
 * "asked and empty" only in combination with PARTIAL_CATEGORIES below — see the
 * note there, because the difference matters.
 *
 * OVERLAP IS DELIBERATE. The three optic categories share members on purpose:
 * `optics` is the broad slot on the weapon, `riser-optics` the narrower pool a
 * riser opens, `red-dot-optics` the narrowest. An item that fits all three is
 * listed three times. Deduplicating them into one list with flags is exactly the
 * shape that lost the distinction in the first place — a sight is not "a red
 * dot" in the abstract, it is a sight that a particular slot will accept.
 */
export const CATEGORY_FITS: Record<string, string[]> = {
  // --- barrel group -------------------------------------------------------
  // Both RM277-exclusive and neither in the 414. Dictated with the Whale Shark
  // first. This list had nowhere to live while uncatalogued items were held
  // apart from catalogued ones -- a slot whose every member is missing from
  // the 414 simply had no entry here at all, which read as "no barrels" rather
  // than "two barrels, both absent from one source".
  barrel: [
    'rm277-whale-shark-barrel-combo',
    'rm277-heavy-integral-barrel',
  ],

  // 16 named for the RM277 out of the catalogue's 37 muzzles — a real
  // per-weapon filter, unlike foregrip. Dictated order, reversed. The first two
  // are not in the 414; they are in UNCATALOGUED, and named here by id like
  // everything else, because whether the catalogue happens to carry a part is
  // not a fact about which slot takes it.
  muzzle: [
    'rm277-breaker-suppressor',
    'cobweb-titanium-muzzle-brake',
    'spiral-fire-flash-hider',
    'advanced-multi-caliber-suppressor',
    'm7-practical-suppressor', // transcribed "MC-7"
    'silent-suppressor',
    'sandstorm-vertical-compensator',
    'bastion-horizontal-compensator',
    'poseidon-flash-hider',
    'whisper-tactical-suppressor',
    'titanium-contest-muzzle-brake',
    'blazing-fire-suppressor',
    'steel-muzzle-brake',
    'practical-suppressor',
    'birdcage-flash-hider', // transcribed "Breed Cage"
    'practical-flash-hider',
  ],
  handguard: [],
  foregrip: [
    'resonant-mk-iii-grip',
    'ec-universal-front-hand-stop',
    // 23 named for the RM277 across two passes, 21 resolve — and those 21 are
    // EVERY foregrip in the catalogue. Unlike muzzle (14 of 37), this slot is
    // not filtered at all, which is also why the two that do not resolve read as
    // catalogue gaps rather than as items the RM277 cannot take.
    //
    // Dictated order, reversed as requested. The two missing items were spoken
    // last and so head the list:
    //   'resonant-mk-iii-grip',           <- named, absent from ATTACHMENTS
    //   'ec-universal-front-hand-stop',   <- named, absent from ATTACHMENTS
    'dawn-angled-flashlight-grip', // transcribed "down angle"
    'daybreak-vertical-flashlight-grip',
    'cr-prism-hand-stop',
    'resonant-mkii-foregrip',
    'collapsible-bipod-grip', // transcribed "compa-compatible B-bot grip"
    'k1-elite-bevel-foregrip',
    'x25u-angled-combat-grip',
    'resonant-ergonomic-grip', // transcribed "resonance economic grip"
    'phantom-vertical-foregrip',
    'tactical-vertical-foregrip',
    'secret-order-bevel-foregrip',
    'rk-0-foregrip',
    'tactical-angled-foregrip',
    'angled-hand-stop',
    'competition-hand-stop',
    'phase-combat-foregrip', // transcribed "face combat foregrip"
    'folding-grip', // transcribed "holding grip"
    'vfg-knight-foregrip',
    'zfsg-tactical-grip', // transcribed "ZFSG practical grip"
    'mini-hand-stop',
    'practical-vertical-foregrip',
  ],

  // --- rail group ---------------------------------------------------------

  /** Rail bipod — one option. */
  'rail-bipod': ['practical-bipod'],

  /**
   * Upper rail — 11 named, 9 resolve. A subset of the side rails: same five
   * panels and five of the lights/lasers, but not the OLIGHT Odin S, the OLIGHT
   * Baldr Pro R or the Practical Weapon Light.
   */
  'upper-rail': [
    'olight-warrior-3s-tactical-flashlight',
    // 'olight-warrior-3s-tactical-flashlight',  <- named, absent
    'dbal-x2-purple-laser-light-combo',
    'perst-7-blue-laser-light-combo',
    'flare-tactical-flashlight',
    'la-3c-green-laser-light-combo',
    'peq-2-red-laser-light-combo',
    'modular-handguard-panel',
    'hornet-handguard',
    'dd-python-handguard-panel',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /**
   * Left rail — 13 named, 11 resolve. Eight lights and lasers plus the five
   * handguard panels. Absent from the 414: OLIGHT Odin S Tactical Flashlight,
   * DD Python Handguard Panel.
   *
   * The Warrior 3S was dictated onto this list and is not on it. It is on the
   * right rail and the upper rail, which is what made the mistake easy: three
   * lists that agree about almost everything, transcribed in one sitting.
   */
  'left-rail': [
    'olight-odin-s-tactical-flashlight',
    // 'olight-odin-s-tactical-flashlight',      <- named, absent
    'olight-baldr-pro-r-multi-function-flashlight',
    'dbal-x2-purple-laser-light-combo',
    'perst-7-blue-laser-light-combo', // transcribed "Burst ST-7"
    'flare-tactical-flashlight',
    'la-3c-green-laser-light-combo',
    'peq-2-red-laser-light-combo',
    'practical-weapon-light',
    'modular-handguard-panel',
    'hornet-handguard',
    'dd-python-handguard-panel',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /**
   * Right rail — 14 named, 11 resolve. Absent from the 414: OLIGHT Warrior 3S
   * Tactical Flashlight, OLIGHT Odin S Tactical Flashlight, DD Python
   * Handguard Panel.
   *
   * Dictated as identical to the left at first, then corrected to leave the
   * Odin S off, then corrected back. It carries the Warrior 3S and the left
   * rail does not, so the two lists still differ and are still written out in
   * full rather than aliased to each other. Two slots that agree about eleven
   * of thirteen entries are still two slots, and every time this pair has been
   * re-read the difference has moved.
   */
  'right-rail': [
    'olight-warrior-3s-tactical-flashlight',
    'olight-odin-s-tactical-flashlight',
    // 'olight-warrior-3s-tactical-flashlight',  <- named, absent
    // 'olight-odin-s-tactical-flashlight',      <- named, absent
    'olight-baldr-pro-r-multi-function-flashlight',
    'dbal-x2-purple-laser-light-combo',
    'perst-7-blue-laser-light-combo', // transcribed "Burst ST-7"
    'flare-tactical-flashlight',
    'la-3c-green-laser-light-combo',
    'peq-2-red-laser-light-combo',
    'practical-weapon-light',
    'modular-handguard-panel',
    'hornet-handguard',
    'dd-python-handguard-panel',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /** Left patch — handguard panels only. 5 named, 4 resolve. */
  'left-patch': [
    'modular-handguard-panel',
    'hornet-handguard',
    'dd-python-handguard-panel',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /** Right patch — the same five panels, written out for the reason above. */
  'right-patch': [
    'modular-handguard-panel',
    'hornet-handguard',
    'dd-python-handguard-panel',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  // --- optic group: three overlapping pools, widest first -----------------

  /**
   * The weapon's own optic slot — 31 named, 22 resolve. The widest of the three
   * optic pools, and now complete: the earlier version stopped at "1P—".
   *
   * Absent from the 414 (9): White Phosphor Thermal Scope, Advanced Thermal Fusion
   * Holographic Sight, VMX Frameless Sight, 1P-33 2/4x Scope, UHX Holographic
   * Sight, Prism Universal 2x Optic, M157 Fire Control System, 1P-29 Russian 3x
   * Sight, MEO Micro Sight Riser.
   *
   * The catalogue's other 11 optics are absent from this list rather than from
   * the game: the offset sights, the PSO scopes, the 8x snipers, the M3 and the
   * 6/12s. An assault rifle does not take them.
   */
  optics: [
    'white-phosphor-thermal-scope',
    'advanced-thermal-fusion-holographic-sight',
    'vmx-frameless-sight',
    '1p-33-2-4x-scope',
    'uhx-holographic-sight',
    'prism-universal-2x-optic',
    // 'white-phosphor-thermal-scope',               <- named, absent
    // 'advanced-thermal-fusion-holographic-sight',  <- named, absent
    // 'vmx-frameless-sight',                        <- named, absent
    // '1p-33-2-4x-scope',                           <- named, absent.
    //     Heard "1P-32 4X" once and "1P-332/4X" the next time; read as a
    //     variable 2-4x. The id is a guess until the item turns up.
    // 'uhx-holographic-sight',                      <- named, absent
    // 'prism-universal-2x-optic',                   <- named, absent
    'insight-3-7-sniper-scope',
    'm157-fire-control-system',
    // 'm157-fire-control-system',                   <- named, absent
    'viewpoint-3x-scope',
    '1p-29-russian-3x-sight',
    // '1p-29-russian-3x-sight',                     <- named, absent
    'lpvo-scope',
    '3-7-adjustable-scope',
    'recon-1-5-5-adjustable-scope',
    'hamr-combined-scope',
    'meo-micro-sight-riser',
    // the three risers
    // 'meo-micro-sight-riser',                      <- named, absent
    'multi-purpose-tactical-riser',
    'micro-sight-riser',
    // then the plain optic options
    'acog-precision-6x-scope',
    'osight-red-dot',
    'cobra-accuracy-sight',
    'combat-red-dot-sight',
    'mini-red-dot-sight',
    'okp-7-reflex-sight',
    'xcog-assault-3-5x-scope',
    'xro-quick-response-sight',
    'panoramic-red-dot-sight',
    'ap5000-reflex-sight',
    'holographic-sight-type-ii',
    'reflex-sight',
    'russian-accuracy-2x-scope',
    'holographic-sight',
  ],

  /**
   * The slot a riser opens. 16 named, 12 resolve.
   *
   * Absent from the 414 and so commented in place rather than dropped, since
   * four of sixteen is too much of the list to lose:
   *   Advanced Thermal Fusion Holographic Sight  (first in the dictated order;
   *     heard "ATV thermal fusion" in the optic pass and "Adv" in this one)
   *   VMX Frameless Sight
   *   UHX Holographic Sight
   *   MEO Micro Sight Riser
   */
  'riser-optics': [
    'advanced-thermal-fusion-holographic-sight',
    'vmx-frameless-sight',
    'uhx-holographic-sight',
    'meo-micro-sight-riser',
    // 'advanced-thermal-fusion-holographic-sight',
    // 'vmx-frameless-sight',
    // 'uhx-holographic-sight',
    // 'meo-micro-sight-riser',
    'micro-sight-riser',
    'osight-red-dot',
    'cobra-accuracy-sight',
    'combat-red-dot-sight',
    'mini-red-dot-sight',
    'okp-7-reflex-sight',
    'xro-quick-response-sight',
    'panoramic-red-dot-sight',
    'holographic-sight-type-ii',
    'reflex-sight',
    'russian-accuracy-2x-scope',
    'holographic-sight',
  ],

  /**
   * What a riser stacked on a riser will accept. 6 named, 5 resolve.
   *
   * A strict subset of `riser-optics`, which is the cross-check between two
   * separately dictated lists. The catalogue carries an `offset-` twin of all
   * five that resolve, so the VMX looks like a real gap, not a mishearing.
   */
  'red-dot-optics': [
    'vmx-frameless-sight',
    // 'vmx-frameless-sight',
    'osight-red-dot',
    'combat-red-dot-sight',
    'mini-red-dot-sight',
    'xro-quick-response-sight',
    'panoramic-red-dot-sight',
  ],

  /**
   * Offset optics — 5 named, all 5 resolve. The only category so far with no
   * gaps at all.
   *
   * Exactly the offset twins of the five red dots, in the same order, and it
   * accounts for five of the eleven catalogue optics the base list omitted:
   * they were not missing from the weapon, they belong to a different slot.
   * Note there is no offset VMX, which fits — the VMX is the one red dot the
   * catalogue has no `offset-` twin for.
   */
  'offset-optics': [
    'offset-osight-red-dot',
    'offset-combat-red-dot-sight',
    'offset-mini-red-dot-sight',
    'offset-xro-quick-response-sight',
    'offset-panoramic-red-dot-sight',
  ],

  /**
   * Kill flash — 1 named, it resolves. The shortest list here, and complete:
   * the slot was described as having the one option.
   *
   * The catalogue files the Honeycomb Killflash under `functional`, alongside
   * bolt covers and the like, which is another case of one cat spanning slots
   * that have nothing to do with each other. It is the slot that says where it
   * goes, not the cat.
   */
  'kill-flash': ['honeycomb-killflash'],

  /**
   * Tactical device — 4 named, all 4 resolve.
   *
   * The same four laser-light combos also appear on all three rails. Both are
   * true: an item can be compatible with more than one slot, which is why these
   * pools overlap rather than partition. The earlier guess at this list was
   * walked back because it had been offered as the ONLY home for these four.
   */
  'tactical-device': [
    'dbal-x2-purple-laser-light-combo',
    'perst-7-blue-laser-light-combo',
    'la-3c-green-laser-light-combo',
    'peq-2-red-laser-light-combo',
  ],

  // --- receiver group -----------------------------------------------------

  /**
   * Magazine — 1 named, 1 resolves. "M768 45 round drum mag" is the M7 6.8
   * 45-Round Drum Mag; the RM277 is chambered in 6.8x51mm, so the caliber
   * agrees with the match.
   *
   * The catalogue holds exactly two 6.8 mags — this one and the M7 6.8 30-Round
   * Mag — and only the drum was named. Worth confirming the 30-round is really
   * excluded rather than simply not read out.
   */
  mag: ['m7-6-8-45-round-drum-mag'],

  /** Magazine mount — 3 named, all 3 resolve. */
  'mag-mount': [
    'grizzly-full-p-mag-assist-sand',
    'grizzly-full-p-mag-assist-green',
    'grizzly-full-p-mag-assist-black',
  ],

  /**
   * Rear grip — 9 named, 7 resolve. Absent from the 414: AR Modular Rear Grip,
   * AR MOE Rear Grip.
   *
   * Two of them open further slots, the first grants outside the optic group:
   * AR Modular Rear Grip opens the rear-grip patch, AR Heavy Tower Grip the
   * rear-grip mount.
   *
   * "416 Practical Rear Grip" is the catalogue's exact name — no HK prefix.
   */
  'rear-grip': [
    'ar-modular-rear-grip',
    // 'ar-modular-rear-grip',  <- named, absent. Opens the rear-grip patch.
    'ar-heavy-tower-grip',
    'invasion-rear-grip',
    'phantom-rear-grip',
    'ar-moe-rear-grip',
    // 'ar-moe-rear-grip',      <- named, absent
    'marksman-d-2-rear-grip',
    'hurricane-d-1-rear-grip',
    'm7-stable-rear-grip',
    '416-practical-rear-grip',
  ],

  /** Rear grip patch — 2 named, neither in the 414. */
  'rear-grip-patch': [
    'ar-light-grip-piece',
    'ar-heavy-grip-piece',
    // 'ar-light-grip-piece',   <- named, absent
    // 'ar-heavy-grip-piece',   <- named, absent
  ],

  /** Rear grip mount — 2 named, both resolve. */
  'rear-grip-mount': ['balanced-grip-base', 'stable-grip-base'],

  stock: [],

  /** Cheek pad — 1 named, absent from the 414. */
  'cheek-pad': [
    'rm277-cheek-pad',
    // 'rm277-cheek-pad',   <- named, absent. The catalogue carries M700, QBZ
    //                         and Universal cheek pads but no RM277 one.
  ],

  /** Stock pad — 1 named, absent from the 414. */
  'stock-pad': [
    'rm277-pad',
    // 'rm277-pad',         <- named, absent from ATTACHMENTS
  ],

  functional: [],
};

/**
 * Categories whose array is known to be incomplete.
 *
 * An empty array and a partial array both look like data; neither is. This set
 * is what stops a caller treating a half-transcribed list as the whole truth,
 * and it is why the ladder's bottom rung reads as unknown rather than as two
 * items.
 */
export const PARTIAL_CATEGORIES = new Set<string>();

/** A category's list, or null when it is empty or known incomplete. */
export function fitsForCategory(cat: string): string[] | null {
  const list = CATEGORY_FITS[cat];
  if (!list || list.length === 0) return null;
  return PARTIAL_CATEGORIES.has(cat) ? null : list;
}

/** Named views onto the optic categories, for callers that want them directly. */
export const RISER_OPTIC_FITS = CATEGORY_FITS['riser-optics'];
export const RED_DOT_FITS = CATEGORY_FITS['red-dot-optics'];

/**
 * THE NESTING.  optics ⊇ riser optics ⊇ red dots
 *
 * Not a stacking rule — which slot a riser opens is on the riser itself, in
 * ATTACH_RULES. This records only that the three optic pools nest, which is the
 * cross-check between three separately dictated lists. Built from the category
 * arrays so it cannot drift out of step with them.
 */
export const OPTIC_LADDER: (string[] | null)[] = [
  fitsForCategory('optics'),
  fitsForCategory('riser-optics'),
  fitsForCategory('red-dot-optics'),
];

/**
 * Slot keys used in WEAPON_FITS that are not in SLOT_TYPES.
 *
 * The two lists are written by different hands — SLOT_TYPES from the gunsmith's
 * own layout, WEAPON_FITS from whatever a transcript happened to cover — so a
 * typo in either simply produces a slot nothing ever reads.
 */
export function unknownSlotKeys(): string[] {
  const bad = new Set<string>();
  for (const bySlot of Object.values(WEAPON_FITS)) {
    for (const slot of Object.keys(bySlot)) {
      if (!SLOT_TYPE_BY_ID[slot]) bad.add(slot);
    }
  }
  return [...bad];
}

export function ladderViolations(): string[] {
  const out: string[] = [];
  for (let i = 1; i < OPTIC_LADDER.length; i++) {
    const below = OPTIC_LADDER[i - 1];
    const here = OPTIC_LADDER[i];
    if (!below || !here) continue; // an unknown rung constrains nothing
    for (const id of here) {
      if (!below.includes(id)) out.push(`rung ${i}: ${id} is not in rung ${i - 1}`);
    }
  }
  return out;
}

/**
 * Rules for items the transcript describes but the catalogue does not carry.
 *
 * Parked rather than dropped: the fact was expensive to obtain and the item may
 * appear in a later catalogue pass. Nothing reads this at runtime — it exists so
 * the knowledge survives, and so `danglingRuleIds` stays quiet about ids that
 * were never claimed to exist.
 */
export const PENDING_RULES: Record<string, AttachRule> = {
  'meo-micro-sight-riser': {
    grants: ['red-dot-optics'],
  },

  /*
   * The third thing to open a red dot mount, after the two micro sight risers
   * and the 3/7 Adjustable Scope's own. Unlike those it is not a riser at all
   * but a sight in its own right, which is what "hybrid" is saying.
   *
   * First seen on the MK47 and not in the 414, so it waits here.
   */
  'apx-hybrid-sight': {
    grants: ['red-dot-optics'],
  },

  /*
   * The first attachments that REMOVE slots, and the first slot rules outside
   * the optic ladder. Both are RM277-exclusive and absent from the 414, so they
   * park here rather than dangling in ATTACH_RULES — but the rules are the
   * valuable part and are written down in full.
   */
  'rm277-heavy-integral-barrel': {
    grants: ['upper-rail'],
    // An integral barrel occupies the muzzle, and rules out the rail bipod.
    conflictSlots: ['muzzle', 'rail-bipod'],
  },
  'ar-modular-rear-grip': {
    grants: ['rear-grip-patch'],
    /*
     * Its card prints Grip Mount under "Conflicting Slots", and this rule used
     * to carry it. IT CANNOT EVER FIRE, so it is gone.
     *
     * The mount is opened by the AR Heavy Tower Grip, which goes in the rear
     * grip slot -- the same slot this grip is in. Fitting one takes the other
     * off, so the mount does not exist in any build that has the modular grip
     * in it. The rule was true and had nothing to be true about.
     *
     * It was not free, either. A conflict is part of what the page matches a
     * traced layout against, so declaring one obliged all three weapons to
     * record `blocks: ["rear-grip-mount"]` on an arrangement where no mount
     * was ever open; get that wrong and the page silently composes a picture
     * instead of using the one that was watched, and every chip drifts a few
     * pixels. Three specs and three layout files carried that just to agree
     * with a rule that could not apply.
     *
     * The lesson is not that the card was wrong. It is that a rule copied from
     * a card wants asking whether the situation it forbids can happen.
     */
  },
  /*
   * The MCX LT's two barrels, and between them the counterexample to the shape
   * the other two rifles taught: LEFT AND RIGHT PATCHES ARE NOT SOMETHING A GUN
   * HAS. They are something a barrel brings, and on this rifle either barrel
   * brings them. The bare MCX LT has an upper patch and no side patches at all.
   *
   * The Fierce Barrel opens a third slot on top of that, a heat shield round
   * the barrel, which no other weapon here has. It takes nothing away: it is
   * drawn with a fat can on the front and the recording of it shows no muzzle
   * chip, which is why this rule said it occupied the muzzle for one commit.
   * Al has since checked in the game -- the muzzle slot survives it. The
   * recorded arrangement is the one that is wrong, and it is short a chip
   * rather than short a slot; see the note in data/cut-specs/mcx-lt-layouts.json.
   */
  'mcx-lt-fierce-barrel': {
    grants: ['heat-shield', 'left-patch', 'right-patch'],
  },
  'mcx-lt-hunter-barrel': {
    grants: ['left-patch', 'right-patch'],
  },
  'm157-fire-control-system': {
    grants: ['kill-flash'],
  },
  'rm277-whale-shark-barrel-combo': {
    grants: ['upper-rail'],
    // It does block the bipod, confirmed later than the rest of the rule. The
    // note that used to sit here said no conflict had been *stated* and warned
    // that silence was not the same as none — which is exactly how it turned
    // out. Only the bipod: unlike the Heavy Integral Barrel this one has not
    // been seen to take the muzzle, so the muzzle is not listed.
    conflictSlots: ['rail-bipod'],
  },

  /*
   * The AR-57's long barrel, read off its card in the same clip the slot layout
   * came from. Like the RM277's two it opens an upper rail; unlike them it has
   * not been seen to take anything away, so nothing is listed — silence here is
   * "not observed", which the Whale Shark taught us is not the same as "none".
   */
  'ar57-wave-blaster-ultra-long-barrel': {
    grants: ['upper-rail'],
  },
};

/**
 * Which attachments fit which slot, PER WEAPON.
 *
 * Keyed by weapon id (as in WEAPONS), then by slot. This is deliberately not a
 * global slot -> items map: the transcript below names 14 of the catalogue's 37
 * muzzles and excludes every shotgun-, pistol- and AK-specific one, which is
 * exactly what a single weapon's compatibility list looks like. Store it
 * globally and you assert that a shotgun choke fits an assault rifle.
 *
 * Absent weapon = not yet transcribed, NOT "fits nothing". Anything reading this
 * must fall back to the whole category when a weapon has no entry — see
 * `fitsFor` below, which is the only correct way to ask.
 */
/**
 * Three of the maps above are categories rather than RM277 slots.
 *
 * The rifle is a bullpup with an integral handguard: it presents no handguard,
 * no stock and no functional slot, and the lists under those keys are the
 * game's categories, gathered for weapons nobody has traced yet. Handing them
 * to the RM277 asserts three slots it does not have.
 */
const NOT_ON_THE_RM277 = new Set(['handguard', 'stock', 'functional']);
/*
 * The muzzle devices a small-bore carbine takes.
 *
 * Dictated for the AR-57 and then, item for item and in the same order, for
 * the MCX LT: fifteen of the catalogue's thirty-seven plus two it does not
 * carry. Against the RM277's list it is that weapon's whole list bar the
 * weapon-exclusive Breaker Suppressor, plus the FFC brake and the SMG Echo
 * Suppressor -- which is the tell that muzzles ARE filtered, and filtered by
 * calibre: a 5.7 carbine and a .300 Blackout carbine both get the SMG can, a
 * 6.8 rifle does not.
 */
const SMALL_BORE_MUZZLES = [
  'cobweb-titanium-muzzle-brake',
  'ffc-double-port-muzzle-brake',
  'spiral-fire-flash-hider',
  'advanced-multi-caliber-suppressor',
  'm7-practical-suppressor',
  'smg-echo-suppressor',
  'silent-suppressor',
  'sandstorm-vertical-compensator',
  'bastion-horizontal-compensator',
  'poseidon-flash-hider',
  'whisper-tactical-suppressor',
  'titanium-contest-muzzle-brake',
  'blazing-fire-suppressor',
  'steel-muzzle-brake',
  'practical-suppressor',
  'birdcage-flash-hider',
  'practical-flash-hider',
];

const RM277_FITS: Record<string, string[]> = Object.fromEntries(
  Object.entries(CATEGORY_FITS).filter(([slot]) => !NOT_ON_THE_RM277.has(slot)),
);

export const WEAPON_FITS: Record<string, Partial<Record<string, string[]>>> = {
  /*
   * The MCX LT, traced from one recording on 2026-09-03. Its twenty-one slots
   * are all placed; its lists are not read. These two entries are the whole of
   * what the recording showed being fitted in a slot, and each is ONE ITEM OUT
   * OF AN UNKNOWN NUMBER -- the picker was never opened on either. They are
   * here because the page needs a slot to file an uncatalogued item under, and
   * the ledes in SECTIONS say what they are.
   */
  'mcx-lt': {
    // Every list read off the picker in one pass. Six of them are shared word
    // for word with a rifle already here, and are referenced rather than
    // copied: the whole optic ladder and the rails and patches from the RM277,
    // the small-bore muzzles from the AR-57.
    optics: CATEGORY_FITS.optics,
    'red-dot-optics': CATEGORY_FITS['red-dot-optics'],
    'riser-optics': CATEGORY_FITS['riser-optics'],
    'offset-optics': CATEGORY_FITS['offset-optics'],
    'kill-flash': CATEGORY_FITS['kill-flash'],
    muzzle: SMALL_BORE_MUZZLES,
    'left-rail': CATEGORY_FITS['left-rail'],
    'right-rail': CATEGORY_FITS['right-rail'],
    'upper-rail': CATEGORY_FITS['upper-rail'],
    'left-patch': CATEGORY_FITS['left-patch'],
    'right-patch': CATEGORY_FITS['right-patch'],
    'rear-grip': CATEGORY_FITS['rear-grip'],
    'mag-mount': CATEGORY_FITS['mag-mount'],
    'tactical-device': CATEGORY_FITS['tactical-device'],
    'rear-grip-patch': CATEGORY_FITS['rear-grip-patch'],
    'rear-grip-mount': CATEGORY_FITS['rear-grip-mount'],
    // The five handguard panels, same as the two side patches on this rifle
    // and on the RM277. The one place "same as the RM277" could not be taken
    // at its word: that weapon has no upper patch to copy. This is the patch
    // list, which all three of this rifle's patch slots share.
    'upper-patch': CATEGORY_FITS['left-patch'],

    // Both weapon-exclusive, neither in the catalogue, and one of them is the
    // part that gives this rifle three of its slots.
    barrel: ['mcx-lt-fierce-barrel', 'mcx-lt-hunter-barrel'],
    'heat-shield': ['sur-heat-shield'],

    // SIXTEEN OF THE TWENTY-THREE, and the correction to what the AR-57's list
    // seemed to prove one commit ago. Two rifles agreeing on the whole
    // foregrip category looked like evidence that the slot was not filtered;
    // the third rifle takes a strict subset of it, in the same order, missing
    // the Resonant MK III and MKII, both flashlight grips, the K1 Elite Bevel,
    // the Secret Order Bevel and the Competition Hand Stop. Two weapons
    // agreeing was a coincidence of those two weapons.
    foregrip: [
      'ec-universal-front-hand-stop',
      'cr-prism-hand-stop',
      'collapsible-bipod-grip',
      'x25u-angled-combat-grip',
      'resonant-ergonomic-grip',
      'phantom-vertical-foregrip',
      'tactical-vertical-foregrip',
      'rk-0-foregrip',
      'tactical-angled-foregrip',
      'angled-hand-stop',
      'phase-combat-foregrip',
      'folding-grip',
      'vfg-knight-foregrip',
      'zfsg-tactical-grip',
      'mini-hand-stop',
      'practical-vertical-foregrip',
    ],

    // Nineteen: the AR-57's eighteen, less the Cardinal Advanced Combat, plus
    // the MRGS Skeleton and the UR Spec Ops Tactical. Another slot filtered
    // per weapon, and by a small enough margin that copying one list to the
    // other would have looked right.
    stock: [
      'anchor-point-rail-stock',
      'qr-high-performance-stock',
      'ct-enhanced-stock',
      'shadow-buffer-tube-stock',
      'mrgs-skeleton-stock',
      'ur-spec-ops-tactical-stock',
      'shadow-rail-stock',
      'skeleton-sniper-stock',
      '416-stable-stock',
      '416-light-stock',
      'elite-light-stock',
      'invasion-core-stock',
      'cardinal-stable-stock',
      'lightning-rail-stock',
      'm4-recoil-buffer-tube',
      'practical-light-stock',
      'practical-tactical-stock',
      'practical-stable-stock',
      'core-rail-stock',
    ],

    // Five, and the names came off the picker rather than out of the
    // dictation: four of the five were heard as "M4" and two of those are
    // "AR". The import carries the two M4s and neither AR, which is the gap
    // that only shows up when a whole list is read instead of sampled.
    mag: [
      'ar-60-round-extended-mag',
      'm4-60-round-drum-mag',
      'm4-45-round-extended-mag',
      'ar-30-round-polymer-mag',
      '5-56x45-30-round-polymer-mag',
    ],
  },

  // Every list in CATEGORY_FITS was dictated while reading the RM277's
  // gunsmith, so that map IS this weapon's, whole. Referenced rather than
  // copied: a copy is what would silently go stale the first time a name is
  // corrected above.
  //
  // It is spelled out here, and not left implicit, because the second weapon
  // below is what makes the distinction real. CATEGORY_FITS says what kind of
  // part each slot takes; this says which parts THIS gun's slot takes, and only
  // for the RM277 are the two the same thing.
  rm277: RM277_FITS,

  /*
   * The AR-57, traced from a clip of the bare weapon on 2026-09-01.
   *
   * Its slot LAYOUT is fully read — thirteen chips and where each one points —
   * but its attachment lists are not, and these two entries are all that has
   * been confirmed so far. An absent slot here is "not read yet", never "takes
   * nothing": the page says as much on every empty slot rather than drawing an
   * authoritative zero.
   */
  'ar-57': {
    // Twenty-four of the thirty-one the RM277 takes, and a strict subset of
    // them: no UHX, no Insight 3/7, no M157, no LPVO, no 3/7 Adjustable, no
    // Multi-Purpose Tactical Riser, no OKP-7. Two of those absences change the
    // shape of the gun rather than just the list. The MPTR is what opens the
    // riser-optic and tactical-device slots, so this rifle has neither. And of
    // the five scopes that open a killflash, only the Recon 1.5/5 is here, so
    // its killflash hangs off one optic where the RM277's hangs off five.
    optics: [
      'white-phosphor-thermal-scope',
      'advanced-thermal-fusion-holographic-sight',
      'vmx-frameless-sight',
      '1p-33-2-4x-scope',
      'prism-universal-2x-optic',
      'viewpoint-3x-scope',
      '1p-29-russian-3x-sight',
      'recon-1-5-5-adjustable-scope',
      'hamr-combined-scope',
      'meo-micro-sight-riser',
      'micro-sight-riser',
      'acog-precision-6x-scope',
      'osight-red-dot',
      'cobra-accuracy-sight',
      'combat-red-dot-sight',
      'mini-red-dot-sight',
      'xcog-assault-3-5x-scope',
      'xro-quick-response-sight',
      'panoramic-red-dot-sight',
      'ap5000-reflex-sight',
      'holographic-sight-type-ii',
      'reflex-sight',
      'russian-accuracy-2x-scope',
      'holographic-sight',
    ],

    // Opened by either micro sight riser, both of which are in the list above.
    // The pool itself has not been dictated for this weapon.

    // Same as the RM277's, dictated for this weapon: the offset twins of the
    // five red dots, the one bipod, and nine rear grips -- two of which open
    // slots of their own, so this rifle has a grip patch and a grip mount.
    'offset-optics': CATEGORY_FITS['offset-optics'],
    'rail-bipod': CATEGORY_FITS['rail-bipod'],
    'rear-grip': CATEGORY_FITS['rear-grip'],

    // Seen in this rifle's killflash slot in the same clip the layout came
    // from, and now sayable: the Recon 1.5/5 is on the optic list above, so
    // the slot has an opener and the gun can be shown to have it.
    'kill-flash': CATEGORY_FITS['kill-flash'],

    // Seventeen, and the MCX LT dictated the same seventeen in the same order,
    // so they live in SMALL_BORE_MUZZLES above rather than twice down here.
    muzzle: SMALL_BORE_MUZZLES,

    // Both weapon-exclusive and neither in the 414, like the RM277's pair.
    barrel: [
      'night-gale-integrally-suppressed-combo',
      'ar57-wave-blaster-ultra-long-barrel',
    ],

    // Two integral stocks, filed by the game under `rear grip` rather than
    // `stock` -- the same lesson the handguard panels taught under
    // `functional`, and the reason slot and category are separate ideas here.
    //
    // "Resident 2" as dictated; the catalogue's is RESONANT 2, sitting
    // directly beside the Restricted Zone in the same category, which is the
    // pair as dictated. Read as the same item.
    'stock-kit': ['resonant-2-integral-stock', 'restricted-zone-integral-stock'],

    // Dictated separately for this weapon and identical to the RM277's, item
    // for item and in order, all four of them -- the uncatalogued lights and
    // the DD Python panel included, which is exactly what naming everything by
    // id buys: the shared list is the whole list, so referencing it is enough.
    //
    // Two independently dictated lists coming out the same is itself the
    // evidence that rails and patches are not filtered per weapon the way
    // muzzles plainly are.
    'left-rail': CATEGORY_FITS['left-rail'],
    'right-rail': CATEGORY_FITS['right-rail'],
    'left-patch': CATEGORY_FITS['left-patch'],
    'right-patch': CATEGORY_FITS['right-patch'],

    // And the foregrips, dictated as twenty-three names and matching the
    // RM277's list item for item and in the same order -- the catalogue's
    // whole foregrip category, on both rifles. Referenced rather than copied.
    //
    // THIS LOOKED LIKE PROOF THAT THE SLOT IS NOT FILTERED. It was not. The
    // MCX LT, read a day later, takes sixteen of the twenty-three. Two rifles
    // agreeing on a whole category is a fact about those two rifles.
    //
    // Six of the twenty-three came through the dictation misheard, and each
    // resolved to exactly one catalogue name: Down Angle Flashlight TSK ->
    // Dawn Angled Flashlight, E-Brake Vertical -> Daybreak Vertical (the two
    // are a pair, Dawn and Daybreak, and sit next to each other), Resident MK2
    // -> Resonant MKII, 3K Order Bevel -> Secret Order Bevel, Face Combat ->
    // Phase Combat, Practical Tactical -> Practical Vertical.
    foregrip: CATEGORY_FITS.foregrip,

    // And the upper rail with them, dictated as the RM277's whole list. Which
    // makes five rails and patches identical across two rifles that share
    // neither a calibre nor a barrel list -- the case for these being filtered
    // by what the rail IS rather than by what it is bolted to.
    //
    // This one is only sayable now: the upper rail is a granted slot, opened
    // by the Wave Blaster barrel, and until that barrel was on the AR-57's
    // list there was no slot here to fill.
    'upper-rail': CATEGORY_FITS['upper-rail'],

    // Eighteen, in the order the picker shows them, which is also the order
    // they were dictated -- unlike the muzzles, so no reversal here. The tier
    // bands were given as three runs and they fall where the picker sorts:
    // five purple, eight blue, five green, best first. Fifteen are in the
    // catalogue; the Anchor Point, the QR and the CT are not.
    //
    // The 416 and M4 parts in here are not a mistake. This rifle is an AR15
    // lower -- its own card says so -- so it takes that family's buffer tubes
    // and stocks, which is also why a P90-calibre carbine ends up sharing a
    // stock list with a 416.
    stock: [
      'anchor-point-rail-stock',
      'qr-high-performance-stock',
      'ct-enhanced-stock',
      'shadow-buffer-tube-stock',
      'shadow-rail-stock',
      'skeleton-sniper-stock',
      'cardinal-advanced-combat-stock',
      '416-stable-stock',
      '416-light-stock',
      'elite-light-stock',
      'invasion-core-stock',
      'cardinal-stable-stock',
      'lightning-rail-stock',
      'm4-recoil-buffer-tube',
      'practical-light-stock',
      'practical-tactical-stock',
      'practical-stable-stock',
      'core-rail-stock',
    ],
  },

  /*
   * The MK47, in 7.62x39mm, and the first weapon here whose calibre is visible
   * in a list. Its muzzles are the small-bore seventeen MINUS the two that are
   * only ever on something small -- the SMG Echo Suppressor and the Birdcage
   * Flash Hider -- PLUS five that belong to the AK family and appear here for
   * the first time on this site: the DTK and AK Practical Compensator, the AK
   * Bravefire and PBS Russian suppressors, and the Bell Mouth Flash Hider.
   *
   * Written out rather than derived from SMALL_BORE_MUZZLES, because THE ORDER
   * IS DATA. The game lists a slot's parts by rarity, most to least, and that
   * order is what says where one rarity band ends and the next begins -- it is
   * how the five new ones got their colour without a card being opened. A
   * derived list would keep the right items and throw the evidence away.
   */
  mk47: {
    muzzle: [
      'cobweb-titanium-muzzle-brake',
      'ffc-double-port-muzzle-brake',
      'spiral-fire-flash-hider',
      'advanced-multi-caliber-suppressor',
      'dtk-muzzle-brake',
      'm7-practical-suppressor',
      'ak-bravefire-suppressor',
      'pbs-russian-suppressor',
      'silent-suppressor',
      'sandstorm-vertical-compensator',
      'bastion-horizontal-compensator',
      'poseidon-flash-hider',
      'whisper-tactical-suppressor',
      'titanium-contest-muzzle-brake',
      'blazing-fire-suppressor',
      'ak-practical-compensator',
      'steel-muzzle-brake',
      'practical-suppressor',
      'bell-mouth-flash-hider',
      'practical-flash-hider',
    ],
    /*
     * THE OLIGHT WARRIOR 3S IS ON NONE OF THE THREE RAILS. It is on the MCX
     * LT's right and upper rails, and its absence here is consistent across
     * all three of this rifle's lists rather than a gap in one -- which is the
     * only reason it is recorded as absence and not as an unread line.
     *
     * The side rails take NO handguard panels, and the upper rail takes all
     * five. Every other weapon here that has been read puts panels on both.
     * So on this rifle a panel goes on top or on a patch, and never on a side
     * rail, which is the second shape the MK47 has broken.
     */
    'left-rail': [
      'olight-odin-s-tactical-flashlight',
      'olight-baldr-pro-r-multi-function-flashlight',
      'dbal-x2-purple-laser-light-combo',
      'perst-7-blue-laser-light-combo',
      'flare-tactical-flashlight',
      'la-3c-green-laser-light-combo',
      'peq-2-red-laser-light-combo',
      'practical-weapon-light',
    ],
    /*
     * The left rail's list again, item for item and in the same order --
     * INCLUDING THE OLIGHT ODIN S, which on the RM277 is the one light that
     * fits the left side only. Two weapons, two answers, and this one was
     * dictated with the Odin S at the top of both lists.
     */
    'right-rail': [
      'olight-odin-s-tactical-flashlight',
      'olight-baldr-pro-r-multi-function-flashlight',
      'dbal-x2-purple-laser-light-combo',
      'perst-7-blue-laser-light-combo',
      'flare-tactical-flashlight',
      'la-3c-green-laser-light-combo',
      'peq-2-red-laser-light-combo',
      'practical-weapon-light',
    ],
    'upper-rail': [
      'dbal-x2-purple-laser-light-combo',
      'perst-7-blue-laser-light-combo',
      'flare-tactical-flashlight',
      'la-3c-green-laser-light-combo',
      'peq-2-red-laser-light-combo',
      'modular-handguard-panel',
      'hornet-handguard',
      'dd-python-handguard-panel',
      'kc-hound-handguard',
      'ranger-handguard',
    ],
    /*
     * The whole foregrip category, twenty-three items, matching the RM277's and
     * the AR-57's list for item and for order. The MCX LT's sixteen is the odd
     * one out, not this.
     */
    foregrip: [
      'resonant-mk-iii-grip',
      'ec-universal-front-hand-stop',
      'dawn-angled-flashlight-grip',
      'daybreak-vertical-flashlight-grip',
      'cr-prism-hand-stop',
      'resonant-mkii-foregrip',
      'collapsible-bipod-grip',
      'k1-elite-bevel-foregrip',
      'x25u-angled-combat-grip',
      'resonant-ergonomic-grip',
      'phantom-vertical-foregrip',
      'tactical-vertical-foregrip',
      'secret-order-bevel-foregrip',
      'rk-0-foregrip',
      'tactical-angled-foregrip',
      'angled-hand-stop',
      'competition-hand-stop',
      'phase-combat-foregrip',
      'folding-grip',
      'vfg-knight-foregrip',
      'zfsg-tactical-grip',
      'mini-hand-stop',
      'practical-vertical-foregrip',
    ],
    barrel: [
      'mk47-battle-barrel',
      'mk47-ember-barrel',
    ],
    /* All three patches, the same five panels, all on the bare rifle. */
    'left-patch': [
      'modular-handguard-panel',
      'hornet-handguard',
      'dd-python-handguard-panel',
      'kc-hound-handguard',
      'ranger-handguard',
    ],
    'right-patch': [
      'modular-handguard-panel',
      'hornet-handguard',
      'dd-python-handguard-panel',
      'kc-hound-handguard',
      'ranger-handguard',
    ],
    'upper-patch': [
      'modular-handguard-panel',
      'hornet-handguard',
      'dd-python-handguard-panel',
      'kc-hound-handguard',
      'ranger-handguard',
    ],
    'offset-optics': [
      'offset-osight-red-dot',
      'offset-combat-red-dot-sight',
      'offset-mini-red-dot-sight',
      'offset-xro-quick-response-sight',
      'offset-panoramic-red-dot-sight',
    ],
    /*
     * Eighteen. Seventeen of them are a strict subset of the RM277's
     * thirty-one, and the eighteenth is the APX Hybrid Sight, which appears
     * here for the first time on this site and opens a red dot mount.
     *
     * NOT a subset of the AR-57's twenty-four -- this rifle takes six the
     * AR-57 does not, the Multi-Purpose Tactical Riser among them, so it gets
     * riser optics and a tactical device where the AR-57 has neither slot.
     */
    optics: [
      'white-phosphor-thermal-scope',
      'advanced-thermal-fusion-holographic-sight',
      'apx-hybrid-sight',
      'vmx-frameless-sight',
      '1p-33-2-4x-scope',
      'uhx-holographic-sight',
      'prism-universal-2x-optic',
      'insight-3-7-sniper-scope',
      'm157-fire-control-system',
      'viewpoint-3x-scope',
      '1p-29-russian-3x-sight',
      'lpvo-scope',
      '3-7-adjustable-scope',
      'recon-1-5-5-adjustable-scope',
      'hamr-combined-scope',
      'meo-micro-sight-riser',
      'multi-purpose-tactical-riser',
      'micro-sight-riser',
    ],
    'red-dot-optics': [
      'vmx-frameless-sight',
      'osight-red-dot',
      'combat-red-dot-sight',
      'mini-red-dot-sight',
      'xro-quick-response-sight',
      'panoramic-red-dot-sight',
    ],
    'kill-flash': ['honeycomb-killflash'],
    'rear-grip': [
      'ar-modular-rear-grip',
      'ar-heavy-tower-grip',
      'invasion-rear-grip',
      'phantom-rear-grip',
      'ar-moe-rear-grip',
      'marksman-d-2-rear-grip',
      'hurricane-d-1-rear-grip',
      'm7-stable-rear-grip',
      '416-practical-rear-grip',
    ],
    'rear-grip-patch': ['ar-light-grip-piece', 'ar-heavy-grip-piece'],
    'rear-grip-mount': ['balanced-grip-base', 'stable-grip-base'],
    /*
     * THE MCX LT'S NINETEEN, IN THE SAME ORDER, with one swapped for another:
     * the M4 Recoil Buffer Tube is gone and the MK47 Dominator Stock is in at
     * the fourth place. Everything else matches item for item and position for
     * position, which is a stronger check on this list than anything the site
     * could run -- two transcripts of nineteen items agreeing that exactly on
     * a list read months apart is not a thing that happens by accident.
     *
     * The Dominator's fourth place is also what gives it its colour: the run
     * from the Anchor Point Rail Stock to the Shadow Rail Stock is purple, and
     * position four is inside it.
     */
    stock: [
      'anchor-point-rail-stock',
      'qr-high-performance-stock',
      'ct-enhanced-stock',
      'mk47-dominator-stock',
      'shadow-buffer-tube-stock',
      'mrgs-skeleton-stock',
      'ur-spec-ops-tactical-stock',
      'shadow-rail-stock',
      'skeleton-sniper-stock',
      '416-stable-stock',
      '416-light-stock',
      'elite-light-stock',
      'invasion-core-stock',
      'cardinal-stable-stock',
      'lightning-rail-stock',
      'practical-light-stock',
      'practical-tactical-stock',
      'practical-stable-stock',
      'core-rail-stock',
    ],
    mag: ['mk47-30-round-mag', 'akm-40-round-extended-mag'],
    /* The same three as the RM277's and the MCX LT's, in the same order. */
    'mag-mount': [
      'grizzly-full-p-mag-assist-sand',
      'grizzly-full-p-mag-assist-green',
      'grizzly-full-p-mag-assist-black',
    ],
  },
};

/**
 * The attachments that fit `slot` on `weaponId`.
 *
 * Falls back to the whole category when the weapon has not been transcribed,
 * because "no data" and "nothing fits" are different answers and confusing them
 * would silently empty a reel.
 */
export function fitsFor(weaponId: string, slot: string): string[] | null {
  return WEAPON_FITS[weaponId]?.[slot] ?? null;
}

/*
 * UNRESOLVED_NAMES used to sit here: the names heard in a transcript that no
 * catalogue id matched, listed again per weapon and per slot. Both of its jobs
 * are done better elsewhere now. The names live in UNCATALOGUED, once each,
 * and where they fit is said by WEAPON_FITS naming their ids in the ordinary
 * way -- so the fact that a part is missing from the 414 has stopped being a
 * different KIND of fact, told in a different place, from the fact that a part
 * fits a slot.
 */

/** Rules for an attachment, or an empty rule if it has none. */
export const ruleFor = (id: string): AttachRule => ATTACH_RULES[id] ?? {};

/**
 * Does fitting `a` rule out `b`?
 *
 * Reads both directions so a conflict only has to be written down once. A pair
 * recorded on one side and forgotten on the other is the commonest way this
 * kind of table goes wrong, and asking the question here rather than at every
 * call site means it cannot happen.
 */
export function conflictsWith(a: string, b: string): boolean {
  return (
    (ATTACH_RULES[a]?.conflicts?.includes(b) ?? false) ||
    (ATTACH_RULES[b]?.conflicts?.includes(a) ?? false)
  );
}

/** Every slot `fitted` opens up, before any removals are applied. */
export function grantedSlots(fitted: string[]): GrantedSlot[] {
  const out = new Set<GrantedSlot>();
  for (const id of fitted) for (const s of ruleFor(id).grants ?? []) out.add(s);
  return [...out];
}

/*
 * openSlots(fitted) used to sit here: base slots, plus what the fitted parts
 * grant, minus what they conflict with. Deleted rather than fixed, for two
 * reasons that arrived together.
 *
 * Nothing called it. The page runs its own copy, in the gunsmith script, which
 * has to exist there anyway because the answer changes as the reader equips
 * things.
 *
 * And it was wrong in a way that would not have shown up until somebody used
 * it: it started from `SLOT_TYPES.filter(kind === 'base')`, one global set of
 * base slots for every weapon in the game. The MCX LT is the counterexample --
 * it carries an upper rail and an upper patch on the bare rifle, and gets its
 * side patches from a barrel, which is both halves of that assumption
 * inverted. The page's version starts from the weapon's own traced slots and
 * never had the problem.
 */

/**
 * Patch entries the matching rail does not also accept.
 *
 * The patch slots take handguard panels, and the rails take those same panels
 * plus the lights and lasers. Two separately dictated lists again, so the
 * containment is worth checking rather than assuming.
 */
export function panelSubsetViolations(): string[] {
  const out: string[] = [];
  for (const side of ['left', 'right'] as const) {
    const rail = CATEGORY_FITS[`${side}-rail`] ?? [];
    for (const id of CATEGORY_FITS[`${side}-patch`] ?? []) {
      if (!rail.includes(id)) out.push(`${side}-patch: ${id} is not in ${side}-rail`);
    }
  }
  // The upper rail was dictated as a shorter version of the side rails, so
  // anything on it that NEITHER side rail takes means one list was misheard.
  //
  // It used to be checked against the left rail alone, which was right only by
  // accident: the two side rails differ by exactly the OLIGHT lights, and both
  // of those were uncatalogued and therefore absent from these arrays. With
  // the lists complete the upper rail carries the Warrior 3S, the left rail
  // carries the Odin S instead, and the containment holds against the pair.
  const sides = new Set([...(CATEGORY_FITS['left-rail'] ?? []),
                         ...(CATEGORY_FITS['right-rail'] ?? [])]);
  for (const id of CATEGORY_FITS['upper-rail'] ?? []) {
    if (!sides.has(id)) out.push(`upper-rail: ${id} is on neither side rail`);
  }
  return out;
}

/** Slot ids named in a `conflictSlots` that are not real slots. */
export function unknownConflictSlots(): string[] {
  const bad = new Set<string>();
  for (const r of [...Object.values(ATTACH_RULES), ...Object.values(PENDING_RULES)]) {
    for (const slot of r.conflictSlots ?? []) if (!SLOT_TYPE_BY_ID[slot]) bad.add(slot);
  }
  return [...bad];
}

/**
 * Ids named in this file that no longer exist in ATTACHMENTS.
 *
 * Rules are written from transcripts and the catalogue moves independently, so
 * the join can rot silently — a conflict pointing at a renamed id simply stops
 * firing, and nothing complains. Call it from a test or a build step.
 */
export function danglingRuleIds(): string[] {
  const bad = new Set<string>();
  // ATTACH_RULES is for catalogued items only, by definition: a rule on an
  // uncatalogued one goes in PENDING_RULES, and that is the whole distinction
  // between the two maps. So this half still asks the narrower question.
  for (const [id, rule] of Object.entries(ATTACH_RULES)) {
    if (!ATTACH_BY_ID[id]) bad.add(id);
    for (const c of rule.conflicts ?? []) if (!ATTACH_BY_ID[c]) bad.add(c);
  }
  // The lists ask the wider one. An id in a slot list is fine whether the
  // catalogue carries the item or UNCATALOGUED does; it is an id in NEITHER
  // that means a name was typed twice and spelled differently once.
  //
  // This used to subtract the keys of PENDING_RULES at the end, which was a
  // way of saying "these ones we know about" — a list of known-missing items,
  // maintained as a side effect of them happening to have slot rules. Items
  // with no rule were simply never checked.
  for (const bySlot of Object.values(WEAPON_FITS)) {
    for (const ids of Object.values(bySlot)) {
      for (const id of ids ?? []) if (!KNOWN_ITEM(id)) bad.add(id);
    }
  }
  for (const id of [...RISER_OPTIC_FITS, ...RED_DOT_FITS, ...STACKABLE_RISERS]) {
    if (!KNOWN_ITEM(id)) bad.add(id);
  }
  // And a rule parked for an item nobody has claimed exists is the same rot in
  // the other direction: it can never fire and nothing else would say so.
  for (const id of Object.keys(PENDING_RULES)) if (!KNOWN_ITEM(id)) bad.add(id);
  return [...bad];
}
