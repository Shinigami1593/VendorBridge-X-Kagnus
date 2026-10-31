from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrOfficerOrManager
from rfqs.models import RFQ
from vendors.models import Vendor


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOfficerOrManager]

    def get(self, request):
        vendors = Vendor.objects.all()
        return Response({
            'welcome_role': request.user.get_role_display(),
            'cards': {
                'active_rfqs': RFQ.objects.filter(
                    status='open', deadline__gt=timezone.now()
                ).count(),
                'pending_approvals': 0,
                'pos_this_month': 0,
                'overdue_invoices': 0,
                'total_vendors': vendors.count(),
                'active_vendors': vendors.filter(status='active').count(),
            },
            'recent_purchase_orders': [],
            'spending_trends': [],
        })
