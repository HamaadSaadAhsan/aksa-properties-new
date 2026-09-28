"""AI-rendered 360 aerial: for each 3D angle, an AI photoreal still (made from our 3D still, same camera) animated with a
locked camera (cars, people, trees).  Outlines and pins are the 3D ones (same camera).  -> D['aiReel'] + media/mp/ai_*.
usage: python3 build_ai.py 000=url 045=url ...   (video urls; stills taken from hf/st/s_XXX.png)"""
import sys, os, json, subprocess
from PIL import Image
SITE = '/home/claude/aksa/site'; ST = '/home/claude/aksa/hf/st'
def run(*a): subprocess.run(a, check=True, capture_output=True)
urls = dict(a.split('=', 1) for a in sys.argv[1:])
for a, u in urls.items():
    raw = f'{ST}/v_{a}.mp4'
    if not os.path.exists(raw): run('curl', '-sS', '-o', raw, u)
    Image.open(f'{ST}/s_{a}.png').convert('RGB').resize((1280, 720), Image.LANCZOS).save(f'{SITE}/media/mp/ai_{a}.jpg', quality=86, optimize=True, progressive=True)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw], capture_output=True, text=True).stdout)
    D = 1.0
    fc = (f'[0:v]split[x][y];[x]trim=start={D},setpts=PTS-STARTPTS[a];[y]trim=0:{D},setpts=PTS-STARTPTS[b];'
          f'[a][b]xfade=transition=fade:duration={D}:offset={dur-2*D:.3f},scale=1280:720:flags=lanczos,format=yuv420p')
    run('ffmpeg', '-v', 'error', '-y', '-i', raw, '-filter_complex', fc, '-c:v', 'libx264', '-crf', '24', '-preset', 'slow', '-movflags', '+faststart', '-an', f'{SITE}/media/mp/ai_{a}_loop.mp4')
    print(a, 'ok')
Dj = json.load(open(f'{SITE}/data.json'))
mp = Dj['masterplan']
have = {a for a in [x['id'] for x in mp['angles']] if os.path.exists(f'{SITE}/media/mp/ai_{a}_loop.mp4')}
angles = []
for x in mp['angles']:
    if x['id'] not in have: continue
    y = dict(x); y['still'] = f'media/mp/ai_{x["id"]}.jpg'; y['loop'] = f'media/mp/ai_{x["id"]}_loop.mp4'
    y['label'] = x['label'].replace('Aerial', 'Aerial 360°'); angles.append(y)
Dj['aiReel'] = {'viewBox': mp['viewBox'], 'start': mp['start'], 'angles': angles, 'ai': True}
json.dump(Dj, open(f'{SITE}/data.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('aiReel', [a['id'] for a in angles])
