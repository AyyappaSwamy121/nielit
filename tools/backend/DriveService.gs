// backend/DriveService.gs
// Handles Google Drive Operations

const DriveManager = {
  
  /**
   * Gets or creates the main "Admissions" folder
   */
  getMainFolder() {
    let parentFolder = CONFIG.ROOT_DRIVE_FOLDER_ID ? 
      DriveApp.getFolderById(CONFIG.ROOT_DRIVE_FOLDER_ID) : 
      DriveApp.getRootFolder();

    const folderIterator = parentFolder.getFoldersByName("Admissions");
    if (folderIterator.hasNext()) {
      return folderIterator.next();
    } else {
      return parentFolder.createFolder("Admissions");
    }
  },

  /**
   * Creates a folder for a specific applicant and saves all files
   * @param {string} folderName Name of the folder (e.g. Aadhaar Number)
   * @param {string} filePrefix Prefix for files (e.g. Aadhaar Number)
   * @param {object} files Object containing base64 data for each file type
   * @returns {object} Maps of file types to their Drive URLs
   */
  saveApplicantFiles(folderName, filePrefix, files) {
    const mainFolder = this.getMainFolder();
    const appFolder = mainFolder.createFolder(folderName);
    
    // Set folder permissions so anyone with link can view (optional, useful for admin dashboard)
    appFolder.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

    const fileLinks = {};

    const saveFile = (key, data, defaultExt) => {
      if (!data || !data.base64) return;
      
      const ext = data.mimeType ? data.mimeType.split('/')[1] : defaultExt;
      // If the key is 'photo', use 'profile' as requested by the user, otherwise use the key
      const displayName = key === 'photo' ? 'profile' : key;
      const filename = `${filePrefix}_${displayName}.${ext}`;
      
      const blob = Utils.base64ToBlob(data.base64, filename, data.mimeType);
      const driveFile = appFolder.createFile(blob);
      
      fileLinks[key] = driveFile.getUrl();
    };

    saveFile('photo', files.photo, 'jpg');
    saveFile('signature', files.signature, 'jpg');
    saveFile('thumb', files.thumb, 'jpg');
    saveFile('aadhaar', files.aadhaar, 'pdf');
    saveFile('community', files.community, 'pdf');
    saveFile('registration', files.registration, 'pdf');
    saveFile('abc', files.abc, 'pdf');
    
    if (files.supporting && files.supporting.base64) {
      saveFile('supporting', files.supporting, 'pdf');
    }

    return fileLinks;
  }
};
