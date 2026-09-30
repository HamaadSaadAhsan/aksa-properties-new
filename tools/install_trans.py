"""Install Magnific Kling 3.0 orbit clips (30 Sept 2026) as per-pair rotation transitions.
Each raw clip a->b is encoded forward and reversed (b->a). The first 0.2s blend in from still a and the
last 0.25s blend into still b, so the clip starts and ends exactly on the stills shown on the site."""
import glob, os, subprocess
from concurrent.futures import ThreadPoolExecutor
MG = '/home/claude/aksa/hf/mg'; SITE = '/home/claude/aksa/site'
SETS = {'mp': ('media/mp/ai_{}.jpg', 'media/mp/ai_trans_{}-{}.mp4'),
        'cl': ('media/close/close_{}.jpg', 'media/close/ai_ctrans_{}-{}.mp4')}
def enc(raw, sa, sb, out, rev):
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw],
                               capture_output=True, text=True).stdout)
    v = '[0:v]' + ('reverse,' if rev else '') + 'scale=1280:720:flags=lanczos,setsar=1,format=yuv420p[v]'
    fc = (f'{v};[1:v]scale=1280:720,format=yuv420p,fade=t=out:st=0:d=0.2:alpha=1[a];'
          f'[2:v]scale=1280:720,format=yuv420p,fade=t=in:st={dur-0.25:.3f}:d=0.25:alpha=1[b];'
          f'[v][a]overlay=format=auto:shortest=1[va];[va][b]overlay=format=auto:shortest=1,format=yuv420p')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw,
                    '-loop', '1', '-t', f'{dur}', '-framerate', '24', '-i', f'{SITE}/{sa}',
                    '-loop', '1', '-t', f'{dur}', '-framerate', '24', '-i', f'{SITE}/{sb}',
                    '-filter_complex', fc, '-r', '24', '-c:v', 'libx264', '-crf', '24', '-preset', 'slow',
                    '-movflags', '+faststart', '-an', f'{SITE}/{out}'], check=True)
    return out
jobs = []
for k, (st, tr) in SETS.items():
    for raw in sorted(glob.glob(f'{MG}/{k}_*-*.mp4')):
        a, b = os.path.basename(raw)[len(k) + 1:-4].split('-')
        jobs.append((raw, st.format(a), st.format(b), tr.format(a, b), False))
        jobs.append((raw, st.format(b), st.format(a), tr.format(b, a), True))
with ThreadPoolExecutor(4) as ex:
    for o in ex.map(lambda j: enc(*j), jobs): print(o)
