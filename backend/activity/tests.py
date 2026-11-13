from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ActivityLog
from .utils import log
from vendors.models import Vendor

User = get_user_model()


class ActivityModelTests(TestCase):
    def test_log_copies_actor_and_object_and_is_immutable(self):
        user = User.objects.create_user(
            email='officer@example.com', username='officer',
            password='password123', role='officer', first_name='Pat',
        )
        log(user, 'rfq', 'rfq_created', 'RFQ created - Chairs', user)
        row = ActivityLog.objects.get()
        self.assertEqual(row.actor, user)
        self.assertEqual(row.actor_name, 'Pat')
        self.assertEqual(row.actor_role, 'officer')
        self.assertEqual(row.object_type, 'user')
        self.assertEqual(row.object_id, user.pk)
        with self.assertRaises(TypeError):
            row.save()
        with self.assertRaises(TypeError):
            row.delete()
        with self.assertRaises(TypeError):
            ActivityLog.objects.filter(pk=row.pk).update(message='changed')
        with self.assertRaises(TypeError):
            ActivityLog.objects.filter(pk=row.pk).delete()
        with self.assertRaises(TypeError):
            ActivityLog.objects.bulk_update([row], ['message'])

    def test_deleting_actor_preserves_log_with_null_actor(self):
        user = User.objects.create_user(
            email='removed@example.com', username='removed',
            password='password123', role='officer',
        )
        log(user, 'rfq', 'rfq_created', 'RFQ created - Chairs')
        user.delete()
        row = ActivityLog.objects.get(action='rfq_created')
        self.assertIsNone(row.actor)
        self.assertEqual(row.actor_name, 'removed@example.com')


class ActivityAPITests(APITestCase):
    def setUp(self):
        self.officer = User.objects.create_user(
            email='officer@example.com', username='officer',
            password='password123', role='officer',
        )
        self.manager = User.objects.create_user(
            email='manager@example.com', username='manager',
            password='password123', role='manager',
        )
        self.admin = User.objects.create_user(
            email='admin@example.com', username='admin',
            password='password123', role='admin',
        )
        self.vendor = User.objects.create_user(
            email='vendor@example.com', username='vendor',
            password='password123', role='vendor',
        )
        log(self.officer, 'rfq', 'rfq_created', 'RFQ created - Chairs')
        log(self.manager, 'quotation', 'quotation_submitted',
            'Quotation submitted - Acme for Chairs')
        log(self.admin, 'invoice', 'invoice_created', 'Invoice created - INV-1')

    def test_auth_permissions_tabs_filters_and_pagination(self):
        response = self.client.get('/api/activity/')
        self.assertEqual(response.status_code, 401)
        self.client.force_authenticate(self.vendor)
        self.assertEqual(self.client.get('/api/activity/').status_code, 403)
        for user in (self.officer, self.manager, self.admin):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get('/api/activity/').status_code, 200)

        self.client.force_authenticate(self.officer)
        response = self.client.get('/api/activity/?tab=rfq&search=Acme')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        response = self.client.get('/api/activity/?tab=invoices&category=invoice')
        self.assertEqual(len(response.data['results']), 1)
        today = timezone.localdate().isoformat()
        self.assertEqual(
            len(self.client.get(
                f'/api/activity/?date_from={today}&date_to={today}'
            ).data['results']),
            3,
        )
        response = self.client.get('/api/activity/?page_size=1')
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(
            self.client.get('/api/activity/?date_from=bad').status_code, 400
        )

    def test_detail_and_log_records_one_event(self):
        row = ActivityLog.objects.first()
        self.client.force_authenticate(self.officer)
        self.assertEqual(
            self.client.get(f'/api/activity/{row.pk}/').status_code, 200
        )
        before = ActivityLog.objects.count()
        log(self.officer, 'vendor', 'vendor_created', 'Vendor created - Acme')
        self.assertEqual(ActivityLog.objects.count(), before + 1)

    def test_vendor_mutations_each_write_one_log(self):
        data = {
            'name': 'Acme',
            'category': 'Office',
            'gst_number': 'ABC123456789012',
            'contact_person': 'Pat',
            'contact_email': 'acme@example.com',
            'contact_phone': '1234567890',
        }
        self.client.force_authenticate(self.officer)
        created = self.client.post('/api/vendors/', data, format='json')
        self.assertEqual(created.status_code, 201)
        vendor = Vendor.objects.get(pk=created.data['id'])
        event = ActivityLog.objects.get(action='vendor_created')
        self.assertEqual(event.actor, self.officer)
        self.assertEqual(event.category, 'vendor')
        self.assertEqual(event.object_id, vendor.pk)
        self.assertEqual(ActivityLog.objects.filter(action='vendor_created').count(), 1)

        updated = self.client.patch(
            f'/api/vendors/{vendor.pk}/', {'contact_person': 'Sam'},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(ActivityLog.objects.filter(action='vendor_updated').count(), 1)
        self.client.patch(
            f'/api/vendors/{vendor.pk}/', {'status': 'active'}, format='json'
        )
        self.assertEqual(
            ActivityLog.objects.filter(action='vendor_status_changed').count(), 1
        )
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.delete(f'/api/vendors/{vendor.pk}/').status_code, 204
        )
        self.assertEqual(
            ActivityLog.objects.filter(action='vendor_deleted').count(), 1
        )
