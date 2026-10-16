"""
Extracts the authentic Neo-Geo / Metal Slug arcade intro sequence frames
(Nazca logo, Neo-Geo startup, Title Screen animation, and How to Play instructions)
from MetalSlug-gameplay.mp4 using native macOS AVFoundation via ctypes.
"""
import os
import sys
import ctypes
from ctypes import c_void_p, c_char_p, c_int64, c_int32, c_uint32, byref, Structure

# Load macOS Frameworks
objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
foundation = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Foundation.framework/Foundation")
avfoundation = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AVFoundation.framework/AVFoundation")
coremedia = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreMedia.framework/CoreMedia")
coregraphics = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
imageio = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ImageIO.framework/ImageIO")

objc.objc_getClass.restype = c_void_p
objc.objc_getClass.argtypes = [c_char_p]
objc.sel_registerName.restype = c_void_p
objc.sel_registerName.argtypes = [c_char_p]

# CMTime struct: value (int64), timescale (int32), flags (uint32), epoch (int64)
class CMTime(Structure):
    _fields_ = [
        ("value", c_int64),
        ("timescale", c_int32),
        ("flags", c_uint32),
        ("epoch", c_int64)
    ]

# CoreGraphics & Image saving
CGImageDestinationCreateWithURL = imageio.CGImageDestinationCreateWithURL
CGImageDestinationCreateWithURL.restype = c_void_p
CGImageDestinationCreateWithURL.argtypes = [c_void_p, c_void_p, c_uint32, c_void_p]

CGImageDestinationAddImage = imageio.CGImageDestinationAddImage
CGImageDestinationAddImage.restype = None
CGImageDestinationAddImage.argtypes = [c_void_p, c_void_p, c_void_p]

CGImageDestinationFinalize = imageio.CGImageDestinationFinalize
CGImageDestinationFinalize.restype = ctypes.c_bool
CGImageDestinationFinalize.argtypes = [c_void_p]

def extract_intro_frames():
    mp4_path = os.path.abspath("MetalSlug-gameplay.mp4")
    if not os.path.exists(mp4_path):
        print(f"Error: {mp4_path} not found!")
        return

    output_dir = "Assets/Intro_Frames"
    os.makedirs(output_dir, exist_ok=True)

    NSURL = objc.objc_getClass(b"NSURL")
    NSString = objc.objc_getClass(b"NSString")
    AVURLAsset = objc.objc_getClass(b"AVURLAsset")
    AVAssetImageGenerator = objc.objc_getClass(b"AVAssetImageGenerator")

    sel_str = objc.sel_registerName(b"stringWithUTF8String:")
    sel_fileURL = objc.sel_registerName(b"fileURLWithPath:")
    sel_assetWithURL = objc.sel_registerName(b"URLAssetWithURL:options:")
    sel_generator = objc.sel_registerName(b"assetImageGeneratorWithAsset:")
    sel_copyCGImage = objc.sel_registerName(b"copyCGImageAtTime:actualTime:error:")
    sel_setTolerance = objc.sel_registerName(b"setRequestedTimeToleranceBefore:")
    sel_setToleranceAfter = objc.sel_registerName(b"setRequestedTimeToleranceAfter:")

    msg_str = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_char_p)(objc.objc_msgSend)
    msg_url = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_void_p)(objc.objc_msgSend)
    msg_asset = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_void_p, c_void_p)(objc.objc_msgSend)
    msg_gen = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, c_void_p)(objc.objc_msgSend)
    msg_tolerance = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, CMTime)(objc.objc_msgSend)
    msg_copy = ctypes.CFUNCTYPE(c_void_p, c_void_p, c_void_p, CMTime, c_void_p, c_void_p)(objc.objc_msgSend)

    # Load asset
    ns_path = msg_str(NSString, sel_str, mp4_path.encode("utf-8"))
    url = msg_url(NSURL, sel_fileURL, ns_path)
    asset = msg_asset(AVURLAsset, sel_assetWithURL, url, None)
    generator = msg_gen(AVAssetImageGenerator, sel_generator, asset)

    # Set precise time tolerance
    zero_time = CMTime(0, 600, 1, 0)
    msg_tolerance(generator, sel_setTolerance, zero_time)
    msg_tolerance(generator, sel_setToleranceAfter, zero_time)

    # Extract 1 frame every 0.15s (approx 6.6 FPS) from 0.0s to 33.0s (Intro, Title, How to Play, Insert Coin)
    # Total frames: ~220 frames, perfect for smooth arcade slideshow/playback in pygame
    timescale = 600
    fps = 10  # 10 frames per second
    total_seconds = 32.0
    frame_count = int(total_seconds * fps)

    print(f"Extracting {frame_count} frames from {mp4_path} into {output_dir}...")
    
    # UTI for PNG
    kUTTypePNG = msg_str(NSString, sel_str, b"public.png")

    saved_count = 0
    for idx in range(frame_count):
        t_sec = idx / float(fps)
        time = CMTime(int(t_sec * timescale), timescale, 1, 0)
        
        cg_image = msg_copy(generator, sel_copyCGImage, time, None, None)
        if cg_image:
            out_filename = os.path.join(output_dir, f"intro_{idx:04d}.png")
            out_ns_path = msg_str(NSString, sel_str, os.path.abspath(out_filename).encode("utf-8"))
            out_url = msg_url(NSURL, sel_fileURL, out_ns_path)
            
            dest = CGImageDestinationCreateWithURL(out_url, kUTTypePNG, 1, None)
            if dest:
                CGImageDestinationAddImage(dest, cg_image, None)
                CGImageDestinationFinalize(dest)
                saved_count += 1
                if saved_count % 30 == 0 or saved_count == frame_count:
                    print(f"  Extracted {saved_count}/{frame_count} frames ({t_sec:.1f}s)...")

    print(f"Extraction complete! Saved {saved_count} frames in {output_dir}.")

if __name__ == "__main__":
    extract_intro_frames()
