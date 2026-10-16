from PIL import Image
import numpy as np

def analyze(path, name, key=None):
    im = Image.open(path).convert("RGB")
    a = np.array(im).astype(int)
    corner = a[0,0]
    print(f"=== {name} {a.shape[1]}x{a.shape[0]} corner={corner} ===")
    r,g,b = a[:,:,0],a[:,:,1],a[:,:,2]
    keyc = key if key else corner
    tol=14
    bg = (np.abs(r-keyc[0])<=tol)&(np.abs(g-keyc[1])<=tol)&(np.abs(b-keyc[2])<=tol)
    fg = ~bg
    rowsum = fg.sum(axis=1)
    bands=[]; inb=False; start=0
    for i,v in enumerate(rowsum):
        if v>0 and not inb: start=i; inb=True
        elif v==0 and inb: bands.append((start,i-1)); inb=False
    if inb: bands.append((start,len(rowsum)-1))
    for (s,e) in bands:
        print(f"  y {s:4d}..{e:4d}  h={e-s+1:3d}  peak={rowsum[s:e+1].max()}")

analyze("Assets/Non-Playable Characters/Neo Geo _ NGCD - Metal Slug - Non-Playable Characters - P.O.W.s _ Helpful NPCs.png","POW", key=(255,255,255))
analyze("Assets/Enemies & Bosses/Neo Geo _ NGCD - Metal Slug - Enemies & Bosses - Rebel Soldier.png","SOLDIER")
analyze("Assets/Miscellaneous/Neo Geo _ NGCD - Metal Slug - Miscellaneous - Explosion SFX.png","EXPLOSION", key=(0,248,0))
