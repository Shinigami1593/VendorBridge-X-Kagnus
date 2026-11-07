from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from invoices.models import Invoice, InvoiceEmail
from purchase_orders.models import PurchaseOrder, POItem
from approvals.models import Approval
from rfqs.models import RFQ, Quotation
from vendors.models import Vendor


User = get_user_model()


class InvoiceTests(APITestCase):
    def setUp(self):
        self.officer = User.objects.create_user(
            email='officer@example.com', username='officer',
            password='password123', role='officer',
        )
        self.vendor_user = User.objects.create_user(
            email='vendor@example.com', username='vendor',
            password='password123', role='vendor',
        )
        vendor = Vendor.objects.create(
            name='Vendor One', category='Office', gst_number='B' * 15,
            contact_person='Contact', contact_email=self.vendor_user.email,
            contact_phone='1234567890', address='Vendor street',
        )
        self.rfq = RFQ.objects.create(
            title='Supply', category='Office',
            deadline=timezone.now() + timedelta(days=5),
            created_by=self.officer,
        )
        quotation = Quotation.objects.create(
            rfq=self.rfq, vendor=vendor, subtotal=Decimal('100.00'),
            tax_percent=Decimal('18.00'), tax_amount=Decimal('18.00'),
            grand_total=Decimal('118.00'),
        )
        approval = Approval.objects.create(
            rfq=self.rfq, quotation=quotation, requested_by=self.officer,
            status='approved',
        )
        self.po = PurchaseOrder.objects.create(
            po_number='PO-2026-9001', approval=approval,
            quotation=quotation, rfq=self.rfq, vendor=vendor,
            vendor_name=vendor.name, vendor_address=vendor.address,
            vendor_gstin=vendor.gst_number, subtotal=Decimal('100.00'),
            tax_percent=Decimal('18.00'), tax_amount=Decimal('18.00'),
            grand_total=Decimal('118.00'), delivery_days=5,
            payment_terms='Net 30', created_by=self.officer,
        )
        POItem.objects.create(
            purchase_order=self.po, name='Supply', quantity=2, unit='BOX',
            unit_price=Decimal('50.00'), total=Decimal('100.00'),
        )
        self.client.force_authenticate(self.officer)

    def create_invoice(self):
        return self.client.post(
            '/api/invoices/',
            {'purchase_order_id': self.po.pk}, format='json',
        )

    def test_invoice_requires_issued_po_and_copies_tax_parts(self):
        response = self.create_invoice()
        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.cgst_amount + invoice.sgst_amount, invoice.tax_amount)
        self.assertEqual(response.data['grand_total'], Decimal('118.00'))
        self.assertEqual(self.po.status, 'issued')
        self.assertEqual(self.create_invoice().status_code, 400)
        other_vendor = Vendor.objects.create(
            name='Vendor Two', category='Office', gst_number='C' * 15,
            contact_person='Contact', contact_email='other@example.com',
            contact_phone='1234567890',
        )
        other_rfq = RFQ.objects.create(
            title='Other Supply', category='Office',
            deadline=timezone.now() + timedelta(days=5),
            created_by=self.officer,
        )
        other_quote = Quotation.objects.create(
            rfq=other_rfq, vendor=other_vendor, subtotal=Decimal('1.00'),
            tax_percent=Decimal('0.00'), tax_amount=Decimal('0.00'),
            grand_total=Decimal('1.00'),
        )
        other_approval = Approval.objects.create(
            rfq=other_rfq, quotation=other_quote,
            requested_by=self.officer, status='approved',
        )
        other_po = PurchaseOrder.objects.create(
            po_number='PO-2026-9002', approval=other_approval,
            quotation=other_quote, rfq=other_rfq, vendor=other_vendor,
            vendor_name=other_vendor.name, vendor_gstin=other_vendor.gst_number,
            subtotal=Decimal('1.00'), tax_percent=Decimal('0.00'),
            tax_amount=Decimal('0.00'), grand_total=Decimal('1.00'),
            created_by=self.officer, status='invoiced',
        )
        other = self.client.post(
            '/api/invoices/',
            {'purchase_order_id': other_po.pk}, format='json',
        )
        self.assertEqual(other.status_code, 400)

    def test_mark_paid_once_and_pdf_is_real(self):
        response = self.create_invoice()
        invoice_id = response.data['id']
        paid = self.client.post(f'/api/invoices/{invoice_id}/mark-paid/')
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.data['status'], 'paid')
        self.assertEqual(
            self.client.post(
                f'/api/invoices/{invoice_id}/mark-paid/'
            ).status_code,
            400,
        )
        pdf = self.client.get(f'/api/invoices/{invoice_id}/pdf/')
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    @override_settings(
        MAILERS={
            'default': {
                'BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
            },
        }
    )
    def test_email_success_and_failure_are_recorded(self):
        invoice_id = self.create_invoice().data['id']
        mail.outbox.clear()
        sent = self.client.post(
            f'/api/invoices/{invoice_id}/send-email/', {}, format='json'
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data['status'], 'sent')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')

        with patch(
            'invoices.views.EmailMessage.send',
            side_effect=RuntimeError('mail service unavailable'),
        ):
            failed = self.client.post(
                f'/api/invoices/{invoice_id}/send-email/',
                {'to_email': 'billing@example.com'}, format='json',
            )
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(failed.data['status'], 'failed')
        self.assertEqual(InvoiceEmail.objects.filter(status='failed').count(), 1)
        with patch('invoices.views.EmailMessage.send', return_value=0):
            not_sent = self.client.post(
                f'/api/invoices/{invoice_id}/send-email/',
                {'to_email': 'billing@example.com'}, format='json',
            )
        self.assertEqual(not_sent.status_code, 502)
        self.assertEqual(InvoiceEmail.objects.filter(status='failed').count(), 2)

    def test_vendor_can_read_own_invoice_and_cannot_read_other_one(self):
        invoice_id = self.create_invoice().data['id']
        self.client.force_authenticate(self.vendor_user)
        self.assertEqual(
            self.client.get(f'/api/invoices/{invoice_id}/').status_code, 200
        )
        self.assertEqual(
            self.client.get(f'/api/invoices/{invoice_id + 100}/').status_code,
            404,
        )
