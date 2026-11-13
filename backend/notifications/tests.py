from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from activity.models import ActivityLog
from notifications.models import Notification
from notifications.utils import notify
from rfqs.models import RFQ, RFQItem
from vendors.models import Vendor

User = get_user_model()


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.officer = User.objects.create_user(
            email='officer@example.com', username='officer',
            password='password123', role='officer',
        )
        self.other = User.objects.create_user(
            email='other@example.com', username='other',
            password='password123', role='vendor',
        )
        self.vendor_user = User.objects.create_user(
            email='vendor@example.com', username='vendor',
            password='password123', role='vendor',
        )
        self.vendor = Vendor.objects.create(
            name='Acme', category='Office', gst_number='A' * 15,
            contact_person='Contact', contact_email=self.vendor_user.email,
            contact_phone='1234567890', status='active',
        )
        self.rfq = RFQ.objects.create(
            title='Chairs', category='Office',
            deadline=timezone.now() + timedelta(days=5),
            created_by=self.officer,
        )
        self.rfq.vendors.add(self.vendor)
        RFQItem.objects.create(rfq=self.rfq, name='Chair', quantity=1)
        self.client.force_authenticate(self.officer)
        notify(
            [self.officer, self.other], 'rfq', 'New RFQ assigned',
            'New RFQ assigned - Chairs', self.rfq, f'/rfqs/{self.rfq.pk}',
        )
        self.own = Notification.objects.get(user=self.officer)
        self.other_notice = Notification.objects.get(user=self.other)

    def test_private_list_read_count_and_read_all(self):
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.own.pk)
        self.assertEqual(
            self.client.get('/api/notifications/unread-count/').data,
            {'count': 1},
        )
        self.assertEqual(
            self.client.post(
                f'/api/notifications/{self.other_notice.pk}/read/'
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                f'/api/notifications/{self.own.pk}/read/'
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get('/api/notifications/unread-count/').data,
            {'count': 0},
        )
        self.own.is_read = False
        self.own.save(update_fields=['is_read'])
        self.client.post('/api/notifications/read-all/')
        self.assertEqual(
            self.client.get('/api/notifications/unread-count/').data,
            {'count': 0},
        )

    def test_published_rfq_notifies_assigned_vendor_not_actor(self):
        Notification.objects.all().delete()
        self.client.force_authenticate(self.officer)
        response = self.client.post(f'/api/rfqs/{self.rfq.pk}/publish/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Notification.objects.filter(user=self.vendor_user).count(), 1
        )
        self.assertFalse(Notification.objects.filter(user=self.officer).exists())
        self.assertEqual(
            Notification.objects.get(user=self.vendor_user).title,
            'New RFQ assigned',
        )
        event = ActivityLog.objects.get(action='rfq_published')
        self.assertEqual(event.actor, self.officer)
        self.assertEqual(event.object_id, self.rfq.pk)

    def test_submitted_quotation_notifies_rfq_creator_not_vendor_actor(self):
        Notification.objects.all().delete()
        self.rfq.status = 'open'
        self.rfq.save(update_fields=['status'])
        self.client.force_authenticate(self.vendor_user)
        item = self.rfq.items.first()
        response = self.client.put(
            f'/api/rfqs/{self.rfq.pk}/my-quotation/',
            {
                'submit': True,
                'payment_terms': 'Net 30',
                'items': [{
                    'rfq_item': item.pk,
                    'unit_price': '10.00',
                    'delivery_days': 5,
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Notification.objects.filter(
                user=self.officer, title='Quotation received'
            ).count(),
            1,
        )
        self.assertFalse(Notification.objects.filter(user=self.vendor_user).exists())
        event = ActivityLog.objects.get(action='quotation_submitted')
        self.assertEqual(event.actor, self.vendor_user)
        self.assertEqual(event.object_id, response.data['id'])

    def test_failing_notification_storage_does_not_break_rfq_publish(self):
        rfq = RFQ.objects.get(pk=self.rfq.pk)
        with self.assertLogs('notifications.utils', level='ERROR'):
            with patch(
                'notifications.models.Notification.objects.bulk_create',
                side_effect=RuntimeError('storage unavailable'),
            ):
                response = self.client.post(f'/api/rfqs/{rfq.pk}/publish/')
        self.assertEqual(response.status_code, 200)
