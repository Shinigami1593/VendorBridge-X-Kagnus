from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrOfficerOrManager
from .models import ActivityLog


class ActivityPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def activity_data(row):
    return {
        'id': row.pk,
        'category': row.category,
        'action': row.action,
        'message': row.message,
        'actor_name': row.actor_name,
        'actor_role': row.actor_role,
        'object_type': row.object_type,
        'object_id': row.object_id,
        'created_at': row.created_at,
    }


def filtered_logs(request):
    rows = ActivityLog.objects.all()
    category = request.query_params.get('category')
    search = request.query_params.get('search')
    tab = request.query_params.get('tab', 'all')
    if category:
        rows = rows.filter(category=category)
    tab_categories = {
        'all': None,
        'rfq': ('rfq', 'quotation'),
        'approvals': ('approval',),
        'invoices': ('invoice', 'po'),
        'vendors': ('vendor',),
    }
    if tab not in tab_categories:
        raise ValidationError({'tab': 'Use all, rfq, approvals, invoices, or vendors.'})
    if tab_categories[tab]:
        rows = rows.filter(category__in=tab_categories[tab])
    if search:
        rows = rows.filter(
            Q(message__icontains=search) |
            Q(actor_name__icontains=search) |
            Q(action__icontains=search)
        )
    for key, lookup in (('date_from', 'created_at__date__gte'),
                        ('date_to', 'created_at__date__lte')):
        raw = request.query_params.get(key)
        if raw:
            try:
                parsed = parse_date(raw)
            except ValueError:
                parsed = None
            if not parsed:
                raise ValidationError({key: 'Enter a valid date in YYYY-MM-DD format.'})
            rows = rows.filter(**{lookup: parsed})
    return rows


class ActivityListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOfficerOrManager]

    def get(self, request):
        paginator = ActivityPagination()
        page = paginator.paginate_queryset(filtered_logs(request), request)
        return paginator.get_paginated_response([activity_data(row) for row in page])


class ActivityDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOfficerOrManager]

    def get(self, request, pk):
        try:
            row = ActivityLog.objects.get(pk=pk)
        except ActivityLog.DoesNotExist:
            raise NotFound()
        return Response(activity_data(row))
