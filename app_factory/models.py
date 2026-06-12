from django.core.validators import RegexValidator
from django.db import models

# ==========================================
# Справочники и Константы
# ==========================================
PRODUCT_GROUP_CZ_IDS = {
    'null': 0,
    'milk': 8,
    'bio': 17,
}

class ProductGroupChoices(models.TextChoices):
    null = 'null', 'Товарная группа не выбрана'
    milk = 'milk', 'Молочная продукция'
    bio = 'bio', 'Специализированная пищевая продукция и БАД к пище'

    @property
    def ch_group_id(self):
        return PRODUCT_GROUP_CZ_IDS.get(self.value, 0)


class PackagingLevelChoices(models.IntegerChoices):
    """Уровни упаковки для агрегации в Честном ЗНАКе"""
    UNIT = 1, 'Потребительская (Штука)'
    GROUP = 2, 'Групповая (Коробка/Блок)'
    TRANSPORT = 3, 'Транспортная (Паллет)'


class StateConditionChoices(models.TextChoices):
    not_ready_order_km = 'not_ready_order_km', 'Не готов к заказу КМ'
    ready_order_km = 'ready_order_km', 'Готов к заказу КМ'
    ready_commercialization = 'ready_commercialization', 'Готов к вводу в оборот'


class CardStateChoices(models.TextChoices):
    draft = 'draft', 'Черновик'
    on_moderation = 'on_moderation', 'На модерации'
    requires_moderation = 'requires_moderation', 'Требует модерацию'
    awaiting_signature = 'awaiting_signature', 'Ожидает подписания'
    published = 'published', 'Опубликована'
    in_archive = 'in_archive', 'В архиве'
    requires_processing = 'requires_processing', 'Требует обработки'


class ProductionBatchChoices(models.TextChoices):
    draft = 'draft', 'Черновик'
    in_progress = 'in_progress', 'В производстве'
    completed = 'completed', 'Завершен'
    cancelled = 'cancelled', 'Отменен'


# ==========================================
# Производственная структура
# ==========================================
class Workshop(models.Model):
    name = models.CharField(max_length=150, verbose_name='Наименование')
    code = models.CharField(max_length=100, unique=True, verbose_name='Код завода')
    is_active = models.BooleanField(default=True, verbose_name='Действующий')

    class Meta:
        verbose_name = 'Цех'
        verbose_name_plural = 'Цеха'
        ordering = ('code',)

    def __str__(self):
        return f'{self.name} ({self.code})'


class Line(models.Model):
    workshop = models.ForeignKey(
        Workshop, on_delete=models.PROTECT, related_name='lines', verbose_name='Цех'
    )
    name = models.CharField(max_length=150, verbose_name='Наименование')
    code = models.CharField(
        max_length=50, unique=True, help_text='Например, инвентарный номер', verbose_name='Код линии'
    )
    is_active = models.BooleanField(default=True, verbose_name='Действующая')

    class Meta:
        verbose_name = 'Производственная линия'
        verbose_name_plural = 'Производственные линии'
        ordering = ('workshop', 'code')

    def __str__(self):
        status = 'В работе' if self.is_active else 'Простаивает'
        return f'{self.name} ({self.code}) [{status}]'


