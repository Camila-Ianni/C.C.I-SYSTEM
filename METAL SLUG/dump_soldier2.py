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
# column profile for y 30..80 (idle sprites only, above label text)
band = fg[30:80, :180]
colsum = band.sum(axis=0)
print("col profile y30..80 (x: count):")
for x in range(0, 160):
    if colsum[x]>0:
        pass
# print runs with gap detection
runs=[]; s=None
for x,v in enumerate(colsum):
    if v>0 and s is None: s=x
    elif v==0 and s is not None: runs.append((s,x-1)); s=None
if s is not None: runs.append((s,159))
print("runs:", runs)
for (xs,xe) in runs:
    ys=np.where(band[:,xs:xe+1].any(axis=1))[0]
    print(f"  x{xs}..{xe}  y={ys[0]+30}..{ys[-1]+30}  w={xe-xs+1} h={ys[-1]-ys[0]+1}")
