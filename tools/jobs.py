"""Render placeholder media for AKSA Residencies from the OSM-based Three.js scene.
Usage:  python3 jobs.py plan  -> jobs.json ;  python3 jobs.py run <k> <n>
"""
import json, math, os, sys, time
from drv import sync_playwright, open_page, save

W, H = 1280, 720
CW, CH = 2400, 1350
EQ = 4096
FR = 'frames'
SC = [880.8, 8, -1277.4]
TH0 = math.radians(-74.2)       # angle 000 = street side (WSW)
MP = {"target": SC, "radius": 310, "phi": 1.1, "fov": 38}
CU = {"target": [SC[0], 9, SC[2]], "radius": 205, "phi": 1.3, "fov": 40}
ANG = [i * 45 for i in range(8)]
T_FR, LOOP_FR, FLY_FR, PFLY_FR = 36, 24, 48, 30
LOOP_FPS, LOOP_SEC, LOOP_X = 12, 8, 12          # ambient loop: 8 s at 12 fps + 12 frames to cross-fade the seam
TFIX = LOOP_SEC                                   # every still / transition shows the scene at the loop's seam time
PANOS = []

def ease(k): return 4*k*k*k if k < .5 else 1 - (-2*k + 2)**3 / 2
def lerp(a, b, k): return a + (b - a) * k
def mp(i): return dict(MP, theta=TH0 + math.radians(ANG[i]))
def cu(i): return dict(CU, theta=TH0 + math.radians(ANG[i]))
def orbit_lerp(a, b, k):
    return {"target": [lerp(x, y, k) for x, y in zip(a["target"], b["target"])], "radius": lerp(a["radius"], b["radius"], k),
            "phi": lerp(a["phi"], b["phi"], k), "theta": lerp(a["theta"], b["theta"], k), "fov": lerp(a["fov"], b["fov"], k)}
def orbit_pos(o):
    r, p, t = o["radius"], o["phi"], o["theta"]; x, y, z = o["target"]
    return [x + r*math.sin(p)*math.sin(t), y + r*math.cos(p), z + r*math.sin(p)*math.cos(t)]

def plan():
    jobs = []
    for i, a in enumerate(ANG):
        b = ANG[(i + 1) % 8]
        jobs.append({"t": "shot", "view": mp(i), "size": [W, H], "out": f"stills/angle_{a:03d}.jpg"})
        jobs.append({"t": "mask", "mode": "dev", "view": mp(i), "size": [W, H], "out": f"masks/angle_{a:03d}_id.png"})
        jobs.append({"t": "shot", "view": cu(i), "size": [CW, CH], "out": f"stills/close_{a:03d}.jpg"})
        jobs.append({"t": "mask", "mode": "floors", "view": cu(i), "size": [CW, CH], "out": f"masks/close_{a:03d}_id.png"})
    jobs.append({"t": "meta"})
    for i, a in enumerate(ANG):
        b = ANG[(i + 1) % 8]
        for k in range(LOOP_FPS * LOOP_SEC + LOOP_X):
            jobs.append({"t": "shot", "view": mp(i), "time": k / LOOP_FPS, "size": [W, H], "out": f"{FR}/loop_{a:03d}/{k:03d}.jpg"})
        a0 = mp(i); a1 = dict(a0, theta=a0["theta"] + math.radians(45))
        for k in range(T_FR):
            jobs.append({"t": "shot", "view": orbit_lerp(a0, a1, ease(k / (T_FR - 1))), "size": [W, H], "out": f"{FR}/trans_{a:03d}-{b:03d}/{k:03d}.jpg"})
        c0 = cu(i); c1 = dict(c0, theta=c0["theta"] + math.radians(45))
        for k in range(T_FR):
            jobs.append({"t": "shot", "view": orbit_lerp(c0, c1, ease(k / (T_FR - 1))), "size": [W, H], "out": f"{FR}/ctrans_{a:03d}-{b:03d}/{k:03d}.jpg"})
        for k in range(FLY_FR):
            jobs.append({"t": "shot", "view": orbit_lerp(mp(i), cu(i), ease(k / (FLY_FR - 1))), "size": [W, H], "out": f"{FR}/fly_{a:03d}-close/{k:03d}.jpg"})
    for name in PANOS:
        jobs.append({"t": "pano_fly", "name": name})
        jobs.append({"t": "equirect", "which": "main", "name": name, "out": f"360/{name}.jpg"})

    json.dump(jobs, open("jobs.json", "w"))
    print(len(jobs), "jobs")

