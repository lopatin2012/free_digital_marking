# app_true_api/views.py

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from app_true_api.models import DeviceSUZ
from app_true_api.services.true_api_client import TrueAPIClient

logger = logging.getLogger(__name__)

def _check_profile(request):
    """Проверка наличия профиля у пользователя"""
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'success': False, 'error': 'Нет профиля'}, status=400)
    return None


@login_required
@require_http_methods(["POST"])
def api_suz_refresh_token(request):
    """API: Обновить токен СУЗ"""
    try:

        # Проверки.
        _check_profile(request)

        client = TrueAPIClient(user=request.user)
        token = client.refresh_token()

        return JsonResponse({
            'success': True,
            'message': 'Токен успешно обновлён',
            'token': token,
            'valid_until': client.suz_device.token_is_valid_until.isoformat(),
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        logger.error(f'Ошибка при обновлении токена: {e}', exc_info=True)
        return JsonResponse({'success': False, 'message': 'Ошибка сервера'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_suz_invalidate_token(request):
    """API: Сброс токена СУЗ"""
    try:
        # Проверки.
        _check_profile(request)

        organization = request.user.profile.organization
        device = organization.suz_device.filter(is_active=True).first()

        if not device:
            return JsonResponse({'success': False, 'message': 'Нет активного устройства'}, status=400)

        device.current_dynamic_token = ''
        device.token_is_valid_until = timezone.now()
        device.save(update_fields=['current_dynamic_token', 'token_is_valid_until'])
        return JsonResponse({
            'success': True,
            'message': 'Токен успешно сброшен',
        })

    except JsonResponse as e:
        logger.error(f'Ошибка сброса токена: {e}', exc_info=True)
        return JsonResponse({'success': False, 'message': 'Ошибка сервера'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_suz_activate_device(request):
    """API: Активация устройства"""
    try:
        _check_profile(request)

        device_id = request.data.get('device_id')
        if not device_id:
            return JsonResponse({'success': False, 'message': 'Отсутствует ID устройства'}, status=400)

        organization = request.user.profile.organization
        device = organization.suz_device.filter(id=device_id).first()

        device.is_active = True
        device.save(update_fields=['is_active'])

        return JsonResponse({
            'success': True,
            'message': f'Устройство {device.name} активировано',
        })

    except JsonResponse as e:
        return JsonResponse({'success': False, 'message': f'Устройство не найдено'}, status=404)
    except Exception as e:
        logger.error(f'Ошибка активации устройства: {e}', exc_info=True)
        return JsonResponse({'success': False, 'message': 'Ошибка сервера'}, status=500)

@login_required
@require_http_methods(["POST"])
def api_suz_test_connection(request):
    try:
        _check_profile(request)

        # FIXME Исправить на нормальный метод.
        client = TrueAPIClient(user=request.user)
        auth_data = client.get_auth_key()

        return JsonResponse({
            'success': True,
            'message': 'Подключение успешно установлено'
        })

    except Exception as e:
        logger.error(f'Ошибка проверки подключения: {e}', exc_info=True)
        return JsonResponse({'success': False, 'message': 'Ошибка сервера'}, status=500)
