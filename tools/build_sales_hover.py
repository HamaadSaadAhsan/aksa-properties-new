"""Close-up hover by sales block: traces the 'sales' ID masks rendered by render5.html (R.sales + R.mask('sales')) into one
outline per building, floor and sales block (A-D North, E-H South), replacing the whole-floor outlines in data.json.
Mask colour: R = 40 + 80*tower, G = 10 + 8*floor, B = 60 + 40*k (k = index of the sales block within its building).
usage: python3 build_sales_hover.py <masks_dir> <site_dir>"""
import json, sys, numpy as np, cv2
from PIL import Image
MK, SITE = sys.argv[1], sys.argv[2]
TB = {'N': 'ABCD', 'S': 'EFGH'}
def trace(binary, eps, min_area):
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    cs, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True).reshape(-1, 2).tolist() for c in cs if cv2.contourArea(c) >= min_area]
D = json.load(open(f'{SITE}/data.json'))
for A in D['close']['angles']:
    m = np.array(Image.open(f'{MK}/close_{A["id"]}_sales.png').convert('RGB')).astype(int)
    fl = []
    for t, T in enumerate(D['towers']):
        for f in range(T['floors']):
            for k, blk in enumerate(TB[T['id']]):
                b = ((m[:, :, 0] == 40 + t * 80) & (m[:, :, 1] == 10 + f * 8) & (m[:, :, 2] == 60 + 40 * k)).astype(np.uint8) * 255
                if b.sum() == 0: continue
                polys = trace(b, 1.6, 150)
                if polys: fl.append({'tower': T['id'], 'floor': f, 'block': blk, 'polys': polys})
    A['floors'] = fl
    print(A['id'], len(fl), 'block-floor outlines')
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
T0 = '<script id="manifest" type="application/json">'
s = open(f'{SITE}/index.html').read(); a = s.index(T0) + len(T0); b = s.index('</script>', a)
open(f'{SITE}/index.html', 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s[b:])
