"""Lock a drifting AI clip to its still: per-frame homography (ORB+RANSAC) onto the still, gaps filled from the still.
usage: python3 stab.py raw.mp4 still.png out.mp4"""
import sys, cv2, numpy as np, subprocess
raw, still, out = sys.argv[1:4]
cap = cv2.VideoCapture(raw); fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
ref = cv2.resize(cv2.imread(still), (W, H), interpolation=cv2.INTER_AREA)
orb = cv2.ORB_create(6000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
gr = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY); kr, dr = orb.detectAndCompute(gr, None)
gr_s = cv2.resize(gr, (W // 2, H // 2)).astype(np.float32)
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                      '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
Hp = np.eye(3); i = 0; errs = []
while True:
    ok, f = cap.read()
    if not ok: break
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); kf, df = orb.detectAndCompute(g, None)
    m = sorted(bf.match(df, dr), key=lambda x: x.distance)[:1500]
    if len(m) > 40:
        a = np.float32([kf[x.queryIdx].pt for x in m]); b = np.float32([kr[x.trainIdx].pt for x in m])
        Hm, inl = cv2.findHomography(a, b, cv2.RANSAC, 2.0)
        if Hm is not None and inl.sum() > 60: Hp = Hm
    # ECC refine (correlation-based, tolerant of the clip's slight grade shift) at half res
    S = np.diag([.5, .5, 1.]); Hs = (S @ Hp @ np.linalg.inv(S)).astype(np.float32)
    try:
        _, Hs = cv2.findTransformECC(gr_s, cv2.resize(g, (W // 2, H // 2)).astype(np.float32), np.linalg.inv(Hs).astype(np.float32),
                                     cv2.MOTION_HOMOGRAPHY, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5), None, 5)
        Hp = np.linalg.inv(S) @ np.linalg.inv(Hs) @ S
    except cv2.error: pass
    w = cv2.warpPerspective(f, Hp, (W, H), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.full((H, W), 255, np.uint8), Hp, (W, H))
    mask = cv2.GaussianBlur(cv2.erode(mask, np.ones((9, 9), np.uint8)), (21, 21), 0)[..., None] / 255.
    o = (w * mask + ref * (1 - mask)).astype(np.uint8)
    errs.append(np.abs(cv2.cvtColor(o, cv2.COLOR_BGR2GRAY).astype(float) - gr).mean())
    p.stdin.write(o.tobytes()); i += 1
p.stdin.close(); p.wait()
print(raw, 'frames', i, 'diff first %.1f mid %.1f last %.1f' % (errs[0], errs[len(errs) // 2], errs[-1]))
