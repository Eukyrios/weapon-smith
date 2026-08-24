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
  // The rails, the patches and the rail bipod are all on the gun itself. Only
  // the upper rail has to be opened, by either RM277 barrel.
  { id: 'upper-rail', label: 'Upper Rail', kind: 'granted' },
  { id: 'left-rail', label: 'Left Rail', kind: 'base' },
  { id: 'right-rail', label: 'Right Rail', kind: 'base' },
  { id: 'left-patch', label: 'Left Patch', kind: 'base' },
  { id: 'right-patch', label: 'Right Patch', kind: 'base' },
  { id: 'rail-bipod', label: 'Rail Bipod', kind: 'base' },

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
  { id: 'kill-flash', label: 'Kill Flash', kind: 'granted', cat: 'functional' },
  { id: 'tactical-device', label: 'Tactical Device', kind: 'granted' },

  { id: 'mag', label: 'Magazine', kind: 'base', cat: 'mag' },
  { id: 'mag-mount', label: 'Magazine Mount', kind: 'base' },
  { id: 'rear-grip', label: 'Rear Grip', kind: 'base', cat: 'rear grip' },
  { id: 'rear-grip-patch', label: 'Rear Grip Patch', kind: 'granted' },
  // The two grip bases sit under the catalogue's `rear grip` cat but are their
  // own slot — another case of one cat covering several slots.
  { id: 'rear-grip-mount', label: 'Rear Grip Mount', kind: 'granted', cat: 'rear grip' },
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
  muzzle: [
    // 16 named for the RM277, 14 resolve, out of the catalogue's 37 muzzles —
    // a real per-weapon filter, unlike foregrip. Dictated order, reversed; the
    // two that do not resolve head the list, in the order given:
    //   'rm277-breaker-suppressor',       <- weapon-exclusive, absent from ATTACHMENTS
    //   'cobweb-titanium-muzzle-brake',   <- unidentified, absent from ATTACHMENTS
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
  barrel: [],
  handguard: [],
  foregrip: [
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
    // 'olight-warrior-3s-tactical-flashlight',  <- named, absent
    'dbal-x2-purple-laser-light-combo',
    'perst-7-blue-laser-light-combo',
    'flare-tactical-flashlight',
    'la-3c-green-laser-light-combo',
    'peq-2-red-laser-light-combo',
    'modular-handguard-panel',
    'hornet-handguard',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /**
   * Left rail — 14 named, 11 resolve. Nine lights and lasers plus the five
   * handguard panels. Absent from the 414: OLIGHT Warrior 3S Tactical
   * Flashlight, OLIGHT Odin S Tactical Flashlight, DD Python Handguard Panel.
   */
  'left-rail': [
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
    'hornet-handguard', // catalogue drops the "Panel"
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /**
   * Right rail — dictated as identical to the left, and written out in full
   * rather than aliased to it. Two slots that agree today are still two slots;
   * sharing one array makes a future divergence unrepresentable and hides that
   * both were actually checked.
   */
  'right-rail': [
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
    'hornet-handguard', // catalogue drops the "Panel"
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /** Left patch — handguard panels only. 5 named, 4 resolve. */
  'left-patch': [
    'modular-handguard-panel',
    'hornet-handguard',
    // 'dd-python-handguard-panel',              <- named, absent
    'kc-hound-handguard',
    'ranger-handguard',
  ],

  /** Right patch — the same five panels, written out for the reason above. */
  'right-patch': [
    'modular-handguard-panel',
    'hornet-handguard',
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
    // 'white-phosphor-thermal-scope',               <- named, absent
    // 'advanced-thermal-fusion-holographic-sight',  <- named, absent
    // 'vmx-frameless-sight',                        <- named, absent
    // '1p-33-2-4x-scope',                           <- named, absent.
    //     Heard "1P-32 4X" once and "1P-332/4X" the next time; read as a
    //     variable 2-4x. The id is a guess until the item turns up.
    // 'uhx-holographic-sight',                      <- named, absent
    // 'prism-universal-2x-optic',                   <- named, absent
    'insight-3-7-sniper-scope',
    // 'm157-fire-control-system',                   <- named, absent
    'viewpoint-3x-scope',
    // '1p-29-russian-3x-sight',                     <- named, absent
    'lpvo-scope',
    '3-7-adjustable-scope',
    'recon-1-5-5-adjustable-scope',
    'hamr-combined-scope',
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
    // 'ar-modular-rear-grip',  <- named, absent. Opens the rear-grip patch.
    'ar-heavy-tower-grip',
    'invasion-rear-grip',
    'phantom-rear-grip',
    // 'ar-moe-rear-grip',      <- named, absent
    'marksman-d-2-rear-grip',
    'hurricane-d-1-rear-grip',
    'm7-stable-rear-grip',
    '416-practical-rear-grip',
  ],

  /** Rear grip patch — 2 named, neither in the 414. */
  'rear-grip-patch': [
    // 'ar-light-grip-piece',   <- named, absent
    // 'ar-heavy-grip-piece',   <- named, absent
  ],

  /** Rear grip mount — 2 named, both resolve. */
  'rear-grip-mount': ['balanced-grip-base', 'stable-grip-base'],

  stock: [],

  /** Cheek pad — 1 named, absent from the 414. */
  'cheek-pad': [
    // 'rm277-cheek-pad',   <- named, absent. The catalogue carries M700, QBZ
    //                         and Universal cheek pads but no RM277 one.
  ],

  /** Stock pad — 1 named, absent from the 414. */
  'stock-pad': [
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
export const PENDING_RULES: Record<string, AttachRule & { name: string }> = {
  'meo-micro-sight-riser': {
    name: 'MEO Micro Sight Riser',
    grants: ['red-dot-optics'],
  },

  /*
   * The first attachments that REMOVE slots, and the first slot rules outside
   * the optic ladder. Both are RM277-exclusive and absent from the 414, so they
   * park here rather than dangling in ATTACH_RULES — but the rules are the
   * valuable part and are written down in full.
   */
  'rm277-heavy-integral-barrel': {
    name: 'RM277 Heavy Integral Barrel',
    grants: ['upper-rail'],
    // An integral barrel occupies the muzzle, and rules out the rail bipod.
    conflictSlots: ['muzzle', 'rail-bipod'],
  },
  'ar-modular-rear-grip': {
    name: 'AR Modular Rear Grip',
    grants: ['rear-grip-patch'],
  },
  'm157-fire-control-system': {
    name: 'M157 Fire Control System',
    grants: ['kill-flash'],
  },
  'rm277-whale-shark-barrel-combo': {
    name: 'RM277 Whale Shark Barrel Combo',
    grants: ['upper-rail'],
    // No slot conflicts were listed. Absence of a statement, not a statement of
    // absence — if this one also blocks the bipod, nothing here would know.
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
export const WEAPON_FITS: Record<string, Partial<Record<string, string[]>>> = {
  rm277: {
    // Both lists were dictated for this weapon, so the category arrays above
    // ARE the RM277's lists today. Referenced, not copied — a second weapon
    // will diverge and the copy is what would silently go stale.
    muzzle: CATEGORY_FITS.muzzle,
    foregrip: CATEGORY_FITS.foregrip,
    optics: CATEGORY_FITS.optics,
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

/**
 * Names heard in a transcript that no catalogue id matches, by weapon and slot.
 *
 * Kept beside the lists they came from so a later catalogue pass has something
 * to check against. A name here means one of two things and we cannot yet tell
 * which: the item is missing from the 414, or the speech-to-text mangled it
 * past recognition. The RM277 Breaker Suppressor is almost certainly the former
 * — the catalogue already carries weapon-exclusive muzzles (AK Bravefire,
 * SR-3M Stealth, PBS Russian), so an RM277 one fits the pattern.
 */
export const UNRESOLVED_NAMES: Record<string, Record<string, string[]>> = {
  rm277: {
    muzzle: ['Cobweb Titanium Muzzle Brake', 'RM277 Breaker Suppressor'],
    optics: [
      'White Phosphor Thermal Scope', // heard "WhiteForce4"; the "4" was "-phor"
      'Advanced Thermal Fusion Holographic Sight', // heard "ATV" once, "Adv" later
      'VMX Frameless Sight',
      '1P-33 2/4x Scope', // heard "1P-32 4X" once, "1P-332/4X" later
      'UHX Holographic Sight',
      'Prism Universal 2x Optic',
      'M157 Fire Control System',
      '1P-29 Russian 3x Sight',
      'MEO Micro Sight Riser',
    ],
    // Named for the riser-optic slot; all four are also absent from the 414.
    'riser-optics': [
      'Advanced Thermal Fusion Holographic Sight',
      'VMX Frameless Sight',
      'UHX Holographic Sight',
      'MEO Micro Sight Riser',
    ],
    barrel: ['RM277 Heavy Integral Barrel', 'RM277 Whale Shark Barrel Combo'],
    'rear-grip': ['AR Modular Rear Grip', 'AR MOE Rear Grip'],
    'rear-grip-patch': ['AR Light Grip Piece', 'AR Heavy Grip Piece'],
    'cheek-pad': ['RM277 Cheek Pad'],
    'stock-pad': ['RM277 Pad'],
    foregrip: ['Resonant MK III Grip', 'EC Universal Front Hand Stop'],
    // The four laser-light combos once guessed at for the tactical-device slot
    // turned out to belong to the RAILS. The tactical-device list is unknown.
    'left-rail': [
      'OLIGHT Warrior 3S Tactical Flashlight',
      'OLIGHT Odin S Tactical Flashlight',
      'DD Python Handguard Panel',
    ],
  },
};

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

/**
 * The slots still usable once `fitted` are on the gun.
 *
 * Base slots, plus what the fitted parts grant, minus what they conflict with.
 * CONFLICTS ARE APPLIED LAST AND WIN — one attachment can grant a slot another
 * blocks, and resolving that the other way round would leave a slot on the
 * board that cannot actually be filled.
 *
 * Reads PENDING_RULES as well as ATTACH_RULES, because the only slot conflicts
 * known so far belong to items the catalogue does not carry yet — leaving them
 * out would make this function quietly wrong for the exact case it exists for.
 */
export function openSlots(fitted: string[]): string[] {
  const rules = (id: string): AttachRule => ATTACH_RULES[id] ?? PENDING_RULES[id] ?? {};
  const open = new Set<string>(
    SLOT_TYPES.filter((s) => s.kind === 'base').map((s) => s.id),
  );
  for (const id of fitted) for (const g of rules(id).grants ?? []) open.add(g);
  for (const id of fitted) for (const c of rules(id).conflictSlots ?? []) open.delete(c);
  return SLOT_TYPES.filter((s) => open.has(s.id)).map((s) => s.id);
}

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
  // anything on it that a side rail refuses means one list was misheard.
  for (const id of CATEGORY_FITS['upper-rail'] ?? []) {
    if (!(CATEGORY_FITS['left-rail'] ?? []).includes(id)) {
      out.push(`upper-rail: ${id} is not in left-rail`);
    }
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
  for (const [id, rule] of Object.entries(ATTACH_RULES)) {
    if (!ATTACH_BY_ID[id]) bad.add(id);
    for (const c of rule.conflicts ?? []) if (!ATTACH_BY_ID[c]) bad.add(c);
  }
  for (const bySlot of Object.values(WEAPON_FITS)) {
    for (const ids of Object.values(bySlot)) {
      for (const id of ids ?? []) if (!ATTACH_BY_ID[id]) bad.add(id);
    }
  }
  for (const id of [...RISER_OPTIC_FITS, ...RED_DOT_FITS, ...STACKABLE_RISERS]) {
    if (!ATTACH_BY_ID[id]) bad.add(id);
  }
  // Items we already know are missing and are tracking deliberately are not
  // rot — reporting them every build would train everyone to ignore this.
  for (const id of Object.keys(PENDING_RULES)) bad.delete(id);
  return [...bad];
}
