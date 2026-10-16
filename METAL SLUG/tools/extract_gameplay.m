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
        
        NSString *outDir = @"test_output/gameplay_ref";
        [[NSFileManager defaultManager] createDirectoryAtPath:outDir withIntermediateDirectories:YES attributes:nil error:nil];
        
        // Extract 30s to 100s at 1 FPS (70 frames)
        for (int sec = 30; sec <= 100; sec += 1) {
            CMTime time = CMTimeMakeWithSeconds((float)sec, 600);
            NSError *err = nil;
            CGImageRef imgRef = [generator copyCGImageAtTime:time actualTime:NULL error:&err];
            if (imgRef) {
                NSString *fileName = [NSString stringWithFormat:@"%@/sec_%03d.jpg", outDir, sec];
                NSURL *fileURL = [NSURL fileURLWithPath:fileName];
                CGImageDestinationRef dest = CGImageDestinationCreateWithURL((__bridge CFURLRef)fileURL, CFSTR("public.jpeg"), 1, NULL);
                if (dest) {
                    NSDictionary *options = @{(__bridge id)kCGImageDestinationLossyCompressionQuality: @0.85};
                    CGImageDestinationAddImage(dest, imgRef, (__bridge CFDictionaryRef)options);
                    CGImageDestinationFinalize(dest);
                    CFRelease(dest);
                }
                CGImageRelease(imgRef);
            }
        }
        printf("Done extracting gameplay reference frames!\n");
    }
    return 0;
}
