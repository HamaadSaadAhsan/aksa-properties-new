"""Location map base image from the OSM extract (labels and pins are drawn live in the page)."""
import json, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
d = json.load(open('/home/claude/aksa/src/aksa_osm.json')); d2 = json.load(open('/home/claude/aksa/src/aksa_osm_site.json'))
d['ways'] = d['ways'] + d2['ways']
sc = json.load(open('/home/claude/aksa/tools/scene/scene.json'))
water = np.load('/home/claude/aksa/src/water2.npy').astype(np.float32)
EXT = [-450, -1850, 1550, 150]; K = 1.2
Wd, Hd = int((EXT[2] - EXT[0]) * K), int((EXT[3] - EXT[1]) * K)
T = lambda P: [((x - EXT[0]) * K, (z - EXT[1]) * K) for x, z in P]
pts = lambda w: [(w['p'][i], w['p'][i + 1]) for i in range(0, len(w['p']), 2)]
im = Image.new('RGB', (Wd, Hd), '#F2EEE6')
X0, Z0, S = -2500, -3500, 2.0
crop = water[int((EXT[1] - Z0) / S):int((EXT[3] - Z0) / S), int((EXT[0] - X0) / S):int((EXT[2] - X0) / S)]
wm = Image.fromarray((crop * 255).astype('uint8')).resize((Wd, Hd), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 127 else 0)
im.paste(Image.new('RGB', (Wd, Hd), '#B7D3DC'), (0, 0), wm)
dr = ImageDraw.Draw(im)
G = {'park', 'garden', 'grass', 'meadow', 'village_green', 'wood', 'forest', 'scrub', 'grassland', 'pitch', 'flowerbed', 'cemetery'}
for w in d['ways']:
    t = w.get('t', {})
    if len(w['p']) >= 6 and (t.get('leisure') in G or t.get('landuse') in G or t.get('natural') in G): dr.polygon(T(pts(w)), fill='#D6E3C3')
RW = {'trunk': 11, 'primary': 10, 'secondary': 9, 'tertiary': 8, 'unclassified': 6, 'residential': 6, 'living_street': 5, 'service': 3.5,
      'pedestrian': 4.5, 'footway': 1.6, 'path': 1.4, 'cycleway': 1.6}
roads = [w for w in d['ways'] if w.get('t', {}).get('highway') in RW and w['t'].get('area') != 'yes']
for w in roads:
    r = RW[w['t']['highway']]
    if r > 3: dr.line(T(pts(w)), fill='#DAD3C6', width=int((r + 2) * K), joint='curve')
for w in roads:
    r = RW[w['t']['highway']]; dr.line(T(pts(w)), fill='#FFFFFF' if r > 2 else '#E7E1D6', width=max(1, int(r * K)), joint='curve')
for b in sc['buildings']:
    P = [(b['p'][i], b['p'][i + 1]) for i in range(0, len(b['p']), 2)]
    dr.polygon(T(P), fill='#E3DACB', outline='#D3C8B5')
PL = sc['plot']
AR = json.load(open('/home/claude/aksa/tools/scene/arch.json')); SB = AR['site']
be = -math.radians(SB['bearing_up'])          # three.js rotation.y of the site group
def S2W(u, v):                                # site-group local (u, v) -> world (x, z); rotation.y about +y
    return (PL['x'] + u * math.cos(be) + v * math.sin(be), PL['z'] - u * math.sin(be) + v * math.cos(be))
c = SB['commercial']
dr.polygon(T([S2W(u, v) for u, v in [(c['u0'], c['v0']), (c['u1'], c['v0']), (c['u1'], c['v1']), (c['u0'], c['v1'])]]), fill='#C9B79A')
for bu, bv in SB['blocks']:                   # block group: offset (bu,bv), rotation.y = +90deg -> (x,z) -> (z, -x)
    for ring, col in [(AR['p1']['outer'], '#1F5E6B')] + [(h, '#E9D9BD') for h in AR['p1']['holes']]:
        dr.polygon(T([S2W(bu + z, bv - x) for x, z in ring]), fill=col)
im.save('/home/claude/aksa/site/media/loc/map.jpg', quality=86, optimize=True, progressive=True)
json.dump({'image': 'media/loc/map.jpg', 'extent': EXT, 'size': [Wd, Hd], 'plot': [PL['x'], PL['z']], 'landmarks': sc['landmarks']},
          open('/home/claude/aksa/tools/locmap.json', 'w'), ensure_ascii=False)
print(Wd, Hd)
