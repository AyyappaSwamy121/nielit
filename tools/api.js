// api.js - Handles communication with Google Apps Script Backend

const API = {
    /**
     * Submit application to Google Apps Script Web App
     * @param {object} payload 
     * @param {function} onProgress callback for progress updates
     * @returns Promise<object>
     */
    async submitApplication(payload, onProgress) {
        if (CONFIG.APPS_SCRIPT_URL === 'YOUR_APPS_SCRIPT_WEB_APP_URL_HERE') {
            throw new Error("Apps Script URL is not configured. Please update config.js.");
        }

        const MAX_RETRIES = 2;
        let attempt = 0;

        while (attempt <= MAX_RETRIES) {
            try {
                onProgress('Uploading Files to Server...', 40);
                
                // Set a timeout using AbortController (Apps script can be slow)
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout

                const response = await fetch(CONFIG.APPS_SCRIPT_URL, {
                    method: 'POST',
                    mode: 'cors',
                    headers: {
                        'Content-Type': 'text/plain;charset=utf-8', // Prevents CORS preflight issues with GAS
                    },
                    body: JSON.stringify(payload),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                onProgress('Processing Server Response...', 80);

                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.status === 'success') {
                    onProgress('Completed successfully!', 100);
                    return result;
                } else {
                    throw new Error(result.message || 'Unknown server error');
                }

            } catch (error) {
                attempt++;
                console.error(`Submission attempt ${attempt} failed:`, error);
                
                if (error.name === 'AbortError') {
                    Utils.showToast("Connection timed out. Retrying...", "warning");
                }
                
                if (attempt > MAX_RETRIES) {
                    throw new Error(error.message || "Network failure or server unavailable.");
                }
                
                // Wait 2s before retry
                await new Promise(res => setTimeout(res, 2000));
                onProgress(`Retrying connection (Attempt ${attempt}/${MAX_RETRIES})...`, 40);
            }
        }
    }
};
