from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Approval(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    rfq = models.ForeignKey(
        'rfqs.RFQ', on_delete=models.CASCADE, related_name='approvals'
    )
    quotation = models.ForeignKey(
        'rfqs.Quotation', on_delete=models.PROTECT, related_name='approvals'
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending'
    )
    current_level = models.PositiveSmallIntegerField(default=1)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_approvals',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['quotation'],
                condition=models.Q(status__in=['pending', 'approved']),
                name='unique_active_approval_per_quotation',
            )
        ]

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if creating:
            from django.conf import settings

            levels = settings.APPROVAL_LEVELS
            if levels not in (1, 2):
                raise ValueError('APPROVAL_LEVELS must be 1 or 2.')
            with transaction.atomic():
                super().save(*args, **kwargs)
                labels = {1: 'L1 Review', 2: 'L2 Approval'}
                ApprovalStep.objects.bulk_create([
                    ApprovalStep(
                        approval=self,
                        level=level,
                        label=labels[level],
                        status='pending' if level == 1 else 'waiting',
                    )
                    for level in range(1, levels + 1)
                ])
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Approval {self.pk} for {self.rfq}'


class ApprovalStep(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    approval = models.ForeignKey(
        Approval, on_delete=models.CASCADE, related_name='steps'
    )
    level = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=30)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='waiting'
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='decided_approval_steps',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['level']
        constraints = [
            models.UniqueConstraint(
                fields=['approval', 'level'], name='unique_approval_step_level'
            )
        ]

    def __str__(self):
        return f'{self.approval_id} - {self.label}'
