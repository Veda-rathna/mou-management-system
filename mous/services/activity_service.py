from typing import Optional
from django.http import HttpRequest
from django.contrib.auth.models import User
from mous.models import MOU, ActivityLog, ActivityAction


def get_client_ip(request: Optional[HttpRequest]) -> Optional[str]:
    """Extract client IP address safely from request headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class ActivityService:
    """Centralized audit trail service for recording institutional MOU actions."""

    @staticmethod
    def log(
        mou: MOU,
        action: ActivityAction,
        actor: Optional[User] = None,
        actor_name: str = '',
        description: str = '',
        request: Optional[HttpRequest] = None,
    ) -> ActivityLog:
        ip_address = get_client_ip(request)

        # Resolve actor name
        if actor and not actor_name:
            actor_name = actor.get_full_name() or actor.username

        return ActivityLog.objects.create(
            mou=mou,
            action=action,
            actor=actor,
            actor_name=actor_name,
            description=description,
            ip_address=ip_address,
        )
