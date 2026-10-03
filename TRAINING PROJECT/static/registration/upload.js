// upload.js - Handles the entire file upload and processing pipeline

const UploadManager = {
    // Store processed files (base64)
    files: {
        photo: null,
        signature: null,
        thumb: null,
        aadhaar: null,
        community: null,
        registration: null,
        abc: null,
        supporting: null
    },

    init() {
        // Bind Image Inputs
        const imageInputs = document.querySelectorAll('.file-input');
        imageInputs.forEach(input => {
            input.addEventListener('change', (e) => this.handleImageUpload(e));
        });

        // Bind PDF/Doc Inputs
        const docInputs = [
            { id: 'input-aadhaar', key: 'aadhaar' },
            { id: 'input-community', key: 'community' },
            { id: 'input-registration', key: 'registration' },
            { id: 'input-abc', key: 'abc' },
            { id: 'input-supporting', key: 'supporting' }
        ];

        docInputs.forEach(doc => {
            const el = document.getElementById(doc.id);
            if (el) {
                el.addEventListener('change', (e) => this.handleDocumentUpload(e, doc.key));
            }
        });
        
        // Restore from LocalStorage if exists
        this.restoreState();
    },

    async handleImageUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const type = e.target.dataset.type; // 'photo', 'signature', 'thumb'
        const constraints = CONFIG.IMAGE[type.toUpperCase()];
        const statusEl = document.getElementById(`status-${type}`);
        
        try {
            statusEl.innerHTML = `<span class="text-info"><span class="spinner-border spinner-border-sm me-1"></span> Processing...</span>`;
            
            // 1. Crop to exact aspect ratio
            const canvas = await ImageCropper.crop(file, type);
            
            // 2. Validate (Face, Blur, Background)
            statusEl.innerHTML = `<span class="text-info"><span class="spinner-border spinner-border-sm me-1"></span> Validating quality...</span>`;
            const validation = await Validator.validate(canvas, type);
            
            if (!validation.valid) {
                let errorHtml = validation.errors.map(err => `<div class="d-flex align-items-start"><span class="material-icons-round fs-6 me-1 text-danger">close</span>${err}</div>`).join('');
                statusEl.innerHTML = `<div class="validation-status error">${errorHtml}</div>`;
                e.target.value = '';
                return;
            }

            // 3. Compress to exact government specifications
            statusEl.innerHTML = `<span class="text-info"><span class="spinner-border spinner-border-sm me-1"></span> Processing at maximum quality...</span>`;
            
            // Create a temporary file from the cropped canvas at full quality
            const blob = await Compressor.canvasToBlob(canvas, constraints.format, 1.0);
            const tempFile = new File([blob], constraints.outputName, { type: constraints.format });
            
            const { file: compressedFile, stats } = await Compressor.compress(tempFile, constraints);
            
            // 4. Final compliance verification
            if (!stats.withinSpec) {
                statusEl.innerHTML = `<span class="validation-status error">
                    <span class="material-icons-round fs-6 me-1">error</span>
                    Output ${stats.fileSizeKB}KB is outside ${constraints.minSize/1024}-${constraints.maxSize/1024}KB range.
                </span>`;
                e.target.value = '';
                return;
            }

            // 5. Success — Convert to Base64 and Store
            const base64Data = await Utils.fileToBase64(compressedFile);
            this.files[type] = base64Data;
            
            // Update Preview
            const previewEl = document.getElementById(`preview-${type}`);
            previewEl.innerHTML = `<img src="data:${base64Data.mimeType};base64,${base64Data.base64}" style="width:100%; height:100%; object-fit:cover;" alt="${type}">`;
            
            // Show validation checklist panel
            const dpiLabel = stats.dpiEmbedded ? `${stats.dpi} DPI (Embedded)` : `${stats.dpi} DPI (Browser Limitation)`;
            const prefLabel = stats.withinPreferred
                ? '<span class="text-success">✔ Within Preferred Range</span>'
                : '<span class="text-warning">⚠ Outside Preferred (Valid)</span>';

            statusEl.innerHTML = `
                <div class="validation-status success">
                    <div class="d-flex align-items-center mb-1">
                        <span class="material-icons-round fs-6 me-1">verified</span>
                        <strong>Government Compliant</strong>
                    </div>
                    <div style="font-size: 0.72rem; line-height: 1.7;">
                        <div class="text-success">✔ JPEG</div>
                        <div class="text-success">✔ ${stats.width} × ${stats.height} px</div>
                        <div class="text-success">✔ ${dpiLabel}</div>
                        <div class="text-success">✔ Quality: ${stats.quality}%</div>
                        <div class="text-success">✔ Size: <strong>${stats.fileSizeKB} KB</strong></div>
                        <div>${prefLabel}</div>
                    </div>
                </div>`;
            
            this.saveState();
            Utils.showToast(`${type.toUpperCase()}: ${stats.fileSizeKB}KB · Q${stats.quality}% · ${stats.width}×${stats.height}`, 'success');

        } catch (error) {
            console.error("Pipeline error:", error);
            statusEl.innerHTML = `<span class="validation-status error"><span class="material-icons-round fs-6 me-1">error</span> ${error.message}</span>`;
            e.target.value = '';
        }
    },

    async handleDocumentUpload(e, key) {
        const file = e.target.files[0];
        if (!file) return;

        if (file.size > CONFIG.DOCUMENT.MAX_SIZE_BYTES) {
            Utils.showToast(`${file.name} is too large. Max size is 2MB.`, 'danger');
            e.target.value = '';
            return;
        }

        try {
            const base64Data = await Utils.fileToBase64(file);
            this.files[key] = base64Data;
            Utils.showToast(`${key.toUpperCase()} uploaded successfully!`, 'success');
            this.saveState();
        } catch (error) {
            console.error("Document upload error:", error);
            Utils.showToast(`Failed to process ${key}.`, 'danger');
            e.target.value = '';
        }
    },

    saveState() {
        // Exclude large base64 strings from localstorage to prevent QuotaExceededError
        // Instead, we just keep them in memory.
        // For a true PWA we might use IndexedDB, but for now we rely on memory for files.
        const fileNames = {};
        for (const [key, data] of Object.entries(this.files)) {
            if (data) fileNames[key] = data.name;
        }
        localStorage.setItem('admission_files_meta', JSON.stringify(fileNames));
    },

    restoreState() {
        // We cannot restore actual File objects due to browser security,
        // and we are not storing huge base64 in LocalStorage.
        // If user refreshes, they must re-upload files.
        // We will just clear the inputs.
    },
    
    validateAllRequired() {
        const required = ['photo', 'signature', 'thumb', 'aadhaar', 'community', 'registration', 'abc'];
        const missing = required.filter(key => !this.files[key]);
        return missing;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    UploadManager.init();
});
