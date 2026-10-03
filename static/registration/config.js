const CONFIG = {
    // Google Apps Script Web App URL (To be updated by user after deployment)
    APPS_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbzkOlQSqMUXsDV-c0-sKZo1KNpHnkkUZQalefssBgyADokyB5shzdJM344pDrbAqUZ6/exec',
    
    // File Constraints (Government Specifications)
    IMAGE: {
        PHOTO: {
            width: 132, height: 170,
            minSize: 5120, maxSize: 51200,       // 5KB – 50KB
            preferredMin: 35840,                  // 35KB
            preferredMax: 46080,                  // 45KB
            dpi: 300,
            format: 'image/jpeg',
            outputName: 'photo.jpg'
        },
        SIGNATURE: {
            width: 170, height: 132,
            minSize: 5120, maxSize: 20480,        // 5KB – 20KB
            preferredMin: 12288,                  // 12KB
            preferredMax: 18432,                  // 18KB
            dpi: 200,
            format: 'image/jpeg',
            outputName: 'signature.jpg'
        },
        THUMB: {
            width: 170, height: 132,
            minSize: 5120, maxSize: 20480,        // 5KB – 20KB
            preferredMin: 12288,                  // 12KB
            preferredMax: 18432,                  // 18KB
            dpi: 200,
            format: 'image/jpeg',
            outputName: 'thumb.jpg'
        }
    },
    DOCUMENT: {
        MAX_SIZE_MB: 2,
        MAX_SIZE_BYTES: 2 * 1024 * 1024
    }
};
