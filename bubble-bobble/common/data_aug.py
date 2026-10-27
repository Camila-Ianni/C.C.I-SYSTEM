import torch

def random_shift(imgs, size = 84, pad = 4):
    m = torch.nn.ReplicationPad2d(pad)
    padded_imgs = m(imgs)
    n, c, h, w = padded_imgs.shape
    w1 = torch.randint(0, w - size + 1, (n,))
    h1 = torch.randint(0, h - size + 1, (n,))
    cropped_imgs = torch.empty((n, c, size, size), dtype=imgs.dtype, device=imgs.device)
    # Shifting should be applied consistently across stacked frames
    for i, (padded_img, w11, h11) in enumerate(zip(padded_imgs, w1, h1)):
        cropped_imgs[i][:] = padded_img[:, h11:h11 + size, w11:w11 + size]
    return cropped_imgs

if __name__=='__main__':
    imgs = torch.arange(96).reshape(3,2,4,4).to(torch.float)
    shifted_imgs = random_shift(imgs, size=4, pad=2)
    import pdb
    pdb.set_trace()