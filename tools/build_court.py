"""Sept 2026 courtyard design: add the architect's 3 new courtyard renders, retire the single-pool courtyard renders (14-22)
from the gallery, amenities and Real views, and update the amenity facts."""
import json, shutil
from PIL import Image
SITE = '/home/claude/aksa/site'; G = f'{SITE}/media/gallery'; UP = '/root/.claude/uploads/a27dce96-3c55-5f10-acbe-1a88accc15fc'
NEW = [(29, '50979328-image.png', 'Courtyard from above: four lot gardens around four pools'),
       (30, 'fc4defc5-image.png', 'Courtyard: four pools, pergolas and play areas'),
       (31, '2618394c-image.png', 'One lot with its own garden and pool (cut-away view)')]
OLD = set(range(14, 23))
items = []
for n, f, cap in NEW:
    im = Image.open(f'{UP}/{f}').convert('RGB'); im.save(f'{G}/render_{n}.jpg', quality=88, optimize=True, progressive=True)
    t = im.copy(); t.thumbnail((520, 364)); t.save(f'{G}/thumb_render_{n}.jpg', quality=82)
    items.append({'image': f'media/gallery/render_{n}.jpg', 'thumb': f'media/gallery/thumb_render_{n}.jpg', 'cat': 'courtyard', 'caption': cap, 'w': im.width, 'h': im.height})
num = lambda it: int(it['image'][-6:-4])
def fix(lst):
    out = [it for it in lst if not (it['image'].startswith('media/gallery/render_') and num(it) in OLD) and not (it['image'].startswith('media/gallery/render_') and num(it) in (29, 30, 31))]
    i = next((k for k, it in enumerate(out) if it.get('cat') == 'commercial'), len(out)); return out[:i] + items + out[i:]
g = json.load(open('/home/claude/aksa/tools/gallery.json')); g = fix(g); json.dump(g, open('/home/claude/aksa/tools/gallery.json', 'w'), indent=1, ensure_ascii=False)
D = json.load(open(f'{SITE}/data.json')); D['gallery']['items'] = fix(D['gallery']['items'])
P = {n: {k: it[k] for k in ('image', 'thumb', 'caption', 'w', 'h')} for n, it in zip((29, 30, 31), items)}
UPD = {'pool': ('8 · four in each courtyard', 'Each courtyard is split into four lot gardens; each lot has its own pool, about 4.4 × 6.3 m, grouped at the centre with sun decks at both ends.', [30, 29, 31]),
       'pergola': ('8 · two timber, two louvred in each courtyard', 'Each lot garden has a pergola: timber pergolas in two, white louvred pergolas in the other two.', [30, 29]),
       'play': ('4 · two in each courtyard', 'Play areas with play towers and slides in two of the lot gardens of each courtyard, plus outdoor fitness stations.', [29, 30]),
       'gardens': ('2 × about 1,250 m², four lot gardens each', 'Each courtyard garden (about 51 × 25 m) is divided into four private lot gardens with lawns, stepping-stone paths, hedges and trees.', [29, 31, 30])}
for a in D['amenities']:
    if a['id'] in UPD:
        a['fact'], a['text'], ims = UPD[a['id']]; a['photos'] = [P[i] for i in ims]
if 'realReel' in D: D['realReel']['angles'] = [x for x in D['realReel']['angles'] if int(x['id']) not in OLD]
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('gallery', len(D['gallery']['items']), 'real views', len(D['realReel']['angles']))
