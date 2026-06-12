from django.db import models
from django.utils import timezone


# ==========================================
# Справочники
# ==========================================
class CodeLevelChoices(models.IntegerChoices):
    """Уровень упаковки кода (важно использовать Integer для экономии места в БД)"""
    UNIT = 1, 'Потребительская (Штука)'
    GROUP = 2, 'Групповая (Коробка/Блок)'
    TRANSPORT = 3, 'Транспортная (Паллет)'


class CodeStatusChoices(models.IntegerChoices):
    """Жизненный цикл кода маркировки"""
    PRINTING_OFFICE = 0, 'Типография'
    REQUESTED = 1, 'Запрошен у ЧЗ'
    RECEIVED = 2, 'Получен от ЧЗ (в системе)'
    PRINTED = 3, 'Напечатан'
    AGGREGATED = 4, 'Агрегирован'
    APPLIED = 5, 'Нанесён'
    INTRODUCED = 6, 'Введён в оборот'
    WRITTEN_OFF = 7, 'Списан (брак/утилизация)'


# ==========================================
# Основная модель кодов
# ==========================================
class MarkingCode(models.Model):
    """
    Таблица кодов маркировки
    """
    code = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Код маркировки (DataMatrix)'
    )
    level = models.IntegerField(
        choices=CodeLevelChoices.choices,
        default=CodeLevelChoices.UNIT,
        db_index=True,
        verbose_name='Уровень упаковки'
    )
    status = models.IntegerField(
        choices=CodeStatusChoices.choices,
        default=CodeStatusChoices.REQUESTED,
        db_index=True,
        verbose_name='Статус'
    )
    batch = models.ForeignKey(
        'app_factory.ProductionBatch',
        on_delete=models.PROTECT,
        related_name='marking_codes',
        verbose_name='Производственная партия'
    )
    parent_code = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_codes',
        verbose_name='Родительский код (агрегация)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания записи')
    printed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата печати')
    aggregated_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата агрегации')

    class Meta:
        verbose_name = 'Код маркировки'
        verbose_name_plural = 'Коды маркировки'

        indexes = [
            # Индекс для быстрого поиска НЕнапечатанных кодов конкретной партии
            models.Index(
                fields=['batch'],
                condition=models.Q(status=CodeStatusChoices.RECEIVED), # ИСПРАВЛЕНО: верхний регистр
                name='idx_unprinted_codes_per_batch'
            ),
            # Индекс для быстрого поиска всех агрегированных кодов конкретного родительского кода
            models.Index(
                fields=['parent_code'],
                condition=models.Q(parent_code__isnull=False),
                name='idx_aggregated_children'
            ),
        ]

    def __str__(self):
        return f'{self.get_level_display()}: {self.code[:20]}... ({self.get_status_display()})'

    @property
    def is_aggregated(self):
        """Проверяет, агрегирован ли код (имеет родителя)"""
        return self.parent_code_id is not None

    def mark_as_printed(self):
        """Безопасное обновление статуса без полной перезаписи объекта (экономит I/O)"""
        if self.status != CodeStatusChoices.PRINTED:
            self.status = CodeStatusChoices.PRINTED
            self.printed_at = timezone.now()
            self.save(update_fields=['status', 'printed_at'])
