// form.js - Form state management, validation, and review generation

const FormManager = {
    formData: {},

    init() {
        this.formEl = document.getElementById('application-form');
        this.restoreState();

        // Listen for input changes to save to LocalStorage continuously
        this.formEl.addEventListener('input', Utils.debounce((e) => {
            if (e.target.name) {
                this.formData[e.target.name] = e.target.value;
                this.saveState();
            }
        }, 500));
        
        // Prevent default submit
        this.formEl.addEventListener('submit', (e) => e.preventDefault());
    },

    saveState() {
        localStorage.setItem('admission_form_data', JSON.stringify(this.formData));
    },

    restoreState() {
        const saved = localStorage.getItem('admission_form_data');
        if (saved) {
            try {
                this.formData = JSON.parse(saved);
                Object.keys(this.formData).forEach(key => {
                    const el = this.formEl.querySelector(`[name="${key}"]`);
                    if (el) el.value = this.formData[key];
                });
            } catch(e) {
                console.error("Error restoring form state", e);
            }
        }
    },

    /**
     * Validates a specific step inside the form
     * @param {number} step 
     * @returns boolean
     */
    validateStep(step) {
        const stepEl = document.getElementById(`step-${step}`);
        if (!stepEl) return true;

        // Force browser HTML5 validation UI
        const inputs = stepEl.querySelectorAll('input, select, textarea');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.checkValidity()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
            }
        });

        // Trigger bootstrap validation styles
        if (!isValid) {
            Utils.showToast("Please fill all required fields correctly.", "warning");
        }

        return isValid;
    },

    /**
     * Generates HTML for the Review Step
     */
    generateReview() {
        const container = document.getElementById('review-container');
        
        // Ensure formData is perfectly synced
        const fd = new FormData(this.formEl);
        for(let [key, val] of fd.entries()) {
            this.formData[key] = val;
        }

        const escapeHtml = (unsafe) => {
            if(!unsafe) return '-';
            return unsafe
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        };

        const html = `
            <h4 class="mb-4 text-primary fw-bold border-bottom pb-2">Review Application</h4>
            
            <h6 class="fw-bold text-secondary mb-3 mt-4">Personal Information</h6>
            <div class="row g-3 text-sm">
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Full Name</span><strong>${escapeHtml(this.formData.fullName)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">DOB</span><strong>${escapeHtml(this.formData.dob)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Gender</span><strong>${escapeHtml(this.formData.gender)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Father's Name</span><strong>${escapeHtml(this.formData.fatherName)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Mother's Name</span><strong>${escapeHtml(this.formData.motherName)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Religion / Community</span><strong>${escapeHtml(this.formData.religion)} / ${escapeHtml(this.formData.community)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Mobile</span><strong>${escapeHtml(this.formData.mobile)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Email</span><strong>${escapeHtml(this.formData.email)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Aadhaar</span><strong>XXXX-XXXX-${this.formData.aadhaar ? this.formData.aadhaar.slice(-4) : ''}</strong></div>
            </div>

            <h6 class="fw-bold text-secondary mb-3 mt-4">Address</h6>
            <div class="row g-3 text-sm">
                <div class="col-12"><span class="text-muted d-block small">Full Address</span><strong>${escapeHtml(this.formData.address)}, ${escapeHtml(this.formData.district)}, ${escapeHtml(this.formData.state)} - ${escapeHtml(this.formData.pincode)}</strong></div>
            </div>

            <h6 class="fw-bold text-secondary mb-3 mt-4">Education Details</h6>
            <div class="row g-3 text-sm">
                <div class="col-6 col-md-4"><span class="text-muted d-block small">ABC ID</span><strong>${escapeHtml(this.formData.abcId)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Institution</span><strong>${escapeHtml(this.formData.institution)}</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Program</span><strong>${escapeHtml(this.formData.program)} (${escapeHtml(this.formData.admissionYear)})</strong></div>
                <div class="col-6 col-md-4"><span class="text-muted d-block small">Registration No.</span><strong>${escapeHtml(this.formData.regNumber)}</strong></div>
            </div>
            
            <h6 class="fw-bold text-secondary mb-3 mt-4">Uploaded Files Status</h6>
            <div class="row g-3 text-sm">
                ${Object.keys(UploadManager.files).map(k => {
                    const status = UploadManager.files[k] ? '<span class="text-success"><span class="material-icons-round fs-6 align-middle">check_circle</span> Uploaded</span>' : '<span class="text-danger">Missing</span>';
                    return `<div class="col-6 col-md-3"><span class="text-muted d-block small">${k.toUpperCase()}</span><strong>${status}</strong></div>`;
                }).join('')}
            </div>
        `;
        
        container.innerHTML = html;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    FormManager.init();
});
