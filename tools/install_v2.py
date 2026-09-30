"""Sept 2026 re-render (real surroundings + 4-pool courtyards): AI photoreal stills for the 8 aerial and 8 close-up angles,
new 3D stills, masterplan pins from the new meta; AI loops only where a new clip exists (hf/st/v2_XXX.mp4)."""
import json, os, subprocess
from PIL import Image
SITE = '/home/claude/aksa/site'; V2 = '/home/claude/aksa/hf/v2'; ST = '/home/claude/aksa/hf/st'; OUT = '/home/claude/aksa/tools/out'
ANG = [f'{a:03d}' for a in range(0, 360, 45)]
def run(*a): subprocess.run(a, check=True, capture_output=True)
for a in ANG:
    Image.open(f'{V2}/ai_close_{a}.png').convert('RGB').resize((2400, 1350), Image.LANCZOS).save(f'{SITE}/media/close/close_{a}.jpg', quality=84, optimize=True, progressive=True)
    Image.open(f'{V2}/ai_angle_{a}.png').convert('RGB').save(f'{ST}/s_{a}.png')
    Image.open(f'{V2}/ai_angle_{a}.png').convert('RGB').resize((1920, 1080), Image.LANCZOS).save(f'{SITE}/media/mp/ai_{a}.jpg', quality=85, optimize=True, progressive=True)
    Image.open(f'{OUT}/stills/angle_{a}.jpg').save(f'{SITE}/media/mp/angle_{a}.jpg', quality=86)
    raw = f'{ST}/v2_{a}.mp4'
    if os.path.exists(raw):
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw], capture_output=True, text=True).stdout); D = 1.0
        fc = (f'[0:v]split[x][y];[x]trim=start={D},setpts=PTS-STARTPTS[a];[y]trim=0:{D},setpts=PTS-STARTPTS[b];'
              f'[a][b]xfade=transition=fade:duration={D}:offset={dur-2*D:.3f},scale=1280:720:flags=lanczos,format=yuv420p')
        run('ffmpeg', '-v', 'error', '-y', '-i', raw, '-filter_complex', fc, '-c:v', 'libx264', '-crf', '24', '-preset', 'slow', '-movflags', '+faststart', '-an', f'{SITE}/media/mp/ai2_{a}_loop.mp4')
D = json.load(open(f'{SITE}/data.json')); meta = json.load(open(f'{OUT}/meta.json'))
for x in D['masterplan']['angles']:
    am = []
    for m in meta['markers'][str(int(x['id']))]['__amen']:
        if not m['visible'] or m['id'] in ('pergola', 'play') or any(q['id'] == m['id'] for q in am): continue
        am.append({'id': m['id'], 'x': round(m['x'], 1), 'y': round(m['y'], 1)})
    x['amenities'] = am; x['loop'] = None      # the old 3D loops show the old scene
angles = []
for x in D['masterplan']['angles']:
    y = dict(x); y['still'] = f'media/mp/ai_{x["id"]}.jpg'
    y['loop'] = f'media/mp/ai2_{x["id"]}_loop.mp4' if os.path.exists(f'{SITE}/media/mp/ai2_{x["id"]}_loop.mp4') else None
    y['label'] = x['label'].replace('Aerial', 'Aerial 360°'); angles.append(y)
import glob
TR = {}
for f in glob.glob(f'{SITE}/media/mp/ai_trans_*.mp4'):
    a, b = os.path.basename(f)[9:-4].split('-'); TR[f'{a}>{b}'] = 'media/mp/' + os.path.basename(f)
D['aiReel'] = {'trans': TR, 'viewBox': D['masterplan']['viewBox'], 'start': '045',   # 045: the AI view closest to the studio renders
                 'angles': angles, 'ai': True}
D['close']['fly'] = {}; D['close'].pop('transition', None); D['masterplan'].pop('transition', None)   # old-scene rotation clips                               # fly clips show the old scene; close-ups cross-fade instead
json.dump(D, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('aiReel', [(a['id'], bool(a['loop'])) for a in angles], 'start', D['masterplan']['start'])
