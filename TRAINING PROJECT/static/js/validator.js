document.addEventListener('DOMContentLoaded', function() {
    const fieldsToCheck = {
        'id_aadhaar_number': 'aadhaar_number',
        'id_mobile_number': 'mobile_number',
        'id_email': 'email',
        'id_abc_id': 'abc_id',
        'id_registration_number': 'registration_number',
        'id_hall_ticket_number': 'hall_ticket_number'
    };

    for (const [elementId, fieldName] of Object.entries(fieldsToCheck)) {
        const inputElement = document.getElementById(elementId);
        if (inputElement) {
            inputElement.addEventListener('blur', function() {
                const value = this.value.trim();
                if (!value) return;

                // Clear previous warnings
                let warningElement = document.getElementById(`${elementId}_warning`);
                if (warningElement) warningElement.remove();

                fetch(`/api/check-duplicate/?field=${fieldName}&value=${encodeURIComponent(value)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.exists) {
                            // Show warning
                            inputElement.classList.add('is-invalid');
                            warningElement = document.createElement('div');
                            warningElement.id = `${elementId}_warning`;
                            warningElement.className = 'invalid-feedback fw-bold';
                            warningElement.innerText = `Warning: This ${fieldName.replace('_', ' ')} is already registered!`;
                            inputElement.parentNode.appendChild(warningElement);
                        } else {
                            inputElement.classList.remove('is-invalid');
                            inputElement.classList.add('is-valid');
                        }
                    })
                    .catch(error => console.error('Error checking duplicate:', error));
            });
        }
    }
});
