import logging

from .models import ActivityLog

logger = logging.getLogger(__name__)


def log(actor, category, action, message, obj=None):
    try:
        actor_name = ''
        actor_role = ''
        if actor:
            actor_name = actor.get_full_name().strip() or actor.email
            actor_role = actor.role
        ActivityLog.objects.create(
            actor=actor,
            actor_name=actor_name,
            actor_role=actor_role,
            category=category,
            action=action,
            message=message,
            object_type=obj._meta.model_name if obj else '',
            object_id=obj.pk if obj else None,
        )
    except Exception:
        logger.exception('Could not write activity log.')
