from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Organization(models.Model):
    """Оrganization"""
    name = models.CharField(max_length=200, verbose_name='Наименование')

    def __str__(self):
        return self.name


class ElectronicDigitalSignature(models.Model):
    """Настройки электронной цифровой подписи"""
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, verbose_name='Организация', related_name='eds_settings'
    )
    name = models.CharField(max_length=200, verbose_name='Наименование')

    is_active = models.BooleanField(default=False, verbose_name='Активна')
    serial_number = models.CharField(max_length=100, verbose_name='Серийный номер ЭЦП')
    valid_from = models.DateTimeField(blank=True, null=True, verbose_name='Действителен с')
    valid_to = models.DateTimeField(blank=True, null=True, verbose_name='Действителен по')

    # Данные берутся из самой цифровой подписи.
    activation_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата активации')
    deactivation_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата деактивации')

    class Meta:
        verbose_name = 'Электронная цифровая подпись'
        verbose_name_plural = 'Электронные цифровые подписи'
        ordering = ('-activation_date',)
        constraints = [
            models.UniqueConstraint(
                fields=['organization'],
                condition=Q(is_active=True),
                name='unique_active_eds_per_organization',
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_active:
            # Деактивируем все остальные подписи этой организации
            ElectronicDigitalSignature.objects.filter(
                organization=self.organization,
                is_active=True,
            ).exclude(pk=self.pk).update(
                is_active=False,
                deactivation_date=timezone.now()
            )
            # У текущей подписи сбрасываем дату деактивации, если она там была
            self.deactivation_date = None
        else:
            # Если мы деактивируем существующую запись, фиксируем время
            if self.pk:
                # Проверяем, была ли она активной до этого сохранения
                old_instance = ElectronicDigitalSignature.objects.filter(pk=self.pk).first()
                if old_instance and old_instance.is_active:
                    self.deactivation_date = timezone.now()

        super().save(*args, **kwargs)

    def clean(self):
        """Валидация на уровне формы/админки"""
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError({'valid_to': 'Дата окончания не может быть раньше даты начала.'})

    @property
    def is_valid_now(self):
        """Проверяем время действия подписи прямо сейчас"""
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True

    def __str__(self):
        status = "Активна" if self.is_active else "Неактивна"
        return f'{self.name} ({self.serial_number}): {status}'


class DeviceSUZManager(models.Manager):
    """Кастомный менеджер для получения активного устройства"""

    def get_active(self, organization=None):
        qs = self.filter(is_active=True)
        if organization:
            qs = qs.filter(organization=organization)
        return qs.first()


class DeviceSUZ(models.Model):
    """Устройство СУЗ (Система Управления Заказами)"""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        verbose_name='Организация',
        related_name='suz_devices'
    )
    name = models.CharField(max_length=100, verbose_name='Наименование')  # Увеличил до 100 для надежности
    is_active = models.BooleanField(default=False, verbose_name='Активно')
    oms_id = models.CharField(max_length=100, verbose_name='OMS ID')
    connection_id = models.CharField(max_length=100, verbose_name='Идентификатор соединения')

    current_dynamic_token = models.CharField(max_length=255, verbose_name='Текущий динамический токен')
    token_is_valid_until = models.DateTimeField(verbose_name='Токен действителен до')

    objects = DeviceSUZManager()

    class Meta:
        verbose_name = 'Устройство СУЗ'
        verbose_name_plural = 'Устройства СУЗ'
        ordering = ('-id',)
        constraints = [
            models.UniqueConstraint(
                fields=['organization'],
                condition=Q(is_active=True),
                name='unique_active_suz_per_organization',
            )
        ]

    def save(self, *args, **kwargs):
        if self.is_active:
            # Деактивируем другие устройства
            DeviceSUZ.objects.filter(
                organization=self.organization,
                is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)

        super().save(*args, **kwargs)

    @property
    def is_token_valid(self):
        """Проверяет валидность токена"""
        return timezone.now() < self.token_is_valid_until

    def __str__(self):
        active_status = 'Да' if self.is_active else 'Нет'
        token_status = 'Да' if self.is_token_valid else 'Нет'

        return (
            f'{self.name} ({self.oms_id}) | Активно: {active_status} | '
            f'Токен валиден: {token_status}'
        )
