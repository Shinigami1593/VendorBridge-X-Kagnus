from django.contrib import admin

from .models import Invoice, InvoiceCounter, InvoiceEmail, InvoiceItem


admin.site.register([Invoice, InvoiceItem, InvoiceEmail, InvoiceCounter])
