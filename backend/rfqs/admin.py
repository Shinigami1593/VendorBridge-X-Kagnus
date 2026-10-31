from django.contrib import admin

from .models import Quotation, QuotationItem, RFQ, RFQAttachment, RFQItem


admin.site.register([RFQ, RFQItem, RFQAttachment, Quotation, QuotationItem])
