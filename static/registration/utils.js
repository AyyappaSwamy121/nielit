// Utility Functions

const Utils = {
    /**
     * Show a Bootstrap toast notification
     * @param {string} message 
     * @param {string} type 'success', 'danger', 'warning', 'info'
     */
    showToast(message, type = 'info') {
        const container = document.querySelector('.toast-container');
        const id = 'toast-' + Date.now();
        
        const iconMap = {
            'success': 'check_circle',
            'danger': 'error',
            'warning': 'warning',
            'info': 'info'
        };

        const html = `
            <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body d-flex align-items-center">
                        <span class="material-icons-round me-2">${iconMap[type]}</span>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', html);
        const toastEl = document.getElementById(id);
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();
        
        // Remove from DOM after hiding
        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    },

    /**
     * Convert File to Base64
     * @param {File} file 
     * @returns {Promise<string>} Base64 string without data prefix
     */
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                // Remove data:image/jpeg;base64, prefix
                const base64String = reader.result.split(',')[1];
                resolve({
                    base64: base64String,
                    mimeType: file.type,
                    name: file.name
                });
            };
            reader.onerror = error => reject(error);
        });
    },

    /**
     * Format bytes to readable size
     */
    formatBytes(bytes, decimals = 2) {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }
};
