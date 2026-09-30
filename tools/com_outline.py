"""Trace the AI-placed commercial building in each corrected aerial -> convex hull polygon (1600x900 space)."""
import numpy as np, cv2, json, sys
from PIL import Image
res = {}; vis = []
for n in ['01', '02', '03']:
    a = np.array(Image.open(f'hf/cm/c_{n}.png').convert('RGB').resize((1600, 900), Image.LANCZOS)).astype(int)
    d = np.array(Image.open(f'cam/r{n}_dev.png').convert('RGB'))
    g = (d == (0, 255, 0)).all(2)
    ys, xs = np.where(g); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = 60; up = 160
    X0, X1, Y0, Y1 = max(0, x0 - pad), min(1599, x1 + pad), max(0, y0 - up), min(899, y1 + 20)
    hsv = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(int)
    grass = (hsv[..., 0] > 25) & (hsv[..., 0] < 50) & (hsv[..., 1] > 70)
    tree = (a[..., 1] > a[..., 0] + 8) & (a[..., 1] > a[..., 2] + 15)
    bldg = (~grass) & (~tree) & (((a.min(2) > 175) & (a.max(2) - a.min(2) < 35)) | (a.max(2) < 75))
    m = np.zeros((900, 1600), np.uint8); m[Y0:Y1, X0:X1] = bldg[Y0:Y1, X0:X1]
    m = cv2.morphologyEx(m * 255, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    k, lab, st, _ = cv2.connectedComponentsWithStats(m)
    # component overlapping the green footprint most
    best = max(range(1, k), key=lambda i: ((lab == i) & g).sum() * 3 + st[i, 4] * .2)
    c = (lab == best).astype(np.uint8) * 255
    cs, _ = cv2.findContours(c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = cv2.convexHull(max(cs, key=cv2.contourArea))
    poly = cv2.approxPolyDP(hull, 2, True).reshape(-1, 2).tolist()
    res[n] = poly
    v = a.astype(np.uint8).copy(); cv2.polylines(v, [np.array(poly)], True, (255, 0, 255), 3)
    vis.append(cv2.resize(v[max(0, Y0 - 40):Y1 + 40, max(0, X0 - 40):X1 + 40], None, fx=.8, fy=.8))
json.dump(res, open('hf/cm/com_poly.json', 'w'))
W = max(x.shape[1] for x in vis)
Image.fromarray(np.vstack([np.pad(x, ((0, 10), (0, W - x.shape[1]), (0, 0))) for x in vis])).save('hf/cm/com_ov.jpg', quality=85)
print({k: len(v) for k, v in res.items()})