def pano_frames(d, name):
    p = d["panos"][name]; pos, look = p["pos"], p["look"]
    dx, dy, dz = (look[i] - pos[i] for i in range(3)); n = math.sqrt(dx*dx + dy*dy + dz*dz); dx, dy, dz = dx/n, dy/n, dz/n
    start = mp(0); sp = orbit_pos(start); sl = start["target"]; end_look = [pos[0] + dx*50, pos[1] + dy*50, pos[2] + dz*50]
    out = []
    for k in range(PFLY_FR):
        e = ease(k / (PFLY_FR - 1))
        out.append({"pos": [lerp(a, b, e) for a, b in zip(sp, pos)], "look": [lerp(a, b, e) for a, b in zip(sl, end_look)], "fov": lerp(38, 70, e)})
    return out, {"yaw": math.atan2(dx, -dz), "pitch": math.asin(max(-1, min(1, dy))), "fov": 70}

def run(k0, n):
    jobs = json.load(open("jobs.json")); os.makedirs("out", exist_ok=True)
    with sync_playwright() as p:
        b, pg = open_page(p); d = pg.evaluate("R.data()"); cur = None; t0 = time.time(); cur_t = None
        for idx, j in enumerate(jobs):
            if idx % n != k0: continue
            if j["t"] in ("shot", "mask"):
                path = os.path.join("out", j["out"]); os.makedirs(os.path.dirname(path), exist_ok=True)
                if os.path.exists(path): continue
                if cur != tuple(j["size"]): pg.evaluate("s=>R.size(s[0],s[1])", j["size"]); cur = tuple(j["size"])
                pg.evaluate("v=>R.view(v)", j["view"])
                t = j.get("time", TFIX)
                if t != cur_t: pg.evaluate("t=>R.time(t)", t); cur_t = t
                url = pg.evaluate("w=>R.shot(w)", t / LOOP_SEC * .25) if j["t"] == "shot" else pg.evaluate("m=>R.mask(m)", j["mode"])
                save(url, path)
            elif j["t"] == "pano_fly":
                frames, start = pano_frames(d, j["name"]); pg.evaluate("s=>R.size(s[0],s[1])", [W, H]); cur = (W, H)
                for k, v in enumerate(frames):
                    path = f"out/{FR}/fly_000-{j['name']}/{k:03d}.jpg"; os.makedirs(os.path.dirname(path), exist_ok=True)
                    if os.path.exists(path): continue
                    pg.evaluate("v=>R.view(v)", v); save(pg.evaluate("R.shot(0)"), path)
                json.dump(start, open(f"out/{FR}/fly_000-{j['name']}/start.json", "w"))
            elif j["t"] == "equirect":
                path = os.path.join("out", j["out"]); os.makedirs(os.path.dirname(path), exist_ok=True)
                if not os.path.exists(path):
                    pos = d["panos"][j["name"]]["pos"] if j["which"] == "main" else d["rooms"][j["room"]]["pos"]
                    save(pg.evaluate("a=>R.equirect(a[0],a[1],a[2],a[3])", [j["which"], pos, EQ, .8]), path)
                cur = None
            elif j["t"] == "meta":
                pg.evaluate("s=>R.size(s[0],s[1])", [W, H]); cur = (W, H); markers = {}
                for i, a in enumerate(ANG):
                    pg.evaluate("v=>R.view(v)", mp(i))
                    markers[a] = {k: pg.evaluate("a=>R.project(a[0],a[1],a[2])", [v["pos"], W, H]) for k, v in d["panos"].items()}
                    markers[a]['__amen'] = [dict(id=m['id'], **pg.evaluate("a=>R.project(a[0],a[1],a[2])", [m["pos"], W, H])) for m in d["amenities"]]
                json.dump({"data": d, "markers": markers}, open("out/meta.json", "w"))
            if idx % 25 == 0: print(f"[{k0}] {idx}/{len(jobs)} {time.time()-t0:.0f}s", flush=True)
        b.close()
    print(f"[{k0}] done {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "plan": plan()
    else: run(int(sys.argv[2]), int(sys.argv[3]))
