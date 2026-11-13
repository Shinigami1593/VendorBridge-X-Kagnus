from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def notification_data(row):
    return {
        'id': row.pk,
        'category': row.category,
        'title': row.title,
        'message': row.message,
        'object_type': row.object_type,
        'object_id': row.object_id,
        'link': row.link,
        'is_read': row.is_read,
        'created_at': row.created_at,
    }


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = Notification.objects.filter(user=request.user)
        unread = request.query_params.get('unread')
        category = request.query_params.get('category')
        if unread is not None and unread.lower() in ('true', '1'):
            rows = rows.filter(is_read=False)
        elif unread is not None and unread.lower() in ('false', '0'):
            rows = rows.filter(is_read=True)
        if category:
            rows = rows.filter(category=category)
        paginator = NotificationPagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response([notification_data(row) for row in page])


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'count': Notification.objects.filter(
                user=request.user, is_read=False
            ).count()
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            row = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            raise NotFound()
        if not row.is_read:
            row.is_read = True
            row.save(update_fields=['is_read'])
        return Response(notification_data(row))


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'updated': True})
