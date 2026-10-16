from PIL import Image
import numpy as np
def load_fg(path, key, tol=14):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    bg = (np.abs(r-key[0])<=tol)&(np.abs(g-key[1])<=tol)&(np.abs(b-key[2])<=tol)
    return ~bg
for name,path,key in [
  ("Tarma","Assets/Playable characters/Neo Geo _ NGCD - Metal Slug - Playable Characters - Tarma Roving.png",(86,177,222)),
]:
    fg=load_fg(path,key)
    print("=== ",name, fg.shape[1],"x",fg.shape[0])
    # bands in y 0..700 x<500
    rowsum=fg[0:700,:500].sum(axis=1)
    bands=[]; inb=False; s=0
    for i,v in enumerate(rowsum):
        if v>0 and not inb: s=i; inb=True
        elif v==0 and inb: bands.append((s,i-1)); inb=False
    if inb: bands.append((s,699))
    for (s,e) in bands:
        band=fg[s:e+1,:500]; col=band.sum(axis=0)
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
            cells.append((xs,int(ys[0])+s,w,h))
        if cells:
            print(f"  y{s}..{e} h={e-s+1}: {cells[:8]}")
