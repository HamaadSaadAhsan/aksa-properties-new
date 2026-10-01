"""Sales inventory (Sales_Inventory_Aksa_Project.xlsx) -> u['inv'] on each of the 320 homes in data.json.
The workbook splits each courtyard block into 4 sales blocks around the ring (A-D = North block, E-H = South block),
7 / 9 / 9 / 7 homes per floor. For each block and floor the ring is cut into those 4 runs at the rotation where the
architect's codes ('Original Unit Code', e.g. 'B4A') best match the site's codes ('B4+A' -> 'B4A'), with the facade
side as a tie-break, then each home takes the row with its own code.
usage: python3 build_inventory.py <xlsx> <site_dir>"""
import json, sys, collections, openpyxl

XL, SITE = sys.argv[1], sys.argv[2]
TOWER_BLOCKS = {'N': 'ABCD', 'S': 'EFGH'}
STATUS = {'Available': 'available', 'Reserved': 'reserved', 'On Contract': 'sold', 'Sold': 'sold', 'Deed Signed': 'sold'}   # workbook -> site (3 colours)
SIDE = {'W': 'West', 'E': 'East', 'N': 'North', 'S': 'South'}
num = lambda v: None if v in (None, 'n/a', '') else (round(float(v), 2) if isinstance(v, (int, float)) else v)
code = lambda u: (u.get('code') or '').replace('+', '')
side = lambda u: SIDE.get((u.get('aspect') or 'X')[0], '?')          # main facade of the home (WSW -> West ...)

inv = collections.defaultdict(list)
wb = openpyxl.load_workbook(XL, data_only=True)
for ws in wb:
    if not ws.title.startswith('Block'): continue
    H = [c.value for c in ws[1]]; ix = {h: i for i, h in enumerate(H)}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[ix['Unit Code']]: continue
        g = lambda h: r[ix[h]] if h in ix else None
        inv[(g('Block'), int(g('Floor')))].append({
            'orig': str(g('Original Unit Code')).split(' - ')[0].strip(), 'code': g('Unit Code'), 'block': g('Block'),
            'status': g('Status') or 'Available', 'typology': g('Typology'), 'duplex': g('Duplex?') == 'Yes',
            'gross': num(g('Rough / Gross Area (m²)')), 'living': num(g('Living Area (m²)')),
            'balc_ext': num(g('Balcony Ext (m²)')), 'balc_int': num(g('Balcony Int (m²)')), 'terrace': num(g('Terrace / Roof (m²)')),
            'outdoor': num(g('Total Outdoor (m²)')), 'total': num(g('Total Area incl. Outdoor (m²)')),
            'parking': num(g('Parking Slots (#)')), 'parking_id': g('Parking ID(s) (Level -1)'),
            'orientation': g('Orientation / View'), 'price': num(g('List Price (€)'))})

D = json.load(open(f'{SITE}/data.json')); miss = []; linked = 0
for t, blocks in TOWER_BLOCKS.items():
    for f in sorted({u['floor'] for u in D['units'] if u['tower'] == t}):
        ring = sorted([u for u in D['units'] if u['tower'] == t and u['floor'] == f], key=lambda u: u['n'])
        segs = [inv[(b, f)] for b in blocks]; sizes = [len(s) for s in segs]
        assert sum(sizes) == len(ring), (t, f, sizes, len(ring))
        best = None
        for rot in range(len(ring)):
            r = ring[rot:] + ring[:rot]; parts, k = [], 0
            for n in sizes: parts.append(r[k:k + n]); k += n
            ok = sum(sum((collections.Counter(code(u) for u in p) & collections.Counter(x['orig'] for x in s)).values()) for p, s in zip(parts, segs))
            ok += .01 * sum(sum((collections.Counter(side(u) for u in p) & collections.Counter((x['orientation'] or '').split()[0] for x in s)).values()) for p, s in zip(parts, segs))
            if best is None or ok > best[0]: best = (ok, parts)
        ok, parts = best
        for p, s in zip(parts, segs):
            pool = list(s)
            for u in p:      # same code and same facade side first, then same code, then whatever is left in this sales block
                m = (next((x for x in pool if x['orig'] == code(u) and (x['orientation'] or '').split()[0] == side(u)), None)
                     or next((x for x in pool if x['orig'] == code(u)), None) or (pool[0] if pool else None))
                if m is None: continue
                pool.remove(m); u['inv'] = m; linked += 1
                u['status'] = STATUS.get(m['status'], 'available'); u['price'] = m['price']   # what the site's status colours and summaries read
                if m['orig'] != code(u): miss.append(f"{u['id']} {u.get('code')}->{m['orig']}")
        print(t, f, 'homes', len(ring), 'code matches', int(ok), 'facade matches', round((ok - int(ok)) * 100))

json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
T0 = '<script id="manifest" type="application/json">'          # keep the manifest embedded in index.html identical
s = open(f'{SITE}/index.html').read(); a = s.index(T0) + len(T0); b = s.index('</script>', a)
open(f'{SITE}/index.html', 'w').write(s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s[b:])
print('linked', linked, 'of', len(D['units']), 'code mismatches', len(miss), miss[:10])
print('status', collections.Counter(u['inv']['status'] for u in D['units'] if 'inv' in u), 'priced', sum(bool(u.get('inv', {}).get('price')) for u in D['units']))
