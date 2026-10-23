from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Vendor


User = get_user_model()


class VendorAPITests(APITestCase):
    def setUp(self):
        self.officer = User.objects.create_user(
            email='officer@example.com',
            username='officer',
            password='password123',
            role='officer',
        )
        self.manager = User.objects.create_user(
            email='manager@example.com',
            username='manager',
            password='password123',
            role='manager',
        )
        self.vendor_user = User.objects.create_user(
            email='vendor@example.com',
            username='vendor',
            password='password123',
            role='vendor',
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='password123',
            role='admin',
        )
        self.data = {
            'name': 'Acme Supplies',
            'category': 'Office',
            'gst_number': 'abc123456789012',
            'contact_person': 'Alex',
            'contact_email': 'alex@example.com',
            'contact_phone': '1234567890',
        }

    def login(self, user):
        self.client.force_authenticate(user=user)

    def test_officer_can_create_vendor(self):
        self.login(self.officer)
        response = self.client.post('/api/vendors/', self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['gst_number'], 'ABC123456789012')
        self.assertEqual(
            Vendor.objects.get().created_by_id, self.officer.pk
        )

    def test_vendor_cannot_list(self):
        self.login(self.vendor_user)
        response = self.client.get('/api/vendors/')
        self.assertEqual(response.status_code, 403)

    def test_manager_can_list_but_cannot_create(self):
        self.login(self.manager)
        self.assertEqual(
            self.client.get('/api/vendors/').status_code, 200
        )
        self.assertEqual(
            self.client.post('/api/vendors/', self.data).status_code, 403
        )

    def test_only_admin_can_delete(self):
        vendor = Vendor.objects.create(
            **{**self.data, 'gst_number': 'ABC123456789012'}
        )
        self.login(self.officer)
        self.assertEqual(
            self.client.delete(f'/api/vendors/{vendor.pk}/').status_code,
            403,
        )
        self.login(self.admin)
        self.assertEqual(
            self.client.delete(f'/api/vendors/{vendor.pk}/').status_code,
            204,
        )

    def test_duplicate_gst_returns_400(self):
        Vendor.objects.create(
            **{**self.data, 'gst_number': 'ABC123456789012'}
        )
        self.login(self.officer)
        response = self.client.post('/api/vendors/', self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('gst_number', response.data)

    def test_search_and_status_filter(self):
        Vendor.objects.create(
            **{
                **self.data,
                'gst_number': 'ABC123456789012',
                'status': 'active',
            }
        )
        Vendor.objects.create(
            **{
                **self.data,
                'name': 'Other Goods',
                'gst_number': 'ZZZ123456789012',
                'status': 'pending',
            }
        )
        self.login(self.officer)
        search = self.client.get('/api/vendors/', {'search': 'acme'})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.data), 1)
        filtered = self.client.get('/api/vendors/', {'status': 'active'})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.data), 1)

    def test_stats_counts(self):
        Vendor.objects.create(
            **{**self.data, 'gst_number': 'ABC123456789012', 'status': 'active'}
        )
        Vendor.objects.create(
            **{
                **self.data,
                'gst_number': 'ZZZ123456789012',
                'status': 'blocked',
            }
        )
        self.login(self.officer)
        response = self.client.get('/api/vendors/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {'all': 2, 'active': 1, 'pending': 0, 'blocked': 1},
        )
