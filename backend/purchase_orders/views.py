from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from approvals.models import Approval
from vendors.utils import get_vendor_for_user
from .models import POItem, PurchaseOrder, PurchaseOrderCounter


def po_summary(po):
    return {
        'id': po.pk,
        'po_number': po.po_number,
        'vendor_name': po.vendor_name,
        'grand_total': po.grand_total,
        'status': po.status,
        'created_at': po.created_at,
    }


def po_detail(po):
    invoice = getattr(po, 'invoice', None)
    return {
        **po_summary(po),
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
        } for item in po.items.all()],
        'subtotal': po.subtotal,
        'tax_percent': po.tax_percent,
        'tax_amount': po.tax_amount,
        'grand_total': po.grand_total,
        'delivery_days': po.delivery_days,
        'payment_terms': po.payment_terms,
        'rfq_number': po.rfq.rfq_number,
        'approval_id': po.approval_id,
        'invoice_id': invoice.pk if invoice else None,
    }


class CreatePOInputSerializer(serializers.Serializer):
    approval_id = serializers.IntegerField(min_value=1)


class PurchaseOrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        orders = PurchaseOrder.objects.select_related(
            'vendor', 'rfq', 'approval'
        ).prefetch_related('items')
        if request.user.role in ('admin', 'officer', 'manager'):
            return orders
        if request.user.role == 'vendor':
            vendor = get_vendor_for_user(request.user)
            return orders.filter(vendor=vendor) if vendor else orders.none()
        return orders.none()

    def get(self, request):
        if request.user.role not in ('admin', 'officer', 'manager', 'vendor'):
            return Response({'error': 'You do not have permission.'}, status=403)
        orders = self.get_queryset(request)
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        if status_filter:
            orders = orders.filter(status=status_filter)
        if search:
            orders = orders.filter(
                Q(po_number__icontains=search) |
                Q(vendor_name__icontains=search)
            )
        return Response([po_summary(po) for po in orders])

    def post(self, request):
        if request.user.role not in ('admin', 'officer'):
            return Response({'error': 'Only admins and officers can create POs.'}, status=403)
        serializer = CreatePOInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            try:
                approval = Approval.objects.select_for_update().select_related(
                    'quotation__vendor', 'rfq'
                ).get(pk=serializer.validated_data['approval_id'])
            except Approval.DoesNotExist:
                raise NotFound('Approval not found.')
            if PurchaseOrder.objects.filter(
                Q(approval=approval) | Q(quotation=approval.quotation)
            ).exists():
                raise ValidationError({'error': 'Purchase order already exists'})
            if approval.status != 'approved':
                raise ValidationError({'error': 'Purchase order requires an approved approval.'})

            year = timezone.localdate().year
            counter, _ = PurchaseOrderCounter.objects.get_or_create(
                year=year, defaults={'value': 0}
            )
            counter = PurchaseOrderCounter.objects.select_for_update().get(pk=counter.pk)
            counter.value += 1
            counter.save(update_fields=['value'])

            quotation = approval.quotation
            vendor = quotation.vendor
            po = PurchaseOrder.objects.create(
                po_number=f'PO-{year}-{counter.value:04d}',
                approval=approval,
                quotation=quotation,
                rfq=approval.rfq,
                vendor=vendor,
                vendor_name=vendor.name,
                vendor_address=vendor.address,
                vendor_gstin=vendor.gst_number,
                subtotal=quotation.subtotal,
                tax_percent=quotation.tax_percent,
                tax_amount=quotation.tax_amount,
                grand_total=quotation.grand_total,
                delivery_days=quotation.delivery_days,
                payment_terms=quotation.payment_terms,
                created_by=request.user,
            )
            POItem.objects.bulk_create([
                POItem(
                    purchase_order=po,
                    name=item.rfq_item.name,
                    quantity=item.rfq_item.quantity,
                    unit=item.rfq_item.unit,
                    unit_price=item.unit_price,
                    total=item.rfq_item.quantity * item.unit_price,
                )
                for item in quotation.items.select_related('rfq_item')
            ])
            approval.rfq.status = 'ordered'
            approval.rfq.save(update_fields=['status', 'updated_at'])
        return Response(po_detail(po), status=201)


class PurchaseOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ('admin', 'officer', 'manager', 'vendor'):
            return Response({'error': 'You do not have permission.'}, status=403)
        orders = PurchaseOrder.objects.select_related(
            'vendor', 'rfq', 'approval'
        ).prefetch_related('items')
        if request.user.role == 'vendor':
            vendor = get_vendor_for_user(request.user)
            if not vendor:
                raise NotFound()
            orders = orders.filter(vendor=vendor)
        try:
            po = orders.get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            raise NotFound()
        return Response(po_detail(po))
