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
# For each row, split columns with gap tolerance 3px, then filter cells with area>= some threshold
rows = [("R1", 0, 45), ("R2", 45, 85), ("R3", 85, 145), ("R4", 145, 205)]
for (name, y0, y1) in rows:
    band = fg[y0:y1, :]
    colsum = band.sum(axis=0)
    # gap-tolerant runs
    cells=[]; cur=None; gap=0
    for x in range(band.shape[1]):
        v = colsum[x]
        if v>0:
            if cur is None: cur=[x,x]
            else: cur[1]=x
            gap=0
        else:
            if cur is not None:
                gap+=1
                if gap>=4:
                    cells.append(cur); cur=None
    if cur is not None: cells.append(cur)
    print(f"--- {name} y{y0}..{y1} ---")
    for (xs,xe) in cells:
        cols = band[:, xs:xe+1]
        ys = np.where(cols.any(axis=1))[0]
        if len(ys)==0: continue
        w=xe-xs+1; h=int(ys[-1])-int(ys[0])+1
        if w<6 or h<6: continue
        print(f"   x{xs:3d}..{xe:3d} (w={w:2d})  y={int(ys[0])+y0:3d}..{int(ys[-1])+y0:3d} (h={h:2d})")
