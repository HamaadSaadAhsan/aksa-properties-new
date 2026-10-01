"""Architect's floor plans without the measurement marks: dimension chains around the building and across the courtyard,
and the red axis lines. Walls, rooms, hatching and furniture stay as drawn.
How: the building is densely drawn (hatching, tiles, walls); the measurement areas are mostly blank with thin lines. Areas of low
ink density connected to the sheet border (outside) or to the centre of the courtyard are cleared to white; red axis pixels are
inpainted from their neighbours.  usage: python3 clean_plans.py <in.jpg> <out.jpg> [...]"""
import sys, numpy as np, cv2

def clean(src, dst, k=61, thr=.16, bbox=None):
    im = cv2.imread(src); H, W = im.shape[:2]
    b, g, r = [im[:, :, i].astype(int) for i in range(3)]
    red = ((r - g > 60) & (r - b > 60)).astype(np.uint8)       # red axis lines (the room hatching is dark red-brown, so only bright red)
    red &= 1 - cv2.morphologyEx(red, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))   # thin lines only, not red/pink filled rooms
    red = cv2.dilate(red, np.ones((3, 3), np.uint8))
    out = cv2.inpaint(im, red, 3, cv2.INPAINT_TELEA)                 # red axis lines
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    ink = ((im.min(axis=2) < 232) & (red == 0)).astype(np.float32)   # anything not white paper (lines, hatching, flat-filled rooms)
    low = (cv2.blur(ink, (k, k)) < thr).astype(np.uint8)
    n, lab = cv2.connectedComponents(low, connectivity=4)
    keep = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1]) | {lab[H // 2, W // 2]}
    keep.discard(0)
    clear = np.isin(lab, list(keep)).astype(np.uint8)
    clear = cv2.morphologyEx(clear, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))   # no bites into balconies
    clear = cv2.erode(clear, np.ones((9, 9), np.uint8)).astype(bool)
    out[clear] = 255                                                   # outside the building + the courtyard
    # measurement chains drawn on coloured ground (the ground floor's pavement): outside the building's outer edge only,
    # thin dark strokes and numbers take the colour of their surroundings
    if bbox:
        x0, y0, x1, y1 = bbox; med = cv2.medianBlur(out, 21)
        dark = (cv2.cvtColor(med, cv2.COLOR_BGR2GRAY).astype(int) - cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(int)) > 25
        outside = np.ones((H, W), bool); outside[y0:y1, x0:x1] = False
        m = cv2.dilate((dark & outside).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & outside
        out[m] = med[m]
    cv2.imwrite(dst, out, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return clear.mean()

if __name__ == '__main__':
    a = sys.argv[1:]
    BOX = (84, 0, 2034, 2700)     # ground floor: outer edge of the homes on the sheet (px), from its unit outlines in data.json
    for s, d in zip(a[::2], a[1::2]): print(d, 'cleared', round(clean(s, d, bbox=BOX if '03_R_Cha' in s else None) * 100, 1), '%')
