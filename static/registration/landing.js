// landing.js - Landing Page Logic for Find Registration / Continue Registration

(function() {
    'use strict';

    // DOM Elements
    const form = document.getElementById('landingSearchForm');
    const searchBySelect = document.getElementById('findSearchBy');
    const searchInput = document.getElementById('findSearchInput');
    const searchLabel = document.getElementById('findSearchLabel');
    const searchIcon = document.getElementById('findInputIcon');
    const continueBtn = document.getElementById('btnContinueFind');
    const continueBtnText = document.getElementById('btnContinueFindText');
    const continueSpinner = continueBtn.querySelector('.spinner-border');
    const resultContainer = document.getElementById('landingResultContainer');
    const searchError = document.getElementById('findSearchError');

    // API URL from form data attribute
    const findRegistrationUrl = form.dataset.findUrl;
    const registrationUrl = form.dataset.registrationUrl;

    // Configuration for search types
    const searchConfigs = {
        aadhaar: {
            label: 'Enter your Aadhaar Number',
            placeholder: 'Enter 12-digit Aadhaar Number',
            maxlength: 12,
            inputmode: 'numeric',
            icon: 'fingerprint',
            pattern: /^\d{12}$/,
            validationMessage: 'Please enter a valid 12-digit Aadhaar Number.'
        },
        email: {
            label: 'Enter your Email Address',
            placeholder: 'Enter your Email Address',
            maxlength: 254,
            inputmode: 'email',
            icon: 'email',
            pattern: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
            validationMessage: 'Please enter a valid Email Address.'
        }
    };

    // Initialize
    function init() {
        setupEventListeners();
        updateInputConfig('aadhaar'); // Default
    }

    function setupEventListeners() {
        // Search by change
        searchBySelect.addEventListener('change', function() {
            updateInputConfig(this.value);
            hideResult();
            clearValidation();
        });

        // Input validation on blur and input
        searchInput.addEventListener('input', function() {
            sanitizeAadhaarInput(this);
            validateInput();
            updateContinueButtonState();
            hideResult();
        });

        searchInput.addEventListener('blur', function() {
            validateInput();
        });

        // Prevent non-numeric input for Aadhaar field
        searchInput.addEventListener('keydown', function(e) {
            if (this.getAttribute('data-type') === 'aadhaar') {
                const allowedKeys = ['Backspace', 'Delete', 'Tab', 'ArrowLeft', 'ArrowRight', 'Home', 'End'];
                if (allowedKeys.includes(e.key)) return;
                if (e.key.length === 1 && !/^\d$/.test(e.key)) {
                    e.preventDefault();
                }
            }
        });

        searchInput.addEventListener('paste', function(e) {
            if (this.getAttribute('data-type') === 'aadhaar') {
                e.preventDefault();
                const pasteData = (e.clipboardData || window.clipboardData).getData('text');
                const sanitized = pasteData.replace(/\D/g, '').slice(0, 12);
                document.execCommand('insertText', false, sanitized);
            }
        });

        // Form submit
        form.addEventListener('submit', handleSearch);
    }

    function sanitizeAadhaarInput(input) {
        if (input.getAttribute('data-type') === 'aadhaar') {
            const sanitized = input.value.replace(/\D/g, '').slice(0, 12);
            if (input.value !== sanitized) {
                input.value = sanitized;
            }
        }
    }

    function updateInputConfig(type) {
        const config = searchConfigs[type];
        searchLabel.textContent = config.label + ' *';
        searchInput.placeholder = config.placeholder;
        searchInput.maxLength = config.maxlength;
        searchInput.inputMode = config.inputmode;
        searchInput.setAttribute('data-type', type);
        searchIcon.innerHTML = `<span class="material-icons-round fs-5">${config.icon}</span>`;
        searchInput.value = '';
        clearValidation();
        updateContinueButtonState();
    }

    function validateInput() {
        const type = searchInput.getAttribute('data-type') || 'aadhaar';
        const config = searchConfigs[type];
        const value = searchInput.value.trim();

        if (!value) {
            showValidationError('This field is required.');
            return false;
        }

        if (!config.pattern.test(value)) {
            showValidationError(config.validationMessage);
            return false;
        }

        clearValidation();
        return true;
    }

    function showValidationError(message) {
        searchInput.classList.add('is-invalid');
        if (message !== 'This field is required.') {
            searchError.textContent = message;
        }
    }

    function clearValidation() {
        searchInput.classList.remove('is-invalid');
        searchError.textContent = '';
    }

    function updateContinueButtonState() {
        const isValid = validateInput();
        continueBtn.disabled = !isValid;
    }

    function setLoading(isLoading) {
        if (isLoading) {
            continueBtn.disabled = true;
            continueBtnText.textContent = 'Searching...';
            continueSpinner.classList.remove('d-none');
        } else {
            continueBtn.disabled = !validateInput();
            continueBtnText.textContent = 'Continue';
            continueSpinner.classList.add('d-none');
        }
    }

    function hideResult() {
        resultContainer.classList.remove('show', 'success', 'error', 'warning');
        resultContainer.innerHTML = '';
    }

    function showResult(type, title, message, details = null, actions = []) {
        const typeClass = type === 'success' ? 'success' : type === 'error' ? 'error' : 'warning';
        const icons = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning'
        };

        let html = `
            <div class="result-header">
                <span class="material-icons-round result-icon text-${typeClass === 'success' ? 'success' : typeClass === 'error' ? 'danger' : 'warning'}">${icons[typeClass]}</span>
                <strong class="result-title">${title}</strong>
            </div>
            <div class="result-details">${message}</div>
        `;

        if (details) {
            html += `<div class="result-details mt-2"><small>${details}</small></div>`;
        }

        if (actions.length > 0) {
            html += '<div class="result-actions">';
            actions.forEach(action => {
                html += `<a href="${action.url}" class="btn btn-${action.style || 'primary'} btn-sm">${action.text}</a>`;
            });
            html += '</div>';
        }

        resultContainer.innerHTML = html;
        resultContainer.className = `landing-result-message ${typeClass} show`;
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    async function handleSearch(event) {
        event.preventDefault();

        if (!validateInput()) {
            searchInput.focus();
            return;
        }

        const searchBy = searchBySelect.value;
        const searchValue = searchInput.value.trim();

        setLoading(true);
        hideResult();

        try {
            const params = new URLSearchParams({
                search_by: searchBy,
                search_value: searchValue
            });

            const response = await fetch(`${findRegistrationUrl}?${params.toString()}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Search failed. Please try again.');
            }

            handleSearchResult(data);

        } catch (error) {
            console.error('Search error:', error);
            showResult('error', 'Search Failed', error.message || 'An error occurred while searching. Please try again.');
        } finally {
            setLoading(false);
        }
    }

    function handleSearchResult(data) {
        const searchBy = searchBySelect.value;
        const searchValue = searchInput.value.trim();

        switch (data.case) {
            case 'submitted':
                // Application already submitted - show status
                const details = data.details || {};
                let detailHtml = '';
                if (details.status) detailHtml += `<strong>Status:</strong> ${details.status}<br>`;
                if (details.submission_date) detailHtml += `<strong>Submitted on:</strong> ${details.submission_date}<br>`;
                if (details.masked_aadhaar) detailHtml += `<strong>Aadhaar:</strong> ${details.masked_aadhaar}`;

                showResult('warning', data.title, data.message, detailHtml, [
                    { text: 'Start New Registration', url: `${registrationUrl}?new=1`, style: 'outline-primary' }
                ]);
                break;

            case 'draft':
                // Draft found - redirect to form with app_id
                showResult('success', data.title, data.message, null, [
                    { text: 'Continue Registration', url: data.redirect_url, style: 'success' }
                ]);
                
                // Auto-redirect after 2 seconds
                setTimeout(() => {
                    window.location.href = data.redirect_url;
                }, 2000);
                break;

            case 'not_found':
                // No record found - redirect to new registration with prefill
                const prefillParam = searchBy === 'aadhaar' ? `prefill_aadhaar=${encodeURIComponent(searchValue)}` : `prefill_email=${encodeURIComponent(searchValue)}`;
                const newRegUrl = `${registrationUrl}?new=1&${prefillParam}`;
                
                showResult('success', data.title, data.message, null, [
                    { text: 'Start New Registration', url: newRegUrl, style: 'success' }
                ]);
                
                // Auto-redirect after 2 seconds
                setTimeout(() => {
                    window.location.href = newRegUrl;
                }, 2000);
                break;

            default:
                showResult('error', 'Unexpected Response', 'Received an unexpected response from the server. Please try again.');
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();