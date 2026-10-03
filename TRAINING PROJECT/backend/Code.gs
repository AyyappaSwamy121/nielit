// backend/Code.gs
// Main Entry Point for Google Apps Script Web App

/**
 * Handle CORS Preflight Options Request
 */
function doOptions(e) {
  return ContentService.createTextOutput("")
    .setMimeType(ContentService.MimeType.TEXT);
}

/**
 * Handle POST Requests from the Netlify Frontend
 */
function doPost(e) {
  try {
    if (!e.postData || !e.postData.contents) {
      throw new Error("No payload received.");
    }
    
    // Parse JSON payload
    const payload = JSON.parse(e.postData.contents);
    const { formData, files, metadata } = payload;
    
    if (!formData || !files) {
      throw new Error("Invalid payload structure.");
    }

    // 1. Generate Application ID
    const appId = Utils.generateAppId();
    
    // 2. Save Files to Drive
    // Ensure all mandatory files are present
    const requiredFiles = ['photo', 'signature', 'thumb', 'aadhaar', 'community', 'registration', 'abc'];
    for (let req of requiredFiles) {
      if (!files[req] || !files[req].base64) {
        throw new Error(`Missing required file: ${req}`);
      }
    }
    // Use Aadhaar number from formData for folder and file names
    const aadhaarNumber = formData.aadhaar || appId;
    const fileLinks = DriveManager.saveApplicantFiles(aadhaarNumber, aadhaarNumber, files);
    
    // 3. Save Record to Sheets
    const timestamp = metadata.timestamp || new Date().toISOString();
    SheetManager.appendRecord(appId, timestamp, formData, fileLinks);
    
    // 4. Send Email Confirmation
    if (formData.email) {
      Utils.sendConfirmationEmail(formData.email, formData.fullName, appId);
    }
    
    // Return Success
    return Utils.buildResponse({
      message: "Application processed successfully",
      applicationId: appId
    });
    
  } catch (error) {
    console.error("Execution Error:", error);
    
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.message || "An unexpected error occurred processing your application."
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
