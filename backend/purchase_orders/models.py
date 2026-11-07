from django.conf import settings
from django.db import models
from django.utils import timezone


class PurchaseOrderCounter(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    value = models.PositiveIntegerField(default=0)


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('issued', 'Issued'),
        ('invoiced', 'Invoiced'),
    ]

    po_number = models.CharField(max_length=20, unique=True, blank=True)
    approval = models.OneToOneField(
        'approvals.Approval', on_delete=models.PROTECT,
        related_name='purchase_order',
    )
    quotation = models.OneToOneField(
        'rfqs.Quotation', on_delete=models.PROTECT,
        related_name='purchase_order',
    )
    rfq = models.ForeignKey(
        'rfqs.RFQ', on_delete=models.PROTECT, related_name='purchase_orders'
    )
    vendor = models.ForeignKey(
        'vendors.Vendor', on_delete=models.PROTECT,
        related_name='purchase_orders',
    )
    vendor_name = models.CharField(max_length=150)
    vendor_address = models.TextField(blank=True)
    vendor_gstin = models.CharField(max_length=15)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2)
    delivery_days = models.PositiveIntegerField(null=True, blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='issued'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_purchase_orders',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.po_number


class POItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name='items'
    )
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2)
