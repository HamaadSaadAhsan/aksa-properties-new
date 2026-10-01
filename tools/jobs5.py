"""Render plan for render5.html (30 Sept 2026): stills at 1920x1080 (masks stay at the 1280x720 overlay space),
orbit transitions, close-up orbits and fly-ins. No ambient loops (not used by the site)."""
import json, sys
import jobs as J
jobs = []
for i, a in enumerate(J.ANG):
    b = J.ANG[(i + 1) % 8]
    jobs.append({"t": "shot", "view": J.mp(i), "size": [1920, 1080], "out": f"stills/angle_{a:03d}.jpg"})
    jobs.append({"t": "mask", "mode": "dev", "view": J.mp(i), "size": [J.W, J.H], "out": f"masks/angle_{a:03d}_id.png"})
    jobs.append({"t": "shot", "view": J.cu(i), "size": [J.CW, J.CH], "out": f"stills/close_{a:03d}.jpg"})
    jobs.append({"t": "mask", "mode": "floors", "view": J.cu(i), "size": [J.CW, J.CH], "out": f"masks/close_{a:03d}_id.png"})
    a0 = J.mp(i); a1 = dict(a0, theta=a0["theta"] + J.math.radians(45))
    for k in range(J.T_FR): jobs.append({"t": "shot", "view": J.orbit_lerp(a0, a1, J.ease(k / (J.T_FR - 1))), "size": [J.W, J.H], "out": f"{J.FR}/trans_{a:03d}-{b:03d}/{k:03d}.jpg"})
    c0 = J.cu(i); c1 = dict(c0, theta=c0["theta"] + J.math.radians(45))
    for k in range(J.T_FR): jobs.append({"t": "shot", "view": J.orbit_lerp(c0, c1, J.ease(k / (J.T_FR - 1))), "size": [J.W, J.H], "out": f"{J.FR}/ctrans_{a:03d}-{b:03d}/{k:03d}.jpg"})
    for k in range(J.FLY_FR): jobs.append({"t": "shot", "view": J.orbit_lerp(J.mp(i), J.cu(i), J.ease(k / (J.FLY_FR - 1))), "size": [J.W, J.H], "out": f"{J.FR}/fly_{a:03d}-close/{k:03d}.jpg"})
json.dump(jobs, open("jobs.json", "w")); print(len(jobs), "jobs")
