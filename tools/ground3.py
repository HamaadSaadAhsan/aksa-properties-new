"""Ground for the project-only scene: grass fields, the real road network near the site, water. No neighbouring buildings."""
import json, math, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
SC = json.load(open('scene/scene.json')); PL = SC['plot']; TX0, TZ0, TSZ = SC['tex']; TS = 8192; k = TS / TSZ
ways = []
for f in ['/home/claude/aksa/src/aksa_osm.json', '/home/claude/aksa/src/aksa_osm_site.json']:
    ways += json.load(open(f))['ways']
pts = lambda w: [(w['p'][i], w['p'][i + 1]) for i in range(0, len(w['p']), 2)]
T = lambda P: [((x - TX0) * k, (z - TZ0) * k) for x, z in P]
dist = lambda P: min(math.hypot(x - PL['x'], z - PL['z']) for x, z in P)
rs = np.random.RandomState(7)
# grass: olive green with large soft mottling and faint mowing bands, like the studio renders
base = np.zeros((TS // 8, TS // 8, 3), np.float32); base[:] = (128, 146, 70)
n1 = cv2.resize(rs.randn(TS // 256, TS // 256).astype(np.float32), (TS // 8, TS // 8), interpolation=cv2.INTER_CUBIC) * 4.5
n2 = cv2.resize(rs.randn(TS // 64, TS // 64).astype(np.float32), (TS // 8, TS // 8), interpolation=cv2.INTER_CUBIC) * 3
base += (n1 + n2)[:, :, None] * np.array([1.0, 1.1, .6])
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((TS, TS), Image.BICUBIC)
dr = ImageDraw.Draw(im)
# water (Tagus) from the coastline mask
water = np.load('/home/claude/aksa/src/water2.npy').astype(np.uint8)
X0, Z0, S = -2500, -3500, 2.0
wm = np.zeros((TS, TS), np.uint8)
M = np.array([[S * k, 0, (X0 - TX0) * k], [0, S * k, (Z0 - TZ0) * k]], np.float32)
wm = cv2.warpAffine(water * 255, M, (TS, TS), flags=cv2.INTER_LINEAR)
im.paste(Image.new('RGB', (TS, TS), (94, 138, 150)), (0, 0), Image.fromarray(wm).filter(ImageFilter.GaussianBlur(2)))
dr = ImageDraw.Draw(im)
RW = {'motorway': 16, 'trunk': 14, 'primary': 12, 'secondary': 11, 'tertiary': 9.5, 'unclassified': 7.5, 'residential': 7.5, 'living_street': 6,
      'service': 5, 'pedestrian': 5, 'footway': 2.4, 'path': 2, 'cycleway': 2.6, 'track': 3}
MAJOR = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary'}
roads = []
for w in ways:
    t = w.get('t', {}); h = t.get('highway')
    if h not in RW or len(w['p']) < 4 or t.get('area') == 'yes': continue
    P = pts(w); d = dist(P)
    if h in MAJOR and d < 2600 or h in ('residential', 'unclassified', 'living_street') and d < 330 or d < 200: roads.append((h, P))
for h, P in roads:                                   # kerbs / pavements
    rw = RW[h]
    if rw > 4: dr.line(T(P), fill=(196, 192, 184), width=max(2, int((rw + 4) * k)), joint='curve')
for h, P in roads:
    rw = RW[h]
    col = (185, 136, 120) if h == 'cycleway' else (205, 200, 190) if rw < 4 else (92, 94, 97)
    dr.line(T(P), fill=col, width=max(2, int(rw * k)), joint='curve')
for h, P in roads:                                   # centre lines on the main roads
    if h in MAJOR: dr.line(T(P), fill=(232, 230, 222), width=max(1, int(.25 * k)))
arr = np.array(im).astype(np.int16)
arr += (rs.randn(TS // 2, TS // 2) * 4).astype(np.int16).repeat(2, 0).repeat(2, 1)[:, :, None]
Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save('scene/ground_green.jpg', quality=88)
print('roads', len(roads), TS)
