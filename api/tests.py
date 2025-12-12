from django.test import TestCase
from api.models import Company, PhoneNumber
import phonenumbers

class PhoneNumberVerificationTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company", url="http://example.com")

    def test_valid_fixed_line_number(self):
        # +1 650 253 0000 is a US number (Google) - usually Fixed Line
        pn = PhoneNumber.objects.create(company=self.company, number="+16502530000", description="Old Desc")
        self.assertTrue(pn.verified)
        # Note: Description depends on phonenumbers lib result for this number
        # We expect "Fixed Line" or similar.
        self.assertIn(pn.description, ["Fixed Line", "Fixed Line or Mobile"])

    def test_invalid_number(self):
        pn = PhoneNumber.objects.create(company=self.company, number="12345", description="Old Desc")
        self.assertFalse(pn.verified)
        self.assertEqual(pn.description, "Old Desc") 

    def test_update_number(self):
        pn = PhoneNumber.objects.create(company=self.company, number="12345", description="Old Desc")
        self.assertFalse(pn.verified)
        
        # Update to valid
        pn.number = "+16502530000"
        pn.save()
        self.assertTrue(pn.verified)
        self.assertIn(pn.description, ["Fixed Line", "Fixed Line or Mobile"])