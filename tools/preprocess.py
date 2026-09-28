"""OpenStreetMap extract (aksa_osm.json) -> scene inputs for the render harness.

Outputs (tools/scene/):
  scene.json   land outline, buildings, trees, filler blocks, plot, landmarks
  ground.jpg   ground texture (roads, greens, plazas, contact shadows) for TEX bounds
"""
import json, math, os, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

SRCS = ['/home/claude/aksa/src/aksa_osm.json', '/home/claude/aksa/src/aksa_osm_site.json']   # riverfront box + site box
OUT = '/home/claude/aksa/tools/scene'; os.makedirs(OUT, exist_ok=True)
d = {'ways': [], 'relations': [], 'pois': []}; seen = set(); BOXES = []
for f in SRCS:
    if not os.path.exists(f): print('missing', f); continue
    e = json.load(open(f)); d.setdefault('origin', e['origin']); d.setdefault('attribution', e['attribution'])
    assert e['origin'] == d['origin'], 'all extracts must share one origin'
    for w in e['ways']:
        if w['i'] not in seen: seen.add(w['i']); d['ways'].append(w)
    d['relations'] += e['relations']; d['pois'] += e['pois']
    lat0, lon0 = e['origin']; kx = 111320 * math.cos(math.radians(lat0)); b = e['bbox'] if 'bbox' in e else None
    if 'tiles' in e: b = [min(t[0] for t in e['tiles']), min(t[1] for t in e['tiles']), max(t[2] for t in e['tiles']), max(t[3] for t in e['tiles'])]
    BOXES.append(((b[0] - lon0) * kx, -(b[3] - lat0) * 110540, (b[2] - lon0) * kx, -(b[1] - lat0) * 110540))
ways = d['ways']; byid = {w['i']: w for w in ways}
print('boxes', [[round(v) for v in b] for b in BOXES], 'ways', len(ways))
def in_boxes(x, z, m=0): return any(b[0] - m < x < b[2] + m and b[1] - m < z < b[3] + m for b in BOXES)
# the site: 38°42'57.8"N 8°57'57.1"W (given by the client), long side parallel to Avenida Dom João II
SITE_LAT, SITE_LON = 38 + 42 / 60 + 57.8 / 3600, -(8 + 57 / 60 + 57.1 / 3600)
_kx = 111320 * math.cos(math.radians(d['origin'][0]))
PLOT = {'x': round((SITE_LON - d['origin'][1]) * _kx, 1), 'z': round(-(SITE_LAT - d['origin'][0]) * 110540, 1), 'rot': 0, 'lat': SITE_LAT, 'lon': SITE_LON}
print('plot', PLOT)
TEX = (PLOT['x'] - 1700, PLOT['z'] - 1700, 3400)   # ground texture: x0, z0, size (m)
TS = 4096

def pts(w): p = w['p']; return [(p[i], p[i + 1]) for i in range(0, len(p), 2)]
def area(P): return abs(sum(P[i][0] * P[i - 1][1] - P[i - 1][0] * P[i][1] for i in range(len(P)))) / 2
def cen(P): return (sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P))
ARCH = json.load(open('/home/claude/aksa/tools/scene/arch.json'))
FR = ARCH['frame']; _B = math.radians(ARCH['site']['bearing_up'])
def to_site(x, z):
    dx, dz = x - PLOT['x'], z - PLOT['z']
    return dx * math.cos(_B) + dz * math.sin(_B), -dx * math.sin(_B) + dz * math.cos(_B)
def in_site(x, z, *_):   # inside the architect's site plan (it replaces OSM there)
    u, v = to_site(x, z); return FR[0] < u < FR[2] and FR[1] < v < FR[3]

# ---------------- water / land mask ----------------
X0, Z0, S, MS = -2500, -3500, 2.0, 6000
W, H = int(MS / S), int(MS / S)
def px(P, x0=X0, z0=Z0, s=S): return np.array([[(x - x0) / s, (z - z0) / s] for x, z in P], np.int32)
m = np.zeros((H, W), np.uint8)
for w in ways:
    if w.get('t', {}).get('natural') == 'coastline': cv2.polylines(m, [px(pts(w))], False, 255, 2)
