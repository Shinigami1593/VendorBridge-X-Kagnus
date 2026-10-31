from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import serializers

from vendors.models import Vendor
from vendors.utils import get_vendor_for_user
from .models import (
    Quotation,
    QuotationItem,
    RFQ,
    RFQAttachment,
    RFQItem,
)


class RFQItemSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = RFQItem
        fields = ['id', 'name', 'quantity', 'unit']
        read_only_fields = ['id']


class RFQSerializer(serializers.ModelSerializer):
    vendors = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Vendor.objects.filter(status='active'),
        required=False,
    )
    items = RFQItemSerializer(many=True, required=False)
    display_status = serializers.SerializerMethodField()
    quotation_count = serializers.SerializerMethodField()
    my_quotation_status = serializers.SerializerMethodField()

    class Meta:
        model = RFQ
        fields = [
            'id', 'rfq_number', 'title', 'category', 'description',
            'deadline', 'status', 'display_status', 'vendors', 'items',
            'selected_quotation', 'quotation_count', 'my_quotation_status',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'rfq_number', 'status', 'selected_quotation', 'created_by',
            'created_at', 'updated_at', 'display_status', 'quotation_count',
            'my_quotation_status',
        ]

    def validate(self, attrs):
        if self.instance and 'items' in attrs and self.instance.status != 'draft':
            raise serializers.ValidationError(
                {'items': 'Items can only be changed while the RFQ is draft.'}
            )
        deadline = attrs.get('deadline')
        if not self.instance and deadline and deadline <= timezone.now():
            raise serializers.ValidationError(
                {'deadline': 'Deadline must be in the future.'}
            )
        items = attrs.get('items')
        if not self.instance and items is None:
            raise serializers.ValidationError(
                {'items': 'At least one item is required.'}
            )
        if items is not None and not items:
            raise serializers.ValidationError(
                {'items': 'At least one item is required.'}
            )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'vendor':
            vendor = get_vendor_for_user(request.user)
            data.pop('selected_quotation', None)
            data['vendors'] = [vendor.pk] if vendor else []
        return data

    def create(self, validated_data):
        vendors = validated_data.pop('vendors', [])
        items = validated_data.pop('items')
        rfq = RFQ.objects.create(**validated_data)
        rfq.vendors.set(vendors)
        RFQItem.objects.bulk_create(
            [RFQItem(rfq=rfq, **item) for item in items]
        )
        return rfq

    def update(self, instance, validated_data):
        vendors = validated_data.pop('vendors', None)
        items = validated_data.pop('items', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if vendors is not None:
            instance.vendors.set(vendors)
        if items is not None:
            instance.items.all().delete()
            RFQItem.objects.bulk_create(
                [RFQItem(rfq=instance, **item) for item in items]
            )
        return instance

    def get_display_status(self, rfq):
        if rfq.status == 'open' and rfq.is_past_deadline:
            return 'closed'
        return rfq.status

    def get_quotation_count(self, rfq):
        return rfq.quotations.filter(status='submitted').count()

    def get_my_quotation_status(self, rfq):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        if request.user.role != 'vendor':
            return None
        vendor = get_vendor_for_user(request.user)
        if not vendor:
            return None
        return rfq.quotations.filter(vendor=vendor).values_list(
            'status', flat=True
        ).first()


class RFQAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RFQAttachment
        fields = ['id', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class QuotationInputItemSerializer(serializers.Serializer):
    rfq_item = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01')
    )
    delivery_days = serializers.IntegerField(min_value=1)


class MyQuotationInputSerializer(serializers.Serializer):
    tax_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        required=False,
        default=Decimal('18.00'),
    )
    payment_terms = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    submit = serializers.BooleanField(required=False, default=False)
    items = QuotationInputItemSerializer(many=True)

    def validate_items(self, items):
        ids = [item['rfq_item'] for item in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Duplicate RFQ items are not allowed.')
        rfq = self.context['rfq']
        valid_ids = set(rfq.items.filter(pk__in=ids).values_list('pk', flat=True))
        if valid_ids != set(ids):
            raise serializers.ValidationError(
                'Every item must belong to this RFQ.'
            )
        return items

    def validate(self, attrs):
        if attrs.get('submit'):
            rfq = self.context['rfq']
            priced = {item['rfq_item'] for item in attrs['items']}
            required = set(rfq.items.values_list('pk', flat=True))
            if priced != required:
                raise serializers.ValidationError(
                    {'items': 'Every RFQ item must be priced before submission.'}
                )
            if not attrs.get('payment_terms', '').strip():
                raise serializers.ValidationError(
                    {'payment_terms': 'Payment terms are required to submit.'}
                )
        return attrs

    def save(self, *, rfq, vendor, quotation=None):
        data = self.validated_data
        items = data['items']
        subtotal = sum(
            (
                item['unit_price'] * rfq.items.get(pk=item['rfq_item']).quantity
                for item in items
            ),
            Decimal('0.00'),
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        tax_percent = data['tax_percent']
        tax_amount = (subtotal * tax_percent / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        submitted = data['submit']
        values = {
            'tax_percent': tax_percent,
            'payment_terms': data.get('payment_terms', ''),
            'notes': data.get('notes', ''),
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'grand_total': subtotal + tax_amount,
            'status': 'submitted' if submitted else 'draft',
            'submitted_at': timezone.now() if submitted else None,
        }
        if quotation is None:
            quotation = Quotation.objects.create(
                rfq=rfq, vendor=vendor, **values
            )
        else:
            for field, value in values.items():
                setattr(quotation, field, value)
            quotation.save()
            quotation.items.all().delete()
        QuotationItem.objects.bulk_create([
            QuotationItem(
                quotation=quotation,
                rfq_item_id=item['rfq_item'],
                unit_price=item['unit_price'],
                delivery_days=item['delivery_days'],
            )
            for item in items
        ])
        return quotation


class QuotationItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='rfq_item.name', read_only=True)
    quantity = serializers.IntegerField(source='rfq_item.quantity', read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = QuotationItem
        fields = [
            'rfq_item', 'item_name', 'quantity', 'unit_price', 'total',
            'delivery_days',
        ]

    def get_total(self, item):
        return item.rfq_item.quantity * item.unit_price


class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationItemSerializer(many=True, read_only=True)
    delivery_days = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Quotation
        fields = [
            'id', 'rfq', 'vendor', 'status', 'tax_percent', 'payment_terms',
            'notes', 'subtotal', 'tax_amount', 'grand_total', 'delivery_days',
            'submitted_at', 'created_at', 'updated_at', 'items',
        ]
        read_only_fields = fields


class VendorQuotationSerializer(serializers.ModelSerializer):
    rfq_number = serializers.CharField(source='rfq.rfq_number', read_only=True)
    title = serializers.CharField(source='rfq.title', read_only=True)
    deadline = serializers.DateTimeField(source='rfq.deadline', read_only=True)

    class Meta:
        model = Quotation
        fields = [
            'id', 'rfq_number', 'title', 'deadline', 'status', 'grand_total',
        ]


class SelectQuotationSerializer(serializers.Serializer):
    quotation_id = serializers.IntegerField(min_value=1)
