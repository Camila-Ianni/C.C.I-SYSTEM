#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ImageIO/ImageIO.h>
#import <CoreMedia/CoreMedia.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *videoPath = @"Grabación de pantalla 2026-10-09 a la(s) 12.59.44 p. m..mov";
        if (argc > 1) {
            videoPath = [NSString stringWithUTF8String:argv[1]];
        }
        NSString *outDir = @"test_output/user_video_latest";
        if (argc > 2) {
            outDir = [NSString stringWithUTF8String:argv[2]];
        }
        float startSec = 0.0;
        if (argc > 3) {
            startSec = atof(argv[3]);
        }
        float fps = 4.0;
        if (argc > 4) {
            fps = atof(argv[4]);
        }
        int totalFrames = 120;
        if (argc > 5) {
            totalFrames = atoi(argv[5]);
        }
        
        NSURL *videoURL = [NSURL fileURLWithPath:videoPath];
        AVURLAsset *asset = [AVURLAsset URLAssetWithURL:videoURL options:nil];
        CMTime duration = [asset duration];
        float durationSec = CMTimeGetSeconds(duration);
        printf("Video duration: %.2f seconds. Extracting from %.2f sec at %.1f fps (%d frames)...\n", durationSec, startSec, fps, totalFrames);
        
        AVAssetImageGenerator *generator = [AVAssetImageGenerator assetImageGeneratorWithAsset:asset];
        generator.appliesPreferredTrackTransform = YES;
        generator.requestedTimeToleranceBefore = kCMTimeZero;
        generator.requestedTimeToleranceAfter = kCMTimeZero;
        
        [[NSFileManager defaultManager] createDirectoryAtPath:outDir withIntermediateDirectories:YES attributes:nil error:nil];
        
        for (int i = 0; i < totalFrames; i++) {
            float sec = startSec + (float)i / fps;
            if (sec > durationSec) break;
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
            }
        }
        printf("Extraction complete!\n");
    }
    return 0;
}
