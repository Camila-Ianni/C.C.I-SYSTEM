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
for (name,y0,y1) in [("R1",0,46),("R3",85,146)]:
    band = fg[y0:y1,:]
    colsum = band.sum(axis=0)
    # print columns where colsum==0 (gaps) or tiny
    gaps=[x for x in range(band.shape[1]) if colsum[x]==0]
    # find contiguous gap runs
    print(f"--- {name} zero-column gap runs ---")
    if gaps:
        s=gaps[0]; prev=gaps[0]
        for x in gaps[1:]:
            if x!=prev+1:
                print(f"   gap x{s}..{prev}")
                s=x
            prev=x
        print(f"   gap x{s}..{prev}")
    else:
        print("   no zero columns")
    print("   column count (nonzero):", (colsum>0).sum(), "of", band.shape[1])
