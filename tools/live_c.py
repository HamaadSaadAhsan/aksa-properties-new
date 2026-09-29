"""Commercial-corrected aerials 01-03: AI still (hf/cm/c_NN.png) + Kling clip -> gallery/aerial_NN.jpg, thumb, live_aerial_NN.mp4;
repoint gallery items 01-03 (gallery.json + data.json). usage: python3 live_c.py NN=url ..."""
import sys, json, subprocess, os
import numpy as np
from PIL import Image
SITE = '/home/claude/aksa/site'; CM = '/home/claude/aksa/hf/cm'; G = f'{SITE}/media/gallery'
def run(*a): subprocess.run(a, check=True, capture_output=True)
done = {}
for arg in sys.argv[1:]:
    n, url = arg.split('=', 1); raw = f'{CM}/raw_{n}.mp4'
    if not os.path.exists(raw): run('curl', '-sS', '-o', raw, url)
    im = Image.open(f'{CM}/c_{n}.png').convert('RGB').resize((1599, 899), Image.LANCZOS)
    im.save(f'{G}/aerial_{n}.jpg', quality=88, optimize=True, progressive=True)
    t = Image.open(f'{G}/thumb_render_{n}.jpg'); im.resize(t.size, Image.LANCZOS).save(f'{G}/thumb_aerial_{n}.jpg', quality=82)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw], capture_output=True, text=True).stdout)
    ref = np.asarray(im.convert('L').resize((480, 270)), float)
    for tag, ss in (('first', ['-ss', '0']), ('last', ['-sseof', '-0.1'])):
        run('ffmpeg', '-v', 'error', '-y', *ss, '-i', raw, '-frames:v', '1', f'{CM}/{tag}_{n}.jpg')
        b = np.asarray(Image.open(f'{CM}/{tag}_{n}.jpg').convert('L').resize((480, 270)), float)
        print(n, tag, 'diff %.1f' % abs(ref - b).mean())
    D = 1.0; out = f'{G}/live_aerial_{n}.mp4'
    fc = (f'[0:v]split[x][y];[x]trim=start={D},setpts=PTS-STARTPTS[a];[y]trim=0:{D},setpts=PTS-STARTPTS[b];'
          f'[a][b]xfade=transition=fade:duration={D}:offset={dur-2*D:.3f},scale=1280:720:flags=lanczos,format=yuv420p')
    run('ffmpeg', '-v', 'error', '-y', '-i', raw, '-filter_complex', fc, '-c:v', 'libx264', '-crf', '25', '-preset', 'slow', '-movflags', '+faststart', '-an', out)
    print(n, 'size %.1f MB' % (os.path.getsize(out) / 1e6))
    done[n] = {'image': f'media/gallery/aerial_{n}.jpg', 'thumb': f'media/gallery/thumb_aerial_{n}.jpg', 'video': f'media/gallery/live_aerial_{n}.mp4',
               'edit': 'updated with AI: commercial building from the design renders, neighbouring buildings as they stand today, four-pool courtyards'}
def patch(items):
    for it in items:
        n = it['image'][-6:-4]
        if n in done: it.update(done[n])
g = json.load(open('/home/claude/aksa/tools/gallery.json')); patch(g); json.dump(g, open('/home/claude/aksa/tools/gallery.json', 'w'), indent=1, ensure_ascii=False)
D_ = json.load(open(f'{SITE}/data.json')); patch(D_['gallery']['items']); json.dump(D_, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('linked', sorted(done))
