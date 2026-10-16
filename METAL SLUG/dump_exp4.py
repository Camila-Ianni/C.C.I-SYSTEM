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
for (name,y0,y1) in [("R2small",45,85),("R4",145,206)]:
    band = fg[y0:y1,:]
    colsum = band.sum(axis=0)
    gaps=[]
    for x in range(band.shape[1]):
        if colsum[x]==0:
            gaps.append(x)
    # gap runs
    runs=[]; 
    if gaps:
        s=gaps[0]; prev=gaps[0]
        for x in gaps[1:]:
            if x!=prev+1:
                runs.append((s,prev)); s=x
            prev=x
        runs.append((s,prev))
    print(f"--- {name} gap runs ---")
    print([f"{a}-{b}" for a,b in runs])
    print("nonzero cols:", (colsum>0).sum())
