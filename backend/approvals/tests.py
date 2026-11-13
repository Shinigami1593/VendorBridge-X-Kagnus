from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from activity.models import ActivityLog
from approvals.models import Approval, ApprovalStep
from notifications.models import Notification
from rfqs.models import Quotation, QuotationItem, RFQ, RFQItem
from vendors.models import Vendor


User = get_user_model()


class ApprovalTests(APITestCase):
    def setUp(self):
        self.officer = self.user('officer', 'officer@example.com')
        self.manager = self.user('manager', 'manager@example.com')
        self.manager2 = self.user('manager', 'manager2@example.com')
        self.vendor_user = self.user('vendor', 'vendor@example.com')
        self.vendor = Vendor.objects.create(
            name='Vendor One', category='Office', gst_number='A' * 15,
            contact_person='Contact', contact_email=self.vendor_user.email,
            contact_phone='1234567890', address='Vendor address',
            status='active', rating=Decimal('4.5'),
        )
        self.rfq = RFQ.objects.create(
            title='Paper', category='Office',
            deadline=timezone.now() + timedelta(days=4),
            status='open', created_by=self.officer,
        )
        item = RFQItem.objects.create(
            rfq=self.rfq, name='Paper', quantity=2, unit='BOX'
        )
        self.rfq.vendors.add(self.vendor)
        self.quotation = Quotation.objects.create(
            rfq=self.rfq, vendor=self.vendor, status='submitted',
            subtotal=Decimal('20.00'), tax_percent=Decimal('18.00'),
            tax_amount=Decimal('3.60'), grand_total=Decimal('23.60'),
            payment_terms='Net 30',
        )
        QuotationItem.objects.create(
            quotation=self.quotation, rfq_item=item,
            unit_price=Decimal('10.00'), delivery_days=5,
        )

    def user(self, role, email):
        return User.objects.create_user(
            email=email, username=email.split('@')[0],
            password='password123', role=role,
        )

    def select(self):
        self.client.force_authenticate(self.officer)
        response = self.client.post(
            f'/api/rfqs/{self.rfq.pk}/select-quotation/',
            {'quotation_id': self.quotation.pk}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        return Approval.objects.get(rfq=self.rfq)

    def decide(self, user, approval, decision='approve', remarks=''):
        self.client.force_authenticate(user)
        return self.client.post(
            f'/api/approvals/{approval.pk}/decide/',
            {'decision': decision, 'remarks': remarks}, format='json',
        )

    def test_selecting_quotation_creates_two_steps(self):
        approval = self.select()
        self.assertEqual(approval.steps.count(), 2)
        self.assertEqual(
            list(approval.steps.values_list('status', flat=True)),
            ['pending', 'waiting'],
        )
        self.assertEqual(
            ActivityLog.objects.filter(action='quotation_selected').count(), 1
        )
        self.assertEqual(
            ActivityLog.objects.filter(action='approval_requested').count(), 1
        )
        self.assertFalse(
            Notification.objects.filter(user=self.officer).exists()
        )
        self.assertEqual(
            Notification.objects.filter(title='Approval needed').count(), 2
        )

    def test_officer_and_vendor_cannot_decide_but_manager_can(self):
        approval = self.select()
        self.assertEqual(self.decide(self.officer, approval).status_code, 403)
        self.assertEqual(self.decide(self.vendor_user, approval).status_code, 403)
        self.assertEqual(self.decide(self.manager, approval).status_code, 200)

    def test_reject_requires_remarks_and_reopens_rfq(self):
        approval = self.select()
        self.assertEqual(
            self.decide(self.manager, approval, 'reject').status_code, 400
        )
        response = self.decide(
            self.manager, approval, 'reject', 'Price too high'
        )
        self.assertEqual(response.status_code, 200)
        approval.refresh_from_db()
        self.rfq.refresh_from_db()
        self.assertEqual(approval.status, 'rejected')
        self.assertEqual(self.rfq.status, 'open')
        self.assertIsNone(self.rfq.selected_quotation_id)
        event = ActivityLog.objects.get(action='approval_rejected')
        self.assertIn('Price too high', event.message)
        self.assertEqual(event.actor, self.manager)
        self.assertTrue(Notification.objects.filter(user=self.officer).exists())

    def test_same_manager_cannot_decide_both_levels_and_second_manager_can(self):
        approval = self.select()
        self.assertEqual(self.decide(self.manager, approval).status_code, 200)
        self.assertEqual(self.decide(self.manager, approval).status_code, 400)
        response = self.decide(self.manager2, approval)
        self.assertEqual(response.status_code, 200)
        approval.refresh_from_db()
        self.rfq.refresh_from_db()
        self.assertEqual(approval.status, 'approved')
        self.assertEqual(self.rfq.status, 'approved')
        self.assertTrue(all(
            step.status == 'approved' for step in approval.steps.all()
        ))
        self.assertEqual(
            ActivityLog.objects.filter(action='approval_level_approved').count(),
            2,
        )

    def test_pending_or_approved_approval_prevents_reselection(self):
        self.select()
        self.client.force_authenticate(self.officer)
        response = self.client.post(
            f'/api/rfqs/{self.rfq.pk}/select-quotation/',
            {'quotation_id': self.quotation.pk}, format='json',
        )
        self.assertEqual(response.status_code, 400)
