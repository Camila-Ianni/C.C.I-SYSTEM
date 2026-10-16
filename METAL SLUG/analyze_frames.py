from PIL import Image
import numpy as np

def load_fg(path, key, tol=14):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    bg = (np.abs(r-key[0])<=tol)&(np.abs(g-key[1])<=tol)&(np.abs(b-key[2])<=tol)
    return ~bg

def frames_in_band(fg, y0, y1):
    """Return list of (x,y,w,h) bounding boxes of connected-ish sprite cells within band."""
    band = fg[y0:y1, :]
    colsum = band.sum(axis=0)
    # find x runs
    runs=[]; inb=False; s=0
    for x,v in enumerate(colsum):
        if v>0 and not inb: s=x; inb=True
        elif v==0 and inb: runs.append((s,x-1)); inb=False
    if inb: runs.append((s,len(colsum)-1))
    boxes=[]
    for (xs,xe) in runs:
        # exact y bounds within this x range
        cols = band[:, xs:xe+1]
        ys = np.where(cols.any(axis=1))[0]
        if len(ys)==0: continue
        ymin,ymax = ys[0]+y0, ys[-1]+y0
        boxes.append((xs, ymin, xe-xs+1, ymax-ymin+1))
    return boxes

def show(path, name, key, bands):
    fg = load_fg(path, key)
    print(f"===== {name} =====")
    for (label,y0,y1) in bands:
        boxes = frames_in_band(fg, y0, y1)
        print(f"[{label}] band y{y0}..{y1}:")
        for b in boxes:
            print(f"    {b}")

POW = "Assets/Non-Playable Characters/Neo Geo _ NGCD - Metal Slug - Non-Playable Characters - P.O.W.s _ Helpful NPCs.png"
show(POW, "POW", (255,255,255), [
    ("tied?", 15, 55),
    ("untying?", 55, 140),
    ("give?", 285, 340),
    ("salute?", 335, 398),
    ("run?", 395, 440),
])
