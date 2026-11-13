from django.conf import settings
from django.db import models


class Notification(models.Model):
    CATEGORIES = [
        ('rfq', 'RFQ'),
        ('approval', 'Approval'),
        ('invoice', 'Invoice'),
        ('po', 'Purchase order'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
    )
    category = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    object_type = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    link = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'category', '-created_at']),
        ]

    def __str__(self):
        return self.title
