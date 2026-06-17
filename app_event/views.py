# app_event/views.py

from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from app_event.models import EventLog


@login_required
@require_GET
@never_cache
def get_events_api(request):
    """
    Возвращаем последние события, доступные пользователю.
    """

    # Фильтрация по правам пользователя.
    allowed_modules = []

    if request.user.has_perm('django_core.view_production'):
        allowed_modules.append('django_core.view_production')
    if request.user.has_perm('django_core.view_suz') or request.user.has_perm('django_core.view_cz'):
        allowed_modules.append('cz')
    if request.user.has_perm('django_core.view_events'):
        allowed_modules.extend(['system', 'equipment'])

    if not allowed_modules:
        allowed_modules = ['system']

    # Фильтр последних событий.
    cutoff_time = timezone.now() - timedelta(seconds=30)
    qs = EventLog.objects.filter(
        module__in=allowed_modules,
        created__gte=cutoff_time,
    ).order_by('-created_time')[:15]

    data = [{
        'id': e.id,
        'level': e.level,
        'message': e.message,
        'time': e.created_at.strftime('%H:%M:%S'),
        'actor': e.actor,
    } for e in qs]

    return JsonResponse({'events': data})
