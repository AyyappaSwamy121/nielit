// validator.js - Image Validation Engine (Face, Blur, Brightness, Background)

const Validator = {
    faceDetector: null,
    
    /**
     * Initialize MediaPipe Face Detection
     */
    async initFaceDetection() {
        if (this.faceDetector) return;
        
        try {
            this.faceDetector = new FaceDetection({locateFile: (file) => {
                return `https://cdn.jsdelivr.net/npm/@mediapipe/face_detection/${file}`;
            }});
            this.faceDetector.setOptions({
                model: 'short',
                minDetectionConfidence: 0.5
            });
        } catch (e) {
            console.error("Failed to init Face Detection", e);
        }
    },

    /**
     * Validate the cropped image canvas based on its type
     * @param {HTMLCanvasElement} canvas 
     * @param {string} type 'photo', 'signature', 'thumb'
     * @returns {Promise<object>} { valid: boolean, errors: array }
     */
    async validate(canvas, type) {
        const errors = [];
        const ctx = canvas.getContext('2d');
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        
        // 1. Basic Image Quality (Brightness, Contrast, Blur)
        const quality = this.checkImageQuality(imgData);
        
        if (quality.isBlurry) errors.push("Image appears too blurry.");
        if (quality.brightness < 40) errors.push("Image is too dark.");
        if (quality.brightness > 240) errors.push("Image is too bright/washed out.");
        if (quality.contrast < 20) errors.push("Image contrast is too low.");

        // 2. Background Check (Estimates if background is somewhat uniform/light)
        const bgWhite = this.checkLightBackground(imgData);
        if (!bgWhite && type === 'photo') {
            errors.push("Background does not appear to be light/white.");
        }

        // 3. Face Detection (Photo only)
        if (type === 'photo') {
            await this.initFaceDetection();
            if (this.faceDetector) {
                // MediaPipe requires an image/video/canvas element
                const tempImg = new Image();
                tempImg.src = canvas.toDataURL('image/jpeg');
                await new Promise(resolve => tempImg.onload = resolve);
                
                let faceCount = 0;
                let isCentered = false;
                
                this.faceDetector.onResults((results) => {
                    if (results.detections && results.detections.length > 0) {
                        faceCount = results.detections.length;
                        
                        // Check if main face is roughly centered and covers decent area
                        const box = results.detections[0].boundingBox;
                        // box coordinates are normalized [0.0, 1.0]
                        const centerX = box.xCenter;
                        if (centerX > 0.35 && centerX < 0.65) {
                            isCentered = true;
                        }
                    }
                });
                
                await this.faceDetector.send({image: tempImg});
                
                if (faceCount === 0) errors.push("No face detected in the photo.");
                if (faceCount > 1) errors.push("Multiple faces detected. Only one face allowed.");
                if (faceCount === 1 && !isCentered) errors.push("Face is not centered in the frame.");
            }
        }

        // 4. Blank Check (Signature / Thumb)
        if (type === 'signature' || type === 'thumb') {
            const isBlank = this.checkIfBlank(imgData);
            if (isBlank) errors.push("The image appears to be completely blank.");
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    },

    /**
     * Native Canvas check for brightness, contrast, and laplacian variance (blur)
     */
    checkImageQuality(imageData) {
        const data = imageData.data;
        let r, g, b;
        let colorSum = 0;
        
        let min = 255;
        let max = 0;
        
        // Convert to grayscale and calculate simple blur metric (adjacent pixel variance)
        let diffSum = 0;

        for (let x = 0, len = data.length; x < len; x += 4) {
            r = data[x];
            g = data[x + 1];
            b = data[x + 2];
            
            const avg = Math.floor((r + g + b) / 3);
            colorSum += avg;
            
            if (avg < min) min = avg;
            if (avg > max) max = avg;
            
            // Simple edge detection for blur
            if (x > 4) {
                const prevR = data[x - 4];
                const prevG = data[x - 3];
                const prevB = data[x - 2];
                const prevAvg = Math.floor((prevR + prevG + prevB) / 3);
                diffSum += Math.abs(avg - prevAvg);
            }
        }

        const brightness = Math.floor(colorSum / (imageData.width * imageData.height));
        const contrast = max - min;
        const blurScore = diffSum / (imageData.width * imageData.height); // Higher = sharper

        return {
            brightness,
            contrast,
            isBlurry: blurScore < 5.0, // Threshold needs tuning based on real images
            blurScore
        };
    },

    checkLightBackground(imageData) {
        const data = imageData.data;
        let lightPixels = 0;
        // Check edges of the image to determine background color
        const w = imageData.width;
        const h = imageData.height;
        
        // Sample border pixels
        const sampleSize = w * 2 + h * 2; 
        
        const isLight = (r, g, b) => (r > 200 && g > 200 && b > 200);

        for (let i = 0; i < w; i++) {
            // Top edge
            let idx = (i) * 4;
            if (isLight(data[idx], data[idx+1], data[idx+2])) lightPixels++;
            // Bottom edge
            idx = ((h - 1) * w + i) * 4;
            if (isLight(data[idx], data[idx+1], data[idx+2])) lightPixels++;
        }
        for (let j = 0; j < h; j++) {
            // Left edge
            let idx = (j * w) * 4;
            if (isLight(data[idx], data[idx+1], data[idx+2])) lightPixels++;
            // Right edge
            idx = (j * w + (w - 1)) * 4;
            if (isLight(data[idx], data[idx+1], data[idx+2])) lightPixels++;
        }

        const lightRatio = lightPixels / sampleSize;
        return lightRatio > 0.4; // At least 40% of edge pixels are light/white
    },

    checkIfBlank(imageData) {
        const data = imageData.data;
        let darkPixels = 0;
        for (let i = 0; i < data.length; i += 4) {
            const avg = (data[i] + data[i+1] + data[i+2]) / 3;
            if (avg < 200) darkPixels++; // Not white
        }
        const darkRatio = darkPixels / (imageData.width * imageData.height);
        return darkRatio < 0.01; // Less than 1% of pixels are ink
    }
};
