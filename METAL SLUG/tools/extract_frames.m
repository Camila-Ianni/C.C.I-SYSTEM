#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ImageIO/ImageIO.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *videoPath = @"MetalSlug-gameplay.mp4";
        NSURL *videoURL = [NSURL fileURLWithPath:videoPath];
        AVURLAsset *asset = [AVURLAsset URLAssetWithURL:videoURL options:nil];
        
        AVAssetImageGenerator *generator = [AVAssetImageGenerator assetImageGeneratorWithAsset:asset];
        generator.appliesPreferredTrackTransform = YES;
        generator.requestedTimeToleranceBefore = kCMTimeZero;
        generator.requestedTimeToleranceAfter = kCMTimeZero;
        
        NSString *outDir = @"Assets/Intro_Frames";
        [[NSFileManager defaultManager] createDirectoryAtPath:outDir withIntermediateDirectories:YES attributes:nil error:nil];
        
        // Extract 0.0s to 32.0s at 10 FPS (320 frames)
        int fps = 10;
        int totalFrames = 320;
        printf("Extracting %d frames from %s...\n", totalFrames, [videoPath UTF8String]);
        
        for (int i = 0; i < totalFrames; i++) {
            float sec = (float)i / (float)fps;
            CMTime time = CMTimeMakeWithSeconds(sec, 600);
            NSError *err = nil;
            CGImageRef imgRef = [generator copyCGImageAtTime:time actualTime:NULL error:&err];
            if (imgRef) {
                NSString *fileName = [NSString stringWithFormat:@"%@/frame_%04d.jpg", outDir, i];
                NSURL *fileURL = [NSURL fileURLWithPath:fileName];
                CGImageDestinationRef dest = CGImageDestinationCreateWithURL((__bridge CFURLRef)fileURL, CFSTR("public.jpeg"), 1, NULL);
                if (dest) {
                    NSDictionary *options = @{(__bridge id)kCGImageDestinationLossyCompressionQuality: @0.85};
                    CGImageDestinationAddImage(dest, imgRef, (__bridge CFDictionaryRef)options);
                    CGImageDestinationFinalize(dest);
                    CFRelease(dest);
                }
                CGImageRelease(imgRef);
                if (i % 40 == 0 || i == totalFrames - 1) {
                    printf("  Extracted frame %d / %d (%.1f s)\n", i, totalFrames, sec);
                }
            }
        }
        printf("Done extracting intro frames!\n");
    }
    return 0;
}
