// backend/SheetService.gs
// Handles Google Sheets Operations

const SheetManager = {
  
  /**
   * Gets the target sheet, creating headers if necessary
   */
  getSheet() {
    let ss;
    if (CONFIG.SPREADSHEET_ID) {
      ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
    } else {
      // If no ID provided, default to the active spreadsheet if bound, or throw error
      ss = SpreadsheetApp.getActiveSpreadsheet();
      if (!ss) {
        throw new Error("Spreadsheet ID is not configured.");
      }
    }
    
    let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(CONFIG.SHEET_NAME);
      // Append headers
      sheet.appendRow(CONFIG.HEADERS);
      sheet.getRange(1, 1, 1, CONFIG.HEADERS.length).setFontWeight("bold");
      sheet.setFrozenRows(1);
    }
    return sheet;
  },

  /**
   * Appends an applicant record to the sheet
   */
  appendRecord(appId, timestamp, formData, fileLinks) {
    // We use LockService to prevent race conditions when multiple users submit at the exact same time
    const lock = LockService.getScriptLock();
    
    try {
      // Wait up to 10 seconds for the lock
      lock.waitLock(10000);
      
      const sheet = this.getSheet();
      
      const rowData = [
        appId,
        timestamp,
        formData.fullName || '',
        formData.dob || '',
        formData.gender || '',
        formData.fatherName || '',
        formData.motherName || '',
        formData.religion || '',
        formData.community || '',
        formData.mobile || '',
        formData.altMobile || '',
        formData.email || '',
        formData.aadhaar ? `'${formData.aadhaar}` : '', // Ensure aadhaar is treated as text
        formData.address || '',
        formData.state || '',
        formData.district || '',
        formData.pincode || '',
        formData.occupation || '',
        formData.abcId ? `'${formData.abcId}` : '',
        formData.institution || '',
        formData.program || '',
        formData.admissionYear || '',
        formData.regNumber || '',
        formData.hallTicket || '',
        fileLinks.photo || '',
        fileLinks.signature || '',
        fileLinks.thumb || '',
        fileLinks.aadhaar || '',
        fileLinks.community || '',
        fileLinks.registration || '',
        fileLinks.abc || '',
        fileLinks.supporting || '',
        'Submitted'
      ];
      
      sheet.appendRow(rowData);
      
    } catch (e) {
      console.error("Failed to append row", e);
      throw e;
    } finally {
      lock.releaseLock();
    }
  }
};
