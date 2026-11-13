from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.utils import log
from accounts.models import User
from notifications.utils import notify
from purchase_orders.models import PurchaseOrder
from vendors.utils import get_vendor_for_user
from .models import Invoice, InvoiceCounter, InvoiceEmail, InvoiceItem
from .pdf import build_invoice_pdf

CENT = Decimal('0.01')


def invoice_summary(invoice):
    return {
        'id': invoice.pk,
        'invoice_number': invoice.invoice_number,
        'po_number': invoice.purchase_order.po_number,
        'vendor_name': invoice.purchase_order.vendor_name,
        'grand_total': invoice.grand_total,
        'status': invoice.status,
        'invoice_date': invoice.invoice_date,
        'due_date': invoice.due_date,
    }


def invoice_detail(invoice):
    po = invoice.purchase_order
    return {
        **invoice_summary(invoice),
        'bill_to': {
            'name': settings.ORG_NAME,
            'address': settings.ORG_ADDRESS,
            'gstin': settings.ORG_GSTIN,
        },
        'vendor': {
            'id': po.vendor_id,
            'name': po.vendor_name,
            'address': po.vendor_address,
            'gstin': po.vendor_gstin,
            'contact_email': po.vendor.contact_email,
        },
        'items': [{
            'name': item.name,
            'quantity': item.quantity,
            'unit': item.unit,
            'unit_price': item.unit_price,
            'total': item.total,
        } for item in invoice.items.all()],
        'subtotal': invoice.subtotal,
        'tax_percent': invoice.tax_percent,
        'cgst_percent': invoice.cgst_percent,
        'cgst_amount': invoice.cgst_amount,
        'sgst_percent': invoice.sgst_percent,
        'sgst_amount': invoice.sgst_amount,
        'tax_amount': invoice.tax_amount,
        'grand_total': invoice.grand_total,
        'paid_at': invoice.paid_at,
        'po_id': po.pk,
        'email_history': [{
            'to_email': row.to_email,
            'status': row.status,
            'error': row.error,
            'sent_by': row.sent_by.get_full_name() or row.sent_by.email,
            'created_at': row.created_at,
        } for row in invoice.emails.select_related('sent_by').all()],
    }


class CreateInvoiceInputSerializer(serializers.Serializer):
    purchase_order_id = serializers.IntegerField(min_value=1)


class InvoiceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        invoices = Invoice.objects.select_related(
            'purchase_order__vendor', 'purchase_order'
        ).prefetch_related('items')
        if request.user.role in ('admin', 'officer', 'manager'):
            return invoices
        if request.user.role == 'vendor':
            vendor = get_vendor_for_user(request.user)
            return invoices.filter(purchase_order__vendor=vendor) if vendor else invoices.none()
        return invoices.none()

    def get(self, request):
        if request.user.role not in ('admin', 'officer', 'manager', 'vendor'):
            return Response({'error': 'You do not have permission.'}, status=403)
        invoices = self.get_queryset(request)
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        if search:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search) |
                Q(purchase_order__vendor_name__icontains=search)
            )
        return Response([invoice_summary(invoice) for invoice in invoices])

    def post(self, request):
        if request.user.role not in ('admin', 'officer'):
            return Response({'error': 'Only admins and officers can create invoices.'}, status=403)
        serializer = CreateInvoiceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            try:
                po = PurchaseOrder.objects.select_for_update().select_related(
                    'vendor'
                ).get(pk=serializer.validated_data['purchase_order_id'])
            except PurchaseOrder.DoesNotExist:
                raise NotFound('Purchase order not found.')
            if hasattr(po, 'invoice'):
                raise ValidationError({'error': 'Invoice already exists for this purchase order.'})
            if po.status != 'issued':
                raise ValidationError({'error': 'Invoice can only be created from an issued purchase order.'})

            today = timezone.localdate()
            counter, _ = InvoiceCounter.objects.get_or_create(
                year=today.year, defaults={'value': 0}
            )
            counter = InvoiceCounter.objects.select_for_update().get(pk=counter.pk)
            counter.value += 1
            counter.save(update_fields=['value'])

            half_percent = (po.tax_percent / Decimal('2')).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            half_tax = (po.tax_amount / Decimal('2')).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            invoice = Invoice.objects.create(
                invoice_number=f'INV-{today.year}-{counter.value:04d}',
                purchase_order=po,
                invoice_date=today,
                due_date=today + timedelta(days=settings.INVOICE_DUE_DAYS),
                subtotal=po.subtotal,
                tax_percent=po.tax_percent,
                cgst_percent=half_percent,
                cgst_amount=half_tax,
                sgst_percent=po.tax_percent - half_percent,
                sgst_amount=po.tax_amount - half_tax,
                tax_amount=po.tax_amount,
                grand_total=po.grand_total,
                created_by=request.user,
            )
            InvoiceItem.objects.bulk_create([
                InvoiceItem(
                    invoice=invoice,
                    name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    total=item.total,
                )
                for item in po.items.all()
            ])
            po.status = 'invoiced'
            po.save(update_fields=['status'])
        invoice = Invoice.objects.select_related(
            'purchase_order__vendor'
        ).prefetch_related('items', 'emails__sent_by').get(pk=invoice.pk)
        log(
            request.user, 'invoice', 'invoice_created',
            f'Invoice created - {invoice.invoice_number}', invoice,
        )
        vendor_users = User.objects.filter(
            role='vendor',
            email__iexact=invoice.purchase_order.vendor.contact_email,
        ).exclude(pk=request.user.pk)
        notify(
            vendor_users, 'invoice', 'Invoice created',
            f'Invoice created - {invoice.invoice_number}', invoice,
            f'/invoices/{invoice.pk}',
        )
        return Response(invoice_detail(invoice), status=201)


