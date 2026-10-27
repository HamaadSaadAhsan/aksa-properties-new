"""Per-home plan images for the floor plan dialog: the architect's floor PDF (vector, 1:100) rendered at high resolution and
cropped to the home's outline (data.json units[].poly, metres in the plan viewBox) plus a margin, red axis lines removed.
One image per sheet and home position (N and S blocks share the sheet; levels 2 and 3 share one drawing).
The site derives each image's path and box from the unit (index.src.html unitBox / unitImg), so UM must match there.
usage: python3 unit_plans.py <dir with the architect PDFs> <site dir> [px per metre]"""
import json, sys, os, fitz, numpy as np
from PIL import Image, ImageFilter
SRC, SITE = sys.argv[1], sys.argv[2]
PXM = float(sys.argv[3]) if len(sys.argv) > 3 else 100
UM = 2.2                                                          # margin around the home (m)
X0, Y0 = 186 / 20, 106 / 20                                       # plan viewBox origin on the sheet (m), build_plans.py crop
PT = 72 / 2.54                                                    # pt per metre at 1:100
SHEET = {0: '03 R_Chão', 1: '04 Piso 1', 2: '05 Piso 2 e 3', 3: '05 Piso 2 e 3', 4: '06 Piso 4'}
D = json.load(open(f'{SITE}/data.json')); OUT = f'{SITE}/media/plans/units'; os.makedirs(OUT, exist_ok=True)
docs, done = {}, {}
for u in D['units']:
    f = u['floor']; slug = os.path.basename(D['plans'][f"{u['tower']}:{f}"]['image']).rsplit('.', 1)[0]
    name = f'{slug}_{u["n"]:02d}.jpg'
    xs, ys = [p[0] for p in u['poly']], [p[1] for p in u['poly']]
    b = (round(min(xs) - UM, 2), round(min(ys) - UM, 2), round(max(xs) + UM, 2), round(max(ys) + UM, 2))
    if name in done:
        assert done[name] == b, (u['id'], name, 'same position, different outline'); continue
    done[name] = b
    doc = docs.setdefault(f, fitz.open(f'{SRC}/{SHEET[f]}.pdf'))
    clip = fitz.Rect((b[0] + X0) * PT, (b[1] + Y0) * PT, (b[2] + X0) * PT, (b[3] + Y0) * PT)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(PXM / PT, PXM / PT), clip=clip, alpha=False)
    im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    a = np.asarray(im).astype(int); r, g, bl = a[..., 0], a[..., 1], a[..., 2]
    red = Image.fromarray(((r - g > 50) & (r - bl > 50)).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(7))
    med = im.filter(ImageFilter.MedianFilter(15))                # thin lines: the window's median is the ground under them
    im.paste(med, mask=red)
    im.save(f'{OUT}/{name}', quality=78, optimize=True, progressive=True)
print(len(done), 'images', sum(os.path.getsize(f'{OUT}/{n}') for n in done) // 1024, 'KB')
