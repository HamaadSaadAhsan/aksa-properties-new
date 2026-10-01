"""Clean floor plans: just the plot. The building's footprint in one soft tone (from the homes' outlines, with the cores and
corridors between them closed in), no architectural lines. The homes themselves are drawn on top by the site, so outlines
and codes come from data.json. Same size and coordinates as the architect's sheets.  usage: python3 flat_plans.py <site_dir>"""
import json, sys, os, numpy as np, cv2
SITE = sys.argv[1]; D = json.load(open(f'{SITE}/data.json'))
W, H = 2131, 2862; os.makedirs(f'{SITE}/media/plans/flat', exist_ok=True)
for key, P in D['plans'].items():
    t, f = key.split(':'); name = os.path.basename(P['image']).replace('.jpg', '.png'); src = 'media/plans/' + name.replace('.png', '.jpg')
    dst = f'{SITE}/media/plans/flat/{name}'
    vb = P['viewBox']; sx, sy = W / vb[2], H / vb[3]
    us = [u for u in D['units'] if u['tower'] == t and u['floor'] == int(f)]
    m = np.zeros((H, W), np.uint8)
    if us:
        for u in us: cv2.fillPoly(m, [np.int32([[x * sx, y * sy] for x, y in u['poly']])], 255)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (71, 71)))
    else:                                             # roof level: no homes, take the drawn building from the cleaned sheet
        im = cv2.imread(f'{SITE}/' + src.replace('media/plans/', 'media/plans/clean/'))
        m = (im.min(axis=2) < 232).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    if us and int(f) > 0:                             # upper floors: close the narrow notches at the stair cores (ground floor keeps its passages)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (121, 121)))
    # fill every hole inside the building except the courtyard (the largest): stair and lift cores, corridors
    cs, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    holes = [c for c, h in zip(cs, hier[0]) if h[3] >= 0]
    if holes:
        court = max(holes, key=cv2.contourArea)
        cv2.drawContours(m, [c for c in holes if c is not court], -1, 255, cv2.FILLED)
    out = np.full((H, W, 3), (242, 247, 250), np.uint8)                          # paper (BGR of #FAF7F2)
    cs, _ = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    cs = [cv2.approxPolyDP(c, 6, True) for c in cs if cv2.contourArea(c) > 4000]   # straight, clean edges
    m = np.zeros_like(m); cv2.drawContours(m, cs, -1, 255, cv2.FILLED)
    out[m > 0] = (205, 216, 224)                                                 # building: soft sand-grey
    cv2.drawContours(out, cs, -1, (110, 120, 128), 4, cv2.LINE_AA)               # one clean outline
    cv2.imwrite(dst, out); P['image'] = f'media/plans/flat/{name}'
    print(key, '->', P['image'], len(us), 'homes')
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
T0 = '<script id="manifest" type="application/json">'
s = open(f'{SITE}/index.html').read(); a = s.index(T0) + len(T0); b = s.index('</script>', a)
open(f'{SITE}/index.html', 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s[b:])
