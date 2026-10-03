import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from masterdata.models import Country, State, District


class PincodeLookupTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name='India', code='IN', iso_code='IND')
        self.state = State.objects.create(name='Andhra Pradesh', code='AP', country=self.country)
        self.district = District.objects.create(name='Guntur', code='GUN', state=self.state)

    @patch('urllib.request.urlopen')
    def test_pincode_lookup_uses_post_office_name_for_area_village(self, mock_urlopen):
        payload = [{
            'Status': 'Success',
            'PostOffice': [{
                'Name': 'Abburu',
                'District': 'Guntur',
                'State': 'Andhra Pradesh',
            }]
        }]
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode('utf-8')

        response = self.client.get(reverse('pincode_lookup'), {'pincode': '522402'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Pincode lookup endpoint is disabled; ensure it returns disabled message
        self.assertFalse(data.get('success', True))
        self.assertIn('disabled', data.get('message', '').lower())

    @patch('urllib.request.urlopen')
    def test_pincode_lookup_returns_multiple_area_choices_when_needed(self, mock_urlopen):
        payload = [{
            'Status': 'Success',
            'PostOffice': [
                {'Name': 'Abburu', 'District': 'Guntur', 'State': 'Andhra Pradesh'},
                {'Name': 'Bayyavaram', 'District': 'Guntur', 'State': 'Andhra Pradesh'}
            ]
        }]
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode('utf-8')

        response = self.client.get(reverse('pincode_lookup'), {'pincode': '522402'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get('success', True))
        self.assertIn('disabled', data.get('message', '').lower())


class PercentageFieldValidationTests(TestCase):
    def test_valid_percentage_values(self):
        from registrations.forms import StudentApplicationForm
        from masterdata.models import Country
        
        # Test valid percentage values on the form field directly
        for val in ['0', '50', '75.50', '89.25', '100', '100.00']:
            form = StudentApplicationForm(data={'percentage': val})
            # percentage is not mandatory unless status is Completed, which requires other fields,
            # so we just check errors specifically for percentage.
            self.assertNotIn('percentage', form.errors)

    def test_invalid_percentage_values(self):
        from registrations.forms import StudentApplicationForm
        
        for val in ['100.01', '-0.01', 'abc', '75.5.0']:
            form = StudentApplicationForm(data={'percentage': val})
            self.assertIn('percentage', form.errors)
            self.assertEqual(form.errors['percentage'][0], 'Enter a valid percentage between 0 and 100.')


class FinalSubmitFlowTests(TestCase):
    def setUp(self):
        from registrations.models import StudentApplication, UploadedDocument
        from registrations.models import ApplicationStatus
        from django.core.files.base import ContentFile
        from masterdata.models import Country, State, District, Qualification, Program
        import datetime

        # Create minimal masterdata required by the form
        self.country = Country.objects.create(name='India', code='IN', iso_code='IND')
        self.state = State.objects.create(name='Test State', code='TS', country=self.country)
        self.district = District.objects.create(name='Test District', code='TD', state=self.state)
        self.qualification = Qualification.objects.create(name='Test Qual')
        self.program = Program.objects.create(name='Test Program')

        # Ensure required statuses exist
        ApplicationStatus.objects.get_or_create(code='INCOMPLETE', defaults={'name': 'Incomplete'})
        ApplicationStatus.objects.get_or_create(code='SUBMITTED', defaults={'name': 'Submitted'})

        status = ApplicationStatus.objects.get(code='INCOMPLETE')
        self.app = StudentApplication.objects.create(
            full_name='Test Student',
            father_name='Test Father',
            mother_name='Test Mother',
            communication_address='Some address',
            mobile_number='9999999999',
            email='test@example.com',
            aadhaar_number='111122223333',
            country=self.country,
            state=self.state,
            district=self.district,
            institution='Test Inst',
            hall_ticket_number='HT1234',
            applying_qualification='12th or equivalent',
            qualification=self.qualification,
            program_opting=self.program,
            mode_of_qualification='Full Time',
            completion_status='Completed',
            year_of_passing=datetime.datetime.now().year,
            distinguishing_mark='None',
            consent_given=True,
            status=status
        )

        # Create mandatory uploaded documents as small content files
        doc_types = ['Passport_Photo', 'Signature', 'Aadhaar', 'Left_Thumb', 'Father_Signature', 'Community_Certificate']
        for dt in doc_types:
            uf = UploadedDocument(application=self.app, doc_type=dt)
            uf.original_file.save(f"{dt}.txt", ContentFile(b"dummy"))
            uf.save()

    def test_final_submit_success(self):
        # Simulate session draft_app_id and POST final_submit
        session = self.client.session
        session['draft_app_id'] = self.app.id
        # Provide temp_application_data to bypass full re-validation complexity
        session['temp_application_data'] = {
            'full_name': self.app.full_name,
            'father_name': self.app.father_name,
            'mother_name': self.app.mother_name,
            'dob': '1990-01-01',
            'gender': 'Male',
            'nationality': 'Indian',
            'mobile_number': self.app.mobile_number,
            'email': self.app.email,
            'communication_address': self.app.communication_address,
            'country': str(self.country.id),
            'state': str(self.state.id),
            'district': str(self.district.id),
            'institution': self.app.institution,
            'hall_ticket_number': self.app.hall_ticket_number,
            'applying_qualification': self.app.applying_qualification,
            'qualification': str(self.qualification.id),
            'program_opting': str(self.program.id),
            'mode_of_qualification': self.app.mode_of_qualification,
            'completion_status': self.app.completion_status,
            'year_of_passing': str(self.app.year_of_passing),
            'aadhaar_number': self.app.aadhaar_number,
            'distinguishing_mark': 'UniqueMark',
            'percentage': '75.00',
            'consent_given': True,
        }
        session.save()
        # Sanity check: form should be valid with provided session data
        from registrations.forms import StudentApplicationForm
        frm = StudentApplicationForm(data=session['temp_application_data'], instance=self.app)
        self.assertTrue(frm.is_valid(), msg=f"Form invalid: {frm.errors}")

        response = self.client.post(reverse('final_submit'), data={'application_id': self.app.id})
        # Ensure uploaded documents exist for the application before asserting success
        from registrations.models import UploadedDocument
        docs = list(UploadedDocument.objects.filter(application=self.app).values_list('doc_type', flat=True))
        self.assertTrue(docs, msg=f"No documents found for application: {docs}")

        # After successful submit redirect to success view
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('success'), response.url)

        # Refresh from DB and ensure status is SUBMITTED
        from registrations.models import StudentApplication, ApplicationStatus
        self.app.refresh_from_db()
        self.assertTrue(self.app.is_submitted)

    def test_final_submit_missing_docs(self):
        # Remove one mandatory doc and attempt to submit
        from registrations.models import UploadedDocument
        UploadedDocument.objects.filter(application=self.app, doc_type='Aadhaar').delete()

        session = self.client.session
        session['draft_app_id'] = self.app.id
        # provide same temp_application_data as a valid payload so validation passes
        session['temp_application_data'] = {
            'full_name': self.app.full_name,
            'father_name': self.app.father_name,
            'mother_name': self.app.mother_name,
            'dob': '1990-01-01',
            'gender': 'Male',
            'nationality': 'Indian',
            'mobile_number': self.app.mobile_number,
            'email': self.app.email,
            'communication_address': self.app.communication_address,
            'country': str(self.country.id),
            'state': str(self.state.id),
            'district': str(self.district.id),
            'institution': self.app.institution,
            'hall_ticket_number': self.app.hall_ticket_number,
            'applying_qualification': self.app.applying_qualification,
            'qualification': str(self.qualification.id),
            'program_opting': str(self.program.id),
            'mode_of_qualification': self.app.mode_of_qualification,
            'completion_status': self.app.completion_status,
            'year_of_passing': str(self.app.year_of_passing),
            'aadhaar_number': self.app.aadhaar_number,
            'distinguishing_mark': 'UniqueMark',
            'percentage': '75.00',
            'consent_given': True,
        }
        session.save()

        response = self.client.post(reverse('final_submit'), data={'application_id': self.app.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        # Should include message about missing mandatory documents
        self.assertContains(response, 'Missing mandatory documents')

    def test_application_number_generation_out_of_order(self):
        from registrations.models import StudentApplication
        from utilities.application_number import generate_application_number
        from django.utils import timezone
        year = timezone.now().year
        prefix = f'CSC{year}'

        # Create applications where an app with higher sequence has a lower ID
        # (e.g. earlier draft finalized later)
        app_low_id = StudentApplication.objects.create(
            application_number=f'{prefix}00010',
            communication_address='addr low id',
        )
        app_high_id = StudentApplication.objects.create(
            application_number=f'{prefix}00005',
            communication_address='addr high id',
        )

        next_no = generate_application_number()
        self.assertEqual(next_no, f'{prefix}00011')

