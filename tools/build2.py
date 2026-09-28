"""Rendered frames + ID masks + architect plans + location/gallery content -> site/media and site/data.json."""
import json, math, os, glob, shutil, subprocess, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

OUT = 'out'; SITE = '../site'; MED = f'{SITE}/media'
ANG = [i * 45 for i in range(8)]
meta = json.load(open(f'{OUT}/meta.json'))
D = meta['data']
PL = json.load(open('/home/claude/aksa/arch/plans.json'))
for d in ['mp', 'close', '360', 'plans', 'loc', 'gallery']: os.makedirs(f'{MED}/{d}', exist_ok=True)
def sh(cmd): subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------- video ----------
ENC = '-c:v libx264 -pix_fmt yuv420p -crf 25 -preset medium -movflags +faststart -an'
def enc(frames_dir, fps, dst):
    if not os.path.exists(dst): sh(f'ffmpeg -y -framerate {fps} -i {frames_dir}/%03d.jpg {ENC} {dst}')
def rev(src, dst):
    if not os.path.exists(dst): sh(f'ffmpeg -y -i {src} -vf reverse {ENC} {dst}')
fly = {}
for i, a in enumerate(ANG):
    b = ANG[(i + 1) % 8]
    shutil.copy(f'{OUT}/stills/angle_{a:03d}.jpg', f'{MED}/mp/angle_{a:03d}.jpg')
    enc(f'{OUT}/frames/loop_{a:03d}', 12, f'{MED}/mp/angle_{a:03d}_loop.mp4')
    enc(f'{OUT}/frames/trans_{a:03d}-{b:03d}', 24, f'{MED}/mp/trans_{a:03d}-{b:03d}.mp4')
    rev(f'{MED}/mp/trans_{a:03d}-{b:03d}.mp4', f'{MED}/mp/trans_{b:03d}-{a:03d}.mp4')
    Image.open(f'{OUT}/stills/close_{a:03d}.jpg').save(f'{MED}/close/close_{a:03d}.jpg', quality=84, optimize=True, progressive=True)
    enc(f'{OUT}/frames/ctrans_{a:03d}-{b:03d}', 24, f'{MED}/close/trans_{a:03d}-{b:03d}.mp4')
    rev(f'{MED}/close/trans_{a:03d}-{b:03d}.mp4', f'{MED}/close/trans_{b:03d}-{a:03d}.mp4')
    enc(f'{OUT}/frames/fly_{a:03d}-close', 24, f'{MED}/close/fly_{a:03d}-close.mp4')
    rev(f'{MED}/close/fly_{a:03d}-close.mp4', f'{MED}/close/fly_close-{a:03d}.mp4')
    fly[f'{a:03d}'] = {'in': f'media/close/fly_{a:03d}-close.mp4', 'out': f'media/close/fly_close-{a:03d}.mp4'}
PANOS = list(D['panos'].keys())
for p in PANOS: enc(f'{OUT}/frames/fly_000-{p}', 24, f'{MED}/360/fly_000-{p}.mp4')
for f in glob.glob(f'{OUT}/360/*.jpg'): Image.open(f).save(f'{MED}/360/' + os.path.basename(f), quality=84, optimize=True, progressive=True)

# ---------- outline tracing from ID masks ----------
def trace(binary, eps, min_area):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)
    cs, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True).reshape(-1, 2).tolist() for c in cs if cv2.contourArea(c) >= min_area]
angles = []
for a in ANG:
    m = np.array(Image.open(f'{OUT}/masks/angle_{a:03d}_id.png').convert('RGB')); h, w = m.shape[:2]
    res = ((m[:, :, 0] > 200) & (m[:, :, 1] < 50)).astype(np.uint8) * 255
    com = ((m[:, :, 1] > 200) & (m[:, :, 0] < 50)).astype(np.uint8) * 255
    markers = [{'pano': k, 'x': round(v['x'], 1), 'y': round(v['y'], 1)} for k, v in meta['markers'][str(a)].items() if v['visible']]
    outl = [{'id': 'aksa', 'label': 'AKSA Residencies', 'target': 'close', 'polys': trace(res, 1.2, 300)}]
    cp = trace(com, 1.2, 150)
    if cp: outl.append({'id': 'commercial', 'label': 'Commercial building', 'target': 'gallery:commercial', 'polys': cp})
    angles.append({'id': f'{a:03d}', 'still': f'media/mp/angle_{a:03d}.jpg', 'loop': f'media/mp/angle_{a:03d}_loop.mp4', 'outlines': outl, 'markers': markers})
