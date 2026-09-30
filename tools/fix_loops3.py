"""Post-process the stabilised v3 loops (hf/st/v2_XXX.mp4): map 045/180 onto their unwarped stills and cover the thin
alignment border slivers with the final still, so the loop matches the still pixel for pixel at the edges."""
import json, os, subprocess, sys, cv2, numpy as np
FIN = '/home/claude/aksa/hf/v3/final'; ST = '/home/claude/aksa/hf/st'
CORR = json.load(open(f'{FIN}/corr.json'))
for a in sys.argv[1:]:
    src = f'{ST}/v2_{a}.mp4'; tmp = f'{ST}/v2_{a}_fix.mp4'
    cap = cv2.VideoCapture(src); fps = cap.get(cv2.CAP_PROP_FPS); W, H = int(cap.get(3)), int(cap.get(4))
    D = np.diag([W / 2688, H / 1520, 1.0]); Hm = D @ np.array(CORR.get(a, np.eye(3).tolist())) @ np.linalg.inv(D)
    s = cv2.resize(cv2.imread(f'{FIN}/mp_{a}.png'), (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)
    hp = f'{FIN}/mp_{a}_hole.png'
    m = cv2.GaussianBlur((cv2.resize(cv2.imread(hp, 0), (W, H)) > 0).astype(np.float32), (0, 0), 4)[..., None] if os.path.exists(hp) else None
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.warpPerspective(f, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        if m is not None: g = g * (1 - m) + s * m
        p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait(); os.replace(tmp, src); print('fixed', a)
