// script.js - Main Application UI Logic (Stepper, Theme, Flow)

document.addEventListener('DOMContentLoaded', () => {
    
    // Theme toggling
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    
    // Check local storage for theme
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        themeIcon.innerText = 'light_mode';
    }

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        if (document.body.classList.contains('dark-mode')) {
            themeIcon.innerText = 'light_mode';
            localStorage.setItem('theme', 'dark');
        } else {
            themeIcon.innerText = 'dark_mode';
            localStorage.setItem('theme', 'light');
        }
    });

    // View Navigation
    const viewInstructions = document.getElementById('view-instructions');
    const viewForm = document.getElementById('view-form');
    const viewLoading = document.getElementById('view-loading');
    const viewSuccess = document.getElementById('view-success');

    const agreeCheck = document.getElementById('agree-instructions');
    const btnStart = document.getElementById('btn-start-app');

    agreeCheck.addEventListener('change', (e) => {
        btnStart.disabled = !e.target.checked;
    });

    btnStart.addEventListener('click', () => {
        viewInstructions.classList.add('d-none');
        viewInstructions.classList.remove('active');
        viewForm.classList.remove('d-none');
        viewForm.classList.add('active');
    });

    // Stepper Logic
    let currentStep = 1;
    const maxSteps = 4;

    const updateStepperUI = () => {
        document.querySelectorAll('.stepper-item').forEach(el => {
            const step = parseInt(el.dataset.step);
            el.classList.remove('active', 'completed');
            if (step < currentStep) el.classList.add('completed');
            if (step === currentStep) el.classList.add('active');
        });

        document.querySelectorAll('.form-step').forEach(el => {
            el.classList.add('d-none');
            el.classList.remove('active');
        });

        const activeStep = document.getElementById(`step-${currentStep}`);
        activeStep.classList.remove('d-none');
        activeStep.classList.add('active');
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    document.querySelectorAll('.btn-next').forEach(btn => {
        btn.addEventListener('click', () => {
            if (currentStep === 1 || currentStep === 2) {
                if (!FormManager.validateStep(currentStep)) return;
            }
            if (currentStep === 3) {
                const missing = UploadManager.validateAllRequired();
                if (missing.length > 0) {
                    Utils.showToast(`Please upload: ${missing.map(m=>m.toUpperCase()).join(', ')}`, 'danger');
                    return;
                }
                FormManager.generateReview();
            }
            
            if (currentStep < maxSteps) {
                currentStep++;
                updateStepperUI();
            }
        });
    });

    document.querySelectorAll('.btn-prev').forEach(btn => {
        btn.addEventListener('click', () => {
            if (currentStep > 1) {
                currentStep--;
                updateStepperUI();
            }
        });
    });

    // Final Submission Logic
    const submitBtn = document.getElementById('btn-submit');
    const declaration = document.getElementById('declaration');

    submitBtn.addEventListener('click', async (e) => {
        e.preventDefault();

        if (!declaration.checked) {
            Utils.showToast("You must agree to the declaration.", "warning");
            declaration.classList.add('is-invalid');
            return;
        }

        // Prepare payload
        const payload = {
            metadata: {
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent
            },
            formData: FormManager.formData,
            files: UploadManager.files
        };

        // Switch to Loading View
        viewForm.classList.add('d-none');
        viewLoading.classList.remove('d-none');

        const pBar = document.getElementById('submission-progress');
        
        try {
            const onProgress = (msg, percent) => {
                pBar.style.width = `${percent}%`;
                pBar.innerText = `${percent}%`;
                // Add tick to previous items visually
                const statuses = ['Generating Application ID...', 'Compressing Images...', 'Uploading Files to Drive...', 'Saving Records...'];
                // We fake the visual steps based on percentage
                if(percent >= 40) document.getElementById('status-1').innerText = 'check_circle';
                if(percent >= 80) document.getElementById('status-2').innerText = 'check_circle';
                if(percent === 100) {
                    document.getElementById('status-3').innerText = 'check_circle';
                    document.getElementById('status-4').innerText = 'check_circle';
                }
            };

            // Fake some initial progress
            onProgress('Generating Application ID...', 10);
            await new Promise(r => setTimeout(r, 1000));
            onProgress('Preparing Payload...', 20);

            // Call API
            const result = await API.submitApplication(payload, onProgress);

            // Show Success
            viewLoading.classList.add('d-none');
            viewSuccess.classList.remove('d-none');

            document.getElementById('success-app-id').innerText = result.applicationId;
            document.getElementById('success-email').innerText = FormManager.formData.email;
            
            // Clear Storage
            localStorage.removeItem('admission_form_data');
            localStorage.removeItem('admission_files_meta');

        } catch (error) {
            console.error("Submission failed", error);
            Utils.showToast(error.message, 'danger');
            
            // Go back to review step
            viewLoading.classList.add('d-none');
            viewForm.classList.remove('d-none');
        }
    });

    // PDF Receipt Download Logic
    document.getElementById('btn-download-receipt').addEventListener('click', () => {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        doc.setFontSize(22);
        doc.setTextColor(11, 94, 215);
        doc.text("Admission Receipt", 105, 20, null, null, "center");
        
        doc.setFontSize(12);
        doc.setTextColor(0, 0, 0);
        doc.text(`Application ID: ${document.getElementById('success-app-id').innerText}`, 20, 40);
        doc.text(`Name: ${FormManager.formData.fullName}`, 20, 50);
        doc.text(`Email: ${FormManager.formData.email}`, 20, 60);
        doc.text(`Program: ${FormManager.formData.program}`, 20, 70);
        doc.text(`Date: ${new Date().toLocaleDateString()}`, 20, 80);
        
        doc.setFontSize(10);
        doc.text("This is an auto-generated receipt. Please keep it for future reference.", 105, 280, null, null, "center");

        doc.save(`${document.getElementById('success-app-id').innerText}_Receipt.pdf`);
    });
});
