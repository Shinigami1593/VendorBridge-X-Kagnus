from django.db import transaction
from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from accounts.permissions import (
    IsAdmin,
    IsAdminOrOfficer,
    IsAdminOrOfficerOrManager,
)
from activity.utils import log
from .models import Vendor
from .serializers import VendorSerializer


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    pagination_class = None
    filter_backends = [SearchFilter]
    search_fields = ['name', 'gst_number', 'category']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'stats'):
            permission = IsAdminOrOfficerOrManager
        elif self.action in ('create', 'update', 'partial_update'):
            permission = IsAdminOrOfficer
        else:
            permission = IsAdmin
        return [permission()]

    def get_queryset(self):
        vendors = super().get_queryset()
        status = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        if status:
            vendors = vendors.filter(status=status)
        if category:
            vendors = vendors.filter(category__iexact=category)
        return vendors

    def perform_create(self, serializer):
        vendor = serializer.save(created_by=self.request.user)
        log(
            self.request.user, 'vendor', 'vendor_created',
            f'Vendor created - {vendor.name}', vendor,
        )

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        vendor = serializer.save()
        if old_status != vendor.status:
            log(
                self.request.user, 'vendor', 'vendor_status_changed',
                f'Vendor status changed - {vendor.name} is now {vendor.status}',
                vendor,
            )
        else:
            log(
                self.request.user, 'vendor', 'vendor_updated',
                f'Vendor updated - {vendor.name}', vendor,
            )

    def perform_destroy(self, instance):
        name = instance.name
        with transaction.atomic():
            log(
                self.request.user, 'vendor', 'vendor_deleted',
                f'Vendor deleted - {name}', instance,
            )
            instance.delete()

    @action(detail=False, methods=['get'])
    def stats(self, request):
        counts = Vendor.objects.aggregate(
            all=Count('id'),
            active=Count('id', filter=Q(status='active')),
            pending=Count('id', filter=Q(status='pending')),
            blocked=Count('id', filter=Q(status='blocked')),
        )
        return Response(counts)
