from PIL import Image
import numpy as np

def load_fg(path, key, tol=14):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    bg = (np.abs(r-key[0])<=tol)&(np.abs(g-key[1])<=tol)&(np.abs(b-key[2])<=tol)
    return ~bg

def frames_in_band(fg, y0, y1):
    band = fg[y0:y1, :]
    colsum = band.sum(axis=0)
    runs=[]; inb=False; s=0
    for x,v in enumerate(colsum):
        if v>0 and not inb: s=x; inb=True
        elif v==0 and inb: runs.append((s,x-1)); inb=False
    if inb: runs.append((s,len(colsum)-1))
    boxes=[]
    for (xs,xe) in runs:
        cols = band[:, xs:xe+1]
        ys = np.where(cols.any(axis=1))[0]
        if len(ys)==0: continue
        boxes.append((xs, int(ys[0])+y0, xe-xs+1, int(ys[-1])-int(ys[0])+1))
    return boxes

M = "Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
fg = load_fg(M, (153,217,234))
for (label,y0,y1) in [
    ("idle-torso? y263", 255, 295),
    ("idle-legs? y276", 270, 300),
    ("run-torso? y477", 468, 510),
    ("run-legs? y511", 505, 535),
    ("jump-torso? y561", 555, 595),
    ("jump-legs? y645", 640, 670),
]:
    boxes = frames_in_band(fg, y0, y1)
    print(f"[{label}] band {y0}..{y1}: n={len(boxes)}")
    for b in boxes[:16]:
        print("   ", b)
