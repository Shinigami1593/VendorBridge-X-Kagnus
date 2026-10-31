from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from django.utils import timezone

from rfqs.models import RFQ
from vendors.models import Vendor
from datetime import timedelta


User = get_user_model()


class DashboardTests(APITestCase):
    def setUp(self):
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

    def test_manager_sees_vendor_counts(self):
        Vendor.objects.create(
            name='Acme',
            category='Office',
            gst_number='ABC123456789012',
            contact_person='Alex',
            contact_email='alex@example.com',
            contact_phone='1234567890',
            status='active',
        )
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['welcome_role'], 'manager/Approver')
        self.assertEqual(response.data['cards']['total_vendors'], 1)
        self.assertEqual(response.data['cards']['active_vendors'], 1)
        self.assertEqual(response.data['recent_purchase_orders'], [])
        self.assertEqual(response.data['spending_trends'], [])

    def test_vendor_cannot_view_dashboard(self):
        self.client.force_authenticate(user=self.vendor_user)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_dashboard_counts_open_rfqs_with_future_deadlines(self):
        RFQ.objects.create(
            title='Current',
            category='Office',
            deadline=timezone.now() + timedelta(days=1),
            status='open',
            created_by=self.manager,
        )
        RFQ.objects.create(
            title='Expired',
            category='Office',
            deadline=timezone.now() - timedelta(days=1),
            status='open',
            created_by=self.manager,
        )
        RFQ.objects.create(
            title='Draft',
            category='Office',
            deadline=timezone.now() + timedelta(days=1),
            status='draft',
            created_by=self.manager,
        )
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.data['cards']['active_rfqs'], 1)