# ==========================================
# Продукция и Упаковки
# ==========================================
class Product(models.Model):
    """Логическая сущность товара (без привязки к конкретному GTIN)"""
    group = models.CharField(
        max_length=50, choices=ProductGroupChoices.choices, verbose_name='Товарная группа продукта'
    )
    name = models.CharField(max_length=255, verbose_name='Наименование')
    item_condition = models.CharField(
        max_length=50, choices=StateConditionChoices.choices, verbose_name='Состояние товара'
    )
    card_status = models.CharField(
        max_length=50, choices=CardStateChoices.choices, verbose_name='Состояние карточки'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ('group', 'name')

    def __str__(self):
        status = 'Активен' if self.is_active else 'Выведен'
        return f'{self.get_group_display()} - {self.name} ({status})'

    @property
    def consumer_gtin(self):
        """Быстрый доступ к GTIN потребительской упаковки (уровень 1)"""
        packaging = self.packagings.filter(level=PackagingLevelChoices.UNIT).first()
        return packaging.gtin if packaging else None


class ProductPackaging(models.Model):
    """Физическая упаковка продукта с собственным GTIN (для агрегации)"""
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='packagings', # product.packagings.all() вернет все упаковки
        verbose_name='Продукт'
    )
    level = models.IntegerField(
        choices=PackagingLevelChoices.choices,
        verbose_name='Уровень упаковки'
    )
    name = models.CharField(
        max_length=150,
        verbose_name='Наименование упаковки',
        help_text='Например: "Бутылка 1л", "Коробка 12 шт.", "Паллет 1200 шт."'
    )
    gtin = models.CharField(
        max_length=14,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{14}$', message='GTIN должен состоять ровно из 14 цифр')],
        verbose_name='GTIN упаковки',
    )
    # Ключевое поле для агрегации: сколько единиц нижнего уровня помещается в эту упаковку
    quantity_inside = models.PositiveIntegerField(
        verbose_name='Количество в упаковке',
        help_text='Сколько штук (или коробок) помещается в эту упаковку. Для штуки = 1.'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Упаковка продукта (GTIN)'
        verbose_name_plural = 'Упаковки продукта (GTIN)'
        ordering = ('product', 'level')
        constraints = [
            # Запрещаем создавать две упаковки одного уровня для одного продукта
            models.UniqueConstraint(
                fields=['product', 'level'],
                name='unique_packaging_level_per_product'
            )
        ]

    def __str__(self):
        level_name = self.get_level_display()
        return f'{self.product.name} | {level_name} | GTIN: {self.gtin}'


class ProductSKU(models.Model):
    """Конкретная номенклатура в учётной системе производства (1С)"""
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Продукт',
        related_name='skus',
    )
    sku_code = models.CharField(
        max_length=100,
        unique=True,
        help_text='Уникальный код внутри организации (например, из 1С)',
        verbose_name='Код внутри организации'
    )
    name = models.CharField(max_length=150, verbose_name='Наименование в 1С')
    is_active = models.BooleanField(default=True, verbose_name='Используется')

    class Meta:
        verbose_name = 'Номенклатура (SKU)'
        verbose_name_plural = 'Номенклатуры (SKUs)'
        ordering = ('product', 'sku_code')

    def __str__(self):
        status = 'Исп.' if self.is_active else 'Выведен'
        return f'{self.sku_code} | {self.name} [{status}]'


# ==========================================
# Производственный процесс
# ==========================================
class ProductionBatch(models.Model):
    product_sku = models.ForeignKey(
        ProductSKU,
        on_delete=models.PROTECT,
        verbose_name='Номенклатура (SKU)',
        related_name='batches'
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.PROTECT,
        verbose_name='Производственная линия',
        related_name='batches'
    )
    batch_number_local = models.CharField(max_length=100, verbose_name='Номер внутренней производственной партии')
    batch_number_cz = models.CharField(max_length=100, blank=True, null=True, verbose_name='Номер партии в ЧЗ')

    production_datetime_start = models.DateTimeField(verbose_name='Дата и время начала выпуска')
    production_datetime_end = models.DateTimeField(verbose_name='Дата и время окончания выпуска')
    marking_datetime = models.DateTimeField(verbose_name='Дата и время начала маркировки')
    expiration_datetime = models.DateTimeField(verbose_name='Срок годности (дата и время)')

    planned_quantity = models.PositiveIntegerField(verbose_name='Плановое количество, шт.')
    produced_quantity = models.PositiveIntegerField(default=0, verbose_name='Фактическое количество, шт.')

    status = models.CharField(
        max_length=50,
        default='draft',
        choices=ProductionBatchChoices.choices,
        verbose_name='Статус'
    )

    class Meta:
        verbose_name = 'Производственная партия'
        verbose_name_plural = 'Производственные партии'
        ordering = ('-production_datetime_start',)

    def __str__(self):
        return f'Партия {self.batch_number_local} | {self.product_sku.sku_code} ({self.get_status_display()})'

    @property
    def product(self):
        return self.product_sku.product

    @property
    def gtin(self):
        """GTIN потребительской упаковки для заказа кодов маркировки"""
        return self.product.consumer_gtin

    @property
    def cz_group_code(self):
        return self.product.group

    @property
    def cz_group_id(self):
        return ProductGroupChoices(self.product.group).ch_group_id

    @property
    def cz_expiration_string(self):
        if self.expiration_datetime:
            return self.expiration_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        return None
