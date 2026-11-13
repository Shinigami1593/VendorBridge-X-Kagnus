from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from activity.utils import log
from accounts.models import User
from notifications.utils import notify
from .models import Approval, ApprovalStep


class ApprovalListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'officer', 'manager'):
            return Response({'error': 'You do not have permission.'}, status=403)
        approvals = Approval.objects.select_related(
            'rfq', 'quotation__vendor', 'requested_by'
        ).prefetch_related('steps')
        status_filter = request.query_params.get('status')
        if status_filter:
            if status_filter not in ('pending', 'approved', 'rejected'):
                raise ValidationError({'status': 'Use pending, approved, or rejected.'})
            approvals = approvals.filter(status=status_filter)
        return Response([{
            'id': row.pk,
            'rfq': row.rfq.rfq_number,
            'quotation_vendor': row.quotation.vendor.name,
            'status': row.status,
            'current_level': row.current_level,
            'created_at': row.created_at,
        } for row in approvals])


class ApprovalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ('admin', 'officer', 'manager'):
            return Response({'error': 'You do not have permission.'}, status=403)
        try:
            approval = Approval.objects.select_related(
                'rfq', 'quotation__vendor', 'requested_by'
            ).prefetch_related('steps__decided_by').get(pk=pk)
        except Approval.DoesNotExist:
            raise NotFound()
        steps = list(approval.steps.all())
        current = next(
            (step for step in steps if step.level == approval.current_level), None
        )
        can_decide = (
            request.user.role in ('admin', 'manager')
            and approval.status == 'pending'
            and current is not None
            and current.status == 'pending'
            and not approval.steps.filter(decided_by=request.user).exists()
        )
        timeline = [{
            'action': 'Submitted',
            'by': approval.requested_by.get_full_name()
            or approval.requested_by.email,
            'role': approval.requested_by.role,
            'at': approval.created_at,
        }]
        timeline.extend({
            'action': step.status.title(),
            'by': step.decided_by.get_full_name() or step.decided_by.email,
            'role': step.decided_by.role,
            'at': step.decided_at,
        } for step in steps if step.decided_at and step.decided_by)
        timeline.sort(key=lambda event: event['at'])
        po = getattr(approval, 'purchase_order', None)
        return Response({
            'id': approval.pk,
            'status': approval.status,
            'current_level': approval.current_level,
            'rfq': {
                'id': approval.rfq_id,
                'rfq_number': approval.rfq.rfq_number,
                'title': approval.rfq.title,
            },
            'quotation': {
                'vendor_name': approval.quotation.vendor.name,
                'grand_total': approval.quotation.grand_total,
                'delivery_days': approval.quotation.delivery_days,
                'vendor_rating': approval.quotation.vendor.rating,
            },
            'steps': [{
                'level': step.level,
                'label': step.label,
                'status': step.status,
                'decided_by': ({
                    'name': step.decided_by.get_full_name()
                    or step.decided_by.email,
                    'role': step.decided_by.role,
                } if step.decided_by else None),
                'decided_at': step.decided_at,
                'remarks': step.remarks,
            } for step in steps],
            'timeline': timeline,
            'can_decide': can_decide,
            'po_id': po.pk if po else None,
        })


class DecideApprovalSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['approve', 'reject'])
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class DecideApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ('manager', 'admin'):
            return Response({'error': 'Only managers and admins can decide.'}, status=403)
        serializer = DecideApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data['decision']
        remarks = serializer.validated_data['remarks'].strip()
        if decision == 'reject' and len(remarks) < 3:
            raise ValidationError({'remarks': 'At least 3 characters are required to reject.'})

        with transaction.atomic():
            try:
                approval = Approval.objects.select_for_update().get(pk=pk)
            except Approval.DoesNotExist:
                raise NotFound()
            if approval.status != 'pending':
                raise ValidationError({'error': 'This approval is not pending.'})
            try:
                step = ApprovalStep.objects.select_for_update().get(
                    approval=approval, level=approval.current_level
                )
            except ApprovalStep.DoesNotExist:
                raise ValidationError({'error': 'The current approval step is missing.'})
            if step.status != 'pending':
                raise ValidationError({'error': 'The current step is not pending.'})
            if approval.steps.filter(decided_by=request.user).exists():
                raise ValidationError({
                    'error': 'You have already decided another level of this approval.'
                })

            now = timezone.now()
            step.decided_by = request.user
            step.decided_at = now
            step.remarks = remarks
            step.status = 'approved' if decision == 'approve' else 'rejected'
            step.save(update_fields=[
                'decided_by', 'decided_at', 'remarks', 'status'
            ])

            if decision == 'reject':
                approval.status = 'rejected'
                approval.decided_at = now
                approval.save(update_fields=['status', 'decided_at'])
                approval.rfq.selected_quotation = None
                approval.rfq.status = 'open'
                approval.rfq.save(update_fields=[
                    'selected_quotation', 'status', 'updated_at'
                ])
                log(
                    request.user, 'approval', 'approval_rejected',
                    f'Approval rejected - {approval.quotation.vendor.name} for '
                    f'{approval.rfq.title}. Remarks: {remarks}', approval,
                )
                notify(
                    [approval.requested_by]
                    if approval.requested_by_id != request.user.pk else [],
                    'approval', 'Approval rejected',
                    f'Approval rejected - {approval.rfq.title}. Remarks: {remarks}',
                    approval, f'/approvals/{approval.pk}',
                )
            else:
                next_step = approval.steps.filter(
                    level__gt=approval.current_level
                ).order_by('level').first()
                if next_step:
                    next_step.status = 'pending'
                    next_step.save(update_fields=['status'])
                    approval.current_level = next_step.level
                    approval.save(update_fields=['current_level'])
                    log(
                        request.user, 'approval', 'approval_level_approved',
                        f'L{step.level} approved - {approval.rfq.title}', approval,
                    )
                    notify(
                        User.objects.filter(role__in=('manager', 'admin'))
                        .exclude(pk=request.user.pk),
                        'approval', 'Approval needed',
                        f'L{next_step.label} needed - {approval.rfq.title}',
                        approval, f'/approvals/{approval.pk}',
                    )
                else:
                    approval.status = 'approved'
                    approval.decided_at = now
                    approval.save(update_fields=['status', 'decided_at'])
                    approval.rfq.status = 'approved'
                    approval.rfq.save(update_fields=['status', 'updated_at'])
                    log(
                        request.user, 'approval', 'approval_level_approved',
                        f'L{step.level} approved - {approval.rfq.title}', approval,
                    )
                    recipients = []
                    if approval.requested_by_id != request.user.pk:
                        recipients.append(approval.requested_by)
                    vendor_users = User.objects.filter(
                        role='vendor',
                        email__iexact=approval.quotation.vendor.contact_email,
                    ).exclude(pk=request.user.pk)
                    notify(
                        [*recipients, *vendor_users],
                        'approval', 'Approval completed',
                        f'Approval completed - {approval.rfq.title}',
                        approval, f'/approvals/{approval.pk}',
                    )
        return Response({
            'id': approval.pk,
            'status': approval.status,
            'current_level': approval.current_level,
        })
