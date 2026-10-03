import io
import zipfile
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from registrations.models import StudentApplication, UploadedDocument


class BulkDownloadCompressedFilesTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staff_admin',
            email='staff@example.com',
            password='Password123!',
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='Password123!',
            is_staff=False
        )

        self.client = Client()
        self.client.login(username='staff_admin', password='Password123!')

        # Create sample application 1
        self.app1 = StudentApplication.objects.create(
            application_number='CSC202600609',
            full_name='Rajesh Kumar',
            aadhaar_number='123456789012',
            communication_address='123 Main St'
        )
        # Sample files
        orig_content = b'ORIGINAL_IMAGE_BYTES_1'
        comp_content = b'COMPRESSED_IMAGE_BYTES_1'

        self.doc1 = UploadedDocument.objects.create(
            application=self.app1,
            doc_type='passport_photo',
            original_file=SimpleUploadedFile('photo_orig.jpg', orig_content, content_type='image/jpeg'),
            compressed_file=SimpleUploadedFile('photo_comp.jpg', comp_content, content_type='image/jpeg'),
            original_file_size=len(orig_content),
            optimized_file_size=len(comp_content)
        )

        sig_orig = b'ORIGINAL_SIGNATURE_BYTES'
        sig_comp = b'COMPRESSED_SIGNATURE_BYTES'
        self.doc2 = UploadedDocument.objects.create(
            application=self.app1,
            doc_type='signature',
            original_file=SimpleUploadedFile('sig_orig.png', sig_orig, content_type='image/png'),
            compressed_file=SimpleUploadedFile('sig_comp.png', sig_comp, content_type='image/png'),
            original_file_size=len(sig_orig),
            optimized_file_size=len(sig_comp)
        )

        # Create sample application 2
        self.app2 = StudentApplication.objects.create(
            application_number='CSC202600610',
            full_name='Priya Sharma',
            aadhaar_number='987654321098',
            communication_address='456 Cross Rd'
        )
        aadhaar_orig = b'ORIGINAL_AADHAAR_BYTES'
        aadhaar_comp = b'COMPRESSED_AADHAAR_BYTES'
        self.doc3 = UploadedDocument.objects.create(
            application=self.app2,
            doc_type='aadhaar',
            original_file=SimpleUploadedFile('aadhaar_orig.jpg', aadhaar_orig, content_type='image/jpeg'),
            compressed_file=SimpleUploadedFile('aadhaar_comp.jpg', aadhaar_comp, content_type='image/jpeg'),
            original_file_size=len(aadhaar_orig),
            optimized_file_size=len(aadhaar_comp)
        )

    def test_single_student_compressed_download(self):
        url = reverse('bulk_ops_download_compressed_files')
        resp = self.client.post(url, {'selected_ids[]': [self.app1.id]})

        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/zip', resp['Content-Type'])
        self.assertIn('attachment; filename="CSC_Selected_Compressed_Documents_', resp['Content-Disposition'])

        zip_buf = io.BytesIO(resp.getvalue() if hasattr(resp, 'getvalue') else b''.join(resp.streaming_content))
        with zipfile.ZipFile(zip_buf, 'r') as zf:
            namelist = zf.namelist()
            # Must contain compressed files in same structure
            self.assertIn('CSC_Selected_Documents/CSC202600609/Passport_Photo/optimized.jpg', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600609/Signature/optimized.png', namelist)

            # Must NOT contain any original files
            for name in namelist:
                self.assertNotIn('original', name)
                self.assertTrue(name.endswith('optimized.jpg') or name.endswith('optimized.png'))

            # Verify contents match compressed files
            self.assertEqual(zf.read('CSC_Selected_Documents/CSC202600609/Passport_Photo/optimized.jpg'), b'COMPRESSED_IMAGE_BYTES_1')
            self.assertEqual(zf.read('CSC_Selected_Documents/CSC202600609/Signature/optimized.png'), b'COMPRESSED_SIGNATURE_BYTES')

    def test_multi_student_compressed_download(self):
        url = reverse('bulk_ops_download_compressed_files')
        resp = self.client.post(url, {'selected_ids[]': [self.app1.id, self.app2.id]})

        self.assertEqual(resp.status_code, 200)
        zip_buf = io.BytesIO(resp.getvalue() if hasattr(resp, 'getvalue') else b''.join(resp.streaming_content))
        with zipfile.ZipFile(zip_buf, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn('CSC_Selected_Documents/CSC202600609/Passport_Photo/optimized.jpg', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600609/Signature/optimized.png', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600610/Aadhaar/optimized.jpg', namelist)

            # No originals
            for name in namelist:
                self.assertNotIn('original', name)

    def test_existing_download_documents_unaffected(self):
        url = reverse('bulk_ops_download_documents')
        resp = self.client.post(url, {'selected_ids[]': [self.app1.id]})

        self.assertEqual(resp.status_code, 200)
        zip_buf = io.BytesIO(resp.getvalue() if hasattr(resp, 'getvalue') else b''.join(resp.streaming_content))
        with zipfile.ZipFile(zip_buf, 'r') as zf:
            namelist = zf.namelist()
            # Original AND compressed both present in existing download
            self.assertIn('CSC_Selected_Documents/CSC202600609/Passport_Photo/original.jpg', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600609/Passport_Photo/optimized.jpg', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600609/Signature/original.png', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600609/Signature/optimized.png', namelist)

    def test_missing_compressed_file_skips_cleanly_without_fallback(self):
        # Add document with only original file, compressed_file is None
        doc_no_comp = UploadedDocument.objects.create(
            application=self.app1,
            doc_type='thumb_impression',
            original_file=SimpleUploadedFile('thumb_orig.jpg', b'THUMB_ORIGINAL_BYTES', content_type='image/jpeg'),
            compressed_file=None,
            original_file_size=20
        )

        url = reverse('bulk_ops_download_compressed_files')
        resp = self.client.post(url, {'selected_ids[]': [self.app1.id]})

        self.assertEqual(resp.status_code, 200)
        zip_buf = io.BytesIO(resp.getvalue() if hasattr(resp, 'getvalue') else b''.join(resp.streaming_content))
        with zipfile.ZipFile(zip_buf, 'r') as zf:
            namelist = zf.namelist()
            # doc1 and doc2 compressed present
            self.assertIn('CSC_Selected_Documents/CSC202600609/Passport_Photo/optimized.jpg', namelist)
            self.assertIn('CSC_Selected_Documents/CSC202600609/Signature/optimized.png', namelist)
            # thumb impression has no compressed file, so should NOT be in zip at all
            for name in namelist:
                self.assertNotIn('Left_Thumb', name)
                self.assertNotIn('thumb', name.lower())
                self.assertNotIn('original', name)

    def test_permissions_and_validations(self):
        url = reverse('bulk_ops_download_compressed_files')

        # 1. Empty selection returns 400
        resp = self.client.post(url, {'selected_ids[]': []})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {'error': 'Please select at least one student.'})

        # 2. GET returns 405 Method not allowed
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

        # 3. Unauthenticated user redirected
        unauth_client = Client()
        resp = unauth_client.post(url, {'selected_ids[]': [self.app1.id]})
        self.assertEqual(resp.status_code, 302)

        # 4. Non-staff user redirected
        non_staff_client = Client()
        non_staff_client.login(username='regular_user', password='Password123!')
        resp = non_staff_client.post(url, {'selected_ids[]': [self.app1.id]})
        self.assertEqual(resp.status_code, 302)