ff = m.copy(); cv2.floodFill(ff, np.zeros((H + 2, W + 2), np.uint8), (int((0 - X0) / S), int((600 - Z0) / S)), 128)
water = (ff == 128).astype(np.uint8)
inner_water = []
for w in ways:
    t = w.get('t', {})
    if (t.get('natural') == 'water' or 'water' in t) and len(w['p']) >= 6:
        P = pts(w)
        if area(P) > 400: cv2.fillPoly(water, [px(P)], 1)
        else: inner_water.append(P)
water = cv2.morphologyEx(water, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
np.save('/home/claude/aksa/src/water2.npy', water)   # X0,Z0,S grid, used by locmap.py
# pad to a much larger area (coarser), replicating the edge (town continues inland, river continues)
C = 8.0; CX0, CZ0 = -9000, -9000; CN = int(18000 / C)
small = cv2.resize(water, (int(MS / C), int(MS / C)), interpolation=cv2.INTER_NEAREST)
ox, oz = int((X0 - CX0) / C), int((Z0 - CZ0) / C)
big = cv2.copyMakeBorder(small, oz, CN - oz - small.shape[0], ox, CN - ox - small.shape[1], cv2.BORDER_REPLICATE)
big[:oz, :] = 0                                   # everything north of the box is land
land = (1 - big).astype(np.uint8)
land = cv2.morphologyEx(land, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
# fine land mask inside the detailed area overrides the coarse one via a second contour set
fine_land = (1 - water).astype(np.uint8)
def contours(mask, x0, z0, s, eps, min_area):
    cs, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    shapes = []
    if hier is None: return shapes
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1: continue
        if cv2.contourArea(c) * s * s < min_area: continue
        outer = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        holes = []; j = hier[i][2]
        while j != -1:
            hc = cs[j]
            if cv2.contourArea(hc) * s * s > min_area: holes.append(cv2.approxPolyDP(hc, eps, True).reshape(-1, 2))
            j = hier[j][0]
        f = lambda a: [[round(float(x * s + x0), 1), round(float(y * s + z0), 1)] for x, y in a]
        shapes.append({'outer': f(outer), 'holes': [f(h) for h in holes]})
    return shapes
# coarse land with the detailed box cut out, then the detailed land on top (slightly higher to hide seams)
cut = land.copy(); bx0, bz0 = int((X0 - CX0) / C), int((Z0 - CZ0) / C)
cut[bz0 + 1:bz0 + small.shape[0] - 1, bx0 + 1:bx0 + small.shape[1] - 1] = 0
land_coarse = contours(cut, CX0, CZ0, C, 1.0, 5000)
land_fine = contours(fine_land, X0, Z0, S, 1.0, 300)
print('land shapes', len(land_coarse), len(land_fine), 'pts', sum(len(s['outer']) for s in land_fine))

# ---------------- buildings ----------------
rnd = random.Random(7)
WALLS = ['#F2EEE6', '#EFE7D8', '#F4F1EA', '#E9DFCB', '#EEE3C8', '#E6E1D6', '#F1E9D9', '#E4D8BF', '#EBDDB0', '#DCE3E4']
TERRA = ['#B4624A', '#A95A43', '#BE6E52', '#9E5440', '#B86A4F']
FLATR = ['#CFCAC0', '#C7C3BA', '#D8D3C9', '#BDB9B1']
blds = []; removed = 0
for w in ways:
    t = w.get('t', {})
    if 'building' not in t or len(w['p']) < 8: continue
    P = pts(w)
    if P[0] == P[-1]: P = P[:-1]
    if len(P) < 3: continue
    c = cen(P)
    if in_site(*c, 60, 46) or any(in_site(x, z) for x, z in P): removed += 1; continue
    a = area(P); ty = t['building']; r = random.Random(w['i'])
    lv = t.get('building:levels')
    try: lv = float(lv)
    except (TypeError, ValueError): lv = None
    if ty == 'ruins': h = 2.5 + r.random() * 2; lv = None
    elif ty in ('garage', 'garages', 'shed', 'roof', 'carport'): h = 2.8
    elif lv: h = lv * 3.1 + .4
    elif ty == 'house': h = (1 if r.random() < .4 else 2) * 3.1 + .4
    elif ty == 'apartments': h = (3 + int(r.random() * 3)) * 3.1 + .4
    elif ty in ('warehouse', 'industrial'): h = 7 + r.random() * 3
    elif ty in ('church', 'chapel'): h = 13
    elif ty in ('school', 'public', 'civic', 'commercial', 'retail'): h = 9 + r.random() * 3
    else: h = (1 + int(r.random() * 3)) * 3.1 + .4
    if ty == 'ruins': wall, roof = '#B9AE9A', None
    elif ty in ('warehouse', 'industrial'): wall, roof = r.choice(['#D9D6CF', '#CFCBC2', '#E3DED3']), r.choice(['#A7ABAB', '#9FA39F', '#B2B0A8'])
    else:
        wall = r.choice(WALLS)
        roof = r.choice(TERRA) if (a < 450 and r.random() < .8) or r.random() < .25 else r.choice(FLATR)
    gable = roof in TERRA and len(P) == 4 and a < 600
    blds.append({'h': round(h, 1), 'w': wall, 'r': roof, 'g': 1 if gable else 0, 'p': [round(v, 1) for q in P for v in q]})
print('buildings', len(blds), 'removed on plot', removed)

# ---------------- trees ----------------
GREEN_T = {'park': .010, 'garden': .006, 'wood': .03, 'forest': .03, 'scrub': .006, 'grass': .002, 'village_green': .004, 'cemetery': .004}
trees = []
for w in ways:
    t = w.get('t', {}); kind = t.get('leisure') or t.get('landuse') or t.get('natural')
    if kind not in GREEN_T or len(w['p']) < 8: continue
    P = pts(w); a = area(P); n = int(a * GREEN_T[kind]); r = random.Random(w['i'])
    if n == 0: continue
    xs = [p[0] for p in P]; zs = [p[1] for p in P]; poly = np.array(P, np.float32)
    k = 0
    for _ in range(n * 6):
        if k >= n: break
        x, z = r.uniform(min(xs), max(xs)), r.uniform(min(zs), max(zs))
        if not (TEX[0] < x < TEX[0] + TEX[2] and TEX[1] < z < TEX[1] + TEX[2]): continue
        if cv2.pointPolygonTest(poly, (x, z), False) > 0 and not in_site(x, z, 58, 44):
            trees.append([round(x, 1), round(z, 1), round(.8 + r.random() * .6, 2), 0]); k += 1
for w in ways:
    if w.get('t', {}).get('natural') != 'tree_row': continue
    P = pts(w)
    for (x0, z0), (x1, z1) in zip(P, P[1:]):
        L = math.hypot(x1 - x0, z1 - z0)
        for s in np.arange(0, L, 9):
            x, z = x0 + (x1 - x0) * s / L, z0 + (z1 - z0) * s / L
            if not in_site(x, z, 58, 44): trees.append([round(x, 1), round(z, 1), 1.0, 0])
print('trees', len(trees))

# ---------------- filler blocks outside the OSM box (town continues) ----------------
filler = []; r = random.Random(3)
for _ in range(16000):
    x, z = PLOT['x'] + r.uniform(-3800, 3800), r.uniform(PLOT['z'] - 3200, 800)
    if in_boxes(x, z, 20) or in_site(x, z): continue
    if z > 450 and x > 300: continue                      # air-base fields, keep open
    gx, gz = int((x - CX0) / C), int((z - CZ0) / C)
    if big[gz, gx] or big[min(CN - 1, gz + 3), gx] or big[max(0, gz - 3), gx]: continue
    dist = math.hypot(x - PLOT['x'], (z - PLOT['z']) * 1.2)
    if r.random() > math.exp(-(dist - 900) / 1400): continue
    wd, dp = 10 + r.random() * 18, 9 + r.random() * 14
    h = (1 + int(r.random() * (4 if r.random() < .8 else 7))) * 3.1
    filler.append([round(x), round(z), round(wd, 1), round(dp, 1), round(h, 1), round(r.random() * 3.14, 2)])
print('filler', len(filler))

# ---------------- ground texture ----------------
tx0, tz0, tsz = TEX; k = TS / tsz
im = Image.new('RGB', (TS, TS), '#CDC9AD'); dr = ImageDraw.Draw(im)
T = lambda P: [((x - tx0) * k, (z - tz0) * k) for x, z in P]
LANDUSE = {'residential': '#DCD6C9', 'commercial': '#DAD4C8', 'retail': '#DAD4C8', 'industrial': '#D3CEC4', 'construction': '#D2C6AE',
           'grass': '#9CB477', 'meadow': '#A8B57E', 'farmland': '#B9B880', 'farmyard': '#CFC7A6', 'orchard': '#98AE70', 'forest': '#6E8E54',
           'greenfield': '#B3B67F', 'flowerbed': '#8FAE6A', 'cemetery': '#A8B08A', 'village_green': '#9CB477'}
NATURAL = {'scrub': '#9DA673', 'grassland': '#AAB27C', 'wood': '#6E8E54', 'wetland': '#8E9E78', 'sand': '#E4D6B2', 'shingle': '#CFC5B0', 'bare_rock': '#BDB4A6', 'beach': '#E4D6B2'}
LEISURE = {'park': '#9CB477', 'garden': '#97B172', 'pitch': '#86A866', 'playground': '#CDBFA3', 'sports_centre': '#C9C2B4', 'stadium': '#C9C2B4', 'track': '#B97A5E', 'marina': '#D6CFBF'}
def poly_fill(order):
    for w in ways:
        t = w.get('t', {})
        col = order(t)
        if col and len(w['p']) >= 6: dr.polygon(T(pts(w)), fill=col)
poly_fill(lambda t: LANDUSE.get(t.get('landuse')))
poly_fill(lambda t: NATURAL.get(t.get('natural')))
poly_fill(lambda t: LEISURE.get(t.get('leisure')))
poly_fill(lambda t: '#CBC6BC' if t.get('amenity') == 'parking' or t.get('highway') == 'pedestrian' or t.get('place') == 'square' else None)
for P in inner_water: dr.polygon(T(P), fill='#5E97A2')
RW = {'motorway': 16, 'trunk': 14, 'primary': 12, 'secondary': 11, 'tertiary': 9.5, 'unclassified': 7.5, 'residential': 7.5, 'living_street': 6,
      'service': 4.5, 'pedestrian': 5, 'footway': 2.4, 'path': 2, 'cycleway': 2.4, 'track': 3, 'steps': 2.4}
roads = [w for w in ways if w.get('t', {}).get('highway') in RW and len(w['p']) >= 4 and w['t'].get('area') != 'yes']
for w in roads:
    t = w['t']; rw = RW[t['highway']]
    if rw > 4: dr.line(T(pts(w)), fill='#C4BFB5', width=max(1, int((rw + 3.2) * k)), joint='curve')
for w in roads:
    t = w['t']; rw = RW[t['highway']]
    col = '#E8E2D6' if rw < 3.5 else ('#D1CBBF' if t['highway'] in ('pedestrian', 'living_street') else '#7E7F7D')
    dr.line(T(pts(w)), fill=col, width=max(1, int(rw * k)), joint='curve')
for w in roads:
    t = w['t']
    if t['highway'] in ('primary', 'secondary', 'tertiary', 'trunk'):
        dr.line(T(pts(w)), fill='#E9E6DC', width=max(1, int(.35 * k)))
for w in ways:
    if w.get('t', {}).get('railway') and len(w['p']) >= 4: dr.line(T(pts(w)), fill='#8A8378', width=int(3 * k))
# the plot: new landscaping replaces the car-wash lot

# contact shadows around buildings
sh = Image.new('L', (TS, TS), 0); sd = ImageDraw.Draw(sh)
for b in blds:
    P = [(b['p'][i], b['p'][i + 1]) for i in range(0, len(b['p']), 2)]
    sd.polygon(T(P), fill=int(min(255, 60 + b['h'] * 6)))
sh = sh.filter(ImageFilter.GaussianBlur(4 * k))
dark = Image.new('RGB', (TS, TS), '#6F6A60')
im = Image.composite(dark, im, sh.point(lambda v: int(v * .45)))
noise = (np.random.RandomState(1).randn(TS // 4, TS // 4) * 7).astype(np.int16)
noise = cv2.resize(noise.astype(np.float32), (TS, TS), interpolation=cv2.INTER_CUBIC)
arr = np.clip(np.array(im).astype(np.float32) + noise[:, :, None], 0, 255).astype(np.uint8)
arr = Image.fromarray(arr); bd = ImageDraw.Draw(arr); e = 10
for box in [(0, 0, TS, e), (0, TS - e, TS, TS), (0, 0, e, TS), (TS - e, 0, TS, TS)]: bd.rectangle(box, fill='#D3CCBC')
arr.save(f'{OUT}/ground.jpg', quality=88)

# ---------------- landmarks (real OSM names; 'near' list from OSM ways around the site) ----------------
want = {'Igreja Matriz ou Igreja do Espírito Santo': 'Igreja Matriz', 'Museu Municipal': 'Museu Municipal', 'Moinho de Maré do Montijo': 'Tide mill',
        'Cais das Faluas - Montijo': 'Cais das Faluas', 'Monumento ao Pescador Montijense': 'Fishermen’s monument', 'Galeria Municipal de Montijo': 'Galeria Municipal',
        'Biblioteca Municipal Manuel Giraldes da Silva': 'Municipal library'}
marks = []
for p in d['pois']:
    n = p['t'].get('name')
    if n in want and not any(m['name'] == want[n] for m in marks): marks.append({'name': want[n], 'osm': n, 'x': p['c'][0], 'z': p['c'][1]})
ferry = next(p for p in d['pois'] if p['t'].get('amenity') == 'ferry_terminal')
marks.append({'name': 'Cais do Seixalinho ferry', 'osm': 'Montijo (ferry terminal)', 'x': ferry['c'][0], 'z': ferry['c'][1]})
marks = [m for m in marks if m['name'] in ('Igreja Matriz', 'Municipal library', 'Cais das Faluas', 'Tide mill', 'Cais do Seixalinho ferry')]
NEAR = [('Esteval windmill', 'Moinho de Vento do Esteval', 802, -1106), ('Bus stop, Av. D. João II', 'Avenida Dom João II (Rotunda)', 924, -1097),
        ('Parque Dr. Sá Carneiro', 'Parque Doutor Francisco Sá Carneiro', 929, -983), ('Lidl', 'Lidl Montijo - Av. de Olivença', 634, -1053),
        ('Estádio Municipal do Esteval', 'Estádio Municipal do Esteval', 1009, -894), ('Escola Básica da Liberdade', 'Escola Básica da Liberdade', 446, -925),
        ('Pingo Doce', 'Pingo Doce', 549, -823), ('Intermarché', 'Intermarché', 958, -670), ('Municipal sports hall', 'Pavilhão Desportivo Municipal N.º2', 753, -515)]
marks = [{'name': n, 'osm': o, 'x': x, 'z': z} for n, o, x, z in NEAR] + marks
for mk in marks: mk['dist'] = round(math.hypot(mk['x'] - PLOT['x'], mk['z'] - PLOT['z']))
print([(m['name'], m['dist']) for m in marks])

json.dump({'plot': PLOT, 'tex': TEX, 'boxes': BOXES, 'landCoarse': land_coarse, 'landFine': land_fine, 'buildings': blds, 'trees': trees,
           'filler': filler, 'landmarks': marks, 'origin': d['origin'], 'attribution': d['attribution']},
          open(f'{OUT}/scene.json', 'w'), separators=(',', ':'))
print('scene.json KB', os.path.getsize(f'{OUT}/scene.json') // 1024)
