from PIL import Image
import numpy as np

def load_fg(path, key, tol=12):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    bg = (np.abs(r-key[0])<=tol)&(np.abs(g-key[1])<=tol)&(np.abs(b-key[2])<=tol)
    return ~bg

E = "Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Explosion SFX.png"
fg = load_fg(E, (0,248,0))

def frames_in_band(fg, y0, y1):
    band = fg[y0:y1, :]
    colsum = band.sum(axis=0)
    # merge frames separated by <4 px gap within this band
    runs=[]; inb=False; s=0; gap=0
    for x,v in enumerate(colsum):
        if v>0:
            if not inb: s=x; inb=True; gap=0
            else: gap=0
        else:
            if inb:
                gap+=1
                if gap>=5:
                    runs.append((s,x-1-gap+1)); inb=False
    if inb: runs.append((s,len(colsum)-1))
    boxes=[]
    for (xs,xe) in runs:
        cols=band[:,xs:xe+1]
        ys=np.where(cols.any(axis=1))[0]
        if len(ys)==0: continue
        boxes.append((xs,int(ys[0])+y0,xe-xs+1,int(ys[-1])-int(ys[0])+1))
    return boxes

for (label,y0,y1) in [
    ("row1 y0..50", 0, 50),
    ("row2 y45..95", 45, 95),
    ("row3 y85..145", 85, 145),
    ("row4 y145..210", 145, 210),
]:
    boxes = frames_in_band(fg, y0, y1)
    print(f"[{label}]: n={len(boxes)}")
    for b in boxes:
        print("   ", b)
