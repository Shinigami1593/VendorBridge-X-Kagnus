from django.conf import settings
from django.db import models


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError('Activity logs are immutable.')

    def delete(self):
        raise TypeError('Activity logs are immutable.')

    def bulk_update(self, objs, fields, batch_size=None):
        raise TypeError('Activity logs are immutable.')


class ActivityLog(models.Model):
    CATEGORIES = [
        ('vendor', 'Vendor'),
        ('rfq', 'RFQ'),
        ('quotation', 'Quotation'),
        ('approval', 'Approval'),
        ('po', 'Purchase order'),
        ('invoice', 'Invoice'),
        ('auth', 'Authentication'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='activity_logs',
    )
    actor_name = models.CharField(max_length=200, blank=True)
    actor_role = models.CharField(max_length=20, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    action = models.CharField(max_length=50)
    message = models.TextField()
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['category', '-created_at'])]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise TypeError('Activity logs are immutable.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError('Activity logs are immutable.')

    def __str__(self):
        return self.message
