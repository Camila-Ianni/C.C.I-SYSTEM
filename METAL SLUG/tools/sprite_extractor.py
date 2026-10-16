"""
Sprite Extraction & Inspection Utility for Metal Slug 1 Spritesheets.
Analyzes Spriters Resource rips, handles chroma key transparency,
and locates individual sprites and animation strips.
"""
import os
import pygame
from PIL import Image
import numpy as np

CHROMA_CYAN = (153, 217, 234) # #99D9EA
CHROMA_GREEN = (0, 248, 0)    # #00F800
CHROMA_MAGENTA = (255, 0, 255) # #FF00FF
CHROMA_WHITE = (255, 255, 255)

def get_chroma_color_from_corner(pil_img):
    """Samples the top-left pixel to determine the chroma key color."""
    rgba = pil_img.convert("RGBA")
    corner_pixel = rgba.getpixel((0, 0))
    if corner_pixel[3] == 0:
        return None # Already transparent
    return corner_pixel[:3]

def remove_color_key(pil_img, key_color=None, tolerance=5):
    """Returns a new PIL RGBA image with the key_color made transparent."""
    img_rgba = pil_img.convert("RGBA")
    if key_color is None:
        key_color = get_chroma_color_from_corner(pil_img)
        if key_color is None:
            return img_rgba
    
    data = np.array(img_rgba)
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    
    mask = (
        (np.abs(r.astype(int) - key_color[0]) <= tolerance) &
        (np.abs(g.astype(int) - key_color[1]) <= tolerance) &
        (np.abs(b.astype(int) - key_color[2]) <= tolerance)
    )
    
    data[mask, 3] = 0
    return Image.fromarray(data)

def find_bounding_boxes_in_region(pil_img_rgba, min_w=8, min_h=8, max_w=200, max_h=200):
    """Finds bounding boxes of non-transparent contiguous islands."""
    data = np.array(pil_img_rgba)
    alpha = data[:, :, 3] > 0
    # Simple projection or connected components
    boxes = []
    # Can use scipy or simple horizontal/vertical profile slicing
    return boxes

if __name__ == "__main__":
    print("Sprite extractor loaded.")
