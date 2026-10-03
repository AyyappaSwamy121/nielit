/**
 * DocumentCompressor – iterative JPG/PNG/PDF → PDF size targeting.
 * Target: 45 KB | Allowed: 20–50 KB | Never exceed 50 KB.
 * Uses binary-search style refinement on scale + JPEG quality (not a fixed Q).
 */
const DocumentCompressor = (() => {
    const TARGET_BYTES = 45 * 1024;
    const MIN_BYTES = 20 * 1024;
    const MAX_BYTES = 50 * 1024;
    const MAX_INPUT_BYTES = 2 * 1024 * 1024;

    const ALLOWED_EXT = new Set(['jpg', 'jpeg', 'png', 'pdf']);
    const ALLOWED_MIME = new Set([
        'image/jpeg',
        'image/jpg',
        'image/png',
        'application/pdf',
        'application/x-pdf',
        '' // some browsers omit MIME for certain drops
    ]);

    function formatSize(bytes) {
        if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        return (bytes / 1024).toFixed(1) + ' KB';
    }

    function getExtension(name) {
        const i = name.lastIndexOf('.');
        return i >= 0 ? name.slice(i + 1).toLowerCase() : '';
    }

    function validateFile(file) {
        if (!file) throw new Error('No file provided.');
        const ext = getExtension(file.name);
        if (!ALLOWED_EXT.has(ext)) {
            throw new Error('Unsupported file format. Please upload JPG, JPEG, PNG, or PDF.');
        }
        const mime = (file.type || '').toLowerCase();
        if (mime && !ALLOWED_MIME.has(mime)) {
            // Extension ok but MIME clearly wrong (e.g. text/plain)
            if (!mime.startsWith('image/') && mime !== 'application/pdf' && mime !== 'application/octet-stream') {
                throw new Error('Unsupported file format. Please upload JPG, JPEG, PNG, or PDF.');
            }
        }
        if (file.size > MAX_INPUT_BYTES) {
            throw new Error('File size exceeds the 2 MB maximum.');
        }
        return ext;
    }

    function ensureLibs() {
        if (!window.jspdf || !window.jspdf.jsPDF) {
            throw new Error('PDF library not loaded. Please refresh the page.');
        }
    }

    async function loadImageElement(file) {
        const url = URL.createObjectURL(file);
        try {
            const img = await new Promise((resolve, reject) => {
                const el = new Image();
                el.onload = () => resolve(el);
                el.onerror = () => reject(new Error('Unable to convert this file to PDF.'));
                el.src = url;
            });
            return img;
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    function imageToCanvas(img) {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
        return canvas;
    }

    async function pdfFileToCanvases(file) {
        if (!window.pdfjsLib) {
            throw new Error('PDF viewer library not loaded. Please refresh the page.');
        }
        const data = new Uint8Array(await file.arrayBuffer());
        const pdf = await window.pdfjsLib.getDocument({ data }).promise;
        const canvases = [];
        const maxPages = Math.min(pdf.numPages, 10);
        for (let i = 1; i <= maxPages; i++) {
            const page = await pdf.getPage(i);
            // Render at decent base resolution; scale search will downscale later
            const base = page.getViewport({ scale: 1.5 });
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.floor(base.width));
            canvas.height = Math.max(1, Math.floor(base.height));
            const ctx = canvas.getContext('2d');
            await page.render({ canvasContext: ctx, viewport: base }).promise;
            canvases.push(canvas);
        }
        if (!canvases.length) {
            throw new Error('Unable to convert this file to PDF.');
        }
        return canvases;
    }

    function scaleCanvas(source, scale) {
        const w = Math.max(1, Math.round(source.width * scale));
        const h = Math.max(1, Math.round(source.height * scale));
        const c = document.createElement('canvas');
        c.width = w;
        c.height = h;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, w, h);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(source, 0, 0, w, h);
        return c;
    }

    function canvasToJpegDataUrl(canvas, quality) {
        return canvas.toDataURL('image/jpeg', quality);
    }

    function buildPdfBlob(canvases, scale, quality) {
        ensureLibs();
        const { jsPDF } = window.jspdf;
        let doc = null;

        canvases.forEach((src, idx) => {
            const scaled = scaleCanvas(src, scale);
            // Page size in mm from pixel dims @ 96 DPI approximation
            const pxToMm = 25.4 / 96;
            const pageW = Math.max(20, scaled.width * pxToMm);
            const pageH = Math.max(20, scaled.height * pxToMm);
            if (!doc) {
                doc = new jsPDF({
                    orientation: pageW >= pageH ? 'l' : 'p',
                    unit: 'mm',
                    format: [pageW, pageH],
                    compress: true
                });
            } else {
                doc.addPage([pageW, pageH], pageW >= pageH ? 'l' : 'p');
            }
            const dataUrl = canvasToJpegDataUrl(scaled, quality);
            doc.addImage(dataUrl, 'JPEG', 0, 0, pageW, pageH, undefined, 'FAST');
        });

        return doc.output('blob');
    }

    async function padPdfBlob(blob, targetBytes) {
        const buf = await blob.arrayBuffer();
        const current = buf.byteLength;
        if (current >= targetBytes) return blob;
        const need = Math.min(targetBytes - current, MAX_BYTES - current);
        if (need <= 0) return blob;
        const bytes = new Uint8Array(buf);
        const eof = [0x25, 0x25, 0x45, 0x4F, 0x46];
        let eofAt = -1;
        for (let i = bytes.length - 5; i >= 0; i--) {
            let ok = true;
            for (let j = 0; j < 5; j++) if (bytes[i + j] !== eof[j]) { ok = false; break; }
            if (ok) { eofAt = i; break; }
        }
        const header = '\n% PAD ';
        const padLen = Math.max(0, need - header.length - 1);
        const padStr = header + 'X'.repeat(padLen) + '\n';
        const padBytes = new TextEncoder().encode(padStr);
        let out;
        if (eofAt >= 0) {
            out = new Uint8Array(bytes.length + padBytes.length);
            out.set(bytes.subarray(0, eofAt), 0);
            out.set(padBytes, eofAt);
            out.set(bytes.subarray(eofAt), eofAt + padBytes.length);
        } else {
            out = new Uint8Array(bytes.length + padBytes.length);
            out.set(bytes, 0);
            out.set(padBytes, bytes.length);
        }
        return new Blob([out], { type: 'application/pdf' });
    }

    async function generateCandidate(canvases, scale, quality) {
        let blob = buildPdfBlob(canvases, scale, quality);
        // If under target and at high quality, pad toward target (never past MAX)
        if (blob.size < TARGET_BYTES && quality >= 0.92 && scale >= 0.95) {
            blob = await padPdfBlob(blob, Math.min(TARGET_BYTES, MAX_BYTES));
        } else if (blob.size < MIN_BYTES) {
            // Always try to reach at least MIN when content is tiny
            blob = await padPdfBlob(blob, Math.min(TARGET_BYTES, MAX_BYTES));
        }
        return blob;
    }

    /**
     * Iterative search: refine scale then quality to land closest to 45 KB
     * without exceeding 50 KB.
     */
    async function searchBest(canvases) {
        let bestValid = null;
        let bestDist = Infinity;
        let bestMeta = null;

        const consider = (blob, scale, quality) => {
            const size = blob.size;
            if (size > MAX_BYTES) return;
            if (size < MIN_BYTES) return;
            const dist = Math.abs(size - TARGET_BYTES);
            if (dist < bestDist || (dist === bestDist && size <= TARGET_BYTES && bestValid && bestValid.size > TARGET_BYTES)) {
                bestDist = dist;
                bestValid = blob;
                bestMeta = { scale, quality, size };
            }
        };

        // Coarse grid over scale × quality
        const scales = [1.0, 0.85, 0.7, 0.55, 0.4, 0.3, 0.22, 0.15];
        const qualities = [0.92, 0.8, 0.68, 0.55, 0.42, 0.32];

        for (const scale of scales) {
            for (const quality of qualities) {
                const blob = await generateCandidate(canvases, scale, quality);
                consider(blob, scale, quality);
                // Early exit on near-perfect hit
                if (bestValid && Math.abs(bestValid.size - TARGET_BYTES) <= 512) {
                    return { blob: bestValid, meta: bestMeta };
                }
            }
        }

        // Binary-search refine around best scale/quality if we have a seed,
        // or walk quality at mid scales if nothing valid yet.
        let loS = 0.12;
        let hiS = 1.0;
        let q = 0.75;

        for (let iter = 0; iter < 14; iter++) {
            const midS = (loS + hiS) / 2;
            const blob = await generateCandidate(canvases, midS, q);
            consider(blob, midS, q);

            if (blob.size > TARGET_BYTES) {
                hiS = midS;
            } else {
                loS = midS;
            }
        }

        // Quality refine at best scale
        const baseScale = bestMeta ? bestMeta.scale : (loS + hiS) / 2;
        let loQ = 0.25;
        let hiQ = 0.95;
        for (let iter = 0; iter < 12; iter++) {
            const midQ = (loQ + hiQ) / 2;
            const blob = await generateCandidate(canvases, baseScale, midQ);
            consider(blob, baseScale, midQ);
            if (blob.size > TARGET_BYTES) {
                hiQ = midQ;
            } else {
                loQ = midQ;
            }
        }

        // Extra pass: nudge scale in small steps near best
        if (bestMeta) {
            const neighbors = [
                bestMeta.scale * 0.92,
                bestMeta.scale * 0.96,
                bestMeta.scale,
                Math.min(1, bestMeta.scale * 1.04),
                Math.min(1, bestMeta.scale * 1.08)
            ];
            const qNeighbors = [
                Math.max(0.2, bestMeta.quality - 0.08),
                bestMeta.quality,
                Math.min(0.95, bestMeta.quality + 0.08)
            ];
            for (const s of neighbors) {
                for (const qq of qNeighbors) {
                    const blob = await generateCandidate(canvases, s, qq);
                    consider(blob, s, qq);
                }
            }
        }

        if (!bestValid) {
            throw new Error('Unable to compress the document within the required 20–50 KB range.');
        }
        return { blob: bestValid, meta: bestMeta };
    }

    /**
     * @param {File} file
     * @returns {Promise<{file: File, stats: object}>}
     */
    async function compress(file) {
        validateFile(file);
        ensureLibs();

        const ext = getExtension(file.name);
        let canvases;
        try {
            if (ext === 'pdf') {
                canvases = await pdfFileToCanvases(file);
            } else {
                const img = await loadImageElement(file);
                canvases = [imageToCanvas(img)];
            }
        } catch (e) {
            if (/Unable to convert|PDF viewer|library/i.test(e.message)) throw e;
            throw new Error('Unable to convert this file to PDF.');
        }

        const { blob, meta } = await searchBest(canvases);

        if (blob.size < MIN_BYTES || blob.size > MAX_BYTES) {
            throw new Error('Unable to compress the document within the required 20–50 KB range.');
        }

        const outName = (file.name.replace(/\.[^.]+$/, '') || 'document') + '.pdf';
        const outFile = new File([blob], outName, { type: 'application/pdf' });
        const compressionPct = file.size > 0
            ? (((file.size - outFile.size) / file.size) * 100).toFixed(1)
            : '0.0';

        return {
            file: outFile,
            stats: {
                originalName: file.name,
                originalSize: file.size,
                originalSizeLabel: formatSize(file.size),
                finalSize: outFile.size,
                finalSizeLabel: formatSize(outFile.size),
                outputFormat: 'PDF',
                compressionPercent: compressionPct,
                scale: meta.scale,
                quality: meta.quality,
                withinRange: outFile.size >= MIN_BYTES && outFile.size <= MAX_BYTES,
                targetKb: 45
            }
        };
    }

    return {
        compress,
        validateFile,
        formatSize,
        TARGET_BYTES,
        MIN_BYTES,
        MAX_BYTES,
        MAX_INPUT_BYTES
    };
})();
