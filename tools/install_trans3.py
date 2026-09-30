"""30 Sept 2026 (v3 stills, identical buildings on every angle): encode the Magnific Kling 3.0 orbit clips as per-pair
rotation transitions, forward and reversed. Per frame:
  * a homography correction, interpolated from the start angle's to the end angle's, maps the keyframe geometry onto the
    final still (only 045 and 180 aerial differ: those stills are used unwarped);
  * the thin border slivers left by aligning the stills to the 3D camera are covered with the still near each end;
  * the first 0.2 s blend in from the start still and the last 0.25 s into the end still.
"""
import glob, json, os, subprocess, cv2, numpy as np
from concurrent.futures import ThreadPoolExecutor
MG = '/home/claude/aksa/hf/mg3'; FIN = '/home/claude/aksa/hf/v3/final'; SITE = '/home/claude/aksa/site'
W, H = 1280, 720
CORR = {('mp', a): np.array(m) for a, m in json.load(open(f'{FIN}/corr.json')).items()}
D = np.diag([W / 2688, H / 1520, 1.0])
OUT = {'mp': 'media/mp/ai_trans_{}-{}.mp4', 'cl': 'media/close/ai_ctrans_{}-{}.mp4'}
cache = {}
def still(k, a):
    if (k, a) not in cache:
        s = cv2.resize(cv2.imread(f'{FIN}/{k}_{a}.png'), (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)
        hp = f'{FIN}/{k}_{a}_hole.png'
        m = cv2.resize(cv2.imread(hp, 0), (W, H)) if os.path.exists(hp) else np.zeros((H, W), np.uint8)
        m = cv2.GaussianBlur((m > 0).astype(np.float32), (0, 0), 4)[..., None]
        cache[(k, a)] = (s, m)
    return cache[(k, a)]
def corr(k, a):
    M = CORR.get((k, a), np.eye(3)); return D @ M @ np.linalg.inv(D)
def enc(k, a, b, rev):
    raw = f'{MG}/{k}_{a}-{b}.mp4' if not rev else f'{MG}/{k}_{b}-{a}.mp4'
    cap = cv2.VideoCapture(raw); fps = cap.get(cv2.CAP_PROP_FPS) or 24; fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA))
    if rev: fr = fr[::-1]
    n = len(fr); (sa, ma), (sb, mb) = still(k, a), still(k, b); Ha, Hb = corr(k, a), corr(k, b)
    out = SITE + '/' + OUT[k].format(a, b)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-crf', '24', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', out],
                         stdin=subprocess.PIPE)
    fa, fb = int(round(.2 * fps)), int(round(.25 * fps))
    for i, f in enumerate(fr):
        t = i / (n - 1); Hm = (1 - t) * Ha + t * Hb; Hm /= Hm[2, 2]
        g = cv2.warpPerspective(f, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        wa, wb = max(0., 1 - t / .4), max(0., 1 - (1 - t) / .4)          # cover border slivers near each end
        g = g * (1 - ma * wa) + sa * ma * wa; g = g * (1 - mb * wb) + sb * mb * wb
        if i < fa: x = i / fa; g = sa * (1 - x) + g * x
        if i >= n - fb: x = (i - (n - fb) + 1) / fb; g = g * (1 - x) + sb * x
        p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait(); return out
jobs = []
for raw in sorted(glob.glob(f'{MG}/[mc][pl]_*-*.mp4')):
    k = os.path.basename(raw)[:2]; a, b = os.path.basename(raw)[3:-4].split('-')
    jobs += [(k, a, b, False), (k, b, a, True)]
with ThreadPoolExecutor(2) as ex:
    for o in ex.map(lambda j: enc(*j), jobs): print(o, flush=True)
