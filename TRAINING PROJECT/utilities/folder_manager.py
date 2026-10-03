import os
import re

def get_student_folder_name(aadhaar_number, full_name):
    aadhaar = re.sub(r"\D", "", str(aadhaar_number or ""))
    name = re.sub(r"[^A-Za-z0-9\s_-]", "", str(full_name or ""))
    name = re.sub(r"\s+", "_", name.strip())
    name = re.sub(r"_+", "_", name)

    if len(aadhaar) != 12:
        raise ValueError("A valid 12-digit Aadhaar number is required.")

    if not name:
        raise ValueError("Student name is required.")

    return f"{aadhaar}_{name}"

FOLDER_MAPPING = {
    'Passport_Photo': 'Passport',
    'Signature': 'Signature',
    'Left_Thumb': 'Thumb',
    'Abc_id': 'ABC',
    'Aadhaar': 'Aadhaar',
    'Community_certificate': 'Community',
    'Registration': 'Registration',
    'Supporting': 'Supporting'
}

def get_upload_path(instance, filename):
    """
    Generates the dynamic folder path for student uploads.
    Structure: AADHAAR_Name/DocType/filename
    """
    if hasattr(instance, 'application'):
        # Check if we have the stable storage_folder
        if hasattr(instance.application, 'storage_folder') and instance.application.storage_folder:
            folder_name = instance.application.storage_folder
        else:
            # Fallback for old/unmigrated records just in case
            folder_name = get_student_folder_name(
                instance.application.aadhaar_number, 
                instance.application.full_name
            )
            
        doc_type = instance.doc_type
        # Map the doc_type to the required folder name
        mapped_folder = FOLDER_MAPPING.get(doc_type, doc_type)
        return f"{folder_name}/{mapped_folder}/{filename}"
    return f"others/{filename}"

def get_acknowledgement_path(instance, filename):
    if hasattr(instance, 'storage_folder') and instance.storage_folder:
        folder_name = instance.storage_folder
    else:
        folder_name = get_student_folder_name(instance.aadhaar_number, instance.full_name)
    return f"{folder_name}/acknowledgement/{filename}"
