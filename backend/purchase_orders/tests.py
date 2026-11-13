from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from activity.models import ActivityLog
from approvals.models import Approval
from notifications.models import Notification
from purchase_orders.models import POItem, PurchaseOrder
from rfqs.models import Quotation, QuotationItem, RFQ, RFQItem
from vendors.models import Vendor


User = get_user_model()


class PurchaseOrderTests(APITestCase):
    def setUp(self):
        self.officer = self.user('officer', 'officer@example.com')
        self.vendor_user = self.user('vendor', 'vendor@example.com')
        self.other_user = self.user('vendor', 'other@example.com')
        self.vendor = self.make_vendor(self.vendor_user.email, 'Vendor One')
        self.other_vendor = self.make_vendor(self.other_user.email, 'Vendor Two')
        self.approval = self.make_approval(self.vendor, 1)

    def user(self, role, email):
        return User.objects.create_user(
            email=email, username=email.split('@')[0],
            password='password123', role=role,
        )

    def make_vendor(self, email, name):
        return Vendor.objects.create(
            name=name, category='Office',
            gst_number=f'{Vendor.objects.count() + 1:015d}',
            contact_person='Contact', contact_email=email,
            contact_phone='1234567890', address=f'{name} address',
            status='active',
        )

    def make_approval(self, vendor, serial):
        rfq = RFQ.objects.create(
            title=f'Purchase {serial}', category='Office',
            deadline=timezone.now() + timedelta(days=4),
            status='approved', created_by=self.officer,
        )
        item = RFQItem.objects.create(
            rfq=rfq, name=f'Item {serial}', quantity=2, unit='BOX'
        )
        quotation = Quotation.objects.create(
            rfq=rfq, vendor=vendor, status='submitted',
            subtotal=Decimal('20.00'), tax_percent=Decimal('18.00'),
            tax_amount=Decimal('3.60'), grand_total=Decimal('23.60'),
            payment_terms='Net 30',
        )
        QuotationItem.objects.create(
            quotation=quotation, rfq_item=item,
            unit_price=Decimal('10.00'), delivery_days=5,
        )
        return Approval.objects.create(
            rfq=rfq, quotation=quotation, requested_by=self.officer,
            status='approved',
        )

    def create_po(self, approval=None):
        self.client.force_authenticate(self.officer)
        return self.client.post(
            '/api/purchase-orders/',
            {'approval_id': (approval or self.approval).pk}, format='json',
        )

    def test_po_requires_approved_approval_and_duplicates_are_rejected(self):
        pending = self.make_approval(self.other_vendor, 2)
        pending.status = 'pending'
        pending.save(update_fields=['status'])
        self.assertEqual(self.create_po(pending).status_code, 400)
        response = self.create_po()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['subtotal'], Decimal('20.00'))
        self.assertEqual(response.data['grand_total'], Decimal('23.60'))
        self.assertEqual(POItem.objects.get().total, Decimal('20.00'))
        self.assertEqual(self.create_po().status_code, 400)
        self.assertEqual(
            ActivityLog.objects.filter(action='po_generated').count(), 1
        )
        self.assertEqual(
            ActivityLog.objects.get(action='po_generated').object_id,
            response.data['id'],
        )
        self.assertEqual(
            Notification.objects.filter(
                user=self.vendor_user, title='Purchase order issued'
            ).count(),
            1,
        )
        self.approval.rfq.refresh_from_db()
        self.assertEqual(self.approval.rfq.status, 'ordered')

    def test_vendor_only_sees_their_own_purchase_orders(self):
        first = self.create_po()
        second_approval = self.make_approval(self.other_vendor, 3)
        second = self.create_po(second_approval)
        self.client.force_authenticate(self.vendor_user)
        response = self.client.get('/api/purchase-orders/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['id'] for row in response.data], [first.data['id']])
        self.assertEqual(
            self.client.get(
                f'/api/purchase-orders/{second.data["id"]}/'
            ).status_code,
            404,
        )

    def test_non_approved_approval_cannot_create_po(self):
        approval = self.make_approval(self.other_vendor, 4)
        approval.status = 'rejected'
        approval.save(update_fields=['status'])
        self.assertEqual(self.create_po(approval).status_code, 400)
