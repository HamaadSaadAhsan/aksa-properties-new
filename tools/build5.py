"""30 Sept 2026: every aerial and close-up view rendered from the one 3D model (render5.html), no AI images or AI video.
Frames from the render run (out/stills, out/masks, out/frames) -> site media + data.json + the manifest inside index.html.
usage: python3 build5.py <render_out_dir> <site_dir>"""
import json, os, glob, shutil, subprocess, sys
import numpy as np, cv2
from PIL import Image

OUT, SITE = sys.argv[1], sys.argv[2]
MED = f'{SITE}/media'
ANG = [f'{a:03d}' for a in range(0, 360, 45)]
NXT = {a: ANG[(i + 1) % 8] for i, a in enumerate(ANG)}
ENC = ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23', '-preset', 'slow', '-movflags', '+faststart', '-an']
FF = os.environ.get('FFMPEG', 'ffmpeg')

def sh(*a): subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def enc(frames, dst, fps=24): sh(FF, '-y', '-framerate', str(fps), '-i', f'{frames}/%03d.jpg', *ENC, dst)
def rev(src, dst): sh(FF, '-y', '-i', src, '-vf', 'reverse', *ENC, dst)

# ---------- stills and clips ----------
fly = {}
for a in ANG:
    b = NXT[a]
    Image.open(f'{OUT}/stills/angle_{a}.jpg').save(f'{MED}/mp/angle_{a}.jpg', quality=86, optimize=True, progressive=True)
    Image.open(f'{OUT}/stills/close_{a}.jpg').save(f'{MED}/close/close_{a}.jpg', quality=84, optimize=True, progressive=True)
    enc(f'{OUT}/frames/trans_{a}-{b}', f'{MED}/mp/trans_{a}-{b}.mp4'); rev(f'{MED}/mp/trans_{a}-{b}.mp4', f'{MED}/mp/trans_{b}-{a}.mp4')
    enc(f'{OUT}/frames/ctrans_{a}-{b}', f'{MED}/close/trans_{a}-{b}.mp4'); rev(f'{MED}/close/trans_{a}-{b}.mp4', f'{MED}/close/trans_{b}-{a}.mp4')
    enc(f'{OUT}/frames/fly_{a}-close', f'{MED}/close/fly_{a}-close.mp4'); rev(f'{MED}/close/fly_{a}-close.mp4', f'{MED}/close/fly_close-{a}.mp4')
    fly[a] = {'in': f'media/close/fly_{a}-close.mp4', 'out': f'media/close/fly_close-{a}.mp4'}

# ---------- outlines traced from the ID masks (same method as build4.py) ----------
def trace(binary, eps, min_area):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)
    cs, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True).reshape(-1, 2).tolist() for c in cs if cv2.contourArea(c) >= min_area]

D = json.load(open(f'{SITE}/data.json'))
MP = D['masterplan']
for x in MP['angles']:
    m = np.array(Image.open(f'{OUT}/masks/angle_{x["id"]}_id.png').convert('RGB'))
    res = ((m[:, :, 0] > 200) & (m[:, :, 1] < 50)).astype(np.uint8) * 255
    com = ((m[:, :, 1] > 200) & (m[:, :, 0] < 50)).astype(np.uint8) * 255
    outl = [{'id': 'aksa', 'label': 'AKSA Residencies', 'target': 'close', 'polys': trace(res, 1.2, 300)}]
    cp = trace(com, 1.2, 150)
    if cp: outl.append({'id': 'commercial', 'label': 'Commercial building', 'target': 'gallery:commercial', 'polys': cp})
    x['outlines'] = outl; x['still'] = f'media/mp/angle_{x["id"]}.jpg'; x['loop'] = None
MP['start'] = '000'; MP['transition'] = 'media/mp/trans_{from}-{to}.mp4'; MP.pop('trans', None); MP.pop('ai', None)

TOW = D['towers']; C = D['close']
for x in C['angles']:
    cm = np.array(Image.open(f'{OUT}/masks/close_{x["id"]}_id.png').convert('RGB'))
    fl = []
    for t, T in enumerate(TOW):
        for f in range(T['floors']):
            b = ((cm[:, :, 0] == 40 + t * 80) & (cm[:, :, 1] == 10 + f * 8) & (cm[:, :, 2] == 200)).astype(np.uint8) * 255
            if b.sum() == 0: continue
            polys = trace(b, 1.6, 150)
            if polys: fl.append({'tower': T['id'], 'floor': f, 'polys': polys})
    x['floors'] = fl; x['still'] = f'media/close/close_{x["id"]}.jpg'
C['transition'] = 'media/close/trans_{from}-{to}.mp4'; C['trans'] = {}; C['fly'] = fly
D.pop('aiReel', None)                    # the AI aerial reel redrew the building differently at each angle
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)

# the page falls back to the manifest embedded in index.html, so keep it identical to data.json
T0 = '<script id="manifest" type="application/json">'
s = open(f'{SITE}/index.html').read(); a = s.index(T0) + len(T0); b = s.index('</script>', a)
s = s[:a] + json.dumps(D, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s[b:]
open(f'{SITE}/index.html', 'w').write(s)

# the AI media is no longer referenced
gone = [f for p in ('mp/ai_*', 'mp/ai2_*', 'close/ai_ctrans_*', 'mp/angle_*_loop.mp4') for f in glob.glob(f'{MED}/{p}')]
for f in gone: os.remove(f)
print('outlines', [[len(o['polys']) for o in x['outlines']] for x in MP['angles']])
print('floors per close angle', [len(x['floors']) for x in C['angles']], 'removed', len(gone), 'files')
