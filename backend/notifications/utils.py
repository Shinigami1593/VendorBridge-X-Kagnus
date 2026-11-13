import logging

from .models import Notification

logger = logging.getLogger(__name__)


def notify(users, category, title, message, obj, link):
    try:
        users = list(users)
        if not users:
            return
        Notification.objects.bulk_create([
            Notification(
                user=user,
                category=category,
                title=title,
                message=message,
                object_type=obj._meta.model_name,
                object_id=obj.pk,
                link=link,
            )
            for user in users
        ])
    except Exception:
        logger.exception('Could not create notifications.')
