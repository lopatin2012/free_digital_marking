# app_page/views.py

import logging

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView


logger = logging.getLogger(__name__)


class HomePageView(TemplateView):
    template_name = 'base_hud.html'

class SUZDashboardView(LoginRequiredMixin, TemplateView):
    """Страница управления СУЗ"""
    template_name = 'modules/true_api/suz_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_system'] = 'СУЗ'

        if not hasattr(self.request.user, 'profile'):
            context['error_message'] = 'У вашей учётной записи отсутствует профиль в системе'
            return context

        organization = self.request.user.profile.organization
        context['organization'] = organization

        all_devices = organization.suz_device.all().order_by('-is_active', '-id')
        active_device = all_devices.filter(is_active=True).first()

        context.update({
            'active_device': active_device,
            'all_devices': all_devices,
            'devices_count': all_devices.count(),
            'active_devices': all_devices.filter(is_active=True).count(),
        })

        # Информация о токене.
        if active_device:
            token_status = 'Неизвестно'
            token_remaining_seconds = 0

            if active_device.current_dynamic_token:
                if active_device.is_token_valid:
                    token_status = 'Активный'
                    remaining = active_device.token_is_valid_until - timezone.now()
                    token_remaining_seconds = int(remaining.total_seconds())

                else:
                    token_status = 'Истёк'

            else:
                token_status = 'Отсутствует'

            context.update({
                'token_status': token_status,
                'token_remaining_seconds': token_remaining_seconds,
                'token_is_valid_until': active_device.token_is_valid_until,
            })

        return context


@login_required
def suz_dash(request):
    """Страница управления СУЗ"""

    if not hasattr(request.user, 'profile'):
        return render(request, 'error.html', {
            'error_message': 'У вашего профиля не указана организация',
            'current_system': 'СУЗ'
        })

    organization = request.user.profile.organization

    all_devices = organization.suz_device.all().order_by('-is_active', '-id')
    active_device = all_devices.filter(is_active=True).first()

    context = {
        'current_system': 'СУЗ',
        'organization': organization,
        'active_device': active_device,
        'all_devices': all_devices,
        'devices_count': all_devices.count(),
        'active_devices': all_devices.filter(is_active=True).count(),
    }

    # Информация о текущем активном соединении с СУЗ.
    if active_device:
        token_status = 'Неизвестно'
        token_remaining_seconds = 0
        token_remaining_percent = 0

        if active_device.current_dynamic_token:
            if active_device.is_token_valid:
                token_status = 'Активный'
                remaining = active_device.token_is_valid_until - timezone.now()
                token_remaining_seconds = int(remaining.total_seconds())

                # Расчёт.
                total_token_lifetime = 8 * 60 * 60  # 28800 секунд
                token_remaining_percent = int((token_remaining_seconds / total_token_lifetime) * 100)
            else:
                token_status = 'Истёк'
        else:
            token_status = 'Отсутствует'

        context.update({
            'token_status': token_status,
            'token_remaining_seconds': token_remaining_seconds,
            'token_remaining_percent': token_remaining_percent,
            'token_is_valid_until': active_device.token_is_valid_until,
        })
    return render(request, 'modules/true_api/suz_dashboard.html', context)
