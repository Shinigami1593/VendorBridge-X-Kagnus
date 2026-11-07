from django.contrib import admin

from .models import POItem, PurchaseOrder, PurchaseOrderCounter


admin.site.register([PurchaseOrder, POItem, PurchaseOrderCounter])
