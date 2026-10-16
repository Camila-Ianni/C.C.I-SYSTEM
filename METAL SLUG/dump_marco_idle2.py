from PIL import Image
import numpy as np
def load_fg(path, key, tol=14):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    bg = (np.abs(r-key[0])<=tol)&(np.abs(g-key[1])<=tol)&(np.abs(b-key[2])<=tol)
    return ~bg
M = "Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Marco Rossi.png"
fg = load_fg(M, (153,217,234))
for (y0,y1) in [(400,470)]:
    band=fg[y0:y1,:500]; col=band.sum(axis=0)
    runs=[]; ss=None; gap=0
    for x,v in enumerate(col):
        if v>0:
            if ss is None: ss=x
            gap=0
        else:
            if ss is not None:
                gap+=1
                if gap>=3: runs.append((ss,x-gap)); ss=None
    if ss is not None: runs.append((ss,499))
    cells=[]
    for (xs,xe) in runs:
        ys=np.where(band[:,xs:xe+1].any(axis=1))[0]
        if len(ys)==0: continue
        w=xe-xs+1; h=int(ys[-1])-int(ys[0])+1
        if w<6 or h<6: continue
        cells.append((xs,int(ys[0])+y0,w,h))
    print("Marco y400..470:", cells)
