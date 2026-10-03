// backend/Utilities.gs
// Utility functions for Google Apps Script Backend

const Utils = {
  /**
   * Generates a unique Application ID
   * Format: APP + YYYY + 5 digit sequential or random
   */
  generateAppId() {
    const year = new Date().getFullYear();
    // For true sequential, we'd need to lock and read the sheet, 
    // but random 5-digit is safer for concurrent stateless execution without heavy locking overhead
    // Example: APP202612345
    const randomDigits = Math.floor(10000 + Math.random() * 90000); 
    return `APP${year}${randomDigits}`;
  },

  /**
   * Helper to return standard JSON response
   */
  buildResponse(data, status = "success") {
    return ContentService.createTextOutput(JSON.stringify({
      status: status,
      ...data
    })).setMimeType(ContentService.MimeType.JSON);
  },

  /**
   * Converts Base64 string from client to a Blob
   */
  base64ToBlob(base64Data, filename, mimeType) {
    const decoded = Utilities.base64Decode(base64Data);
    return Utilities.newBlob(decoded, mimeType, filename);
  },

  /**
   * Sends confirmation email
   */
  sendConfirmationEmail(email, name, appId) {
    try {
      const subject = `Application Received - ${appId}`;
      const body = `Dear ${name},\n\nYour application has been successfully submitted. Your Application ID is ${appId}.\n\nPlease keep this ID for future reference.\n\nRegards,\nAdmissions Team`;
      GmailApp.sendEmail(email, subject, body);
    } catch (e) {
      console.error("Email failed", e);
    }
  }
};
