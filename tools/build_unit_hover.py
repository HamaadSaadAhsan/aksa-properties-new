"""Close-up hover by apartment: traces the 'units' ID masks rendered by render5.html (R.sales + R.mask('units')) into one
outline per home (data.json close.angles[].floors entries with tower, floor, unit id), plus one outline per building for the
roof level (no homes). Mask colour: R = 40 + 80*tower, G = 10 + 8*floor, B = 20 + 7*n (home number on its floor); roof level B = 250.
usage: python3 build_unit_hover.py <masks_dir> <site_dir>"""
import json, sys, numpy as np, cv2
from PIL import Image
MK, SITE = sys.argv[1], sys.argv[2]
def trace(binary, eps, min_area):
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    cs, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True).reshape(-1, 2).tolist() for c in cs if cv2.contourArea(c) >= min_area]
D = json.load(open(f'{SITE}/data.json'))
for A in D['close']['angles']:
    m = np.array(Image.open(f'{MK}/close_{A["id"]}_units.png').convert('RGB')).astype(int)
    key = m[:, :, 0] * 65536 + m[:, :, 1] * 256 + m[:, :, 2]
    fl = []
    for t, T in enumerate(D['towers']):
        for f in range(T['floors']):
            us = [u for u in D['units'] if u['tower'] == T['id'] and u['floor'] == f]
            if not us:
                polys = trace(((key == (40 + t * 80) * 65536 + (10 + f * 8) * 256 + 250)).astype(np.uint8) * 255, 1.6, 150)
                if polys: fl.append({'tower': T['id'], 'floor': f, 'polys': polys})
                continue
            for u in us:
                polys = trace((key == (40 + t * 80) * 65536 + (10 + f * 8) * 256 + 20 + 7 * u['n']).astype(np.uint8) * 255, 1.2, 60)
                if polys: fl.append({'tower': T['id'], 'floor': f, 'unit': u['id'], 'polys': polys})
    A['floors'] = fl
    print(A['id'], sum(1 for x in fl if 'unit' in x), 'homes visible')
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
T0 = '<script id="manifest" type="application/json">'
s = open(f'{SITE}/index.html').read(); a = s.index(T0) + len(T0); b = s.index('</script>', a)
open(f'{SITE}/index.html', 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s[b:])
