import sys, pathlib
sys.path.insert(0, '/tmp')
from cut import cards, cut, slug
import re


SHEETS = [
    ('1018fbc7', ['White Phosphor Thermal Scope',
                  'Advanced Thermal Fusion Holographic Sight',
                  'VMX Frameless Sight', '1P-33 2/4x Scope',
                  'UHX Holographic Sight', 'Prism Universal 2x Optic']),
    ('d85d78f3', ['M157 Fire Control System', None, '1P-29 Russian 3x Sight']),
    ('e8a96ac1', ['MEO Micro Sight Riser']),
    ('370cfea1', ['RM277 Breaker Suppressor', 'Cobweb Titanium Muzzle Brake']),
    ('a8c95497', ['RM277 Whale Shark Barrel Combo', 'RM277 Heavy Integral Barrel']),
    ('c130eaff', ['Resonant MK III Grip', 'EC Universal Front Hand Stop']),
    ('4a6e0c9f', ['OLIGHT Warrior 3S Tactical Flashlight',
                  'OLIGHT Odin S Tactical Flashlight']),
    ('05067f76', ['DD Python Handguard Panel']),
    ('f829eeca', ['AR Modular Rear Grip', None]),
    ('6e5d92e7', ['AR MOE Rear Grip']),
    ('d2ff2878', ['AR Light Grip Piece', 'AR Heavy Grip Piece']),
    ('ed9587cf', ['RM277 Cheek Pad']),
    ('f49965d7', ['RM277 Pad']),
]

out = pathlib.Path('/tmp/art'); out.mkdir(exist_ok=True)
made = []
for f, names in SHEETS:
    for card, name in zip(cards(f + '.png', len(names)), names):
        if name is None:
            continue          # already in the mirror at better quality
        img = cut(card, slug(name))
        if img is None:
            print('FAILED', name); continue
        img.save(out / (slug(name) + '.png'))
        made.append(slug(name))
print(len(made), 'written')
