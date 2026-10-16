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

# full row bands
rowsum = fg.sum(axis=1)
bands=[]; inb=False; s=0
for i,v in enumerate(rowsum):
    if v>0 and not inb: s=i; inb=True
    elif v==0 and inb: bands.append((s,i-1)); inb=False
if inb: bands.append((s,len(rowsum)-1))

def frames_in_band(fg, y0, y1, xmax=500):
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

for (s,e) in bands:
    if e-s+1 < 15: 
        continue
    boxes = frames_in_band(fg, s, e)
    # skip bands that are just tiny noise
    if all(b[2]*b[3] < 40 for b in boxes):
        continue
    print(f"BAND y{s}..{e} h={e-s+1}: {len(boxes)} frames")
    for b in boxes:
        print(f"    {b}")
