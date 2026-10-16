from PIL import Image
import numpy as np

def load_fg(path, key, tol=14):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    bg = (np.abs(r-key[0])<=tol)&(np.abs(g-key[1])<=tol)&(np.abs(b-key[2])<=tol)
    return ~bg

S = "Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Rebel Soldier.png"
fg = load_fg(S, (153,217,234))

def frames_in_band(fg, y0, y1, xmax=600):
    band = fg[y0:y1, :xmax]
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

for (label,y0,y1) in [
    ("idle? y44", 35, 90),
    ("run? y308", 300, 355),
    ("knife? y860", 855, 900),
    ("toss? y651", 645, 695),
    ("death? y478", 470, 520),
    ("flame? y2433", 2425, 2490),
]:
    boxes = frames_in_band(fg, y0, y1)
    print(f"[{label}] band {y0}..{y1}: n={len(boxes)}")
    for b in boxes[:20]:
        print("   ", b)
