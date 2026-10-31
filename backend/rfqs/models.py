from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from vendors.models import Vendor


class RFQ(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('selected', 'Selected'),
    ]

    rfq_number = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField()
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='draft'
    )
    vendors = models.ManyToManyField(Vendor, related_name='rfqs', blank=True)
    selected_quotation = models.OneToOneField(
        'Quotation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='selected_for',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_rfqs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.rfq_number:
            year = timezone.localdate().year
            prefix = f'RFQ-{year}-'
            previous = RFQ.objects.filter(
                rfq_number__startswith=prefix
            ).values_list('rfq_number', flat=True)
            sequence = max(
                (int(number.rsplit('-', 1)[1]) for number in previous),
                default=0,
            ) + 1
            self.rfq_number = f'{prefix}{sequence:04d}'
        super().save(*args, **kwargs)

    @property
    def is_past_deadline(self):
        return self.deadline <= timezone.now()

    def __str__(self):
        return self.rfq_number


class RFQItem(models.Model):
    rfq = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, default='NOS')

    def __str__(self):
        return self.name


class RFQAttachment(models.Model):
    rfq = models.ForeignKey(
        RFQ, on_delete=models.CASCADE, related_name='attachments'
    )
    file = models.FileField(upload_to='rfq_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ]

    rfq = models.ForeignKey(
        RFQ, on_delete=models.CASCADE, related_name='quotations'
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, related_name='quotations'
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='draft'
    )
    tax_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('18.00'),
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('100')),
        ],
    )
    payment_terms = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00')
    )
    grand_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal('0.00')
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['rfq', 'vendor'], name='unique_quotation_per_vendor_rfq'
            )
        ]

    @property
    def delivery_days(self):
        return self.items.aggregate(value=models.Max('delivery_days'))['value']

    def __str__(self):
        return f'{self.rfq.rfq_number} - {self.vendor.name}'


class QuotationItem(models.Model):
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name='items'
    )
    rfq_item = models.ForeignKey(
        RFQItem, on_delete=models.PROTECT, related_name='quotation_items'
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    delivery_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['quotation', 'rfq_item'],
                name='unique_quotation_item_for_rfq_item',
            )
        ]