class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_invoice(self, request, pk):
        if request.user.role not in ('admin', 'officer', 'manager', 'vendor'):
            return None
        invoices = Invoice.objects.select_related(
            'purchase_order__vendor'
        ).prefetch_related('items', 'emails__sent_by')
        if request.user.role == 'vendor':
            vendor = get_vendor_for_user(request.user)
            if not vendor:
                raise NotFound()
            invoices = invoices.filter(purchase_order__vendor=vendor)
        try:
            return invoices.get(pk=pk)
        except Invoice.DoesNotExist:
            raise NotFound()

    def get(self, request, pk):
        invoice = self.get_invoice(request, pk)
        if invoice is None:
            return Response({'error': 'You do not have permission.'}, status=403)
        return Response(invoice_detail(invoice))


class InvoiceMarkPaidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ('admin', 'officer'):
            return Response({'error': 'Only admins and officers can mark invoices paid.'}, status=403)
        with transaction.atomic():
            try:
                invoice = Invoice.objects.select_for_update().get(pk=pk)
            except Invoice.DoesNotExist:
                raise NotFound()
            if invoice.status != 'pending_payment':
                raise ValidationError({'error': 'Only pending invoices can be marked paid.'})
            invoice.status = 'paid'
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=['status', 'paid_at'])
        log(
            request.user, 'invoice', 'invoice_marked_paid',
            f'Invoice marked paid - {invoice.invoice_number}', invoice,
        )
        recipients = []
        if invoice.created_by_id != request.user.pk:
            recipients.append(invoice.created_by)
        vendor_users = User.objects.filter(
            role='vendor',
            email__iexact=invoice.purchase_order.vendor.contact_email,
        ).exclude(pk=request.user.pk)
        notify(
            [*recipients, *vendor_users], 'invoice', 'Invoice paid',
            f'Invoice marked paid - {invoice.invoice_number}', invoice,
            f'/invoices/{invoice.pk}',
        )
        return Response({'id': invoice.pk, 'status': invoice.status, 'paid_at': invoice.paid_at})


class InvoicePdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ('admin', 'officer', 'manager', 'vendor'):
            return Response({'error': 'You do not have permission.'}, status=403)
        invoices = Invoice.objects.select_related(
            'purchase_order__vendor'
        ).prefetch_related('items')
        if request.user.role == 'vendor':
            vendor = get_vendor_for_user(request.user)
            if not vendor:
                raise NotFound()
            invoices = invoices.filter(purchase_order__vendor=vendor)
        try:
            invoice = invoices.get(pk=pk)
        except Invoice.DoesNotExist:
            raise NotFound()
        response = HttpResponse(
            build_invoice_pdf(invoice), content_type='application/pdf'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="{invoice.invoice_number}.pdf"'
        )
        return response


class SendInvoiceEmailInputSerializer(serializers.Serializer):
    to_email = serializers.EmailField(required=False)


class InvoiceSendEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ('admin', 'officer'):
            return Response({'error': 'Only admins and officers can send invoices.'}, status=403)
        serializer = SendInvoiceEmailInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invoice = Invoice.objects.select_related(
                'purchase_order__vendor'
            ).prefetch_related('items').get(pk=pk)
        except Invoice.DoesNotExist:
            raise NotFound()
        to_email = serializer.validated_data.get(
            'to_email', invoice.purchase_order.vendor.contact_email
        )
        if parseaddr(to_email)[1] != to_email:
            raise ValidationError({'to_email': 'Enter a valid email address.'})

        message = EmailMessage(
            subject=f'Invoice {invoice.invoice_number}',
            body=f'Please find invoice {invoice.invoice_number} attached.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        message.attach(
            f'{invoice.invoice_number}.pdf',
            build_invoice_pdf(invoice),
            'application/pdf',
        )
        try:
            sent_count = message.send(fail_silently=False)
            if sent_count != 1:
                raise RuntimeError('Email backend did not send the message.')
        except Exception as exc:
            error = (str(exc).strip() or exc.__class__.__name__)[:500]
            InvoiceEmail.objects.create(
                invoice=invoice,
                to_email=to_email,
                status='failed',
                error=error,
                sent_by=request.user,
            )
            log(
                request.user, 'invoice', 'invoice_emailed',
                f'Invoice email failed - {invoice.invoice_number} to {to_email}',
                invoice,
            )
            notify(
                [invoice.created_by]
                if invoice.created_by_id != request.user.pk else [],
                'invoice', 'Invoice email failed',
                f'Invoice email failed - {invoice.invoice_number}',
                invoice, f'/invoices/{invoice.pk}',
            )
            return Response(
                {'status': 'failed', 'error': error[:160]}, status=502
            )
        InvoiceEmail.objects.create(
            invoice=invoice,
            to_email=to_email,
            status='sent',
            sent_by=request.user,
        )
        log(
            request.user, 'invoice', 'invoice_emailed',
            f'Invoice emailed - {invoice.invoice_number} to {to_email}', invoice,
        )
        notify(
            [invoice.created_by]
            if invoice.created_by_id != request.user.pk else [],
            'invoice', 'Invoice emailed',
            f'Invoice emailed - {invoice.invoice_number}',
            invoice, f'/invoices/{invoice.pk}',
        )
        return Response({'status': 'sent', 'to': to_email})