MPW, MPH = w, h
TOW = D['towers']
close_angles = []
for a in ANG:
    cm = np.array(Image.open(f'{OUT}/masks/close_{a:03d}_id.png').convert('RGB')); CH, CW = cm.shape[:2]
    fl = []
    for t, T in enumerate(TOW):
        for f in range(T['floors']):
            b = ((cm[:, :, 0] == 40 + t * 80) & (cm[:, :, 1] == 10 + f * 8) & (cm[:, :, 2] == 200)).astype(np.uint8) * 255
            if b.sum() == 0: continue
            polys = trace(b, 1.6, 150)
            if polys: fl.append({'tower': T['id'], 'floor': f, 'polys': polys})
    close_angles.append({'id': f'{a:03d}', 'still': f'media/close/close_{a:03d}.jpg', 'floors': fl})

# ---------- units from the architect's plans (identical in both blocks) ----------
FLOORNAME = {0: 'Ground floor', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3', 4: 'Level 4', 5: 'Level 5 · penthouses'}
units = []; plans = {}
rnd = random.Random(11)
for T in TOW:
    for f in range(T['floors']):
        F = PL['floors'][str(f)]
        plans[f'{T["id"]}:{f}'] = {'image': F['image'], 'viewBox': PL['viewBox'], 'name': FLOORNAME[f]}
        for u in F['units']:
            x = rnd.random(); top = f / 5 * .15
            status = 'available' if x < .5 - top else 'reserved' if x < .68 - top / 2 else 'sold'
            eur = 3150 + 55 * f + (350 if f == 5 else 0)
            asp = ' + '.join(u['aspect']) if u['aspect'] else ''
            view = (f'{asp} · courtyard' if asp else 'Courtyard') if f < 5 else (f'{asp} terrace' if asp else 'Terrace')
            units.append({'id': f'{T["id"]}-{f}.{u["n"]:02d}', 'n': u['n'], 'tower': T['id'], 'floor': f, 'poly': u['poly'], 'cx': u['cx'], 'cy': u['cy'],
                          'type': u['type'], 'beds': int(u['type'][1]), 'm2': u['area'], 'frac': u['frac'], 'status': status, 'view': view,
                          'price': round(u['area'] * eur / 5000) * 5000, 'tour': 'residence'})
print('units', len(units))

# ---------- interior tour ----------
def yp(frm, to):
    d = [to[i] - frm[i] for i in range(3)]; n = math.sqrt(sum(x * x for x in d))
    return {'yaw': round(math.degrees(math.atan2(d[0], -d[2])), 1), 'pitch': round(math.degrees(math.asin(d[1] / n)), 1)}
rooms = D['rooms']; liv, bed = rooms[0]['pos'], rooms[1]['pos']
tour = {'residence': {'name': 'Residence interior', 'rooms': [
    {'id': 'living', 'name': 'Living & kitchen', 'image': 'media/360/living.jpg', 'start': {'yaw': 0, 'pitch': -3, 'fov': 75},
     'hotspots': [dict(yp(liv, [-4.2, 1.3, 2.2]), to='bedroom', label='Primary bedroom')]},
    {'id': 'bedroom', 'name': 'Primary bedroom', 'image': 'media/360/bedroom.jpg', 'start': {'yaw': 8, 'pitch': -3, 'fov': 75},
     'hotspots': [dict(yp(bed, [97.3, 1.3, 1.5]), to='living', label='Living & kitchen')]}]}}
panos = {}
for k, p in D['panos'].items():
    st = json.load(open(f'{OUT}/frames/fly_000-{k}/start.json'))
    panos[k] = {'name': p['name'], 'meta': p['meta'], 'image': f'media/360/{k}.jpg', 'from': '000', 'fly': f'media/360/fly_000-{k}.mp4',
                'start': {'yaw': round(math.degrees(st['yaw']), 2), 'pitch': max(-6.0, round(math.degrees(st['pitch']), 2)), 'fov': st['fov']}}

# ---------- clouds overlay ----------
cl = Image.new('RGBA', (900, 360), (0, 0, 0, 0)); dr = ImageDraw.Draw(cl); rs = np.random.RandomState(4)
for _ in range(38):
    x, y, r = rs.randint(120, 780), rs.randint(120, 250), rs.randint(40, 95)
    dr.ellipse([x - r * 1.5, y - r * .8, x + r * 1.5, y + r * .8], fill=(255, 255, 255, 150))
cl.filter(ImageFilter.GaussianBlur(26)).save(f'{MED}/clouds.png')

# ---------- location + gallery ----------
loc = json.load(open('locmap.json')); photos = json.load(open('photos.json')); gallery = json.load(open('gallery.json'))
walk = lambda m: max(1, round(m * 1.3 / 80))
location = {
    'title': 'Montijo, on the Tagus',
    'lede': loc.get('lede', 'A riverside town on the south bank of the Tagus estuary, across the water from Lisbon. AKSA Residencies sits on the north-east edge of town in Esteval, beside the Av. D. João II roundabout: parks, schools and supermarkets within a 10-minute walk, the old town and riverfront 20–25 minutes on foot, and fast road links to the Vasco da Gama Bridge.'),
    'video': {'src': 'media/loc/bridge.mp4', 'poster': 'media/loc/bridge.jpg', 'credit': 'Vasco da Gama Bridge · video by Masood Aslami, Pexels', 'source': 'https://www.pexels.com/video/the-bridge-is-long-and-spans-over-the-water-16750639/'},
    'facts': loc.get('facts') or [
        {'k': '≈ 25 min', 'v': 'Ferry to Lisbon (Cais do Sodré) from Cais do Seixalinho', 'src': 'Rome2Rio'},
        {'k': '≈ 30 min', 'v': 'Drive to central Lisbon over the Vasco da Gama Bridge', 'src': 'Rome2Rio'},
        {'k': '2035', 'v': 'Planned opening of the new Lisbon airport (Luís de Camões, Alcochete)', 'src': 'The Portugal News, Jul 2026'},
        {'k': '55,732', 'v': 'Residents in the municipality (2021 census)', 'src': 'Wikipedia'}],
    'map': dict(loc, attribution='© OpenStreetMap contributors (ODbL)'),
    'nearby': [dict(name=m['name'], osm=m['osm'], x=m['x'], z=m['z'], dist=m['dist'], walk=walk(m['dist'])) for m in sorted(loc['landmarks'], key=lambda m: m['dist'])],
    'photos': photos,
}
nres = len(units)
manifest = {
    'project': {'name': 'AKSA Residencies', 'short': 'AKSA', 'place': 'Montijo · Lisbon', 'currency': 'EUR',
                'facts': {'blocks': len(TOW), 'levels': TOW[0]['floors'], 'residences': nres}},
    'masterplan': {'viewBox': [MPW, MPH], 'start': '000', 'angles': angles, 'transition': 'media/mp/trans_{from}-{to}.mp4'},
    'close': {'viewBox': [CW, CH], 'from': '000', 'start': '000', 'angles': close_angles, 'transition': 'media/close/trans_{from}-{to}.mp4', 'fly': fly},
    'towers': [{'id': T['id'], 'name': T['name'], 'floors': T['floors']} for T in TOW],
    'floorNames': FLOORNAME,
    'panos': panos, 'tours': tour, 'plans': plans, 'units': units, 'location': location,
    'gallery': {'cats': [['all', 'All'], ['exterior', 'Architecture'], ['courtyard', 'Courtyard'], ['commercial', 'Commercial']], 'items': gallery},
}
json.dump(manifest, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('outlines', [[len(o['polys']) for o in a['outlines']] for a in angles])
print('floors traced per angle', [len(a['floors']) for a in close_angles], 'units', nres, 'data.json KB', os.path.getsize(f'{SITE}/data.json') // 1024)
