from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from approvals.models import Approval
from invoices.models import Invoice
from purchase_orders.models import PurchaseOrder
from rfqs.models import Quotation, RFQ
from vendors.models import Vendor

User = get_user_model()


class ReportsAPITests(APITestCase):
    def setUp(self):
        self.officer = User.objects.create_user(
            email='officer@example.com', username='officer',
            password='password123', role='officer',
        )
        self.vendor_user = User.objects.create_user(
            email='vendor@example.com', username='vendor',
            password='password123', role='vendor',
        )
        self.vendor = Vendor.objects.create(
            name='=Acme', category='Office', gst_number='B' * 15,
            contact_person='Contact', contact_email=self.vendor_user.email,
            contact_phone='1234567890', status='active',
        )
        self.rfq = RFQ.objects.create(
            title='Chairs', category='Furniture',
            deadline=timezone.now() + timedelta(days=5),
            status='approved', created_by=self.officer,
        )
        self.quotation = Quotation.objects.create(
            rfq=self.rfq, vendor=self.vendor, status='submitted',
            subtotal=Decimal('100.00'), tax_percent=Decimal('18.00'),
            tax_amount=Decimal('18.00'), grand_total=Decimal('118.00'),
            submitted_at=timezone.now(),
        )
        self.approval = Approval.objects.create(
            rfq=self.rfq, quotation=self.quotation,
            requested_by=self.officer, status='approved',
        )
        self.po = PurchaseOrder.objects.create(
            po_number='PO-REPORT-1', approval=self.approval,
            quotation=self.quotation, rfq=self.rfq, vendor=self.vendor,
            vendor_name=self.vendor.name, vendor_gstin=self.vendor.gst_number,
            subtotal=Decimal('100.00'), tax_percent=Decimal('18.00'),
            tax_amount=Decimal('18.00'), grand_total=Decimal('118.00'),
            created_by=self.officer,
        )
        today = timezone.localdate()
        self.invoice = Invoice.objects.create(
            invoice_number='INV-REPORT-1', purchase_order=self.po,
            invoice_date=today, due_date=today - timedelta(days=1),
            status='pending_payment', subtotal=Decimal('100.00'),
            tax_percent=Decimal('18.00'), cgst_percent=Decimal('9.00'),
            cgst_amount=Decimal('9.00'), sgst_percent=Decimal('9.00'),
            sgst_amount=Decimal('9.00'), tax_amount=Decimal('18.00'),
            grand_total=Decimal('118.00'), created_by=self.officer,
        )
        self.client.force_authenticate(self.officer)

    def test_summary_metrics_and_empty_collections(self):
        month = timezone.localdate().strftime('%Y-%m')
        response = self.client.get(f'/api/reports/summary/?month={month}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cards']['total_spend'], Decimal('118.00'))
        self.assertEqual(response.data['cards']['po_fulfillment_percent'], Decimal('0.00'))
        self.assertEqual(response.data['cards']['overdue_invoices'], 1)
        self.assertEqual(response.data['spend_by_category'][0]['category'], 'Furniture')
        self.assertEqual(response.data['top_vendors'][0]['po_count'], 1)
        self.assertEqual(response.data['monthly_trend'][-1]['po_count'], 1)
        self.assertEqual(response.data['stats']['amount_outstanding'], Decimal('118.00'))

        self.invoice.status = 'paid'
        self.invoice.save(update_fields=['status'])
        response = self.client.get(f'/api/reports/summary/?month={month}')
        self.assertEqual(response.data['cards']['po_fulfillment_percent'], Decimal('100.00'))

    def test_validation_permissions_and_csv_safety(self):
        self.assertEqual(
            self.client.get('/api/reports/summary/?date_from=bad&date_to=bad').status_code,
            400,
        )
        self.assertEqual(
            self.client.get('/api/reports/summary/?date_from=2026-03-02&date_to=2026-03-01').status_code,
            400,
        )
        self.client.force_authenticate(self.vendor_user)
        self.assertEqual(self.client.get('/api/reports/summary/').status_code, 403)
        self.client.force_authenticate(self.officer)
        response = self.client.get('/api/reports/export/?type=vendors')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('vendor_id,vendor,status,rating', response.content.decode())
        self.assertIn("'=Acme", response.content.decode())
        self.assertEqual(
            self.client.get('/api/reports/export/?type=unknown').status_code,
            400,
        )

    def test_empty_summary_has_zero_amounts_and_empty_rankings(self):
        Invoice.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        Approval.objects.all().delete()
        Quotation.objects.all().delete()
        RFQ.objects.all().delete()
        response = self.client.get('/api/reports/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['cards']['total_spend'], Decimal('0.00'))
        self.assertEqual(response.data['spend_by_category'], [])
        self.assertEqual(response.data['top_vendors'], [])
