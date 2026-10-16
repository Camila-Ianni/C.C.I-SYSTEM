"""Find mapping video frame -> 320x224 game screen, and camera X per frame by matching the M1 strip."""
import sys, glob, json
import numpy as np
from PIL import Image

BG = np.asarray(Image.open('test_output/m1_bg.png').convert('RGB')).astype(np.int16)
H, W = BG.shape[:2]
# transparent/white pixels in strip = parallax layer (unknown) -> ignore
VALID = ~np.all(BG >= 250, axis=2)


def to_game(path, crop=(0, 2, 642, 466)):
    im = Image.open(path).convert('RGB').crop(crop).resize((320, 224), Image.BILINEAR)
    return np.asarray(im).astype(np.int16)


def match(fr, x_lo=0, x_hi=None, rows=slice(40, 210), step=1):
    """Return best cam_x and error. rows excludes HUD."""
    x_hi = W - 320 if x_hi is None else min(x_hi, W - 320)
    f = fr[rows]
    best = (1e18, -1)
    for cx in range(max(0, x_lo), x_hi + 1, step):
        b = BG[rows, cx:cx + 320]
        v = VALID[rows, cx:cx + 320]
        n = v.sum()
        if n < 5000:
            continue
        d = np.abs(f - b).sum(axis=2)
        # robust: median-ish -> use mean of lower 70% to ignore sprites
        dv = d[v]
        k = int(len(dv) * 0.7)
        e = np.partition(dv, k)[:k].mean()
        if e < best[0]:
            best = (e, cx)
    return best[1], best[0]


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'calib':
        p = sys.argv[2]
        for crop in [(1, 0, 641, 480), (0, 0, 642, 480), (1, 8, 641, 472), (1, 4, 641, 476), (1, 0, 641, 470), (1, 10, 641, 480), (11, 0, 631, 480)]:
            fr = to_game(p, crop)
            cx, e = match(fr, step=2)
            cx2, e2 = match(fr, cx - 3, cx + 3)
            print(crop, cx2, round(e2, 2))
    elif mode == 'track':
        files = sorted(glob.glob(sys.argv[2] + '/*.png'))
        out = []
        prev = 0
        for p in files:
            fr = to_game(p)
            # coarse search near previous position (camera only moves right in M1 mostly)
            lo, hi = prev - 40, prev + 400
            cx, e = match(fr, lo, hi, step=2)
            cx, e = match(fr, cx - 2, cx + 2)
            out.append((p, cx, round(float(e), 2)))
            if e < 25:
                prev = cx
            print(p, cx, round(float(e), 2), flush=True)
        json.dump(out, open(sys.argv[3], 'w'))
    elif mode == 'track2':
        files = sorted(glob.glob(sys.argv[2] + '/*.png'))
        start_t = float(sys.argv[4]); prev = int(sys.argv[5])
        out = []
        for p in files:
            t = float(p.rsplit('t_', 1)[1][:-4])
            if t < start_t:
                continue
            raw = Image.open(p).convert('RGB').crop((0, 2, 642, 466)).resize((320, 224), Image.BILINEAR)
            fr0 = np.asarray(raw).astype(np.int16)
            best = (1e18, 0, 0)
            for dy in range(-16, 17, 2):
                fr = np.roll(fr0, dy, axis=0)
                rows = slice(40 + max(0, dy), 212 + min(0, dy))
                cx, e = match(fr, prev - 8, prev + 160, rows=rows, step=2)
                if e < best[0]:
                    best = (e, cx, dy)
            e, cx, dy = best
            fr = np.roll(fr0, dy, axis=0)
            cx, e = match(fr, cx - 2, cx + 2, rows=slice(40 + max(0, dy), 212 + min(0, dy)))
            prev = max(prev, cx)
            out.append((t, cx, dy, round(float(e), 2)))
            print(t, cx, dy, round(float(e), 2), flush=True)
        json.dump(out, open(sys.argv[3], 'w'))

