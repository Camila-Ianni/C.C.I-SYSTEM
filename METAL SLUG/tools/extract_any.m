#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ImageIO/ImageIO.h>

// Usage: extract_any <video> <outDir> <startSec> <endSec> <stepSec>
// Prints duration if called with only <video>.
int main(int argc, const char * argv[]) {
    @autoreleasepool {
        if (argc < 2) { printf("usage\n"); return 1; }
        NSURL *url = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]];
        AVURLAsset *asset = [AVURLAsset URLAssetWithURL:url options:nil];
        double dur = CMTimeGetSeconds(asset.duration);
        if (argc < 6) {
            AVAssetTrack *t = [[asset tracksWithMediaType:AVMediaTypeVideo] firstObject];
            printf("duration=%.2f size=%.0fx%.0f fps=%.2f\n", dur, t.naturalSize.width, t.naturalSize.height, t.nominalFrameRate);
            return 0;
        }
        NSString *outDir = [NSString stringWithUTF8String:argv[2]];
        double start = atof(argv[3]), end = atof(argv[4]), step = atof(argv[5]);
        [[NSFileManager defaultManager] createDirectoryAtPath:outDir withIntermediateDirectories:YES attributes:nil error:nil];
        AVAssetImageGenerator *g = [AVAssetImageGenerator assetImageGeneratorWithAsset:asset];
        g.appliesPreferredTrackTransform = YES;
        g.requestedTimeToleranceBefore = kCMTimeZero;
        g.requestedTimeToleranceAfter = kCMTimeZero;
        int n = 0;
        for (double s = start; s <= end + 1e-6; s += step) {
            NSError *err = nil;
            CGImageRef img = [g copyCGImageAtTime:CMTimeMakeWithSeconds(s, 600) actualTime:NULL error:&err];
            if (!img) continue;
            NSString *fn = [NSString stringWithFormat:@"%@/t_%07.2f.png", outDir, s];
            CGImageDestinationRef d = CGImageDestinationCreateWithURL((__bridge CFURLRef)[NSURL fileURLWithPath:fn], CFSTR("public.png"), 1, NULL);
            if (d) { CGImageDestinationAddImage(d, img, NULL); CGImageDestinationFinalize(d); CFRelease(d); }
            CGImageRelease(img);
            n++;
        }
        printf("extracted %d frames\n", n);
    }
    return 0;
}
