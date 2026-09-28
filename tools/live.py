"""Higgsfield clips (studio render + AI motion) -> seamless web loops in site/media/gallery/live_NN.mp4,
QC against the source render, and link them in gallery.json + data.json.
usage: python3 live.py NN=url [NN=url ...]"""
import sys, json, subprocess, os
import numpy as np
from PIL import Image
SITE = '/home/claude/aksa/site'; HF = '/home/claude/aksa/hf'; T = '/home/claude/aksa/tools'
def run(*a): subprocess.run(a, check=True, capture_output=True)
done = {}
for arg in sys.argv[1:]:
    n, url = arg.split('=', 1)
    raw = f'{HF}/raw_{n}.mp4'
    if not os.path.exists(raw): run('curl', '-sS', '-o', raw, url)
    if os.path.exists(f'{SITE}/media/gallery/live_{n}.mp4') and url == 'x': pass
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw], capture_output=True, text=True).stdout)
    # QC: last frame vs the studio render (architecture must not drift)
    run('ffmpeg', '-v', 'error', '-y', '-sseof', '-0.1', '-i', raw, '-frames:v', '1', f'{HF}/last_{n}.jpg')
    a = np.asarray(Image.open(f'{SITE}/media/gallery/render_{n}.jpg').convert('L').resize((480, 270)), float)
    b = np.asarray(Image.open(f'{HF}/last_{n}.jpg').convert('L').resize((480, 270)), float)
    diff = abs(a - b).mean()
    D = 1.0; out = f'{SITE}/media/gallery/live_{n}.mp4'
    fc = (f'[0:v]split[x][y];[x]trim=start={D},setpts=PTS-STARTPTS[a];[y]trim=0:{D},setpts=PTS-STARTPTS[b];'
          f'[a][b]xfade=transition=fade:duration={D}:offset={dur-2*D:.3f},scale=1280:720:flags=lanczos,format=yuv420p')
    run('ffmpeg', '-v', 'error', '-y', '-i', raw, '-filter_complex', fc, '-c:v', 'libx264', '-crf', '25', '-preset', 'slow',
        '-movflags', '+faststart', '-an', out)
    im = np.asarray(Image.open(f'{SITE}/media/gallery/render_{n}.jpg').convert('RGB').resize((320, 180)), float)
    white = ((im.min(2) > 200) & (im.max(2) - im.min(2) < 30)).astype(float)   # white facades -> where the buildings are
    col = white.sum(0); fx = float((col * np.arange(320)).sum() / max(col.sum(), 1) / 320) if col.sum() > 50 else .5
    FX = {'02': .58}   # manual focus where other white massing pulls the estimate off our blocks
    done[n] = (f'media/gallery/live_{n}.mp4', FX.get(n, round(min(.85, max(.15, fx)), 3)))
    print(n, 'diff vs render %.1f' % diff, 'size %.1f MB' % (os.path.getsize(out) / 1e6))
for f in [f'{T}/gallery.json']:
    g = json.load(open(f))
    for it in g:
        n = it['image'][-6:-4]
        if n in done: it['video'], it['fx'] = done[n]
    json.dump(g, open(f, 'w'), indent=1, ensure_ascii=False)
D_ = json.load(open(f'{SITE}/data.json'))
for it in D_['gallery']['items']:
    n = it['image'][-6:-4]
    if n in done: it['video'], it['fx'] = done[n]
json.dump(D_, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('linked', sorted(done))
