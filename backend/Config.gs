// backend/Config.gs
// Configuration file for Google Apps Script Backend

const CONFIG = {
  // Drive Folder ID where 'Admissions' folder will be created or used
  // If empty, it creates it in root Drive
  ROOT_DRIVE_FOLDER_ID: '', 
  
  // Google Sheet ID where data will be stored
  // Must have a sheet named "Submissions"
  SPREADSHEET_ID: '',
  
  SHEET_NAME: 'Submissions',
  
  // Headers for the Sheet
  HEADERS: [
    'Application ID', 'Timestamp', 'Full Name', 'DOB', 'Gender',
    'Father Name', 'Mother Name', 'Religion', 'Community', 'Phone',
    'Alternative Phone', 'Email', 'Aadhaar', 'Address', 'State',
    'District', 'Pincode', 'Occupation', 'ABC ID', 'Institution',
    'Program', 'Year', 'Registration Number', 'Hall Ticket',
    'Photo Link', 'Signature Link', 'Thumb Link', 'Aadhaar Link',
    'Community Link', 'Registration Link', 'ABC Link', 'Supporting Link',
    'Status'
  ]
};
