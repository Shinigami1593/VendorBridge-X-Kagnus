from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from django.utils import timezone

from rfqs.models import RFQ
from vendors.models import Vendor
from approvals.models import Approval
from invoices.models import Invoice
from purchase_orders.models import PurchaseOrder
from rfqs.models import Quotation
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
        self.assertEqual(len(response.data['spending_trends']), 6)

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

    def test_dashboard_returns_real_approval_po_invoice_and_spending_totals(self):
        officer = User.objects.create_user(
            email='officer@example.com',
            username='officer',
            password='password123',
            role='officer',
        )
        vendor = Vendor.objects.create(
            name='Supply Co',
            category='Office',
            gst_number='XYZ123456789012',
            contact_person='Alex',
            contact_email='supply@example.com',
            contact_phone='1234567890',
        )
        pending_rfq = RFQ.objects.create(
            title='Pending', category='Office',
            deadline=timezone.now() + timedelta(days=5),
            created_by=officer,
        )
        pending_quote = Quotation.objects.create(
            rfq=pending_rfq, vendor=vendor, subtotal=Decimal('5.00'),
            tax_percent=Decimal('0'), tax_amount=Decimal('0'),
            grand_total=Decimal('5.00'),
        )
        Approval.objects.create(
            rfq=pending_rfq, quotation=pending_quote, requested_by=officer
        )

        po_rfq = RFQ.objects.create(
            title='Ordered', category='Office',
            deadline=timezone.now() + timedelta(days=5),
            created_by=officer,
        )
        po_quote = Quotation.objects.create(
            rfq=po_rfq, vendor=vendor, subtotal=Decimal('125.00'),
            tax_percent=Decimal('0'), tax_amount=Decimal('0'),
            grand_total=Decimal('125.00'),
        )
        approval = Approval.objects.create(
            rfq=po_rfq, quotation=po_quote, requested_by=officer,
            status='approved',
        )
        po = PurchaseOrder.objects.create(
            po_number='PO-2026-8001', approval=approval, quotation=po_quote,
            rfq=po_rfq, vendor=vendor, vendor_name=vendor.name,
            vendor_gstin=vendor.gst_number, subtotal=Decimal('125.00'),
            tax_percent=Decimal('0'), tax_amount=Decimal('0'),
            grand_total=Decimal('125.00'), created_by=officer,
        )
        Invoice.objects.create(
            invoice_number='INV-2026-8001', purchase_order=po,
            invoice_date=timezone.localdate() - timedelta(days=40),
            due_date=timezone.localdate() - timedelta(days=10),
            subtotal=Decimal('125.00'), tax_percent=Decimal('0'),
            cgst_percent=Decimal('0'), cgst_amount=Decimal('0'),
            sgst_percent=Decimal('0'), sgst_amount=Decimal('0'),
            tax_amount=Decimal('0'), grand_total=Decimal('125.00'),
            created_by=officer,
        )

        self.client.force_authenticate(user=officer)
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 200)
        cards = response.data['cards']
        self.assertEqual(cards['pending_approvals'], 1)
        self.assertEqual(cards['pos_this_month'], 1)
        self.assertEqual(
            Decimal(cards['pos_this_month_amount']), Decimal('125.00')
        )
        self.assertEqual(cards['overdue_invoices'], 1)
        self.assertEqual(
            response.data['recent_purchase_orders'][0]['po_number'],
            po.po_number,
        )
        self.assertEqual(len(response.data['spending_trends']), 6)
        self.assertEqual(
            response.data['spending_trends'][-1]['month'],
            timezone.localdate().strftime('%Y-%m'),
        )
