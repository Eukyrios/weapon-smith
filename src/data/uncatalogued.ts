/**
 * Items named in a transcript that the game catalogue we hold does not carry.
 *
 * THE POINT OF THIS FILE IS THAT AN ITEM IS ONE THING.
 *
 * These names used to live inside each weapon's slot lists, spelled out again
 * for every gun that took the part. Two weapons in, the OLIGHT Odin S, the
 * OLIGHT Warrior 3S, the DD Python Handguard Panel and the Cobweb Titanium
 * Muzzle Brake were each written down twice, and a correction to one spelling
 * would have left the other standing -- two pages, two ids, two of an item
 * there is one of. So the name lives here, once, and a weapon's list names it
 * by id exactly the way it names a catalogued part.
 *
 * Everything else about these items is already shared and always was: their
 * stat lines and rarity in card-facts.ts, their slot rules in ATTACH_RULES and
 * PENDING_RULES, their pictures in att/. All of it keyed by the same id. This
 * file is the last piece that was not.
 *
 * An id here is a claim that the item exists and the catalogue is incomplete,
 * not that a transcript was garbled. The RM277 Breaker Suppressor is the clear
 * case: the catalogue already carries weapon-exclusive muzzles for the AK, the
 * SR-3M and the PBS, so an RM277 one fits the pattern exactly.
 */
export const UNCATALOGUED: Record<string, { name: string }> = {
  /* Optics the catalogue does not carry. Nine of the thirty-one the RM277 takes. */
  'white-phosphor-thermal-scope': { name: 'White Phosphor Thermal Scope' },
  'advanced-thermal-fusion-holographic-sight': { name: 'Advanced Thermal Fusion Holographic Sight' },
  'vmx-frameless-sight': { name: 'VMX Frameless Sight' },
  '1p-33-2-4x-scope': { name: '1P-33 2/4x Scope' },
  'uhx-holographic-sight': { name: 'UHX Holographic Sight' },
  'prism-universal-2x-optic': { name: 'Prism Universal 2x Optic' },
  'm157-fire-control-system': { name: 'M157 Fire Control System' },
  '1p-29-russian-3x-sight': { name: '1P-29 Russian 3x Sight' },
  'meo-micro-sight-riser': { name: 'MEO Micro Sight Riser' },

  /* Muzzles. */
  'rm277-breaker-suppressor': { name: 'RM277 Breaker Suppressor' },
  'cobweb-titanium-muzzle-brake': { name: 'Cobweb Titanium Muzzle Brake' },
  'ffc-double-port-muzzle-brake': { name: 'FFC Double Port Muzzle Brake' },

  /* Barrels. Every one of them is weapon-exclusive, which is why none is in a
 * catalogue compiled by category. */
  'rm277-whale-shark-barrel-combo': { name: 'RM277 Whale Shark Barrel Combo' },
  'rm277-heavy-integral-barrel': { name: 'RM277 Heavy Integral Barrel' },
  'night-gale-integrally-suppressed-combo': { name: 'Night Gale Integrally Suppressed Combo' },
  'ar57-wave-blaster-ultra-long-barrel': { name: 'AR57 Wave Blaster Ultra-Long Barrel' },

  /* Foregrips. */
  'resonant-mk-iii-grip': { name: 'Resonant MK III Grip' },
  'ec-universal-front-hand-stop': { name: 'EC Universal Front Hand Stop' },

  /* Lights and a panel, all three of them on rails. */
  'olight-warrior-3s-tactical-flashlight': { name: 'OLIGHT Warrior 3S Tactical Flashlight' },
  'olight-odin-s-tactical-flashlight': { name: 'OLIGHT Odin S Tactical Flashlight' },
  'dd-python-handguard-panel': { name: 'DD Python Handguard Panel' },

  /* Rear grips and the pieces two of them open. */
  'ar-modular-rear-grip': { name: 'AR Modular Rear Grip' },
  'ar-moe-rear-grip': { name: 'AR MOE Rear Grip' },
  'ar-light-grip-piece': { name: 'AR Light Grip Piece' },
  'ar-heavy-grip-piece': { name: 'AR Heavy Grip Piece' },

  /* Stocks. Three of the AR-57's eighteen; the other fifteen are catalogued,
 * so whatever the import was compiled from was missing these rather than the
 * whole family. */
  'anchor-point-rail-stock': { name: 'Anchor Point Rail Stock' },
  'qr-high-performance-stock': { name: 'QR High Performance Stock' },
  'ct-enhanced-stock': { name: 'CT Enhanced Stock' },

  /* Pads. */
  'rm277-cheek-pad': { name: 'RM277 Cheek Pad' },
  'rm277-pad': { name: 'RM277 Pad' },
};
