from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrOfficerOrManager
from notifications.models import Notification
from rfqs.models import RFQ
from approvals.models import Approval
from invoices.models import Invoice
from purchase_orders.models import PurchaseOrder
from vendors.models import Vendor


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOfficerOrManager]

    def get(self, request):
        vendors = Vendor.objects.all()
        today = timezone.localdate()
        month_start = today.replace(day=1)
        this_month_pos = PurchaseOrder.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=today,
        )
        recent_pos = PurchaseOrder.objects.select_related('vendor')[:5]
        trends = []
        current_month = month_start.year * 12 + month_start.month - 1
        for offset in range(5, -1, -1):
            year, month_index = divmod(current_month - offset, 12)
            month_number = month_index + 1
            start = date(year, month_number, 1)
            end = date(year, month_number, monthrange(year, month_number)[1])
            total = PurchaseOrder.objects.filter(
                created_at__date__gte=start,
                created_at__date__lte=end,
            ).aggregate(total=Sum('grand_total'))['total']
            trends.append({
                'month': f'{year:04d}-{month_number:02d}',
                'total': total if total is not None else Decimal('0.00'),
            })
        return Response({
            'welcome_role': request.user.get_role_display(),
            'cards': {
                'active_rfqs': RFQ.objects.filter(
                    status='open', deadline__gt=timezone.now()
                ).count(),
                'pending_approvals': Approval.objects.filter(
                    status='pending'
                ).count(),
                'pos_this_month': this_month_pos.count(),
                'pos_this_month_amount': (
                    this_month_pos.aggregate(total=Sum('grand_total'))['total']
                    or Decimal('0.00')
                ),
                'overdue_invoices': Invoice.objects.filter(
                    status='pending_payment', due_date__lt=today
                ).count(),
                'total_vendors': vendors.count(),
                'active_vendors': vendors.filter(status='active').count(),
                'unread_notifications': Notification.objects.filter(
                    user=request.user, is_read=False
                ).count(),
            },
            'recent_purchase_orders': [{
                'po_number': po.po_number,
                'vendor_name': po.vendor_name,
                'grand_total': po.grand_total,
                'status': po.status,
            } for po in recent_pos],
            'spending_trends': trends,
        })
