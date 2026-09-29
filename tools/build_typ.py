"""Join the client's typology table (Detailed Table AKSA Residencia 320.xlsx) onto the units.
Designation codes come from the architect's floor plans (fração letter -> code, e.g. F -> A1C);
table rows are matched by code. The table's Block B rows A-C repeat Block A's figures, so a table row
is only used where its livable area agrees with the drawing (within 3 m2); drawing types/areas are kept."""
import json, re, openpyxl
SITE = '/home/claude/aksa/site'; ARCH = '/home/claude/aksa/arch'
X = '/home/claude/aksa/typ/Table of Typologies /Detailed Table AKSA Residencia 320.xlsx'
raw = json.load(open(f'{ARCH}/units_raw.json'))
code_of = {}   # (floor, frac) -> code
for dwg, rows in raw.items():
    floors = [0] if 'R_Cha' in dwg else [1] if 'Piso_1' in dwg else [2, 3] if 'Piso_2' in dwg else [4] if 'Piso_4' in dwg else []
    for c, t, a, frac, side in rows:
        for f in floors: code_of.setdefault((f, frac), c[0] + str(f) + c[2:])
ws = openpyxl.load_workbook(X, data_only=True)['320 AKSA Residencia']
T = {}
for r0, r1 in ((10, 31), (37, 64)):          # Lote 1 block A rows, block B rows (all 8 lots are identical)
    floor = None; r = r0
    while r < r1:
        v = [ws.cell(r, c).value for c in range(3, 12)]   # C..K
        if isinstance(v[0], int): floor = v[0]
        typ, code = v[1], v[8]
        if code and typ and typ != 'Storage':
            code = re.sub(r'\s', '', str(code)); nxt = [ws.cell(r + 1, c).value for c in range(3, 12)]
            row = {'type': typ.strip(), 'm2': v[7], 'balc': round((v[4] or 0) + (v[5] or 0), 2), 'parking': v[2], 'pm2': v[3]}
            if typ.strip().endswith('Duplex') and nxt[1] == 'Storage':
                row.update(upper=nxt[7], terrace=nxt[6], store=nxt[2], pm2=round((v[3] or 0) + (nxt[3] or 0), 2) or None); r += 1
            T[code] = row
        r += 1
D = json.load(open(f'{SITE}/data.json')); used = skipped = 0; nocode = 0
for u in D['units']:
    for k in ('code', 'duplex', 'upper', 'terrace', 'balc', 'parking'): u.pop(k, None)
    c = code_of.get((u['floor'], u['frac']))
    if not c: nocode += 1; continue
    tc = c[:2] + '+' + c[2:] if u['floor'] == 4 else c
    u['code'] = tc; u['bld'] = c[0]
    if u['floor'] == 4: u['duplex'] = True
    t = T.get(tc)
    if t and abs(t['m2'] - u['m2']) < 3:
        used += 1
        if t['balc']: u['balc'] = t['balc']
        if t.get('upper'): u['upper'] = t['upper']
        if t.get('terrace'): u['terrace'] = t['terrace']
        p = t['parking']; u['parking'] = 2 if p == 2 or (isinstance(p, str) and '/' in p) else 1
    elif t: skipped += 1
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
json.dump(T, open('/home/claude/aksa/typ/table.json', 'w'), indent=1, ensure_ascii=False)
import collections
print('table rows', len(T), 'units with code', sum('code' in u for u in D['units']), 'no code', nocode, 'table used', used, 'skipped (area mismatch)', skipped)
print(collections.Counter((u.get('bld'), u['type'] + (' duplex' if u.get('duplex') else '')) for u in D['units']))
