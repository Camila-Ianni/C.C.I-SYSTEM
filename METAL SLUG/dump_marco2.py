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
rowsum = fg.sum(axis=1)
# print rowsum for y 0..700 at coarse resolution to see gaps
for y in range(0, 700, 5):
    print(y, rowsum[y:y+5].min())
