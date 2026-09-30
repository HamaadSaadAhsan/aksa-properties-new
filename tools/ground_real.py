"""Real ground for the scene: DGT OrtoSat 2023 true-colour (Direção-Geral do Território, open data, 'no conditions apply'),
fetched by WMS in EPSG:4326 and stitched into the scene's ground-texture frame (scene x/z are linear in lon/lat)."""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
SC = json.load(open('/home/claude/aksa/tools/scene/scene.json')); TX0, TZ0, TSZ = SC['tex']; lat0, lon0 = SC['origin']
kx = 111320 * math.cos(math.radians(lat0)); ky = 110540
N, TP = 8, 1024; TS = N * TP; step = TSZ / N
D = '/home/claude/aksa/src/ortho'
def fetch(ij):
    i, j = ij; f = f'{D}/t_{i}_{j}.jpg'
    if os.path.exists(f) and os.path.getsize(f) > 5000: return f
    x0, x1 = TX0 + j * step, TX0 + (j + 1) * step; z0, z1 = TZ0 + i * step, TZ0 + (i + 1) * step
    lo0, lo1 = lon0 + x0 / kx, lon0 + x1 / kx; la1, la0 = lat0 - z0 / ky, lat0 - z1 / ky
    u = ('https://ortos.dgterritorio.gov.pt/wms/ortosat2023?service=WMS&version=1.3.0&request=GetMap&layers=ortoSat2023-CorVerdadeira&styles='
         f'&crs=EPSG:4326&bbox={la0},{lo0},{la1},{lo1}&width={TP}&height={TP}&format=image/jpeg')
    for _ in range(3):
        subprocess.run(['curl', '-s', '-o', f, '--max-time', '120', u])
        try: Image.open(f).verify(); return f
        except Exception: pass
    return None
with ThreadPoolExecutor(6) as ex: res = list(ex.map(fetch, [(i, j) for i in range(N) for j in range(N)]))
print('tiles ok', sum(r is not None for r in res), 'of', N * N)
out = Image.new('RGB', (TS, TS), (120, 120, 100))
for i in range(N):
    for j in range(N):
        f = f'{D}/t_{i}_{j}.jpg'
        if os.path.exists(f):
            try: out.paste(Image.open(f).convert('RGB'), (j * TP, i * TP))
            except Exception as e: print('bad', f, e)
out.save('/home/claude/aksa/tools/scene/ground_real.jpg', quality=90)
out.resize((1024, 1024)).save('/home/claude/aksa/src/ortho/preview.jpg', quality=85)
print('saved', TS)
