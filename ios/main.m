//
//  main.m - Punto de entrada nativo de iOS para C.C.I. SYSTEM
//  Inicializa el runtime de Python y entrega el control a main.py sobre SDL2.
//
#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

int main(int argc, char *argv[]) {
    @autoreleasepool {
        NSString *resourcePath = [[NSBundle mainBundle] resourcePath];
        setenv("PYTHONOPTIMIZE", "2", 1);
        setenv("PYTHONDONTWRITEBYTECODE", "1", 1);
        setenv("PYTHONNOUSERSITE", "1", 1);
        setenv("PYTHONPATH", [resourcePath UTF8String], 1);
        setenv("IPHONE_OS", "1", 1);

        NSLog(@"[C.C.I. SYSTEM] Iniciando runtime iOS en: %@", resourcePath);
        return UIApplicationMain(argc, argv, nil, nil);
    }
}
