from django.contrib import admin

from .models import Approval, ApprovalStep


admin.site.register([Approval, ApprovalStep])
