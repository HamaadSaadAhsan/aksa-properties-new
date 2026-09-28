"""Views built from the studio renders.
Camera-matched aerials (cam/r01,r02,r03.json) get block outlines, floor outlines and amenity pins;
every render becomes a view in the carousel. Units, plans, tours and location are kept from data.json (build2)."""
import json, math, os, shutil, glob
import numpy as np, cv2
from PIL import Image

SITE = '/home/claude/aksa/site'; CAM = '/home/claude/aksa/cam'; MED = f'{SITE}/media'
G = f'{MED}/gallery'
D = json.load(open(f'{SITE}/data.json'))
gal = json.load(open('/home/claude/aksa/tools/gallery.json'))
cap = {int(g['image'][-6:-4]): g for g in gal}
SC = json.load(open('/home/claude/aksa/tools/scene/scene.json')); PL = SC['plot']; GY = .8
TH = math.radians(-74.2); C, S = math.cos(TH), math.sin(TH)
W3 = lambda u, v, y: np.array([PL['x'] + u * C + v * S, GY + y, PL['z'] - u * S + v * C])


def trace(binary, eps, min_area):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)
    cs, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True).reshape(-1, 2).tolist() for c in cs if cv2.contourArea(c) >= min_area]

def project(cam, p, w=1600, h=900):
    b = np.array(cam['basis']); right, up, back = b[0], b[1], b[2]
    d = p - np.array(cam['pos']); z = -d @ back
    if z <= 0: return None
    f = h / 2 / math.tan(math.radians(cam['fov'] / 2))
    x = w / 2 + f * (d @ right) / z; y = h / 2 - f * (d @ up) / z
    return (round(x, 1), round(y, 1)) if 20 < x < w - 20 and 40 < y < h - 60 else None

# amenities (evidence: architect's site plan, basement plan, floor plans, studio renders)
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

# amenity pin anchors in site-local metres (u along the blocks, v across, y up), from the architect's site plan.
# Each pin tries its candidates in order and takes the first one not hidden behind a block in that render.
def cy(bu, y): return [bu - 4.1, -2.4, y]          # pool centre in each courtyard
PINS = [
    ('pool', [cy(-52.75, .5), cy(-52.75, 17)]), ('pool', [cy(52.75, .5), cy(52.75, 17)]),
    ('boulevard', [[-30, -62, 1], [30, -62, 1]]),
    ('cycle', [[2, 42, .5], [2, -42, .5], [2, 0, .5]]),
    ('private', [[-60, 36, 1], [60, 36, 1], [-60, -36, 1], [60, -36, 1]]),
    ('terraces', [[92, 31, 17], [-92, 31, 17], [92, -31, 17], [-92, -31, 17]]),
]

MATCHED = {1: 'r01', 2: 'r02', 3: 'r03'}
TOW = D['towers']
ORDER = [3, 1, 2] + [i for i in range(4, 29) if i not in (1, 2, 3)] 
angles = []
for i in ORDER:
    g = cap[i]; vid = f'{i:02d}'
    if not g.get('video'): continue
    v = {'id': vid, 'label': g['caption'], 'still': g['image'], 'loop': g['video'], 'outlines': [], 'amenities': [], 'fx': g.get('fx', .5)}
    if i in MATCHED:
        n = MATCHED[i]; cam = json.load(open(f'{CAM}/{n}.json'))['cam']
        bm = np.array(Image.open(f'{CAM}/{n}_blocks.png').convert('RGB'))
        for t, T in enumerate(TOW):
            b = ((bm[:, :, 0] == 40 + t * 80) & (bm[:, :, 1] == 200)).astype(np.uint8) * 255
            polys = trace(b, 1.2, 300)
            if polys: v['outlines'].append({'id': T['id'], 'label': T['name'], 'target': 'close', 'polys': polys})
        occ = (bm.sum(2) > 0)
        for aid, cands in PINS:
            for p in cands:
                xy = project(cam, W3(*p))
                if not xy: continue
                x, y = int(xy[0]), int(xy[1])
                hidden = occ[max(0, y - 3):y + 4, max(0, x - 3):x + 4].any()
                if p[2] < 5 and hidden: continue
                if any(abs(q['x'] - xy[0]) < 40 and abs(q['y'] - xy[1]) < 40 for q in v['amenities']): continue
                v['amenities'].append({'id': aid, 'x': xy[0], 'y': xy[1]}); break
        xs = [p[0] for o in v['outlines'] for poly in o['polys'] for p in poly]
        if xs: v['fx'] = round((min(xs) + max(xs)) / 2 / 1600, 3)
    angles.append(v)
D['realReel'] = {'viewBox': [1600, 900], 'start': '03', 'angles': angles}
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('real reel', [(a['id'], len(a['outlines']), [m['id'] for m in a['amenities']]) for a in angles])
