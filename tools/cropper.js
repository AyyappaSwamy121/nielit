// cropper.js - Handles image cropping modal and Cropper.js instance

const ImageCropper = {
    cropperInstance: null,
    currentType: null,
    currentFile: null,
    resolvePromise: null,

    init() {
        this.modalEl = document.getElementById('cropperModal');
        this.modal = new bootstrap.Modal(this.modalEl);
        this.imageEl = document.getElementById('cropper-image');
        
        document.getElementById('btn-crop-confirm').addEventListener('click', async () => {
            if (!this.cropperInstance) return;
            
            // Get cropped canvas at target dimensions
            const constraints = CONFIG.IMAGE[this.currentType.toUpperCase()];
            const canvas = this.cropperInstance.getCroppedCanvas({
                width: constraints.width,
                height: constraints.height,
                fillColor: '#fff', // White background for transparent PNGs
                imageSmoothingEnabled: true,
                imageSmoothingQuality: 'high',
            });
            
            // Close modal
            this.modal.hide();
            
            // Resolve promise with canvas
            if (this.resolvePromise) {
                this.resolvePromise(canvas);
            }
        });

        this.modalEl.addEventListener('hidden.bs.modal', () => {
            if (this.cropperInstance) {
                this.cropperInstance.destroy();
                this.cropperInstance = null;
            }
            this.imageEl.src = '';
        });
    },

    /**
     * Open the cropper modal for an image
     * @param {File} file 
     * @param {string} type 'photo', 'signature', 'thumb'
     * @returns {Promise<HTMLCanvasElement>} 
     */
    crop(file, type) {
        return new Promise((resolve) => {
            this.currentType = type;
            this.currentFile = file;
            this.resolvePromise = resolve;
            
            const constraints = CONFIG.IMAGE[type.toUpperCase()];
            const aspectRatio = constraints.width / constraints.height;
            
            document.getElementById('cropper-info').innerText = 
                `Target: ${constraints.width}x${constraints.height} (${type.toUpperCase()})`;

            const reader = new FileReader();
            reader.onload = (e) => {
                this.imageEl.src = e.target.result;
                this.modal.show();
                
                // Initialize cropper after modal is shown to ensure correct dimensions
                this.modalEl.addEventListener('shown.bs.modal', () => {
                    if (this.cropperInstance) this.cropperInstance.destroy();
                    this.cropperInstance = new Cropper(this.imageEl, {
                        aspectRatio: aspectRatio,
                        viewMode: 1,
                        dragMode: 'move',
                        autoCropArea: 1,
                        restore: false,
                        guides: true,
                        center: true,
                        highlight: false,
                        cropBoxMovable: true,
                        cropBoxResizable: true,
                        toggleDragModeOnDblclick: false,
                    });
                }, { once: true });
            };
            reader.readAsDataURL(file);
        });
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    ImageCropper.init();
});
