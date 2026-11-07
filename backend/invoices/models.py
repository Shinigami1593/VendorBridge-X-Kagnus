from django.conf import settings
from django.db import models
from django.utils import timezone


class InvoiceCounter(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    value = models.PositiveIntegerField(default=0)


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'Pending payment'),
        ('paid', 'Paid'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, blank=True)
    purchase_order = models.OneToOneField(
        'purchase_orders.PurchaseOrder', on_delete=models.PROTECT,
        related_name='invoice',
    )
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending_payment'
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2)
    cgst_percent = models.DecimalField(max_digits=5, decimal_places=2)
    cgst_amount = models.DecimalField(max_digits=14, decimal_places=2)
    sgst_percent = models.DecimalField(max_digits=5, decimal_places=2)
    sgst_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_invoices',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items'
    )
    name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2)


class InvoiceEmail(models.Model):
    STATUS_CHOICES = [('sent', 'Sent'), ('failed', 'Failed')]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='emails'
    )
    to_email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    error = models.CharField(max_length=500, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='invoice_emails',
    )
    created_at = models.DateTimeField(auto_now_add=True)
