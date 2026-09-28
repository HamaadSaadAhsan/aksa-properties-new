"""Lanes for moving cars (real roads near the site from OpenStreetMap + the site-plan streets) and walking loops, in world metres."""
import json, math
SC = json.load(open('scene/scene.json')); PL = SC['plot']
TH = math.radians(-74.2); C, S = math.cos(TH), math.sin(TH)
W = lambda u, v: (PL['x'] + u * C + v * S, PL['z'] - u * S + v * C)
ways = []
for f in ['/home/claude/aksa/src/aksa_osm.json', '/home/claude/aksa/src/aksa_osm_site.json']: ways += json.load(open(f))['ways']
pts = lambda w: [(w['p'][i], w['p'][i + 1]) for i in range(0, len(w['p']), 2)]
RW = {'trunk': 14, 'primary': 12, 'secondary': 11, 'tertiary': 9.5, 'unclassified': 7.5, 'residential': 7.5}
def offset(P, d):
    out = []
    for i, (x, z) in enumerate(P):
        a = P[max(0, i - 1)]; b = P[min(len(P) - 1, i + 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]; n = math.hypot(dx, dz) or 1
        out.append((round(x - dz / n * d, 2), round(z + dx / n * d, 2)))
    return out
def length(P): return sum(math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) for i in range(len(P) - 1))
lanes = []; seen = set()
for w in ways:
    t = w.get('t', {}); h = t.get('highway')
    if h not in RW or w['i'] in seen: continue
    P = pts(w)
    dd = min(math.hypot(x - PL['x'], z - PL['z']) for x, z in P)
    if dd > (650 if h in ('trunk', 'primary', 'secondary', 'tertiary') else 330) or length(P) < 60: continue
    seen.add(w['i']); d = RW[h] / 4
    lanes.append({'p': offset(P, d), 'major': h in ('trunk', 'primary', 'secondary', 'tertiary')})
    if t.get('oneway') != 'yes': lanes.append({'p': offset(P[::-1], d), 'major': h in ('trunk', 'primary', 'secondary', 'tertiary')})
# streets drawn on the architect's site plan (site-local u, v)
for (u0, v0), (u1, v1) in [((-125, 54), (125, 54)), ((110.5, -100), (110.5, 58)), ((-103, -100), (-103, 58))]:
    P = [W(u0 + (u1 - u0) * k / 20, v0 + (v1 - v0) * k / 20) for k in range(21)]
    lanes.append({'p': offset(P, 1.8), 'major': False}); lanes.append({'p': offset(P[::-1], 1.8), 'major': False})
# pavements around each block (closed loops) and a path round each courtyard garden
walks = []
for bu in (-52.75, 52.75):
    for off in (4.5, 6.5):
        a, b = 44.7 + off, 32.5 + off
        R = [(bu - a, -b), (bu + a, -b), (bu + a, b), (bu - a, b), (bu - a, -b)]
        P = []
        for i in range(4):
            (u0, v0), (u1, v1) = R[i], R[i + 1]; n = int(math.hypot(u1 - u0, v1 - v0) // 4)
            P += [W(u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * k / n) for k in range(n)]
        walks.append({'p': [(round(x, 2), round(z, 2)) for x, z in P] + [(round(P[0][0], 2), round(P[0][1], 2))], 'loop': True})
    P = [W(bu + 20 * math.cos(t / 40 * 2 * math.pi), 9.5 * math.sin(t / 40 * 2 * math.pi)) for t in range(41)]
    walks.append({'p': [(round(x, 2), round(z, 2)) for x, z in P], 'loop': True, 'court': True})
json.dump({'lanes': lanes, 'walks': walks}, open('scene/traffic.json', 'w'))
print('lanes', len(lanes), 'walks', len(walks))
