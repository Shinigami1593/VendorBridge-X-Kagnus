import math
from pathlib import Path

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from vendors.utils import get_vendor_for_user
from .models import Quotation, RFQ, RFQAttachment
from .serializers import (
    MyQuotationInputSerializer,
    QuotationSerializer,
    RFQAttachmentSerializer,
    RFQSerializer,
    SelectQuotationSerializer,
    VendorQuotationSerializer,
)


class RFQRolePermission(BasePermission):
    def has_permission(self, request, view):
        role = request.user.role
        action_name = getattr(view, 'action', None)
        if action_name in ('list', 'retrieve'):
            return role in ('admin', 'officer', 'manager', 'vendor')
        if action_name in ('create', 'update', 'partial_update', 'publish',
                           'select_quotation', 'attachments',
                           'remove_attachment'):
            return role in ('admin', 'officer')
        if action_name == 'destroy':
            return role == 'admin'
        if action_name == 'my_quotation':
            return role == 'vendor'
        if action_name == 'comparison':
            return role in ('admin', 'officer', 'manager')
        return False


class RFQViewSet(viewsets.ModelViewSet):
    serializer_class = RFQSerializer
    permission_classes = [IsAuthenticated, RFQRolePermission]

    def get_queryset(self):
        rfqs = RFQ.objects.prefetch_related('items', 'vendors')
        role = self.request.user.role
        if role == 'manager':
            rfqs = rfqs.exclude(status='draft')
        elif role == 'vendor':
            vendor = get_vendor_for_user(self.request.user)
            if not vendor:
                return rfqs.none()
            rfqs = rfqs.filter(vendors=vendor).exclude(status='draft')

        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if status_filter:
            rfqs = rfqs.filter(status=status_filter)
        if search:
            rfqs = rfqs.filter(
                Q(title__icontains=search) |
                Q(rfq_number__icontains=search)
            )
        return rfqs.distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if self.get_object().status not in ('draft', 'open'):
            raise ValidationError(
                {'status': 'Only draft or open RFQs can be updated.'}
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != 'draft':
            raise ValidationError(
                {'status': 'Only draft RFQs can be deleted.'}
            )
        instance.delete()

    def _writable_rfq(self):
        rfq = self.get_object()
        if rfq.status not in ('draft', 'open'):
            raise ValidationError(
                {'status': 'This RFQ cannot be changed in its current status.'}
            )
        return rfq

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        rfq = self._writable_rfq()
        if rfq.status != 'draft':
            raise ValidationError({'status': 'Only draft RFQs can be published.'})
        errors = {}
        if not rfq.items.exists():
            errors['items'] = 'Add at least one item before publishing.'
        if not rfq.vendors.exists():
            errors['vendors'] = 'Assign at least one vendor before publishing.'
        if rfq.is_past_deadline:
            errors['deadline'] = 'Deadline must be in the future.'
        if errors:
            raise ValidationError(errors)
        rfq.status = 'open'
        rfq.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(rfq).data)

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
    )
    def attachments(self, request, pk=None):
        rfq = self.get_object()
        uploaded = request.FILES.get('file')
        if not uploaded:
            raise ValidationError({'file': 'A file is required.'})
        allowed = {'.pdf', '.png', '.jpg', '.jpeg', '.docx', '.xlsx'}
        if Path(uploaded.name).suffix.lower() not in allowed:
            raise ValidationError({'file': 'File type is not allowed.'})
        if uploaded.size > 5 * 1024 * 1024:
            raise ValidationError({'file': 'File must be no larger than 5 MB.'})
        attachment = rfq.attachments.create(file=uploaded)
        return Response(
            RFQAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'attachments/(?P<attachment_id>[^/.]+)',
    )
    def remove_attachment(self, request, pk=None, attachment_id=None):
        rfq = self.get_object()
        try:
            attachment = rfq.attachments.get(pk=attachment_id)
        except RFQAttachment.DoesNotExist:
            raise NotFound()
        except (ValueError, TypeError):
            raise NotFound()
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='select-quotation')
    def select_quotation(self, request, pk=None):
        rfq = self.get_object()
        serializer = SelectQuotationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if rfq.status not in ('open', 'closed'):
            raise ValidationError(
                {'status': 'Quotation can only be selected for an open or closed RFQ.'}
            )
        try:
            quotation = Quotation.objects.get(
                pk=serializer.validated_data['quotation_id'], rfq=rfq
            )
        except Quotation.DoesNotExist:
            raise ValidationError(
                {'quotation_id': 'Quotation does not belong to this RFQ.'}
            )
        if quotation.status != 'submitted':
            raise ValidationError(
                {'quotation_id': 'Only submitted quotations can be selected.'}
            )
        rfq.selected_quotation = quotation
        rfq.status = 'selected'
        rfq.save(update_fields=['selected_quotation', 'status', 'updated_at'])
        return Response(self.get_serializer(rfq).data)

    @action(detail=True, methods=['get', 'put'], url_path='my-quotation')
    def my_quotation(self, request, pk=None):
        rfq = self.get_object()
        vendor = get_vendor_for_user(request.user)
        if not vendor or not rfq.vendors.filter(pk=vendor.pk).exists():
            raise NotFound()
        quotation = Quotation.objects.filter(rfq=rfq, vendor=vendor).first()
        if request.method == 'GET':
            if not quotation:
                return Response({})
            return Response(QuotationSerializer(quotation).data)

        if rfq.status != 'open':
            raise ValidationError(
                {'status': 'Quotations can only be edited while the RFQ is open.'}
            )
        if rfq.is_past_deadline:
            raise ValidationError({'detail': 'Deadline has passed'})
        serializer = MyQuotationInputSerializer(
            data=request.data, context={'rfq': rfq}
        )
        serializer.is_valid(raise_exception=True)
        created = quotation is None
        quotation = serializer.save(
            rfq=rfq, vendor=vendor, quotation=quotation
        )
        return Response(
            QuotationSerializer(quotation).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def comparison(self, request, pk=None):
        rfq = self.get_object()
        submitted = list(
            Quotation.objects.filter(rfq=rfq, status='submitted')
            .select_related('vendor')
            .prefetch_related('items__rfq_item')
        )
        try:
            max_delivery = request.query_params.get('max_delivery')
            min_rating = request.query_params.get('min_rating')
            max_delivery_value = int(max_delivery) if max_delivery else None
            min_rating_value = float(min_rating) if min_rating else None
        except ValueError:
            raise ValidationError('Invalid comparison filter value.')
        if max_delivery_value is not None and max_delivery_value < 1:
            raise ValidationError(
                {'max_delivery': 'Must be a positive number of days.'}
            )
        if min_rating_value is not None and (
            not math.isfinite(min_rating_value)
            or min_rating_value < 0
            or min_rating_value > 5
        ):
            raise ValidationError(
                {'min_rating': 'Must be between 0 and 5.'}
            )
        if max_delivery_value is not None:
            submitted = [
                quote for quote in submitted
                if quote.delivery_days is not None
                and quote.delivery_days <= max_delivery_value
            ]
        if min_rating_value is not None:
            submitted = [
                quote for quote in submitted
                if quote.vendor.rating is not None
                and quote.vendor.rating >= min_rating_value
            ]

        complete = []
        rfq_item_ids = set(rfq.items.values_list('pk', flat=True))
        for quote in submitted:
            priced_ids = set(quote.items.values_list('rfq_item_id', flat=True))
            if priced_ids == rfq_item_ids:
                complete.append(quote)
        lowest = min(
            (quote.grand_total for quote in complete), default=None
        )

        sort = request.query_params.get('sort', 'price')
        if sort == 'price':
            submitted.sort(key=lambda quote: quote.grand_total)
        elif sort == 'delivery':
            submitted.sort(
                key=lambda quote: (
                    quote.delivery_days is None,
                    quote.delivery_days or 0,
                )
            )
        elif sort == 'rating':
            submitted.sort(
                key=lambda quote: (
                    quote.vendor.rating is None,
                    -(quote.vendor.rating or 0),
                )
            )
        else:
            raise ValidationError({'sort': 'Use price, delivery, or rating.'})

        quotations = []
        for quote in submitted:
            quotations.append({
                'id': quote.pk,
                'vendor_id': quote.vendor_id,
                'vendor_name': quote.vendor.name,
                'vendor_rating': quote.vendor.rating,
                'subtotal': quote.subtotal,
                'tax_percent': quote.tax_percent,
                'tax_amount': quote.tax_amount,
                'grand_total': quote.grand_total,
                'delivery_days': quote.delivery_days,
                'payment_terms': quote.payment_terms,
                'notes': quote.notes,
                'is_lowest': (
                    quote.grand_total == lowest
                    and quote in complete
                ),
                'is_selected': rfq.selected_quotation_id == quote.pk,
                'items': [{
                    'item_name': item.rfq_item.name,
                    'quantity': item.rfq_item.quantity,
                    'unit_price': item.unit_price,
                    'total': item.rfq_item.quantity * item.unit_price,
                    'delivery_days': item.delivery_days,
                } for item in quote.items.all()],
            })
        return Response({
            'rfq': {
                'id': rfq.pk,
                'rfq_number': rfq.rfq_number,
                'title': rfq.title,
                'category': rfq.category,
                'deadline': rfq.deadline,
                'status': (
                    'closed' if rfq.status == 'open' and rfq.is_past_deadline
                    else rfq.status
                ),
            },
            'quotations': quotations,
        })


class MyQuotationsView(APIView):
    permission_classes = [IsAuthenticated, RFQRolePermission]

    @property
    def action(self):
        return 'my_quotation'

    def get(self, request):
        vendor = get_vendor_for_user(request.user)
        if not vendor:
            return Response([])
        quotations = Quotation.objects.filter(vendor=vendor).select_related('rfq')
        return Response(VendorQuotationSerializer(quotations, many=True).data)
