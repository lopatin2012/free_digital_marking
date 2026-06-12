import secrets
import logging

from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from app_factory.models import Line

logger = logging.getLogger(__name__)


class EquipmentType(models.Model):
    """Тип оборудования"""
    name = models.CharField(max_length=100, verbose_name='Наименование типа')
    code = models.CharField(max_length=50, unique=True, verbose_name='Уникальный код')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Тип оборудования'
        verbose_name_plural = 'Типы оборудования'
        ordering = ('code',)

    def __str__(self):
        return f'{self.name} ({self.code})'


class Equipment(models.Model):
    """Единица оборудования на производстве"""
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.PROTECT,
        related_name='devices',
        verbose_name='Тип оборудования'
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='equipment_list',
        verbose_name='Производственная линия'
    )
    name = models.CharField(max_length=150, verbose_name='Имя устройства')
    inventory_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Инвентарный номер'
    )
    mac_address = models.CharField(max_length=50, blank=True, null=True, verbose_name='MAC-адрес')
    ip_address = models.GenericIPAddressField(
        protocol='both',
        unpack_ipv4=True,
        blank=True, null=True,
        verbose_name='IP-адрес'
    )
    software_version = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name='Версия ПО'
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Настройки устройства'
    )
    is_active = models.BooleanField(default=True, verbose_name='В эксплуатации')
    last_seen = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Последняя активность'
    )

    class Meta:
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудование'
        ordering = ('inventory_number',)
        indexes = [
            models.Index(fields=['mac_address'], name='idx_equip_mac'),
            models.Index(fields=['ip_address'], name='idx_equip_ip'),
        ]

    def __str__(self):
        line_info = f' | Линия: {self.line.name} ({self.line.code})' if self.line else ' | Не назначено'
        status = 'Используется' if self.is_active else 'Не активно'
        # Исправлена лишняя скобка в конце
        return f'{status}: {self.name} ({self.inventory_number}){line_info}'

    def update_last_seen(self):
        """Обновление активности"""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])

    def get_settings(self, key, default=None):
        """Получение настроек из JSON"""
        return self.settings.get(key, default)

    def set_settings(self, key, value):
        """Установка настройки"""
        if self.settings is None:
            self.settings = {}

        self.settings[key] = value
        self.save(update_fields=['settings'])


class DeviceCredentials(models.Model):
    """Учётные данные и параметры авторизации для оборудования"""
    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.CASCADE,
        related_name='credentials',
        verbose_name='Оборудование'
    )
    auth_token = models.CharField(
        max_length=128,
        unique=True,
        default=secrets.token_urlsafe,
        editable=False,
        verbose_name='Секретный токен устройства'
    )
    password = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='Пароль устройства'
    )
    mac_address = models.CharField(
        max_length=50,
        blank=True, null=True,
        db_index=True,
        verbose_name='Разрешенный MAC-адрес',
        help_text='Для автоматизации авторизации (опционально)'
    )
    ip_address = models.GenericIPAddressField(
        protocol='both',
        unpack_ipv4=True,
        blank=True, null=True,
        db_index=True,
        verbose_name='Разрешенный IP-адрес',
        help_text='Для автоматизации авторизации (опционально)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Авторизация разрешена')
    last_auth = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Последняя успешная авторизация'
    )

    class Meta:
        verbose_name = 'Учетные данные устройства'
        verbose_name_plural = 'Учетные данные устройств'

    def __str__(self):
        return f'Доступ для: {self.equipment.name} ({self.equipment.inventory_number})'

    def set_password(self, raw_password):
        """Устанавливает пароль, предварительно хэшируя его"""
        self.password = make_password(raw_password)
        self.save(update_fields=['password'])

    def check_password(self, raw_password):
        """Проверяет правильность введенного пароля"""
        if not self.password:
            return False
        return check_password(raw_password, self.password)

    def record_auth(self):
        """Фиксирует факт успешной авторизации"""
        self.last_auth = timezone.now()
        self.save(update_fields=['last_auth'])
        # Обновляем последнюю активность в основной модели Equipment
        self.equipment.update_last_seen()

    @classmethod
    def authenticate_device(cls, inventory_number=None, mac_address=None, ip_address=None, auth_token=None,
                            password=None):
        """
        Метод для автоматической авторизации устройства.
        Поддерживает авторизацию по токену ИЛИ по инвентарному номеру + паролю ИЛИ по MAC/IP.
        Возвращает объект Equipment, если авторизация успешна, иначе None.
        """
        qs = cls.objects.filter(is_active=True).select_related('equipment')

        # Формируем базовый фильтр
        if auth_token:
            qs = qs.filter(auth_token=auth_token)
        elif inventory_number:
            qs = qs.filter(equipment__inventory_number=inventory_number)
        elif mac_address:
            qs = qs.filter(mac_address__iexact=mac_address)
        else:
            # Нет идентификаторов для поиска
            return None

        # Дополнительная фильтрация по IP, если он передан
        if ip_address:
            qs = qs.filter(ip_address=ip_address)

        # Получаем запись
        credentials = qs.first()

        if credentials:
            # Если был передан пароль, обязательно проверяем его
            if password is not None:
                if not credentials.check_password(password):
                    logger.warning(
                        f'Неверный пароль при попытке авторизации устройства: {credentials.equipment.inventory_number}'
                    )
                    return None

            # Авторизация успешна
            credentials.record_auth()
            return credentials.equipment

        # Если устройство не найдено
        logger.warning(
            f'Попытка авторизации провалена (устройство не найдено или неактивно). '
            f'Входные данные: inv={inventory_number}, mac={mac_address}, ip={ip_address}, token={auth_token}'
        )
        return None
