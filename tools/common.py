"""Shared by build3/build4: amenities (from the drawings and renders) and the 320 homes from the architect's plans."""
import json
gal = json.load(open('/home/claude/aksa/tools/gallery.json'))
cap = {int(g['image'][-6:-4]): g for g in gal}
AMEN = [
    {'id': 'pool', 'name': 'Pools & sun decks', 'fact': '2 · one in each courtyard',
     'text': 'A pool of about 9 × 5 m with a timber sun deck in each courtyard, as drawn on the site plan.', 'images': [15, 17, 20, 21, 14]},
    {'id': 'pergola', 'name': 'Round pergolas', 'fact': '4 · two in each courtyard',
     'text': 'Two round timber pergolas at the ends of each courtyard garden.', 'images': [22, 18, 19]},
    {'id': 'play', 'name': "Children's play areas", 'fact': '2 · one in each courtyard',
     'text': 'A play area with play equipment in each courtyard, next to the pergola lawn.', 'images': [18, 19]},
    {'id': 'gardens', 'name': 'Courtyard gardens', 'fact': '2 × about 1,200 m²',
     'text': 'Landscaped courtyards of about 49 × 24 m with lawns, planting, trees and paths.', 'images': [16, 20, 19, 14]},
    {'id': 'private', 'name': 'Private gardens', 'fact': 'Ground-floor homes',
     'text': 'Ground-floor homes have terraces that open onto planted garden strips along the facades.', 'images': [4, 8, 13]},
    {'id': 'terraces', 'name': 'Roof terraces', 'fact': 'Recuado level',
     'text': 'The set-back roof level holds roof terraces, storage rooms and rooms reached by internal stairs from level 4 (drawing 07).', 'images': [3, 1, 2]},
    {'id': 'balconies', 'name': 'Balconies & loggias', 'fact': 'Levels 1–4',
     'text': 'Homes on levels 1–4 have balconies (varandas) and a laundry drying area (estendal), as shown on the floor plans.', 'images': [9, 6, 10, 5]},
    {'id': 'parking', 'name': 'Underground car park', 'fact': '194 numbered spaces',
     'text': 'A basement car park (planta cave) with 194 numbered parking spaces and the stair and lift cores of each entrance.', 'images': [], 'plan': 'media/amenities/cave.jpg'},
    {'id': 'boulevard', 'name': 'Tree-lined boulevard', 'fact': 'Surface parking',
     'text': 'Surface parking in rows between trees beside the blocks.', 'images': [11, 7, 12, 1]},
    {'id': 'cycle', 'name': 'Cycle path', 'fact': 'Along the avenue and between the blocks',
     'text': 'A cycle path along the avenue and through the gap between the two blocks, as drawn on the site plan.', 'images': [10, 5, 2]},
    {'id': 'commercial', 'name': 'Commercial building', 'fact': 'Part of the development',
     'text': 'A four-storey commercial building, part of the development.', 'images': [23, 24, 25, 26, 27, 28]},
]
for a in AMEN:
    a['photos'] = [{'image': cap[i]['image'], 'thumb': cap[i]['thumb'], 'caption': cap[i]['caption'], 'w': cap[i]['w'], 'h': cap[i]['h']} for i in a['images']]
    if a.get('plan'):
        a['photos'].append({'image': a['plan'], 'thumb': a['plan'], 'caption': 'Basement plan (architect’s drawing 02)', 'w': 1263, 'h': 1600})
    a.pop('images')


def apply_units(D):
    PLN = json.load(open('/home/claude/aksa/arch/plans.json'))
    # Homes: ground floor + levels 1-4, 32 per level per block = 160 per block, 320 in total.
    # The recuado level (drawing 07) holds roof terraces, storage (arrumos) and rooms reached by internal
    # stairs from level 4, so it has no homes of its own.
    FLOORNAME = {0: 'Ground floor', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3', 4: 'Level 4', 5: 'Recuado (roof level)'}
    units = []; plans = {}
    for T in D['towers']:
        for f in range(6):
            F = PLN['floors'][str(f)]
            plans[f'{T["id"]}:{f}'] = {'image': F['image'], 'viewBox': PLN['viewBox'], 'name': FLOORNAME[f]}
            if f == 5:
                plans[f'{T["id"]}:{f}']['note'] = ('Roof level (piso recuado): roof terraces, storage rooms (arrumos) and rooms reached by '
                                                  'internal stairs from level 4, as drawn on the architect\'s drawing 07. No separate homes on this level.')
                continue
            for u in F['units']:
                units.append({'id': f'{T["id"]}-{f}.{u["n"]:02d}', 'n': u['n'], 'tower': T['id'], 'floor': f, 'poly': u['poly'], 'cx': u['cx'], 'cy': u['cy'],
                              'type': u['type'], 'beds': int(u['type'][1]), 'm2': u['area'], 'frac': u['frac'],
                              'aspect': ' + '.join(u['aspect']) if u['aspect'] else ''})
    D['units'] = units; D['plans'] = plans; D['floorNames'] = FLOORNAME
    print('homes', len(units))
