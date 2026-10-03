// compressor.js - Government-Compliant Image Processing Engine
// QUALITY-FIRST: Only compress when image exceeds maximum allowed size.
// Never reduce quality merely because the image already satisfies minimum size.

const Compressor = {

    /**
     * Process an image to strict government specifications.
     *
     * Algorithm:
     *   1. Resize to EXACT required dimensions (high-quality interpolation)
     *   2. Export JPEG at Quality = 100
     *   3. If size > max allowed → binary search quality downward (floor = 80)
     *   4. If size is within allowed range at Q=100 → STOP, do NOT compress further
     *   5. If size < preferred minimum at Q=100 → add harmless metadata padding
     *   6. Embed DPI metadata into JPEG JFIF header
     *
     * @param {File} file           Original image file
     * @param {object} constraints  From CONFIG.IMAGE[type]
     * @returns {Promise<{file: File, stats: object}>}
     */
    async compress(file, constraints) {
        try {
            // ── Step 1: Decode source into highest-quality bitmap ──
            const sourceBitmap = await this._decodeToBitmap(file);

            // ── Step 2: Resize to EXACT target pixels ──
            const canvas = this._resizeToCanvas(sourceBitmap, constraints.width, constraints.height);
            if (sourceBitmap.close) sourceBitmap.close();

            // ── Step 3: Export at MAXIMUM quality (Q=100) ──
            let jpegBlob = await this._canvasToBlob(canvas, 1.0);
            let usedQuality = 100;

            // ── Step 4: ONLY compress if size EXCEEDS the maximum ──
            // If the image is already within the allowed range, we DO NOT touch it.
            if (jpegBlob.size > constraints.maxSize) {
                const result = await this._binarySearchQuality(canvas, constraints);
                jpegBlob = result.blob;
                usedQuality = result.quality;
            }
            // If size is within [minSize, maxSize] at Q=100 → keep it. No further compression.

            // ── Step 5: Embed DPI metadata into JFIF header ──
            const dpi = constraints.dpi || 300;
            let jpegArrayBuffer = await jpegBlob.arrayBuffer();
            jpegArrayBuffer = this._embedDPI(jpegArrayBuffer, dpi);

            // ── Step 6: If below preferred range at Q=100, add metadata padding ──
            // This increases file size without modifying ANY pixel data.
            let finalSize = jpegArrayBuffer.byteLength;
            if (usedQuality === 100 && finalSize < constraints.preferredMin && finalSize < constraints.maxSize) {
                // Pad up to preferredMin, but never exceed maxSize
                const paddingTarget = Math.min(constraints.preferredMin, constraints.maxSize);
                jpegArrayBuffer = this._addMetadataPadding(jpegArrayBuffer, paddingTarget);
                finalSize = jpegArrayBuffer.byteLength;
            }

            // ── Step 7: Build final File ──
            const outputName = constraints.outputName || 'output.jpg';
            const finalFile = new File([jpegArrayBuffer], outputName, { type: 'image/jpeg' });

            // ── Step 8: Assemble diagnostic stats ──
            const stats = {
                width: constraints.width,
                height: constraints.height,
                fileSize: finalFile.size,
                fileSizeKB: (finalFile.size / 1024).toFixed(2),
                quality: usedQuality,
                compressionRatio: ((1 - finalFile.size / file.size) * 100).toFixed(1),
                dpi: dpi,
                dpiEmbedded: true,
                isJpeg: true,
                withinSpec: finalFile.size >= constraints.minSize && finalFile.size <= constraints.maxSize,
                withinPreferred: finalFile.size >= constraints.preferredMin && finalFile.size <= constraints.preferredMax
            };

            return { file: finalFile, stats };

        } catch (error) {
            console.error('[Compressor] Fatal error:', error);
            throw new Error('Image compression failed: ' + error.message);
        }
    },

    // ═══════════════════════════════════════════════
    //  DECODE: Any image format → ImageBitmap
    // ═══════════════════════════════════════════════
    async _decodeToBitmap(file) {
        if (typeof createImageBitmap === 'function') {
            return createImageBitmap(file);
        }
        // Fallback for older browsers
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = URL.createObjectURL(file);
        });
    },

    // ═══════════════════════════════════════════════
    //  RESIZE: Exact pixel dimensions, best quality
    //  Uses multi-step halving for large source images
    //  to preserve skin tones, hair detail, eye sharpness
    // ═══════════════════════════════════════════════
    _resizeToCanvas(source, targetW, targetH) {
        const canvas = document.createElement('canvas');
        canvas.width = targetW;
        canvas.height = targetH;
        const ctx = canvas.getContext('2d');

        // White background (handles transparent PNGs / WebP)
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, targetW, targetH);

        // Highest quality smoothing — preserves facial edges and details
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        const srcW = source.width;
        const srcH = source.height;

        // Multi-step downscale for large images (>2× target)
        if (srcW > targetW * 2 || srcH > targetH * 2) {
            const stepped = this._stepDownResize(source, srcW, srcH, targetW, targetH);
            ctx.drawImage(stepped, 0, 0, targetW, targetH);
        } else {
            ctx.drawImage(source, 0, 0, targetW, targetH);
        }

        return canvas;
    },

    /**
     * Multi-step halving for large-to-small resizes.
     * Each step halves dimensions until within 2× of target.
     * Prevents jagged edges and preserves fine detail.
     */
    _stepDownResize(source, srcW, srcH, targetW, targetH) {
        let currentW = srcW;
        let currentH = srcH;
        let currentSource = source;

        while (currentW > targetW * 2 || currentH > targetH * 2) {
            const nextW = Math.max(Math.floor(currentW / 2), targetW);
            const nextH = Math.max(Math.floor(currentH / 2), targetH);

            const stepCanvas = document.createElement('canvas');
            stepCanvas.width = nextW;
            stepCanvas.height = nextH;
            const stepCtx = stepCanvas.getContext('2d');
            stepCtx.imageSmoothingEnabled = true;
            stepCtx.imageSmoothingQuality = 'high';
            stepCtx.drawImage(currentSource, 0, 0, nextW, nextH);

            currentSource = stepCanvas;
            currentW = nextW;
            currentH = nextH;
        }

        return currentSource;
    },

    // ═══════════════════════════════════════════════
    //  BINARY SEARCH: ONLY invoked when Q=100 > maxSize
    //  Finds the HIGHEST quality that fits within maxSize.
    //  Floor: quality 80 (extends lower only if forced)
    // ═══════════════════════════════════════════════
    async _binarySearchQuality(canvas, constraints) {
        const { maxSize } = constraints;

        let lo = 0.80;  // Never go below 80% unless absolutely forced
        let hi = 1.0;
        let bestBlob = null;
        let bestQuality = 100;

        // First: check if Q=80 is sufficient
        const testBlob = await this._canvasToBlob(canvas, lo);
        if (testBlob.size > maxSize) {
            // Even Q=80 is too large — reluctantly extend search below 80
            lo = 0.30;
        }

        // Binary search: find highest quality that fits
        for (let i = 0; i < 14; i++) {
            const mid = (lo + hi) / 2;
            const blob = await this._canvasToBlob(canvas, mid);

            if (blob.size > maxSize) {
                // Still too large — reduce quality
                hi = mid;
            } else {
                // Fits — remember this as best (highest quality that fits)
                bestBlob = blob;
                bestQuality = Math.round(mid * 100);
                lo = mid; // Try even higher quality
            }

            // Converged close enough
            if (hi - lo < 0.003) break;
        }

        if (!bestBlob) {
            // Absolute fallback
            bestBlob = await this._canvasToBlob(canvas, 0.30);
            bestQuality = 30;
        }

        return { blob: bestBlob, quality: bestQuality };
    },

    // ═══════════════════════════════════════════════
    //  DPI EMBEDDING: Modify JFIF APP0 density fields
    //  or inject a JFIF segment if one doesn't exist
    // ═══════════════════════════════════════════════
    _embedDPI(arrayBuffer, dpi) {
        const bytes = new Uint8Array(arrayBuffer);

        // Verify SOI marker (FF D8)
        if (bytes[0] !== 0xFF || bytes[1] !== 0xD8) {
            console.warn('[Compressor] Not a valid JPEG, skipping DPI embed');
            return arrayBuffer;
        }

        // Check for existing JFIF APP0 marker at bytes[2..3] = FF E0
        if (bytes[2] === 0xFF && bytes[3] === 0xE0) {
            // Verify JFIF identifier at bytes[6..9] = "JFIF"
            const ident = String.fromCharCode(bytes[6], bytes[7], bytes[8], bytes[9]);
            if (ident === 'JFIF') {
                // JFIF header structure (offsets from SOI start):
                //   [2..3]   = FF E0 (APP0 marker)
                //   [4..5]   = segment length
                //   [6..10]  = "JFIF\0"
                //   [11..12] = version (01 01)
                //   [13]     = density units (01 = dots per inch)
                //   [14..15] = X density (big-endian)
                //   [16..17] = Y density (big-endian)
                bytes[13] = 0x01; // Units = DPI
                bytes[14] = (dpi >> 8) & 0xFF;
                bytes[15] = dpi & 0xFF;
                bytes[16] = (dpi >> 8) & 0xFF;
                bytes[17] = dpi & 0xFF;
                return bytes.buffer;
            }
        }

        // No JFIF header found — inject one right after SOI
        const jfifSegment = new Uint8Array([
            0xFF, 0xE0,                           // APP0 marker
            0x00, 0x10,                           // Length: 16 bytes
            0x4A, 0x46, 0x49, 0x46, 0x00,         // "JFIF\0"
            0x01, 0x01,                           // Version 1.1
            0x01,                                 // Units: DPI
            (dpi >> 8) & 0xFF, dpi & 0xFF,        // X density
            (dpi >> 8) & 0xFF, dpi & 0xFF,        // Y density
            0x00, 0x00                            // No thumbnail
        ]);

        // Build: SOI + new JFIF + rest of original JPEG
        const result = new Uint8Array(2 + jfifSegment.length + bytes.length - 2);
        result[0] = 0xFF;
        result[1] = 0xD8;
        result.set(jfifSegment, 2);
        result.set(bytes.subarray(2), 2 + jfifSegment.length);
        return result.buffer;
    },

    // ═══════════════════════════════════════════════
    //  METADATA PADDING: Harmless JPEG COM segments
    //  Increases file size WITHOUT modifying pixels.
    //  Uses standard JPEG Comment (COM / FF FE) segments.
    // ═══════════════════════════════════════════════
    _addMetadataPadding(arrayBuffer, targetSize) {
        const currentSize = arrayBuffer.byteLength;
        if (currentSize >= targetSize) return arrayBuffer;

        const deficit = targetSize - currentSize;
        // COM segment overhead: 2 (marker FF FE) + 2 (length) = 4 bytes
        const paddingPayload = deficit - 4;
        if (paddingPayload <= 0) return arrayBuffer;

        // Clamp to max COM segment payload (65533 bytes) — more than enough
        const payloadSize = Math.min(paddingPayload, 65533);

        // Build COM segment: FF FE + length(2 bytes, big-endian, includes self) + payload
        const comSegment = new Uint8Array(4 + payloadSize);
        comSegment[0] = 0xFF;
        comSegment[1] = 0xFE; // COM marker
        const segLen = payloadSize + 2; // Length field includes itself but not marker
        comSegment[2] = (segLen >> 8) & 0xFF;
        comSegment[3] = segLen & 0xFF;
        // Fill payload with spaces (0x20) — completely harmless
        for (let i = 4; i < comSegment.length; i++) {
            comSegment[i] = 0x20;
        }

        // Insert COM segment right after SOI (first 2 bytes)
        const original = new Uint8Array(arrayBuffer);
        const result = new Uint8Array(original.length + comSegment.length);
        result[0] = original[0]; // FF
        result[1] = original[1]; // D8
        result.set(comSegment, 2);
        result.set(original.subarray(2), 2 + comSegment.length);
        return result.buffer;
    },

    // ═══════════════════════════════════════════════
    //  UTILITY: Canvas → JPEG Blob
    // ═══════════════════════════════════════════════
    _canvasToBlob(canvas, quality) {
        return new Promise((resolve, reject) => {
            canvas.toBlob(
                (blob) => blob ? resolve(blob) : reject(new Error('toBlob returned null')),
                'image/jpeg',
                quality
            );
        });
    },

    // Public utility — also used by upload.js for initial canvas export
    canvasToBlob(canvas, mimeType, quality) {
        return new Promise(resolve => canvas.toBlob(resolve, mimeType, quality));
    }
};
