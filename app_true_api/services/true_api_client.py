# app_true_api/services/true_api_client.py

import logging
from datetime import timedelta
from typing import Dict, Any

import requests
from django.contrib.auth import get_user_model
from django.utils import timezone

from django_core.settings import DEBUG

from app_true_api.helpers.helper_signature import CadesSigner

logger = logging.getLogger(__name__)
User = get_user_model()

class TrueAPIClient:
    """Клиент для работы с True API"""

    def __init__(self, user: User):
        self.user = user

        # Получаем профиль и организацию
        if not hasattr(user, 'profile'):
            raise ValueError(f'У пользователя {user.username} нет профиля')

        self.organization = user.profile.organization
        self.base_url = (
            'https://markirovka.sandbox.crptech.ru/api/v3/true-api'
            if DEBUG
            else 'https://markirovka.crpt.ru/api/v3/true-api'
        )

        # Получение активной ЭЦП.
        eds = self.organization.eds_settings.filter(is_active=True).first()
        if not eds:
            raise ValueError(
                f'У организации {self.organization.name} нет активной ЭЦП'
            )

        self.signer = CadesSigner(serial_number=eds.serial_number)
        self.suz_device = self.organization.suz_device.filter(is_active=True).first()
        if not self.suz_device:
            raise ValueError(
                f'У организации {self.organization.name} нет активного устройства СУЗ'
            )

    def _make_request(
            self, method: str, endpoint: str,
            is_true_api: bool = True,  **kwargs
    ) -> Dict[str, Any]:
        """HTTP запрос к API"""

        url = (
            f'{self.base_url}{endpoint}'
            if is_true_api
            else f'{self.base_url}{endpoint}'.replace('/true-api/', '/')
        )

        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f'Ошибка запроса к True API: {url}, {e}')
            raise

    def get_auth_key(self) -> Dict[str, str]:
        """Получаем uuid и data для подписи"""
        logger.info('Запрос auth/key')
        return self._make_request('GET', '/auth/key')

    def _get_token_by_signature(self, uuid: str, signed_data: str, united_token: bool = True) -> Dict[str, Any]:
        """Отправляем подписанные данные для получения динамического токена СУЗ.
        """
        logger.info(f'Запрос токена для uuid: {uuid}')

        payload = {
            'uuid': uuid,
            'data': signed_data,
            'inn': self.organization.inn,
            'unitedToken': united_token
        }

        if hasattr(self.organization, 'inn') and self.organization.inn:
            payload['inn'] = self.organization.inn

        # Обновлённый метод. Станет обязательным с 2027 года.
        if united_token:
            payload['unitedToken'] = True

        headers = {'Content-type': 'application/json'}

        response = self._make_request(
            'POST', f'/auth/simpleSignIn/{self.suz_device.connection_id}',
            json=payload, headers=headers)

        if united_token:
            return {
                'token': response.get('token'),
            }
        else:
            return {
                'token': response.get('uuidToken'),
            }


    def refresh_token(self) -> str:
        """Обновляем токен через API и сохраняем в DeviceSUZ"""
        logger.info(f'Обновление токена для организации: {self.organization.name}')

        # Получаем данные для подписи
        auth_data = self.get_auth_key()
        uuid = auth_data['uuid']
        data = auth_data['data']

        # Подписываем данные откреплённой подписью
        _, signature = self.signer.sign_data(data)

        # Получаем токен
        token_data = self._get_token_by_signature(uuid, signature)
        token = token_data['token']

        # Сохраняем токен в DeviceSUZ
        self.suz_device.current_dynamic_token = token
        self.suz_device.token_is_valid_until = timezone.now() + timedelta(hours=8)
        self.suz_device.save(update_fields=['current_dynamic_token', 'token_is_valid_until'])

        logger.info(f'Токен успешно обновлён, действителен до: {self.suz_device.token_is_valid_until}')
        return token

    def get_token(self) -> str:
        """Получает токен (проверяет кэш в DeviceSUZ)"""
        if self.suz_device.is_token_valid and self.suz_device.current_dynamic_token:
            logger.info("Используем существующий токен из БД")
            return self.suz_device.current_dynamic_token

        # Токен невалиден или отсутствует -> обновляем
        return self.refresh_token()

    def invalidate_token(self):
        """Сбрасывает токен в БД"""
        self.suz_device.current_dynamic_token = ''
        self.suz_device.token_is_valid_until = timezone.now()
        self.suz_device.save(update_fields=['current_dynamic_token', 'token_is_valid_until'])
        logger.info('Токен сброшен в БД')

    def request_with_auth(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Выполняем авторизованный запрос к API"""
        token = self.get_token()

        # Добавляем токен в заголовки
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {token}'

        try:
            return self._make_request(method, endpoint, headers=headers, **kwargs)
        except requests.exceptions.HTTPError as e:
            # Если токен невалиден (401), пробуем обновить и повторить запрос
            if e.response.status_code == 401:
                logger.warning('Токен невалиден (401), пробуем обновить')
                self.invalidate_token()
                token = self.get_token()
                headers['Authorization'] = f'Bearer {token}'
                return self._make_request(method, endpoint, headers=headers, **kwargs)
            raise
